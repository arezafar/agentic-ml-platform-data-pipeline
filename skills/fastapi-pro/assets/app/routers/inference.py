"""
Job 1: Inference Router

High-performance prediction endpoints with async patterns.
Implements the look-aside cache and thread pool offloading.

Endpoints:
- POST /predict - Single prediction
- POST /predict/batch - Batch predictions
"""

from datetime import datetime
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.concurrency import run_in_threadpool

from ..models.schemas import (
    PredictionRequest,
    BatchPredictionRequest,
    PredictionResponse,
    PredictionResult,
    ErrorResponse,
)
from ..core.mojo_predictor import get_predictor, MojoPredictor
from ..core.redis_cache import get_cache, RedisCache

router = APIRouter(prefix="/predict", tags=["inference"])


async def get_predictor_dep() -> MojoPredictor:
    """Dependency to get predictor instance."""
    try:
        return get_predictor()
    except RuntimeError:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Service initializing."
        )


async def get_cache_dep() -> RedisCache:
    """Dependency to get cache instance."""
    return await get_cache()


@router.post(
    "",
    response_model=PredictionResponse,
    responses={
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    summary="Single Prediction",
    description="Score a single record against the deployed model."
)
async def predict(
    request: PredictionRequest,
    predictor: MojoPredictor = Depends(get_predictor_dep),
    cache: RedisCache = Depends(get_cache_dep),
) -> PredictionResponse:
    """
    High-performance single prediction endpoint.
    
    Flow:
    1. Generate cache key from features
    2. Check Redis cache (async, non-blocking)
    3. If miss, offload to thread pool
    4. Write-back to cache (async)
    5. Return response
    """
    request_id = request.request_id or datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    start_time = datetime.utcnow()
    
    # Generate cache key
    cache_key = predictor.generate_cache_key(request.features)
    
    # Check cache (async, non-blocking)
    cached_result = await cache.get(cache_key)
    
    if cached_result:
        # Cache hit - return immediately (<5ms)
        return PredictionResponse(
            status="success",
            request_id=request_id,
            predictions=[PredictionResult(
                prediction=cached_result['predictions'][0].get('predict', 0),
                probabilities={
                    'class_0': cached_result['predictions'][0].get('p0', 0),
                    'class_1': cached_result['predictions'][0].get('p1', 0),
                },
                confidence=max(
                    cached_result['predictions'][0].get('p0', 0),
                    cached_result['predictions'][0].get('p1', 0),
                ),
            )],
            metadata={
                'model_version': cached_result.get('model_version', 'unknown'),
                'latency_ms': (datetime.utcnow() - start_time).total_seconds() * 1000,
                'cache_hit': True,
            }
        )
    
    # Cache miss - offload to thread pool
    # This prevents event loop blocking for CPU-bound inference
    result = await predictor.predict_async(request.features)
    
    end_time = datetime.utcnow()
    total_latency_ms = (end_time - start_time).total_seconds() * 1000
    
    # Write-back to cache (async, non-blocking)
    await cache.set(cache_key, result)
    
    # Format response
    predictions = []
    for pred in result.get('predictions', []):
        predictions.append(PredictionResult(
            prediction=pred.get('predict', 0),
            probabilities={
                'class_0': pred.get('p0', 0),
                'class_1': pred.get('p1', 0),
            } if 'p0' in pred else None,
            confidence=max(pred.get('p0', 0), pred.get('p1', 0)) if 'p0' in pred else None,
        ))
    
    return PredictionResponse(
        status="success",
        request_id=request_id,
        predictions=predictions,
        metadata={
            'model_version': result.get('model_version', 'unknown'),
            'latency_ms': round(total_latency_ms, 2),
            'inference_latency_ms': result.get('latency_ms', 0),
            'cache_hit': False,
            'runtime': result.get('runtime', 'unknown'),
        }
    )


@router.post(
    "/batch",
    response_model=PredictionResponse,
    summary="Batch Prediction",
    description="Score multiple records in a single request."
)
async def predict_batch(
    request: BatchPredictionRequest,
    predictor: MojoPredictor = Depends(get_predictor_dep),
) -> PredictionResponse:
    """
    Batch prediction for multiple records.
    
    Offloads entire batch to thread pool for efficiency.
    Caching is skipped for batch requests (too many keys).
    """
    request_id = request.request_id or datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    start_time = datetime.utcnow()
    
    # Offload batch to thread pool
    result = await predictor.predict_async(request.records)
    
    end_time = datetime.utcnow()
    total_latency_ms = (end_time - start_time).total_seconds() * 1000
    
    # Format response
    predictions = []
    for pred in result.get('predictions', []):
        predictions.append(PredictionResult(
            prediction=pred.get('predict', 0),
            probabilities={
                'class_0': pred.get('p0', 0),
                'class_1': pred.get('p1', 0),
            } if 'p0' in pred else None,
            confidence=max(pred.get('p0', 0), pred.get('p1', 0)) if 'p0' in pred else None,
        ))
    
    return PredictionResponse(
        status="success",
        request_id=request_id,
        predictions=predictions,
        metadata={
            'model_version': result.get('model_version', 'unknown'),
            'latency_ms': round(total_latency_ms, 2),
            'record_count': len(request.records),
            'cache_hit': False,
        }
    )
