"""
Contracts Package - Development View (DEV)

This package contains shared Pydantic models that serve as
contracts between Mage (Producer) and FastAPI (Consumer).

Key Contracts:
- FeatureVector: Core feature data exchange
- PredictionRequest/Response: Inference API contracts
- TrainingDataExport: Training snapshot format
- ModelMetrics: Performance metrics schema

Usage:
    # In Mage block
    from contracts import FeatureVector, TrainingDataExport
    
    # In FastAPI endpoint
    from contracts import PredictionRequest, PredictionResponse
"""

from .feature_vector import (
    FeatureVector,
    FeatureBatch,
    PredictionRequest,
    PredictionResponse,
    TrainingDataExport,
    ModelMetrics,
)

__all__ = [
    "FeatureVector",
    "FeatureBatch",
    "PredictionRequest",
    "PredictionResponse",
    "TrainingDataExport",
    "ModelMetrics",
]
