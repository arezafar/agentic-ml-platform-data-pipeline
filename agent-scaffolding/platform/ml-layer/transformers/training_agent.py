"""
Job 2: Training Agent - H2O Cluster Orchestration

Specialized Mage Transformer Block designated as the "Training Agent".
Initializes connection to remote H2O Docker container and converts
local DataFrames to H2OFrame objects for distributed processing.

Success Criteria:
- Connection to H2O cluster is stable
- Data is successfully transferred to H2O memory
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def training_agent(data: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    The Training Agent: Orchestrates H2O cluster for model training.
    
    This block acts as the bridge between Mage's pipeline orchestration
    and H2O's distributed compute capabilities.
    
    Responsibilities:
    1. Initialize and validate H2O cluster connection
    2. Convert DataFrame to H2OFrame
    3. Configure training parameters
    4. Execute AutoML and return leaderboard
    
    Args:
        data: Output from data ingestion block
        
    Returns:
        Dictionary with H2O training results
    """
    from os import environ
    
    h2o_url = kwargs.get('h2o_url', environ.get('H2O_URL', 'http://h2o-ai:54321'))
    
    print(f"[TRAINING-AGENT] Initializing H2O connection: {h2o_url}")
    
    # Step 1: Connect to H2O cluster
    h2o_connection = _connect_to_h2o(h2o_url)
    
    if not h2o_connection['connected']:
        raise Exception(f"Failed to connect to H2O: {h2o_connection.get('error')}")
    
    print(f"[TRAINING-AGENT] ✅ Connected to H2O cluster")
    print(f"[TRAINING-AGENT] Cluster info: {h2o_connection.get('cluster_info', {})}")
    
    # Step 2: Convert DataFrame to H2OFrame
    h2o_data = _convert_to_h2o_frame(data, kwargs)
    
    if h2o_data.get('error'):
        raise Exception(f"Failed to convert data: {h2o_data['error']}")
    
    print(f"[TRAINING-AGENT] ✅ H2OFrame created: {h2o_data.get('frame_id')}")
    
    # Step 3: Execute AutoML training
    training_config = {
        'target_column': kwargs.get('target_column', 'target'),
        'max_runtime_secs': kwargs.get('max_runtime_secs', int(environ.get('MAX_RUNTIME_SECS', 3600))),
        'max_models': kwargs.get('max_models', 20),
        'sort_metric': kwargs.get('sort_metric', environ.get('PRIMARY_METRIC', 'AUC')),
        'seed': kwargs.get('seed', 42),
        'nfolds': kwargs.get('nfolds', 5),
    }
    
    print(f"[TRAINING-AGENT] Training config: {json.dumps(training_config, indent=2)}")
    
    training_result = _execute_automl(h2o_data, training_config)
    
    # Step 4: Return comprehensive result
    result = {
        'h2o_connection': h2o_connection,
        'h2o_frame': h2o_data,
        'training_result': training_result,
        'config': training_config,
        'trained_at': datetime.utcnow().isoformat(),
    }
    
    return result


def _connect_to_h2o(url: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Connect to H2O cluster with retry logic.
    
    Uses the URL configured in docker-compose networking.
    Default: http://h2o-ai:54321
    """
    import time
    
    try:
        import h2o
        
        for attempt in range(max_retries):
            try:
                h2o.init(url=url, nthreads=-1)
                
                # Validate connection
                cluster_info = h2o.cluster()
                
                return {
                    'connected': True,
                    'url': url,
                    'cluster_info': {
                        'version': h2o.__version__,
                        'cloud_name': cluster_info.cloud_name if hasattr(cluster_info, 'cloud_name') else 'unknown',
                    },
                }
                
            except Exception as e:
                print(f"[TRAINING-AGENT] Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
        
        return {'connected': False, 'error': 'Max retries exceeded'}
        
    except ImportError:
        return {'connected': False, 'error': 'H2O library not installed', 'mock': True}


def _convert_to_h2o_frame(data: Dict[str, Any], config: Dict) -> Dict[str, Any]:
    """
    Convert local DataFrame to H2OFrame for distributed processing.
    """
    try:
        import h2o
        import pandas as pd
        
        # Get or create DataFrame
        df = data.get('dataframe')
        if df is None:
            return {'error': 'No dataframe provided'}
        
        if isinstance(df, list):
            df = pd.DataFrame(df)
        
        # Clean column names (H2O requirement)
        df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]
        
        # Convert to H2OFrame
        print(f"[TRAINING-AGENT] Converting {len(df)} rows to H2OFrame...")
        hf = h2o.H2OFrame(df)
        
        # Handle target column encoding
        target_column = config.get('target_column', 'target')
        problem_type = config.get('problem_type', 'classification')
        
        if problem_type == 'classification' and target_column in hf.columns:
            hf[target_column] = hf[target_column].asfactor()
        
        return {
            'h2o_frame': hf,
            'frame_id': hf.frame_id,
            'nrows': hf.nrows,
            'ncols': hf.ncols,
            'columns': hf.columns,
        }
        
    except ImportError:
        return {
            'mock': True,
            'frame_id': 'mock_frame',
            'nrows': data.get('row_count', 0),
            'ncols': len(data.get('columns', [])),
            'columns': data.get('columns', []),
        }


def _execute_automl(h2o_data: Dict, config: Dict) -> Dict[str, Any]:
    """
    Execute H2O AutoML with configured constraints.
    
    Monitor progress via H2O Flow UI exposed at port 54321.
    """
    try:
        import h2o
        from h2o.automl import H2OAutoML
        
        hf = h2o_data.get('h2o_frame')
        if hf is None:
            return {'error': 'No H2OFrame available', 'mock': True}
        
        target = config['target_column']
        
        # Define predictors (exclude target and ID columns)
        x = [c for c in hf.columns if c != target and 'id' not in c.lower()]
        y = target
        
        print(f"[TRAINING-AGENT] AutoML: {len(x)} predictors -> {y}")
        print(f"[TRAINING-AGENT] Max runtime: {config['max_runtime_secs']}s")
        print(f"[TRAINING-AGENT] Max models: {config['max_models']}")
        
        # Initialize AutoML
        aml = H2OAutoML(
            max_models=config['max_models'],
            max_runtime_secs=config['max_runtime_secs'],
            seed=config['seed'],
            nfolds=config['nfolds'],
            sort_metric=config['sort_metric'],
            project_name=f"automl_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        
        # Execute training
        start_time = datetime.utcnow()
        aml.train(x=x, y=y, training_frame=hf)
        end_time = datetime.utcnow()
        
        training_duration = (end_time - start_time).total_seconds()
        
        # Extract leaderboard
        lb = aml.leaderboard.as_data_frame()
        
        # Get leader model
        leader = aml.leader
        
        print(f"[TRAINING-AGENT] ✅ Training complete in {training_duration:.1f}s")
        print(f"[TRAINING-AGENT] Best model: {leader.model_id}")
        
        return {
            'automl': aml,
            'leader': leader,
            'leader_id': leader.model_id,
            'leaderboard': lb.head(10).to_dict('records'),
            'models_trained': len(lb),
            'training_duration_secs': training_duration,
            'predictors': x,
        }
        
    except ImportError:
        return _mock_automl_result()


def _mock_automl_result() -> Dict[str, Any]:
    """Return mock AutoML result for testing."""
    return {
        'mock': True,
        'leader_id': 'mock_GBM_1',
        'leaderboard': [
            {'model_id': 'mock_GBM_1', 'auc': 0.89},
            {'model_id': 'mock_XGBoost_1', 'auc': 0.88},
        ],
        'models_trained': 15,
        'training_duration_secs': 300.0,
    }


if __name__ == '__main__':
    mock_data = {
        'dataframe': [{'feature_1': 1, 'target': 0}, {'feature_1': 2, 'target': 1}],
        'row_count': 2,
        'columns': ['feature_1', 'target'],
    }
    result = training_agent(mock_data)
    print(json.dumps({k: v for k, v in result.items() if k not in ['h2o_frame', 'automl', 'leader']}, indent=2, default=str))
