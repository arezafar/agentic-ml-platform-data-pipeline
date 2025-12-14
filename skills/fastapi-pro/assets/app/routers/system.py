"""
Job 3: System Router

Administrative endpoints for health checks and hot-swapping.

Endpoints:
- GET /health - Service health check
- POST /system/reload-model - Zero-downtime model swap
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header

from ..models.schemas import (
    HealthResponse,
    ModelReloadRequest,
    ModelReloadResponse,
)
from ..core.mojo_predictor import get_predictor, init_predictor
from ..core.redis_cache import get_cache
from ..core.database import get_db

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check service health and component availability."
)
async def health_check() -> HealthResponse:
    """
    Comprehensive health check for all components.
    
    Used by load balancers and monitoring systems.
    """
    model_loaded = False
    cache_connected = False
    database_connected = False
    
    # Check model
    try:
        predictor = get_predictor()
        model_loaded = predictor._model is not None
    except RuntimeError:
        pass
    
    # Check cache
    try:
        cache = await get_cache()
        cache_connected = cache._client is not None
    except Exception:
        pass
    
    # Check database
    try:
        db = await get_db()
        database_connected = db._pool is not None
    except Exception:
        pass
    
    status = "healthy" if model_loaded else "degraded"
    
    return HealthResponse(
        status=status,
        version="1.0.0",
        model_loaded=model_loaded,
        cache_connected=cache_connected,
        database_connected=database_connected,
    )


@router.post(
    "/system/reload-model",
    response_model=ModelReloadResponse,
    summary="Hot-Reload Model",
    description="Zero-downtime model swap triggered by Mage webhook."
)
async def reload_model(
    request: ModelReloadRequest,
    background_tasks: BackgroundTasks,
    x_reload_token: Optional[str] = Header(None),
) -> ModelReloadResponse:
    """
    Hot-swap the model for zero-downtime updates.
    
    Called by Mage pipeline after training completes.
    Uses BackgroundTasks to load asynchronously.
    
    Security: Should be protected by token in production.
    """
    import os
    
    # Validate token (simple security)
    expected_token = os.environ.get("RELOAD_TOKEN", "dev-token")
    if x_reload_token != expected_token:
        raise HTTPException(
            status_code=403,
            detail="Invalid reload token"
        )
    
    start_time = datetime.utcnow()
    
    try:
        predictor = get_predictor()
        previous_version = predictor.version
        
        # Reload model (blocking but fast - just file load)
        predictor.reload(request.model_path)
        
        # Invalidate cache if requested
        cache_invalidated = 0
        if request.invalidate_cache:
            try:
                cache = await get_cache()
                cache_invalidated = await cache.invalidate_pattern(f"{previous_version}:*")
            except Exception as e:
                print(f"[RELOAD] Cache invalidation warning: {e}")
        
        reload_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return ModelReloadResponse(
            status="success",
            previous_version=previous_version,
            new_version=predictor.version,
            cache_invalidated=cache_invalidated,
            reload_time_ms=round(reload_time_ms, 2),
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Model reload failed: {str(e)}"
        )
