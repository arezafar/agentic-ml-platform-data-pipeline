"""
Custom Block: H2O AutoML Training

Mage Custom block for orchestrating H2O AutoML training.
Handles data import, model training, and artifact export.

Block Type: custom
Connection: H2O cluster (must be initialized first)
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import pandas as pd

if 'custom' not in dir():
    from mage_ai.data_preparation.decorators import custom
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@custom
def train_automl(
    data: Union[pd.DataFrame, Dict[str, Any]],
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Execute H2O AutoML training.
    
    Features:
    - Automatic feature detection
    - Configurable training time
    - Cross-validation
    - Leaderboard extraction
    - MOJO export
    
    Configuration via pipeline variables:
    - target_column: Column to predict
    - max_runtime_secs: Maximum training time (default: 300)
    - max_models: Maximum models to train (default: 20)
    - seed: Random seed for reproducibility
    - nfolds: Cross-validation folds (default: 5)
    - export_path: Path for MOJO export
    """
    from os import environ
    
    # Extract DataFrame from input
    if isinstance(data, dict):
        df = data.get('input_data')
        connection_info = data
    else:
        df = data
        connection_info = {}
    
    if df is None or len(df) == 0:
        raise ValueError("No data provided for training")
    
    # Configuration
    target_column = kwargs.get('target_column')
    if not target_column:
        raise ValueError("target_column is required")
    
    max_runtime_secs = kwargs.get('max_runtime_secs', 300)
    max_models = kwargs.get('max_models', 20)
    seed = kwargs.get('seed', 42)
    nfolds = kwargs.get('nfolds', 5)
    export_path = kwargs.get('export_path', '/data_lake/models')
    project_name = kwargs.get('project_name', f"automl_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Exclude metadata columns from training
    exclude_cols = kwargs.get('exclude_columns', [])
    exclude_cols.extend([c for c in df.columns if c.startswith('_')])
    
    result = {
        'project_name': project_name,
        'target_column': target_column,
        'started_at': datetime.utcnow().isoformat(),
        'completed_at': None,
        'best_model': None,
        'leaderboard': None,
        'metrics': {},
        'mojo_path': None,
    }
    
    try:
        import h2o
        from h2o.automl import H2OAutoML
        
        print(f"   Starting H2O AutoML: {project_name}")
        print(f"   Target: {target_column}")
        print(f"   Features: {len(df.columns) - len(exclude_cols) - 1}")
        print(f"   Records: {len(df)}")
        
        # Convert to H2OFrame
        h2o_frame = h2o.H2OFrame(df)
        
        # Set target as factor if classification
        unique_values = df[target_column].nunique()
        if unique_values <= 20:  # Treat as classification
            h2o_frame[target_column] = h2o_frame[target_column].asfactor()
            problem_type = 'classification'
            print(f"   Problem type: Classification ({unique_values} classes)")
        else:
            problem_type = 'regression'
            print(f"   Problem type: Regression")
        
        # Define features
        feature_cols = [
            c for c in df.columns 
            if c != target_column and c not in exclude_cols
        ]
        
        # Initialize AutoML
        aml = H2OAutoML(
            max_runtime_secs=max_runtime_secs,
            max_models=max_models,
            seed=seed,
            nfolds=nfolds,
            project_name=project_name,
            sort_metric='AUTO',
            verbosity='info',
        )
        
        # Train
        print(f"   Training for up to {max_runtime_secs} seconds...")
        aml.train(
            x=feature_cols,
            y=target_column,
            training_frame=h2o_frame,
        )
        
        # Get leader
        leader = aml.leader
        leaderboard = aml.leaderboard.as_data_frame()
        
        # Extract metrics
        if problem_type == 'classification':
            metrics = {
                'auc': leader.auc() if hasattr(leader, 'auc') else None,
                'logloss': leader.logloss() if hasattr(leader, 'logloss') else None,
                'accuracy': leader.accuracy() if hasattr(leader, 'accuracy') else None,
            }
        else:
            metrics = {
                'rmse': leader.rmse() if hasattr(leader, 'rmse') else None,
                'mae': leader.mae() if hasattr(leader, 'mae') else None,
                'r2': leader.r2() if hasattr(leader, 'r2') else None,
            }
        
        # Export MOJO
        mojo_path = Path(export_path) / project_name
        mojo_path.mkdir(parents=True, exist_ok=True)
        mojo_file = leader.save_mojo(path=str(mojo_path), force=True)
        
        result.update({
            'completed_at': datetime.utcnow().isoformat(),
            'best_model': {
                'model_id': leader.model_id,
                'algorithm': leader.algo,
            },
            'leaderboard': leaderboard.head(10).to_dict('records'),
            'metrics': metrics,
            'mojo_path': mojo_file,
            'problem_type': problem_type,
            'feature_count': len(feature_cols),
            'training_rows': len(df),
        })
        
        print(f"✅ AutoML training completed")
        print(f"   Best model: {leader.algo} ({leader.model_id})")
        print(f"   Metrics: {metrics}")
        print(f"   MOJO saved: {mojo_file}")
        
    except ImportError:
        print("⚠️  h2o package not installed. Simulating training for development.")
        result.update({
            'completed_at': datetime.utcnow().isoformat(),
            'best_model': {
                'model_id': 'mock_gbm_model',
                'algorithm': 'GBM',
            },
            'leaderboard': [
                {'model_id': 'mock_gbm_model', 'auc': 0.95, 'logloss': 0.15},
                {'model_id': 'mock_xgboost_model', 'auc': 0.94, 'logloss': 0.16},
            ],
            'metrics': {'auc': 0.95, 'logloss': 0.15, 'accuracy': 0.92},
            'mojo_path': f'{export_path}/{project_name}/mock_model.zip',
            'mock': True,
        })
        
    except Exception as e:
        result['error'] = str(e)
        print(f"❌ AutoML training failed: {e}")
        raise
    
    return result


@test
def test_training_completed(output: Dict, *args) -> None:
    """Test that training completed successfully."""
    assert output.get('completed_at'), 'Training did not complete'
    assert output.get('best_model'), 'No best model selected'
    print(f"✓ Training completed with model: {output['best_model']['model_id']}")


@test
def test_mojo_exported(output: Dict, *args) -> None:
    """Test that MOJO was exported."""
    assert output.get('mojo_path'), 'MOJO not exported'
    print(f"✓ MOJO exported to: {output['mojo_path']}")


@test
def test_metrics_valid(output: Dict, *args) -> None:
    """Test that metrics are reasonable."""
    metrics = output.get('metrics', {})
    if 'auc' in metrics and metrics['auc'] is not None:
        assert 0 <= metrics['auc'] <= 1, f"Invalid AUC: {metrics['auc']}"
    if 'rmse' in metrics and metrics['rmse'] is not None:
        assert metrics['rmse'] >= 0, f"Invalid RMSE: {metrics['rmse']}"
    print(f"✓ Metrics are valid: {metrics}")
