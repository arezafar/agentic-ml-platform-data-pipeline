"""
FastAPI Application Entry Point

Main application module for the Agentic ML Platform Serving Layer.
Includes:
- CORS middleware configuration
- Health check endpoints
- Router registration
- Startup/shutdown lifecycle events
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .dependencies import get_db_pool, get_mojo_scorer
from .routers import predictions, health

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    logger.info("Starting up Agentic ML Platform API...")
    
    # Initialize database pool
    app.state.db_pool = await get_db_pool()
    logger.info("Database connection pool initialized")
    
    # Initialize MOJO scorer (if configured)
    try:
        app.state.mojo_scorer = get_mojo_scorer()
        logger.info("MOJO scorer initialized")
    except Exception as e:
        logger.warning(f"MOJO scorer not available: {e}")
        app.state.mojo_scorer = None
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    if hasattr(app.state, 'db_pool') and app.state.db_pool:
        await app.state.db_pool.close()
        logger.info("Database pool closed")


# =============================================================================
# APPLICATION FACTORY
# =============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Agentic ML Platform API",
        description="High-performance ML inference and data serving API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(predictions.router, prefix="/api/v1", tags=["Predictions"])
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
    
    return app


# Create application instance
app = create_app()


# =============================================================================
# ROOT ENDPOINT
# =============================================================================

@app.get("/", response_model=dict[str, Any])
async def root() -> dict[str, Any]:
    """Root endpoint with API information.
    
    Returns:
        API metadata including version and documentation links.
    """
    return {
        "name": "Agentic ML Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
