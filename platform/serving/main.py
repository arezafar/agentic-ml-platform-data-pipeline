"""
FastAPI Pro - High-Concurrency ML Inference API

Main application entry point with lifespan management
for proper resource initialization and cleanup.

Architecture:
- Async event loop for non-blocking I/O
- Thread pool for CPU-bound inference
- Redis look-aside cache for <5ms cache hits
- asyncpg for non-blocking database access
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import inference, system
from .core.mojo_predictor import init_predictor, get_inference_executor
from .core.redis_cache import init_cache
from .core.database import init_database, close_database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Initializes resources on startup and cleans up on shutdown.
    This is the correct pattern for FastAPI resource management.
    """
    print("[APP] Starting FastAPI Pro MLOps Inference Service...")
    
    # Initialize thread pool for inference
    executor = get_inference_executor(
        max_workers=int(os.environ.get("INFERENCE_WORKERS", 4))
    )
    print(f"[APP] Inference thread pool initialized")
    
    # Initialize Redis cache
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        cache = await init_cache(redis_url)
        print(f"[APP] Redis cache initialized")
    except Exception as e:
        print(f"[APP] ⚠️ Redis unavailable: {e}")
    
    # Initialize database pool
    db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/mlops")
    try:
        db = await init_database(db_url)
        print(f"[APP] Database pool initialized")
    except Exception as e:
        print(f"[APP] ⚠️ Database unavailable: {e}")
    
    # Initialize MOJO predictor
    model_path = os.environ.get("MODEL_PATH", "/models/production/model.mojo")
    genmodel_path = os.environ.get("GENMODEL_JAR", "/models/production/h2o-genmodel.jar")
    model_version = os.environ.get("MODEL_VERSION", "latest")
    
    try:
        predictor = init_predictor(model_path, genmodel_path, model_version)
        print(f"[APP] Model loaded: {model_path}")
    except FileNotFoundError:
        print(f"[APP] ⚠️ Model not found at {model_path}. Will use mock mode.")
        # Create mock predictor for testing
        try:
            init_predictor("/tmp/mock.mojo")  # Will use mock mode
        except:
            pass
    
    print("[APP] ✅ Startup complete")
    
    yield  # Application runs here
    
    # Shutdown
    print("[APP] Shutting down...")
    
    await close_database()
    executor.shutdown(wait=True)
    
    print("[APP] ✅ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="FastAPI Pro MLOps Inference",
    description="High-concurrency ML model serving with H2O MOJO",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(inference.router)
app.include_router(system.router)


@app.get("/", tags=["root"])
async def root():
    """Root endpoint."""
    return {
        "service": "FastAPI Pro MLOps Inference",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1,
    )
