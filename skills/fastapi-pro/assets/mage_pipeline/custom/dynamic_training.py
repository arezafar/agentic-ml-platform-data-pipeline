"""
Job 2: Dynamic Training Blocks - Fan-Out Controller

Mage pipeline block that returns configuration lists to spawn
parallel H2O AutoML training jobs.

This implements the Map-Reduce pattern:
1. Parent block queries feature store and returns param lists
2. Mage spawns N parallel child blocks (one per config)
3. Reduction step selects leader model

Success Criteria:
- Parallel model training without manual DAG duplication
- Resource-efficient fan-out with Celery executor
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def generate_training_configs(*args, **kwargs) -> List[Dict[str, Any]]:
    """
    Parent block: Generate training configurations for fan-out.
    
    Returns a list of dictionaries where each dictionary spawns
    a parallel downstream training block.
    
    This enables hyperparameter grid search without manual DAG setup.
    """
    from os import environ
    
    # Base configuration
    base_config = {
        'target_column': kwargs.get('target_column', 'target'),
        'sort_metric': kwargs.get('sort_metric', environ.get('PRIMARY_METRIC', 'AUC')),
        'seed': kwargs.get('seed', 42),
        'nfolds': kwargs.get('nfolds', 5),
    }
    
    # Define hyperparameter grid
    max_depths = kwargs.get('max_depths', [5, 10, 15])
    max_runtimes = kwargs.get('max_runtimes', [1800, 3600])  # 30min, 60min
    
    configs = []
    
    for depth in max_depths:
        for runtime in max_runtimes:
            config = {
                **base_config,
                'config_id': f"depth_{depth}_runtime_{runtime}",
                'max_runtime_secs': runtime,
                'stopping_metric': 'AUTO',
                'stopping_rounds': 3,
                'stopping_tolerance': 0.001,
                'max_depth': depth,
            }
            configs.append(config)
    
    print(f"[DYNAMIC-BLOCKS] Generated {len(configs)} training configurations")
    print(f"[DYNAMIC-BLOCKS] Configs: {[c['config_id'] for c in configs]}")
    
    # Return list - Mage will spawn parallel blocks
    return configs


def train_with_config(config: Dict[str, Any], data: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Child block: Execute single training job with specific config.
    
    This block is spawned in parallel for each config returned
    by generate_training_configs.
    """
    from os import environ
    
    config_id = config.get('config_id', 'unknown')
    print(f"[TRAIN-CHILD] Starting training for: {config_id}")
    
    try:
        import h2o
        from h2o.automl import H2OAutoML
        
        h2o_url = environ.get('H2O_URL', 'http://h2o-ai:54321')
        h2o.init(url=h2o_url)
        
        # Get H2O frame
        hf = data.get('h2o_frame')
        if hf is None:
            raise ValueError("No H2O frame provided")
        
        target = config['target_column']
        x = [c for c in hf.columns if c != target and 'id' not in c.lower()]
        
        # Initialize AutoML with specific config
        aml = H2OAutoML(
            max_runtime_secs=config['max_runtime_secs'],
            max_models=20,
            seed=config['seed'],
            nfolds=config['nfolds'],
            sort_metric=config['sort_metric'],
            stopping_metric=config.get('stopping_metric', 'AUTO'),
            stopping_rounds=config.get('stopping_rounds', 3),
            stopping_tolerance=config.get('stopping_tolerance', 0.001),
            project_name=f"automl_{config_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        )
        
        # Train
        start_time = datetime.utcnow()
        aml.train(x=x, y=target, training_frame=hf)
        training_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Get leader
        leader = aml.leader
        lb = aml.leaderboard.as_data_frame()
        
        print(f"[TRAIN-CHILD] ✅ {config_id} complete: {leader.model_id}")
        
        return {
            'config_id': config_id,
            'config': config,
            'leader_id': leader.model_id,
            'leader_metrics': lb.iloc[0].to_dict(),
            'models_trained': len(lb),
            'training_duration_secs': training_duration,
            'automl': aml,
            'leader': leader,
        }
        
    except ImportError:
        print(f"[TRAIN-CHILD] ⚠️ H2O not available. Mock result for {config_id}")
        import random
        return {
            'config_id': config_id,
            'config': config,
            'leader_id': f'mock_{config_id}_GBM_1',
            'leader_metrics': {'auc': round(random.uniform(0.75, 0.95), 4)},
            'models_trained': 10,
            'mock': True,
        }


def select_leader(training_results: List[Dict[str, Any]], *args, **kwargs) -> Dict[str, Any]:
    """
    Reduction block: Select the best model across all parallel runs.
    
    Called after all child blocks complete.
    """
    sort_metric = kwargs.get('sort_metric', 'auc').lower()
    
    print(f"[REDUCTION] Selecting leader from {len(training_results)} training runs")
    
    # Sort by metric (descending for AUC, ascending for loss metrics)
    ascending = 'loss' in sort_metric or 'error' in sort_metric
    sorted_results = sorted(
        training_results,
        key=lambda x: x.get('leader_metrics', {}).get(sort_metric, 0),
        reverse=not ascending,
    )
    
    leader = sorted_results[0]
    
    print(f"[REDUCTION] ✅ Leader: {leader['leader_id']}")
    print(f"[REDUCTION] {sort_metric}: {leader['leader_metrics'].get(sort_metric)}")
    
    return {
        'leader': leader,
        'all_results': [
            {
                'config_id': r['config_id'],
                'leader_id': r['leader_id'],
                'metric': r['leader_metrics'].get(sort_metric),
            }
            for r in sorted_results
        ],
        'selected_at': datetime.utcnow().isoformat(),
    }


if __name__ == '__main__':
    # Test config generation
    configs = generate_training_configs()
    print(json.dumps(configs, indent=2))
