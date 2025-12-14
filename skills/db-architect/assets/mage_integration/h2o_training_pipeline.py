"""
H2O AutoML Training Pipeline Template

Mage pipeline for automated H2O model training with model registry integration.
Implements the full MLOps lifecycle from data extraction to model deployment.

Pipeline Stages:
1. Extract training data from PostgreSQL (with type enforcement)
2. Export to shared volume (zero-copy pattern)
3. Execute H2O AutoML training
4. Register model in h2o_intelligence.model_registry
5. Store metrics history for drift detection

Sensor: Triggered by data drift or row count threshold
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

# =============================================================================
# Data Loader: Extract Training Data with Type Enforcement
# =============================================================================

def extract_training_data(*args, **kwargs) -> Dict[str, Any]:
    """
    Extract and type-cast training data from PostgreSQL.
    
    CRITICAL: H2O is sensitive to data types. 
    Columns that look numeric but contain 'N/A' will become Enum.
    This loader enforces strict typing to prevent AutoML failures.
    """
    from os import environ
    
    target_table = kwargs.get('target_table', 'training_data')
    target_schema = kwargs.get('target_schema', 'feature_store')
    sample_size = kwargs.get('sample_size', 100000)
    
    # Type-enforcing query with NULLIF and CAST
    query = f"""
        SELECT
            -- Numeric features (force NULL instead of 'N/A')
            NULLIF(feature_1, 'N/A')::FLOAT as feature_1,
            NULLIF(feature_2, 'N/A')::FLOAT as feature_2,
            COALESCE(feature_3::FLOAT, 0.0) as feature_3,
            
            -- Categorical features (ensure VARCHAR)
            COALESCE(category_1, 'unknown')::VARCHAR as category_1,
            
            -- Target variable
            target::FLOAT as target,
            
            -- Metadata (excluded from training)
            id,
            created_at
            
        FROM {target_schema}.{target_table}
        WHERE target IS NOT NULL
        ORDER BY RANDOM()
        LIMIT {sample_size}
    """
    
    # Execute query
    # df = loader.load(query)
    
    result = {
        'query': query,
        'row_count': 0,  # Placeholder
        'extracted_at': datetime.utcnow().isoformat(),
    }
    
    print(f"Extracted training data from {target_schema}.{target_table}")
    return result


# =============================================================================
# Transformer: Export to Shared Volume (Zero-Copy Pattern)
# =============================================================================

def export_to_shared_volume(data: Any, *args, **kwargs) -> Dict[str, str]:
    """
    Export DataFrame to shared Docker volume for H2O consumption.
    
    Uses PostgreSQL COPY command for high-performance export.
    H2O reads directly from the shared mount - no network transfer.
    """
    from os import environ
    
    shared_path = environ.get('DATA_EXCHANGE_PATH', '/data/exchange')
    export_filename = f"train_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    export_path = Path(shared_path) / export_filename
    
    # Using PostgreSQL COPY for maximum performance
    copy_command = f"""
        COPY ({data['query']}) 
        TO '{export_path}' 
        WITH CSV HEADER
    """
    
    # cursor.execute(copy_command)
    
    result = {
        'export_path': str(export_path),
        'format': 'csv',
        'exported_at': datetime.utcnow().isoformat(),
    }
    
    print(f"Exported data to: {export_path}")
    return result


# =============================================================================
# Custom Block: H2O AutoML Training
# =============================================================================

def train_h2o_automl(export_info: Dict, *args, **kwargs) -> Dict[str, Any]:
    """
    Execute H2O AutoML training on exported data.
    
    Key Configurations:
    - max_models: Limit number of models to train
    - max_runtime_secs: Time budget for training
    - stopping_metric: Metric for early stopping
    """
    from os import environ
    
    # Training configuration
    max_models = kwargs.get('max_models', 20)
    max_runtime_secs = kwargs.get('max_runtime_secs', 3600)
    target_column = kwargs.get('target_column', 'target')
    problem_type = kwargs.get('problem_type', 'regression')
    project_name = kwargs.get('project_name', f"automl_{datetime.now().strftime('%Y%m%d')}")
    
    # H2O connection
    h2o_url = environ.get('H2O_URL', 'http://h2o:54321')
    
    try:
        import h2o
        from h2o.automl import H2OAutoML
        
        # Initialize H2O
        h2o.init(url=h2o_url)
        
        # Import data (reads directly from shared volume)
        data_path = export_info['export_path']
        train = h2o.import_file(path=data_path)
        
        # Identify features (exclude metadata and target)
        exclude_cols = ['id', 'created_at', target_column]
        feature_cols = [c for c in train.columns if c not in exclude_cols]
        
        # Configure AutoML
        aml = H2OAutoML(
            max_models=max_models,
            max_runtime_secs=max_runtime_secs,
            seed=42,
            project_name=project_name,
            sort_metric='RMSE' if problem_type == 'regression' else 'AUC',
        )
        
        # Train
        aml.train(
            x=feature_cols,
            y=target_column,
            training_frame=train,
        )
        
        # Extract leader model
        leader = aml.leader
        leaderboard = aml.leaderboard.as_data_frame()
        
        # Export MOJO
        mojo_path = Path('/opt/h2o/models') / project_name
        mojo_path.mkdir(parents=True, exist_ok=True)
        mojo_file = leader.save_mojo(path=str(mojo_path), force=True)
        
        result = {
            'model_id': leader.model_id,
            'algorithm': leader.algo,
            'metrics': {
                'rmse': leader.rmse() if hasattr(leader, 'rmse') else None,
                'auc': leader.auc() if hasattr(leader, 'auc') else None,
                'logloss': leader.logloss() if hasattr(leader, 'logloss') else None,
            },
            'leaderboard': leaderboard.head(10).to_dict('records'),
            'mojo_path': mojo_file,
            'feature_columns': feature_cols,
            'target_column': target_column,
            'problem_type': problem_type,
            'trained_at': datetime.utcnow().isoformat(),
        }
        
        print(f"✅ AutoML training complete: {leader.model_id}")
        return result
        
    except ImportError:
        print("⚠️  H2O not available. Returning mock training result.")
        return {
            'model_id': f'mock_{project_name}_gbm',
            'algorithm': 'GBM',
            'metrics': {'rmse': 0.15, 'auc': 0.92},
            'mojo_path': f'/opt/h2o/models/{project_name}/mock_model.zip',
            'mock': True,
        }


# =============================================================================
# Data Exporter: Register Model in PostgreSQL
# =============================================================================

def register_model_in_registry(training_result: Dict, *args, **kwargs) -> Dict:
    """
    Insert trained model into h2o_intelligence.model_registry.
    Also records metrics history for drift detection.
    """
    model_id = training_result['model_id']
    algorithm = training_result['algorithm']
    metrics = training_result.get('metrics', {})
    mojo_path = training_result.get('mojo_path')
    feature_columns = training_result.get('feature_columns', [])
    target_column = training_result.get('target_column', 'target')
    problem_type = training_result.get('problem_type', 'regression')
    
    # Capabilities description for agent routing
    capabilities = (
        f"Trained {algorithm} model for {problem_type}. "
        f"Predicts {target_column} using {len(feature_columns)} features."
    )
    
    # Insert into model_registry
    insert_query = """
        INSERT INTO h2o_intelligence.model_registry (
            model_id, model_name, algorithm, problem_type,
            capabilities_description, required_features,
            validation_rmse, validation_auc, validation_logloss,
            mojo_path, version, created_at
        ) VALUES (
            %(model_id)s, %(model_name)s, %(algorithm)s, %(problem_type)s,
            %(capabilities)s, %(features)s::jsonb,
            %(rmse)s, %(auc)s, %(logloss)s,
            %(mojo_path)s, '1.0.0', NOW()
        )
        ON CONFLICT (model_id) DO UPDATE SET
            validation_rmse = EXCLUDED.validation_rmse,
            validation_auc = EXCLUDED.validation_auc,
            mojo_path = EXCLUDED.mojo_path
    """
    
    params = {
        'model_id': model_id,
        'model_name': model_id.replace('_', ' ').title(),
        'algorithm': algorithm,
        'problem_type': problem_type,
        'capabilities': capabilities,
        'features': json.dumps(feature_columns),
        'rmse': metrics.get('rmse'),
        'auc': metrics.get('auc'),
        'logloss': metrics.get('logloss'),
        'mojo_path': mojo_path,
    }
    
    # cursor.execute(insert_query, params)
    
    # Insert metrics history for drift detection
    for metric_name, metric_value in metrics.items():
        if metric_value is not None:
            history_query = """
                INSERT INTO h2o_intelligence.model_metrics_history 
                (model_id, metric_name, metric_value, dataset_name)
                VALUES (%(model_id)s, %(metric)s, %(value)s, 'training')
            """
            # cursor.execute(history_query, {'model_id': model_id, 'metric': metric_name, 'value': metric_value})
    
    print(f"✅ Model registered: {model_id}")
    
    return {
        'registered_model_id': model_id,
        'capabilities': capabilities,
        'metrics': metrics,
        'registered_at': datetime.utcnow().isoformat(),
    }


# =============================================================================
# Pipeline Configuration
# =============================================================================

PIPELINE_CONFIG = {
    'name': 'h2o_automl_training',
    'description': 'Automated H2O model training with registry integration',
    'trigger': {
        'type': 'sensor',
        'condition': 'new_data_threshold_or_drift',
    },
    'blocks': [
        {
            'name': 'extract_data',
            'type': 'data_loader',
            'function': 'extract_training_data',
        },
        {
            'name': 'export_to_volume',
            'type': 'transformer',
            'function': 'export_to_shared_volume',
            'upstream': ['extract_data'],
        },
        {
            'name': 'train_automl',
            'type': 'custom',
            'function': 'train_h2o_automl',
            'upstream': ['export_to_volume'],
        },
        {
            'name': 'register_model',
            'type': 'data_exporter',
            'function': 'register_model_in_registry',
            'upstream': ['train_automl'],
        },
    ],
}
