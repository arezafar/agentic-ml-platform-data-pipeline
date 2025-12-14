"""
Dynamic Training Fan-Out Block (Mage Custom Block)
=============================================================================
PROC-01-02: Dynamic Block for Parallel H2O Training

This block implements the "Fan-Out" pattern for horizontal scalability.
It returns a specific data structure that Mage interprets to spawn
parallel downstream tasks.

Key Patterns:
- Returns List[List[Config], List[Metadata]] to trigger dynamic execution
- Each config spawns a separate H2O training job
- H2O cluster connection with retry logic
- Robust error handling for distributed systems

Usage:
    1. Copy to your Mage project's custom/ directory
    2. Configure H2O_URL environment variable
    3. Connect upstream data loader and downstream model exporter
=============================================================================
"""

import os
import time
from typing import Any
import pandas as pd

# Conditional imports for standalone testing
if __name__ != "__main__":
    from mage_ai.data_preparation.decorators import custom
    from mage_ai.data_preparation.shared.secrets import get_secret_value
else:
    def custom(func):
        return func


# Configuration
H2O_URL = os.getenv("H2O_URL", "http://h2o-ai:54321")
MAX_RUNTIME_SECS = 3600  # 1 hour max per model
MAX_MODELS = 20
NFOLDS = 5


def connect_h2o_with_retry(max_retries: int = 5, base_delay: float = 2.0):
    """
    Connect to H2O cluster with exponential backoff.
    
    Handles:
    - Cluster not ready yet
    - Network issues
    - Split-brain recovery
    """
    import h2o
    
    for attempt in range(max_retries):
        try:
            h2o.init(url=H2O_URL, verbose=False)
            cluster_info = h2o.cluster()
            print(f"Connected to H2O cluster: {cluster_info.cloud_healthy}")
            return True
        except Exception as e:
            if attempt == max_retries - 1:
                raise ConnectionError(f"Failed to connect to H2O after {max_retries} attempts: {e}")
            delay = base_delay * (2 ** attempt)
            print(f"H2O connection attempt {attempt + 1} failed, retrying in {delay}s...")
            time.sleep(delay)
    
    return False


@custom
def dynamic_training_fanout(
    df: pd.DataFrame, 
    *args, 
    **kwargs
) -> list[list[dict[str, Any]]]:
    """
    Dynamic block that fans out training jobs based on data segments.
    
    PROC-01-02: Returns the specific structure for Mage dynamic execution:
    [[config1, config2, ...], [metadata1, metadata2, ...]]
    
    Each config will spawn a parallel downstream training block.
    
    Args:
        df: Input DataFrame with training data
        
    Returns:
        List of [configs, metadata] for parallel execution
    """
    # Define segmentation strategy
    # Option 1: By categorical column (e.g., region, product_type)
    segment_column = kwargs.get("segment_column", "region")
    
    # Option 2: By time windows for walk-forward validation
    use_temporal_split = kwargs.get("temporal_split", False)
    
    configs = []
    metadata = []
    
    if use_temporal_split:
        # SCN-01-02: Time-series walk-forward validation
        # Prevents look-ahead bias by training on past, testing on future
        time_column = kwargs.get("time_column", "event_time")
        df_sorted = df.sort_values(time_column)
        
        # Create rolling windows
        window_size = len(df_sorted) // 5  # 5 splits
        for i in range(4):  # 4 training windows
            train_end = window_size * (i + 2)
            test_start = train_end
            test_end = min(train_end + window_size, len(df_sorted))
            
            config = {
                "window_id": i,
                "train_start_idx": 0,
                "train_end_idx": train_end,
                "test_start_idx": test_start,
                "test_end_idx": test_end,
                "train_size": train_end,
                "test_size": test_end - test_start,
            }
            meta = {
                "block_uuid": f"train_window_{i}",
                "description": f"Walk-forward window {i}: train on first {train_end} rows",
            }
            configs.append(config)
            metadata.append(meta)
    else:
        # Segment-based parallel training
        if segment_column not in df.columns:
            # Fallback: single training job
            configs.append({
                "segment": "all",
                "segment_filter": None,
                "row_count": len(df),
            })
            metadata.append({
                "block_uuid": "train_all",
                "description": "Full dataset training",
            })
        else:
            segments = df[segment_column].unique()
            for segment in segments:
                segment_df = df[df[segment_column] == segment]
                if len(segment_df) < 100:  # Skip small segments
                    continue
                
                config = {
                    "segment": str(segment),
                    "segment_column": segment_column,
                    "row_count": len(segment_df),
                }
                meta = {
                    "block_uuid": f"train_{segment}",
                    "description": f"Training for {segment_column}={segment}",
                }
                configs.append(config)
                metadata.append(meta)
    
    print(f"Created {len(configs)} parallel training configurations")
    return [configs, metadata]


@custom
def train_h2o_model(
    df: pd.DataFrame,
    dynamic_config: dict[str, Any],
    *args,
    **kwargs
) -> dict[str, Any]:
    """
    Downstream block that receives dynamic config and trains H2O model.
    
    This block is spawned multiple times in parallel by the fan-out block.
    
    Args:
        df: Full training DataFrame
        dynamic_config: Config from fan-out block
        
    Returns:
        Training results with model path and metrics
    """
    import h2o
    from h2o.automl import H2OAutoML
    
    # Connect to H2O cluster
    connect_h2o_with_retry()
    
    try:
        # Apply segment filter if specified
        if dynamic_config.get("segment_filter"):
            col = dynamic_config["segment_column"]
            val = dynamic_config["segment"]
            df = df[df[col] == val]
        elif dynamic_config.get("train_end_idx"):
            # Temporal split
            df = df.iloc[
                dynamic_config["train_start_idx"]:dynamic_config["train_end_idx"]
            ]
        
        # Convert to H2O Frame
        hf = h2o.H2OFrame(df)
        
        # Define target and features
        target = kwargs.get("target_column", "target")
        features = [c for c in hf.columns if c != target]
        
        # Configure AutoML
        aml = H2OAutoML(
            max_runtime_secs=MAX_RUNTIME_SECS,
            max_models=MAX_MODELS,
            nfolds=NFOLDS,
            seed=42,
            project_name=f"automl_{dynamic_config.get('segment', 'all')}",
            exclude_algos=["DeepLearning"],  # Skip slow algorithms
            sort_metric="AUC" if hf[target].isfactor()[0] else "RMSE",
        )
        
        # Train
        aml.train(x=features, y=target, training_frame=hf)
        
        # Get best model
        leader = aml.leader
        model_id = leader.model_id
        
        # Export MOJO
        model_path = os.getenv("MODEL_OUTPUT_PATH", "/models")
        segment_name = dynamic_config.get("segment", "all")
        mojo_path = leader.save_mojo(
            path=f"{model_path}/staging/{segment_name}",
            force=True
        )
        
        # Collect metrics
        metrics = {
            "model_id": model_id,
            "segment": segment_name,
            "mojo_path": mojo_path,
            "algorithm": leader.algo,
        }
        
        # Add performance metrics
        if hf[target].isfactor()[0]:
            metrics["auc"] = leader.auc()
            metrics["logloss"] = leader.logloss()
        else:
            metrics["rmse"] = leader.rmse()
            metrics["mae"] = leader.mae()
        
        return metrics
        
    finally:
        # Cleanup H2O frames
        h2o.remove_all()


# Test harness
if __name__ == "__main__":
    import pandas as pd
    
    # Create test data
    test_df = pd.DataFrame({
        "region": ["US", "EU", "US", "EU", "APAC"] * 100,
        "feature_a": range(500),
        "feature_b": range(500, 1000),
        "target": [0, 1] * 250,
    })
    
    result = dynamic_training_fanout(test_df)
    print(f"Configs: {result[0]}")
    print(f"Metadata: {result[1]}")
