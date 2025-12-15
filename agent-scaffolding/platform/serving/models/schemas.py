"""
Job 1: Pydantic Data Contracts

Strict schema definitions for API requests and responses.
Follows the Development View: /app/models is reserved for data contracts only.

These schemas enforce type safety BEFORE data reaches the predictor,
catching malformed requests early and generating OpenAPI docs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator


# =============================================================================
# Request Models
# =============================================================================

class PredictionFeatures(BaseModel):
    """
    Input features for prediction.
    
    This is a flexible model that accepts any numeric/string features.
    For production, define explicit fields matching your model.
    """
    
    class Config:
        extra = "allow"  # Allow additional fields
    
    @validator('*', pre=True)
    def coerce_types(cls, v):
        """Coerce string numbers to float."""
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return v
        return v


class PredictionRequest(BaseModel):
    """Single prediction request."""
    
    features: Dict[str, Any] = Field(
        ...,
        description="Feature dictionary for prediction",
        example={"feature_1": 1.5, "feature_2": 2.3, "category": "A"}
    )
    request_id: Optional[str] = Field(
        None,
        description="Optional client-provided request ID for tracking"
    )
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Prediction options (e.g., return_probabilities)"
    )


class BatchPredictionRequest(BaseModel):
    """Batch prediction request for multiple records."""
    
    records: List[Dict[str, Any]] = Field(
        ...,
        description="List of feature dictionaries",
        min_items=1,
        max_items=1000,
    )
    request_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)


# =============================================================================
# Response Models
# =============================================================================

class PredictionResult(BaseModel):
    """Single prediction result."""
    
    prediction: Union[int, float, str] = Field(
        ...,
        description="Predicted class or value"
    )
    probabilities: Optional[Dict[str, float]] = Field(
        None,
        description="Class probabilities (for classification)"
    )
    confidence: Optional[float] = Field(
        None,
        description="Prediction confidence score"
    )


class PredictionResponse(BaseModel):
    """API response for prediction endpoint."""
    
    status: str = Field("success", description="Request status")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    predictions: List[PredictionResult] = Field(
        ...,
        description="List of predictions"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response metadata"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "request_id": "req_12345",
                "predictions": [
                    {
                        "prediction": 1,
                        "probabilities": {"class_0": 0.15, "class_1": 0.85},
                        "confidence": 0.85
                    }
                ],
                "metadata": {
                    "model_version": "v1.2.0",
                    "latency_ms": 12.5,
                    "cache_hit": False
                }
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field("healthy", description="Service status")
    version: str = Field(..., description="API version")
    model_loaded: bool = Field(..., description="Model availability")
    cache_connected: bool = Field(..., description="Redis availability")
    database_connected: bool = Field(..., description="Database availability")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )


class ModelReloadRequest(BaseModel):
    """Request to reload model (hot-swap)."""
    
    model_path: Optional[str] = Field(
        None,
        description="Path to new MOJO file (uses default if not provided)"
    )
    invalidate_cache: bool = Field(
        True,
        description="Whether to invalidate prediction cache"
    )


class ModelReloadResponse(BaseModel):
    """Response for model reload."""
    
    status: str
    previous_version: str
    new_version: str
    cache_invalidated: int = 0
    reload_time_ms: float


class ErrorResponse(BaseModel):
    """Standard error response."""
    
    status: str = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
