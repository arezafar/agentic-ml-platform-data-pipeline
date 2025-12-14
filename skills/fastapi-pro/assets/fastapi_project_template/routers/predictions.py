"""
Predictions Router

Handles ML prediction requests including:
- Single predictions
- Batch predictions
- Prediction feedback logging
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class FeatureVector(BaseModel):
    """Input features for prediction."""
    
    entity_id: Optional[str] = Field(
        None,
        description="Optional entity identifier for tracking"
    )
    features: dict[str, Any] = Field(
        ...,
        description="Feature name to value mapping"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "user_123",
                "features": {
                    "age": 35,
                    "income": 75000,
                    "credit_score": 720,
                }
            }
        }


class PredictionResponse(BaseModel):
    """Prediction result."""
    
    prediction_id: str = Field(
        ...,
        description="Unique prediction identifier"
    )
    entity_id: Optional[str] = Field(
        None,
        description="Entity identifier if provided"
    )
    prediction: Any = Field(
        ...,
        description="Model prediction (class label or numeric value)"
    )
    probabilities: Optional[list[float]] = Field(
        None,
        description="Class probabilities for classification"
    )
    confidence: Optional[float] = Field(
        None,
        description="Prediction confidence score"
    )
    model_version: str = Field(
        ...,
        description="Version of the model used"
    )
    latency_ms: float = Field(
        ...,
        description="Prediction latency in milliseconds"
    )
    timestamp: str = Field(
        ...,
        description="Prediction timestamp (ISO format)"
    )


class BatchPredictionRequest(BaseModel):
    """Batch prediction request."""
    
    instances: list[FeatureVector] = Field(
        ...,
        description="List of feature vectors to score",
        min_length=1,
        max_length=1000,
    )


class BatchPredictionResponse(BaseModel):
    """Batch prediction result."""
    
    batch_id: str = Field(..., description="Unique batch identifier")
    predictions: list[PredictionResponse] = Field(..., description="Individual predictions")
    total_latency_ms: float = Field(..., description="Total batch latency")
    count: int = Field(..., description="Number of predictions")


class FeedbackRequest(BaseModel):
    """Prediction feedback for model monitoring."""
    
    prediction_id: str = Field(..., description="Original prediction ID")
    actual_value: Any = Field(..., description="Actual observed value")
    feedback_type: str = Field(
        default="outcome",
        description="Type of feedback (outcome, correction, etc.)"
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/predict",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
)
async def predict(
    request: Request,
    feature_vector: FeatureVector,
) -> PredictionResponse:
    """Make a single prediction.
    
    Args:
        request: FastAPI request object
        feature_vector: Input features for prediction
        
    Returns:
        Prediction result with metadata
        
    Raises:
        HTTPException: If prediction fails
    """
    start_time = time.perf_counter()
    prediction_id = str(uuid.uuid4())
    
    try:
        # Get MOJO scorer from app state
        scorer = getattr(request.app.state, 'mojo_scorer', None)
        
        if scorer is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model scorer not available",
            )
        
        # Make prediction
        result = scorer.predict(feature_vector.features)
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        response = PredictionResponse(
            prediction_id=prediction_id,
            entity_id=feature_vector.entity_id,
            prediction=result.get('prediction'),
            probabilities=result.get('probability'),
            confidence=max(result.get('probability', [0.5])) if result.get('probability') else None,
            model_version=result.get('model_id', 'unknown'),
            latency_ms=round(latency_ms, 2),
            timestamp=datetime.utcnow().isoformat(),
        )
        
        # Log prediction asynchronously (fire and forget)
        # In production, use background task or message queue
        logger.info(
            f"Prediction {prediction_id}: entity={feature_vector.entity_id}, "
            f"result={result.get('prediction')}, latency={latency_ms:.2f}ms"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}",
        )


@router.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_200_OK,
)
async def predict_batch(
    request: Request,
    batch_request: BatchPredictionRequest,
) -> BatchPredictionResponse:
    """Make batch predictions.
    
    Args:
        request: FastAPI request object
        batch_request: Batch of feature vectors
        
    Returns:
        Batch prediction results
        
    Raises:
        HTTPException: If batch prediction fails
    """
    start_time = time.perf_counter()
    batch_id = str(uuid.uuid4())
    
    try:
        predictions = []
        
        for feature_vector in batch_request.instances:
            # Reuse single prediction logic
            pred_response = await predict(request, feature_vector)
            predictions.append(pred_response)
        
        total_latency_ms = (time.perf_counter() - start_time) * 1000
        
        return BatchPredictionResponse(
            batch_id=batch_id,
            predictions=predictions,
            total_latency_ms=round(total_latency_ms, 2),
            count=len(predictions),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}",
        )


@router.post(
    "/feedback",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_feedback(
    request: Request,
    feedback: FeedbackRequest,
) -> dict[str, str]:
    """Submit feedback for a prediction.
    
    Used for:
    - Model monitoring and drift detection
    - Ground truth collection
    - Retraining data collection
    
    Args:
        request: FastAPI request object
        feedback: Feedback data
        
    Returns:
        Acknowledgment message
    """
    try:
        # Log feedback to database
        pool = getattr(request.app.state, 'db_pool', None)
        
        if pool:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO serving.prediction_feedback 
                        (prediction_id, actual_value, feedback_type, submitted_at)
                    VALUES ($1, $2::jsonb, $3, NOW())
                    ON CONFLICT (prediction_id) DO UPDATE
                    SET actual_value = EXCLUDED.actual_value,
                        feedback_type = EXCLUDED.feedback_type,
                        submitted_at = NOW()
                """, 
                    uuid.UUID(feedback.prediction_id),
                    feedback.actual_value,
                    feedback.feedback_type,
                )
        
        logger.info(f"Feedback received for prediction {feedback.prediction_id}")
        
        return {"status": "accepted", "prediction_id": feedback.prediction_id}
        
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit feedback",
        )


@router.get(
    "/models",
    response_model=dict[str, Any],
)
async def list_models(request: Request) -> dict[str, Any]:
    """List available models.
    
    Returns:
        Available models and their status
    """
    try:
        pool = getattr(request.app.state, 'db_pool', None)
        
        if not pool:
            return {"models": [], "count": 0}
        
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT name, version, model_type, status, created_at
                FROM model_registry.models
                WHERE status IN ('staging', 'production')
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            models = [
                {
                    "name": row['name'],
                    "version": row['version'],
                    "type": row['model_type'],
                    "status": row['status'],
                    "created_at": row['created_at'].isoformat(),
                }
                for row in rows
            ]
        
        return {"models": models, "count": len(models)}
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve models",
        )
