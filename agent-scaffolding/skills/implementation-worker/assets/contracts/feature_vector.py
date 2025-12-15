"""
Feature Vector Contract - DEV-01-02

This module defines the shared Pydantic models that serve as
contracts between Producer (Mage ETL) and Consumer (FastAPI).

The Pattern:
    Both sides import from this shared module.
    Changes to the contract are immediately visible to both.
    CI validates that serialized output matches input expectations.

TDD Task:
    Contract tests should verify:
    1. Mage serializes data matching FeatureVector schema
    2. FastAPI can deserialize without ValidationError
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class FeatureVector(BaseModel):
    """
    Shared contract for feature data exchange.
    
    This model is used by:
    - Mage ETL: Serializing features after transformation
    - FastAPI: Deserializing features for inference
    
    The schema-on-read flexibility of JSONB is preserved
    through the `dynamic_features` field.
    """
    
    model_config = ConfigDict(
        # Allow extra fields for forward compatibility
        extra="allow",
        # Use enum values for JSON serialization
        use_enum_values=True,
        # Validate on assignment
        validate_assignment=True,
    )
    
    # Entity Identity
    entity_id: UUID = Field(
        ...,
        description="Unique entity identifier"
    )
    
    entity_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Entity category: user, product, session"
    )
    
    # Temporal Context
    event_timestamp: datetime = Field(
        ...,
        description="When the event occurred"
    )
    
    # Static Features (Known schema)
    country_code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=3,
        description="ISO country code"
    )
    
    segment: Optional[str] = Field(
        None,
        max_length=50,
        description="Business segment"
    )
    
    # Dynamic Features (Flexible schema)
    dynamic_features: Dict[str, Any] = Field(
        default_factory=dict,
        description="Schema-on-read feature signals"
    )
    
    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Ensure entity_type is lowercase for consistency."""
        return v.lower().strip()
    
    def to_model_input(self) -> Dict[str, Any]:
        """
        Convert to flat dictionary for ML model input.
        
        Merges static and dynamic features into a single dict.
        """
        base = {
            "entity_id": str(self.entity_id),
            "entity_type": self.entity_type,
            "event_timestamp": self.event_timestamp.isoformat(),
            "country_code": self.country_code,
            "segment": self.segment,
        }
        base.update(self.dynamic_features)
        return base


class FeatureBatch(BaseModel):
    """Batch of feature vectors for bulk operations."""
    
    features: List[FeatureVector] = Field(
        ...,
        min_length=1,
        description="List of feature vectors"
    )
    
    batch_id: Optional[str] = Field(
        None,
        description="Optional batch identifier for tracking"
    )
    
    def to_model_inputs(self) -> List[Dict[str, Any]]:
        """Convert batch to list of model input dicts."""
        return [f.to_model_input() for f in self.features]


class PredictionRequest(BaseModel):
    """
    Request schema for inference endpoint.
    
    Used by FastAPI to validate incoming prediction requests.
    """
    
    model_config = ConfigDict(extra="forbid")
    
    features: FeatureVector = Field(
        ...,
        description="Feature vector for prediction"
    )
    
    model_name: Optional[str] = Field(
        None,
        description="Specific model to use (default: production)"
    )
    
    include_explanation: bool = Field(
        False,
        description="Include SHAP/feature importance"
    )


class PredictionResponse(BaseModel):
    """
    Response schema for inference endpoint.
    
    Standardized response format for all predictions.
    """
    
    prediction: Union[float, int, str, List[float]] = Field(
        ...,
        description="Model prediction (type depends on model)"
    )
    
    probability: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Prediction confidence (for classification)"
    )
    
    model_id: str = Field(
        ...,
        description="ID of the model that made the prediction"
    )
    
    model_version: str = Field(
        ...,
        description="Version of the model"
    )
    
    latency_ms: float = Field(
        ...,
        ge=0,
        description="Inference latency in milliseconds"
    )
    
    explanation: Optional[Dict[str, float]] = Field(
        None,
        description="Feature importance scores"
    )


class TrainingDataExport(BaseModel):
    """
    Contract for training data snapshots.
    
    Used when Mage exports data for H2O training.
    Includes metadata for reproducibility.
    """
    
    snapshot_timestamp: datetime = Field(
        ...,
        description="Point-in-time for this snapshot"
    )
    
    entity_type: str = Field(
        ...,
        description="Entity type filter"
    )
    
    record_count: int = Field(
        ...,
        ge=0,
        description="Number of records in snapshot"
    )
    
    features: List[FeatureVector] = Field(
        ...,
        description="Training data records"
    )
    
    feature_columns: List[str] = Field(
        ...,
        description="List of feature column names"
    )
    
    target_column: str = Field(
        ...,
        description="Name of the target variable"
    )


class ModelMetrics(BaseModel):
    """
    Contract for model performance metrics.
    
    Stored in model_registry.metrics JSONB column.
    """
    
    primary_metric: str = Field(
        ...,
        description="Name of primary evaluation metric"
    )
    
    primary_value: float = Field(
        ...,
        description="Value of primary metric"
    )
    
    # Common metrics
    auc: Optional[float] = Field(None, ge=0, le=1)
    accuracy: Optional[float] = Field(None, ge=0, le=1)
    precision: Optional[float] = Field(None, ge=0, le=1)
    recall: Optional[float] = Field(None, ge=0, le=1)
    f1: Optional[float] = Field(None, ge=0, le=1)
    rmse: Optional[float] = Field(None, ge=0)
    mae: Optional[float] = Field(None, ge=0)
    
    # All metrics as dict for flexibility
    all_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="All computed metrics"
    )
