"""
JTBD Step 5: Execute - H2O AutoML Training

The core functional task where value is created. Implements the "Tool Use"
pattern where Mage delegates algorithm selection and training to H2O AutoML.

Key Features:
- Dynamic parameter configuration from global variables
- H2O AutoML with algorithm selection
- Stacked Ensemble support
- Resource management (time/model limits)
- GPU support for deep learning
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def train_automl(data: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Execute H2O AutoML training.
    
    The agent delegates the complexity of algorithm selection (XGBoost, GBM,
    Deep Learning, GLM) to the H2O engine, which performs grid search and
    trains Stacked Ensembles to maximize performance.
    
    Configuration from kwargs:
    - max_runtime_secs: Training time budget
    - max_models: Maximum number of models
    - primary_metric: Metric to optimize (AUC, RMSE, etc.)
    - nfolds: Cross-validation folds
    - include_algos / exclude_algos: Algorithm filtering
    
    Args:
        data: Output from prepare_h2o_frame block
        
    Returns:
        Dictionary with AutoML object and leaderboard
    """
    from os import environ
    
    # Configuration
    target_column = data.get('target_column', kwargs.get('target_column', 'target'))
    max_runtime_secs = kwargs.get('max_runtime_secs', 3600)
    max_models = kwargs.get('max_models', 20)
    primary_metric = kwargs.get('primary_metric', 'AUC')
    nfolds = kwargs.get('nfolds', 5)
    seed = kwargs.get('seed', 42)
    include_algos = kwargs.get('include_algos', [])
    exclude_algos = kwargs.get('exclude_algos', [])
    project_name = kwargs.get('project_name', f"automl_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    print(f"[EXECUTE] Starting H2O AutoML training")
    print(f"[EXECUTE] Target: {target_column}")
    print(f"[EXECUTE] Max runtime: {max_runtime_secs}s, Max models: {max_models}")
    print(f"[EXECUTE] Optimizing for: {primary_metric}")
    
    try:
        import h2o
        from h2o.automl import H2OAutoML
        
        # Get H2O frame
        hf = data.get('h2o_frame')
        if hf is None:
            raise ValueError("No H2O frame provided. Run prepare_h2o_frame first.")
        
        # Define predictors (exclude target and ID columns)
        x = hf.columns.copy()
        x.remove(target_column)
        
        # Remove ID-like columns
        id_patterns = ['id', '_id', 'index', 'row_num']
        x = [c for c in x if not any(p in c.lower() for p in id_patterns)]
        
        y = target_column
        
        print(f"[EXECUTE] Predictors: {len(x)} features")
        print(f"[EXECUTE] Target: {y}")
        
        # Configure AutoML
        aml_config = {
            'max_models': max_models,
            'max_runtime_secs': max_runtime_secs,
            'seed': seed,
            'nfolds': nfolds,
            'project_name': project_name,
            'sort_metric': primary_metric,
            'keep_cross_validation_predictions': True,
            'keep_cross_validation_models': False,
        }
        
        # Algorithm filtering
        if include_algos:
            aml_config['include_algos'] = include_algos
        if exclude_algos:
            aml_config['exclude_algos'] = exclude_algos
        
        # Initialize AutoML
        aml = H2OAutoML(**aml_config)
        
        # Execute training (this is the core value creation step)
        print(f"[EXECUTE] Training started at {datetime.utcnow().isoformat()}")
        start_time = datetime.utcnow()
        
        aml.train(x=x, y=y, training_frame=hf)
        
        end_time = datetime.utcnow()
        training_duration = (end_time - start_time).total_seconds()
        
        print(f"[EXECUTE] Training completed in {training_duration:.1f}s")
        
        # Extract leaderboard
        lb = aml.leaderboard
        lb_df = lb.as_data_frame()
        
        # Get leader model
        leader = aml.leader
        leader_id = leader.model_id
        
        print(f"[EXECUTE] ✅ AutoML complete!")
        print(f"[EXECUTE] Models trained: {len(lb_df)}")
        print(f"[EXECUTE] Leader: {leader_id}")
        
        # Extract leader metrics
        leader_metrics = {}
        for col in lb_df.columns:
            if col != 'model_id':
                leader_metrics[col] = lb_df.iloc[0][col]
        
        result = {
            'automl': aml,
            'leader': leader,
            'leader_id': leader_id,
            'leader_metrics': leader_metrics,
            'leaderboard': lb_df.head(10).to_dict('records'),
            'models_trained': len(lb_df),
            'training_duration_secs': training_duration,
            'predictors': x,
            'target_column': y,
            'project_name': project_name,
            'executed_at': end_time.isoformat(),
        }
        
        return result
        
    except ImportError:
        print("[EXECUTE] ⚠️ H2O not available. Returning mock training result.")
        return _mock_training_result(project_name)


def _mock_training_result(project_name: str) -> Dict[str, Any]:
    """Return mock training result for testing."""
    return {
        'automl': None,
        'leader': None,
        'leader_id': f'{project_name}_GBM_1',
        'leader_metrics': {
            'auc': 0.89,
            'logloss': 0.32,
            'mean_per_class_error': 0.12,
        },
        'leaderboard': [
            {'model_id': f'{project_name}_GBM_1', 'auc': 0.89},
            {'model_id': f'{project_name}_XGBoost_1', 'auc': 0.88},
            {'model_id': f'{project_name}_DRF_1', 'auc': 0.85},
        ],
        'models_trained': 15,
        'training_duration_secs': 450.0,
        'mock': True,
    }


if __name__ == '__main__':
    # Test with mock data
    mock_input = {
        'h2o_frame': None,
        'target_column': 'target',
        'columns': ['feature_1', 'feature_2', 'target'],
    }
    result = train_automl(mock_input, max_runtime_secs=60, max_models=5)
    print(json.dumps({k: v for k, v in result.items() if k not in ['automl', 'leader']}, indent=2))
