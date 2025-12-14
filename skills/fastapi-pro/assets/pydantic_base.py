"""
Pydantic Base Models

Foundational Pydantic models and patterns for the API including:
- Base model configurations
- Common field types
- Validation patterns
- Response wrappers
"""

from datetime import datetime
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# BASE CONFIGURATIONS
# =============================================================================

class StrictModel(BaseModel):
    """Base model with strict validation.
    
    Use for request bodies where we want to reject unknown fields.
    """
    model_config = ConfigDict(
        strict=True,
        extra='forbid',
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class FlexibleModel(BaseModel):
    """Base model with flexible validation.
    
    Use for response bodies or internal models.
    """
    model_config = ConfigDict(
        extra='ignore',
        validate_assignment=True,
        from_attributes=True,  # Allows ORM model conversion
    )


# =============================================================================
# COMMON FIELD TYPES
# =============================================================================

class EntityReference(StrictModel):
    """Reference to an entity in the system."""
    
    entity_id: UUID = Field(..., description="Unique entity identifier")
    entity_type: str = Field(..., description="Type of entity")
    
    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        """Validate entity type is non-empty."""
        if not v or not v.strip():
            raise ValueError("entity_type cannot be empty")
        return v.strip().lower()


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class AuditMixin(TimestampMixin):
    """Mixin for audit fields."""
    
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


# =============================================================================
# RESPONSE WRAPPERS
# =============================================================================

DataT = TypeVar('DataT')


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper.
    
    Provides consistent response format across all endpoints.
    """
    
    success: bool = True
    data: Optional[DataT] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @classmethod
    def ok(cls, data: DataT, message: Optional[str] = None) -> 'APIResponse[DataT]':
        """Create a successful response."""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error(cls, message: str) -> 'APIResponse[None]':
        """Create an error response."""
        return cls(success=False, data=None, message=message)


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated response for list endpoints."""
    
    items: list[DataT]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1, le=1000)
    has_next: bool
    has_prev: bool
    
    @classmethod
    def create(
        cls,
        items: list[DataT],
        total: int,
        page: int,
        page_size: int,
    ) -> 'PaginatedResponse[DataT]':
        """Create paginated response with computed fields."""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
            has_prev=page > 1,
        )


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    code: str = Field(..., description="Error code for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    field: Optional[str] = Field(None, description="Field that caused the error")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error details")


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    success: bool = False
    errors: list[ErrorDetail]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# FEATURE MODELS
# =============================================================================

class FeatureValue(StrictModel):
    """Single feature value with metadata."""
    
    name: str = Field(..., min_length=1, max_length=255)
    value: Any
    data_type: Optional[str] = Field(None, description="Expected data type")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate feature name format."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Feature name must be alphanumeric with underscores/hyphens")
        return v


class FeatureSet(FlexibleModel):
    """Collection of features for an entity."""
    
    entity_id: UUID
    feature_set_name: str
    version: str = "1.0.0"
    features: dict[str, Any]
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_to: Optional[datetime] = None


# =============================================================================
# MODEL REGISTRY MODELS
# =============================================================================

class ModelInfo(FlexibleModel):
    """Model information from registry."""
    
    id: UUID
    name: str
    version: str
    model_type: str
    framework: str = "h2o"
    artifact_path: str
    status: str = "registered"
    created_at: datetime
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate model status."""
        valid_statuses = {'registered', 'staging', 'production', 'archived'}
        if v.lower() not in valid_statuses:
            raise ValueError(f"Status must be one of: {valid_statuses}")
        return v.lower()


class ModelMetrics(FlexibleModel):
    """Model performance metrics."""
    
    model_id: UUID
    metric_name: str
    metric_value: float
    dataset_partition: Optional[str] = None
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# PREDICTION MODELS
# =============================================================================

class PredictionInput(StrictModel):
    """Input for prediction request."""
    
    entity_id: Optional[str] = None
    features: dict[str, Any] = Field(
        ...,
        min_length=1,
        description="Feature name to value mapping",
    )
    model_version: Optional[str] = Field(
        None,
        description="Specific model version to use (default: production)",
    )
    
    @field_validator('features')
    @classmethod
    def validate_features(cls, v: dict) -> dict:
        """Validate feature dictionary."""
        if not v:
            raise ValueError("Features cannot be empty")
        
        # Check for None values
        for key, value in v.items():
            if value is None:
                raise ValueError(f"Feature '{key}' has null value")
        
        return v


class PredictionOutput(FlexibleModel):
    """Output from prediction."""
    
    prediction_id: UUID
    entity_id: Optional[str] = None
    prediction: Any
    probabilities: Optional[list[float]] = None
    confidence: Optional[float] = None
    model_id: UUID
    model_version: str
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
