"""
Mage Dynamic Block Pattern - PROC-02-01

This module implements the Process View pattern for parallel training
execution using Mage's dynamic block fan-out mechanism.

The Pattern:
    A parent block yields a list of metadata dictionaries.
    Mage's orchestrator spawns N parallel child blocks.
    Each child receives one metadata item.

Key Constraints:
    - Limit concurrency to prevent H2O cluster overload
    - Implement time-series walk-forward splits correctly
    - Ensure max(train_date) < min(test_date) for each split

TDD Task:
    Write test_dynamic_fanout.py that:
    1. Mocks upstream data
    2. Asserts the block returns correct nested list structure
    3. Validates temporal splits are non-overlapping
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json


@dataclass
class TrainingSplitConfig:
    """Configuration for a single training split."""
    split_id: str
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    segment: Optional[str] = None
    h2o_config: Optional[Dict[str, Any]] = None
    
    def validate(self) -> bool:
        """Ensure train end is before test start (no data leakage)."""
        return self.train_end < self.test_start
    
    def to_metadata(self) -> Dict[str, Any]:
        """Convert to Mage-compatible metadata dictionary."""
        return {
            "block_uuid": f"train_split_{self.split_id}",
            "split_config": {
                "split_id": self.split_id,
                "train_start": self.train_start.isoformat(),
                "train_end": self.train_end.isoformat(),
                "test_start": self.test_start.isoformat(),
                "test_end": self.test_end.isoformat(),
                "segment": self.segment,
                "h2o_config": self.h2o_config or {}
            }
        }


def generate_walk_forward_splits(
    start_date: datetime,
    end_date: datetime,
    train_window: timedelta,
    test_window: timedelta,
    step_size: Optional[timedelta] = None,
    segments: Optional[List[str]] = None
) -> List[TrainingSplitConfig]:
    """
    Generate time-series walk-forward validation splits.
    
    Walk-Forward Validation:
        Standard cross-validation leaks future data in time-series.
        Walk-forward ensures all training data precedes test data.
    
    Example:
        Split 1: Train Jan, Test Feb
        Split 2: Train Jan-Feb, Test Mar
        Split 3: Train Jan-Mar, Test Apr
    
    Args:
        start_date: Beginning of data range
        end_date: End of data range
        train_window: Size of training window
        test_window: Size of test window
        step_size: How much to advance each split (default: test_window)
        segments: Optional list of segments to create splits for
        
    Returns:
        List of TrainingSplitConfig objects
    """
    if step_size is None:
        step_size = test_window
    
    splits = []
    split_id = 0
    current_train_end = start_date + train_window
    
    segments = segments or [None]  # Default to single segment
    
    while current_train_end + test_window <= end_date:
        test_start = current_train_end
        test_end = test_start + test_window
        
        for segment in segments:
            split = TrainingSplitConfig(
                split_id=f"{split_id:03d}_{segment or 'all'}",
                train_start=start_date,  # Expanding window
                train_end=current_train_end,
                test_start=test_start,
                test_end=test_end,
                segment=segment
            )
            
            # Validate temporal integrity
            assert split.validate(), f"Invalid split: train_end >= test_start"
            splits.append(split)
        
        split_id += 1
        current_train_end += step_size
    
    return splits


def generate_rolling_splits(
    start_date: datetime,
    end_date: datetime,
    train_window: timedelta,
    test_window: timedelta,
    step_size: Optional[timedelta] = None
) -> List[TrainingSplitConfig]:
    """
    Generate rolling window splits (fixed-size training window).
    
    Unlike walk-forward, each split has the same training window size.
    
    Example:
        Split 1: Train Jan, Test Feb
        Split 2: Train Feb, Test Mar
        Split 3: Train Mar, Test Apr
    """
    if step_size is None:
        step_size = test_window
    
    splits = []
    split_id = 0
    current_start = start_date
    
    while current_start + train_window + test_window <= end_date:
        train_end = current_start + train_window
        test_start = train_end
        test_end = test_start + test_window
        
        split = TrainingSplitConfig(
            split_id=f"rolling_{split_id:03d}",
            train_start=current_start,  # Rolling window
            train_end=train_end,
            test_start=test_start,
            test_end=test_end
        )
        
        splits.append(split)
        split_id += 1
        current_start += step_size
    
    return splits


# Mage Block Template
"""
# dynamic_training_fanout.py - Mage Custom Block

@custom
def generate_training_splits(data, *args, **kwargs):
    '''
    Dynamic block that generates parallel training configurations.
    
    This block returns a list of metadata dictionaries.
    Mage spawns one child block per item.
    
    metadata.yaml:
        dynamic: true
        executor_config:
            max_concurrency: 4  # Prevent H2O overload
    '''
    from mage_dynamic_block import generate_walk_forward_splits
    from datetime import datetime, timedelta
    
    # Extract date range from data
    min_date = data['event_timestamp'].min()
    max_date = data['event_timestamp'].max()
    
    # Generate splits
    splits = generate_walk_forward_splits(
        start_date=min_date,
        end_date=max_date,
        train_window=timedelta(days=30),
        test_window=timedelta(days=7),
        segments=data['segment'].unique().tolist()
    )
    
    # Return metadata list for dynamic block fan-out
    return [split.to_metadata() for split in splits]
"""


# Child Block Template
"""
# train_split.py - Mage Custom Block (Child of dynamic block)

@custom
def train_model_split(data, *args, **kwargs):
    '''
    Trains a model on a specific temporal split.
    
    Receives split_config from parent dynamic block.
    '''
    split_config = kwargs.get('split_config', {})
    
    train_start = datetime.fromisoformat(split_config['train_start'])
    train_end = datetime.fromisoformat(split_config['train_end'])
    test_start = datetime.fromisoformat(split_config['test_start'])
    test_end = datetime.fromisoformat(split_config['test_end'])
    
    # Filter data
    train_data = data[
        (data['event_timestamp'] >= train_start) &
        (data['event_timestamp'] < train_end)
    ]
    
    if split_config.get('segment'):
        train_data = train_data[train_data['segment'] == split_config['segment']]
    
    # Validate no data leakage
    assert train_data['event_timestamp'].max() < test_start
    
    # Train model...
    return {'split_id': split_config['split_id'], 'model_path': '...'}
"""


def validate_splits_no_leakage(splits: List[TrainingSplitConfig]) -> bool:
    """
    Validate that all splits maintain temporal integrity.
    
    Returns True if all splits have train_end < test_start.
    """
    for split in splits:
        if not split.validate():
            return False
    return True


def estimate_parallel_jobs(
    splits: List[TrainingSplitConfig],
    max_concurrency: int
) -> Dict[str, Any]:
    """
    Estimate resource requirements for parallel training.
    
    Use this to configure executor_config in metadata.yaml.
    """
    total_splits = len(splits)
    batches = (total_splits + max_concurrency - 1) // max_concurrency
    
    return {
        "total_splits": total_splits,
        "max_concurrency": max_concurrency,
        "estimated_batches": batches,
        "splits_per_batch": min(total_splits, max_concurrency)
    }
