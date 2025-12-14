"""
Schemas Package - Logical View (LOG)

This package contains SQLAlchemy models implementing the Hybrid Feature Store
Schema from the 4+1 Architectural View Model.

Key Components:
- feature_store.py: Hybrid JSONB schema with GIN indexing
- model_registry.py: Model registry with training job linkage

Usage:
    from schemas import Base, FeatureStore, ModelRegistry
    
    # Create all tables
    Base.metadata.create_all(engine)
"""

from .feature_store import Base, FeatureStore, query_snapshot, export_training_snapshot
from .model_registry import ModelRegistry, TrainingJobLog, ModelStatus

__all__ = [
    "Base",
    "FeatureStore",
    "ModelRegistry",
    "TrainingJobLog",
    "ModelStatus",
    "query_snapshot",
    "export_training_snapshot",
]
