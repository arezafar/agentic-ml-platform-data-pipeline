"""
H2O AutoML Training Template

Template for training ML models using H2O AutoML with:
- Feature Store integration
- MOJO export
- Model Registry registration
- Performance logging

Customize the configuration and feature selection for your use case.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import h2o
from h2o.automl import H2OAutoML


# =============================================================================
# CONFIGURATION
# =============================================================================

class AutoMLConfig:
    """Configuration for H2O AutoML training."""
    
    def __init__(
        self,
        project_name: str,
        target_column: str,
        max_runtime_secs: int = 3600,
        max_models: int = 20,
        seed: int = 42,
        nfolds: int = 5,
        sort_metric: str = 'AUTO',
        exclude_algos: Optional[list[str]] = None,
        include_algos: Optional[list[str]] = None,
        stopping_metric: str = 'AUTO',
        stopping_rounds: int = 3,
        stopping_tolerance: float = 0.001,
    ):
        self.project_name = project_name
        self.target_column = target_column
        self.max_runtime_secs = max_runtime_secs
        self.max_models = max_models
        self.seed = seed
        self.nfolds = nfolds
        self.sort_metric = sort_metric
        self.exclude_algos = exclude_algos
        self.include_algos = include_algos
        self.stopping_metric = stopping_metric
        self.stopping_rounds = stopping_rounds
        self.stopping_tolerance = stopping_tolerance
        
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'project_name': self.project_name,
            'target_column': self.target_column,
            'max_runtime_secs': self.max_runtime_secs,
            'max_models': self.max_models,
            'seed': self.seed,
            'nfolds': self.nfolds,
            'sort_metric': self.sort_metric,
            'exclude_algos': self.exclude_algos,
            'include_algos': self.include_algos,
        }


# =============================================================================
# H2O INITIALIZATION
# =============================================================================

def initialize_h2o(
    max_mem_size: str = '4G',
    nthreads: int = -1,
) -> None:
    """Initialize H2O cluster.
    
    Args:
        max_mem_size: Maximum memory for H2O (e.g., '4G', '8G')
        nthreads: Number of threads (-1 = all available)
    """
    h2o.init(
        max_mem_size=max_mem_size,
        nthreads=nthreads,
    )
    print(f"H2O cluster initialized: {h2o.cluster().show_status()}")


def shutdown_h2o() -> None:
    """Shutdown H2O cluster."""
    h2o.cluster().shutdown()


# =============================================================================
# DATA LOADING
# =============================================================================

def load_features_from_store(
    entity_ids: list[str],
    feature_set: str,
    feature_version: str = '1.0.0',
) -> h2o.H2OFrame:
    """Load features from PostgreSQL Feature Store.
    
    Args:
        entity_ids: List of entity IDs to load
        feature_set: Name of the feature set
        feature_version: Version of features to load
        
    Returns:
        H2OFrame with features
    """
    import asyncio
    import asyncpg
    import pandas as pd
    
    async def fetch_features():
        conn = await asyncpg.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', 5432)),
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
        )
        try:
            rows = await conn.fetch("""
                SELECT 
                    e.external_id,
                    f.features,
                    f.computed_at
                FROM feature_store.features f
                JOIN feature_store.entities e ON f.entity_id = e.id
                WHERE e.id = ANY($1::uuid[])
                  AND f.feature_set = $2
                  AND f.feature_version = $3
                  AND f.valid_to IS NULL
                ORDER BY f.computed_at DESC
            """, entity_ids, feature_set, feature_version)
            
            # Flatten JSONB features into columns
            records = []
            for row in rows:
                record = {'entity_id': row['external_id']}
                record.update(row['features'])
                records.append(record)
            
            return pd.DataFrame(records)
        finally:
            await conn.close()
    
    df = asyncio.run(fetch_features())
    return h2o.H2OFrame(df)


def load_dataframe(df: 'pandas.DataFrame') -> h2o.H2OFrame:
    """Convert pandas DataFrame to H2OFrame.
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        H2OFrame
    """
    return h2o.H2OFrame(df)


# =============================================================================
# AUTOML TRAINING
# =============================================================================

def train_automl(
    train_frame: h2o.H2OFrame,
    config: AutoMLConfig,
    validation_frame: Optional[h2o.H2OFrame] = None,
    leaderboard_frame: Optional[h2o.H2OFrame] = None,
    ignored_columns: Optional[list[str]] = None,
) -> H2OAutoML:
    """Train models using H2O AutoML.
    
    Args:
        train_frame: Training data
        config: AutoML configuration
        validation_frame: Optional validation data
        leaderboard_frame: Optional leaderboard data for final ranking
        ignored_columns: Columns to ignore during training
        
    Returns:
        Trained H2OAutoML object
    """
    # Identify feature and target columns
    y = config.target_column
    x = [col for col in train_frame.columns if col != y]
    
    if ignored_columns:
        x = [col for col in x if col not in ignored_columns]
    
    # Determine if classification or regression
    if train_frame[y].isfactor()[0]:
        print(f"Classification task detected for target '{y}'")
    else:
        print(f"Regression task detected for target '{y}'")
    
    # Build AutoML configuration
    aml_kwargs = {
        'max_runtime_secs': config.max_runtime_secs,
        'max_models': config.max_models,
        'seed': config.seed,
        'nfolds': config.nfolds,
        'sort_metric': config.sort_metric,
        'stopping_metric': config.stopping_metric,
        'stopping_rounds': config.stopping_rounds,
        'stopping_tolerance': config.stopping_tolerance,
        'project_name': config.project_name,
    }
    
    if config.exclude_algos:
        aml_kwargs['exclude_algos'] = config.exclude_algos
    if config.include_algos:
        aml_kwargs['include_algos'] = config.include_algos
    
    # Initialize and train
    aml = H2OAutoML(**aml_kwargs)
    
    aml.train(
        x=x,
        y=y,
        training_frame=train_frame,
        validation_frame=validation_frame,
        leaderboard_frame=leaderboard_frame,
    )
    
    print(f"\nAutoML training complete. Models trained: {len(aml.leaderboard)}")
    print("\nLeaderboard:")
    print(aml.leaderboard.head(10))
    
    return aml


# =============================================================================
# MODEL EXPORT
# =============================================================================

def export_mojo(
    model: h2o.estimators.H2OEstimator,
    output_dir: str,
    model_name: Optional[str] = None,
) -> Path:
    """Export model as MOJO artifact.
    
    Args:
        model: Trained H2O model
        output_dir: Directory to save MOJO
        model_name: Optional custom name (default: model ID)
        
    Returns:
        Path to exported MOJO file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Export MOJO
    mojo_path = model.save_mojo(path=str(output_path), force=True)
    
    # Rename if custom name provided
    if model_name:
        original = Path(mojo_path)
        new_path = output_path / f"{model_name}.zip"
        original.rename(new_path)
        mojo_path = str(new_path)
    
    print(f"MOJO exported to: {mojo_path}")
    
    # Also export genmodel JAR for inference
    genmodel_path = h2o.download_genmodel(
        path=str(output_path),
        model=model,
    )
    print(f"GenModel JAR: {genmodel_path}")
    
    return Path(mojo_path)


# =============================================================================
# MODEL REGISTRATION
# =============================================================================

def register_model(
    model: h2o.estimators.H2OEstimator,
    mojo_path: Path,
    config: AutoMLConfig,
    version: str = '1.0.0',
) -> dict[str, Any]:
    """Register model in the Model Registry.
    
    Args:
        model: Trained H2O model
        mojo_path: Path to MOJO artifact
        config: Training configuration
        version: Model version string
        
    Returns:
        Registration metadata
    """
    import asyncio
    import asyncpg
    import uuid
    
    # Extract model metadata
    model_id = str(uuid.uuid4())
    model_type = type(model).__name__.replace('Estimator', '')
    
    # Get performance metrics
    metrics = {}
    try:
        perf = model.model_performance()
        if hasattr(perf, 'auc'):
            metrics['auc'] = perf.auc()
        if hasattr(perf, 'rmse'):
            metrics['rmse'] = perf.rmse()
        if hasattr(perf, 'logloss'):
            metrics['logloss'] = perf.logloss()
        if hasattr(perf, 'mean_per_class_error'):
            metrics['mean_per_class_error'] = perf.mean_per_class_error()
    except Exception:
        pass
    
    # Get hyperparameters
    hyperparams = {}
    try:
        hyperparams = model.get_params()
    except Exception:
        pass
    
    registration = {
        'id': model_id,
        'name': config.project_name,
        'version': version,
        'model_type': model_type,
        'framework': 'h2o',
        'artifact_path': str(mojo_path.absolute()),
        'hyperparameters': hyperparams,
        'metrics': metrics,
        'config': config.to_dict(),
        'created_at': datetime.now().isoformat(),
    }
    
    async def save_registration():
        conn = await asyncpg.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=int(os.environ.get('DB_PORT', 5432)),
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
        )
        try:
            # Insert model
            await conn.execute("""
                INSERT INTO model_registry.models 
                    (id, name, version, model_type, framework, artifact_path, hyperparameters)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            """, 
                uuid.UUID(model_id),
                config.project_name,
                version,
                model_type,
                'h2o',
                str(mojo_path.absolute()),
                json.dumps(hyperparams),
            )
            
            # Insert metrics
            for metric_name, metric_value in metrics.items():
                await conn.execute("""
                    INSERT INTO model_registry.model_metrics 
                        (model_id, metric_name, metric_value)
                    VALUES ($1, $2, $3)
                """, uuid.UUID(model_id), metric_name, metric_value)
            
            print(f"Model registered: {model_id}")
        finally:
            await conn.close()
    
    try:
        asyncio.run(save_registration())
    except Exception as e:
        print(f"Warning: Could not register model in database: {e}")
    
    return registration


# =============================================================================
# MAIN TRAINING PIPELINE
# =============================================================================

def run_training_pipeline(
    train_data: 'pandas.DataFrame',
    target_column: str,
    project_name: str,
    output_dir: str = './models',
    max_runtime_secs: int = 3600,
    max_models: int = 20,
    test_data: Optional['pandas.DataFrame'] = None,
) -> dict[str, Any]:
    """Run complete AutoML training pipeline.
    
    Args:
        train_data: Training DataFrame
        target_column: Name of target column
        project_name: Name for the project
        output_dir: Directory for model artifacts
        max_runtime_secs: Maximum training time
        max_models: Maximum number of models to train
        test_data: Optional test DataFrame
        
    Returns:
        Pipeline results including model path and metrics
    """
    # Initialize
    initialize_h2o()
    
    try:
        # Configure
        config = AutoMLConfig(
            project_name=project_name,
            target_column=target_column,
            max_runtime_secs=max_runtime_secs,
            max_models=max_models,
        )
        
        # Load data
        train_frame = load_dataframe(train_data)
        test_frame = load_dataframe(test_data) if test_data is not None else None
        
        # Train
        aml = train_automl(
            train_frame=train_frame,
            config=config,
            leaderboard_frame=test_frame,
        )
        
        # Get leader model
        leader = aml.leader
        print(f"\nLeader model: {leader.model_id}")
        
        # Export MOJO
        mojo_path = export_mojo(
            model=leader,
            output_dir=output_dir,
            model_name=f"{project_name}_v1",
        )
        
        # Register
        registration = register_model(
            model=leader,
            mojo_path=mojo_path,
            config=config,
        )
        
        return {
            'success': True,
            'leader_model': leader.model_id,
            'mojo_path': str(mojo_path),
            'registration': registration,
            'leaderboard': aml.leaderboard.as_data_frame().to_dict(),
        }
        
    finally:
        # Cleanup
        shutdown_h2o()


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == '__main__':
    import pandas as pd
    
    # Example: Create sample classification data
    from sklearn.datasets import make_classification
    
    X, y = make_classification(
        n_samples=1000,
        n_features=20,
        n_informative=10,
        n_redundant=5,
        random_state=42,
    )
    
    df = pd.DataFrame(X, columns=[f'feature_{i}' for i in range(20)])
    df['target'] = y
    
    # Run training
    result = run_training_pipeline(
        train_data=df,
        target_column='target',
        project_name='example_classifier',
        output_dir='./models/example',
        max_runtime_secs=120,  # 2 minutes for demo
        max_models=5,
    )
    
    print("\nTraining complete!")
    print(f"MOJO path: {result['mojo_path']}")
