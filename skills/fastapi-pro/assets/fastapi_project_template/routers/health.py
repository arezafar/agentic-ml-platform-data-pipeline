"""
Health Check Router

Provides health and readiness endpoints for:
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring systems
"""

from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint.
    
    Returns:
        Health status with timestamp.
    """
    from datetime import datetime
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/ready",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def readiness_check(request: Request) -> dict[str, Any]:
    """Readiness check including dependencies.
    
    Checks:
    - Database connectivity
    - MOJO scorer availability
    
    Returns:
        Detailed readiness status.
        
    Raises:
        HTTPException: If any dependency is unhealthy.
    """
    from datetime import datetime
    from fastapi import HTTPException
    
    checks = {
        "database": False,
        "mojo_scorer": False,
    }
    
    # Check database
    try:
        if hasattr(request.app.state, 'db_pool') and request.app.state.db_pool:
            async with request.app.state.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            checks["database"] = True
    except Exception:
        pass
    
    # Check MOJO scorer
    if hasattr(request.app.state, 'mojo_scorer') and request.app.state.mojo_scorer:
        checks["mojo_scorer"] = True
    
    # Determine overall status
    all_healthy = all(checks.values())
    
    if not checks["database"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection unavailable",
        )
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/live",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
)
async def liveness_check() -> dict[str, str]:
    """Kubernetes liveness probe endpoint.
    
    Simple check that the application is running.
    
    Returns:
        Simple alive status.
    """
    return {"status": "alive"}
