"""
Thread Pool Inference Wrapper
=============================================================================
PROC-02-01: Thread Pool Offloading for CPU-Bound Inference

This module demonstrates the correct pattern for integrating CPU-bound
ML inference with FastAPI's async architecture without blocking the
event loop.

The Problem:
- FastAPI uses asyncio event loop for high concurrency
- ML inference (H2O MOJO) is CPU-bound and synchronous
- Calling sync code in async handlers blocks the entire server

The Solution:
- Offload CPU-bound work to a ThreadPoolExecutor
- Use asyncio.to_thread() or run_in_executor()
- Event loop remains responsive during inference

Key Patterns:
- ThreadPoolExecutor for CPU parallelism within process
- MOJO model loading with singleton pattern
- Graceful error handling for model failures

Usage:
    predictor = MojoPredictor()
    await predictor.load()
    
    # This does NOT block the event loop
    result = await predictor.predict_async(features)
=============================================================================
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Optional
import threading

from pydantic import BaseModel


# Configuration
MODEL_PATH = os.getenv("MODEL_PATH", "/models/production/model.mojo")
THREAD_POOL_SIZE = int(os.getenv("THREAD_POOL_SIZE", "8"))


class PredictionRequest(BaseModel):
    """Input features for prediction."""
    features: dict[str, Any]
    request_id: Optional[str] = None


class PredictionResponse(BaseModel):
    """Model prediction response."""
    prediction: Any
    probability: Optional[float] = None
    model_version: str
    latency_ms: float
    cache_hit: bool = False


class MojoPredictor:
    """
    MOJO model predictor with thread pool offloading.
    
    PROC-02-01: Wraps CPU-bound inference in ThreadPoolExecutor
    to prevent blocking the asyncio event loop.
    
    Thread Safety:
    - Model object is thread-safe for read operations
    - ThreadPoolExecutor manages worker threads
    - Lock used only for model hot-swap operations
    """
    
    def __init__(
        self,
        model_path: str = MODEL_PATH,
        thread_pool_size: int = THREAD_POOL_SIZE,
    ):
        self.model_path = model_path
        self.thread_pool_size = thread_pool_size
        self._executor: Optional[ThreadPoolExecutor] = None
        self._model: Optional[Any] = None
        self._model_version: str = "unknown"
        self._lock = threading.Lock()
        self._loaded = False
    
    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self._loaded and self._model is not None
    
    def _create_executor(self) -> ThreadPoolExecutor:
        """Create thread pool for inference."""
        return ThreadPoolExecutor(
            max_workers=self.thread_pool_size,
            thread_name_prefix="inference_worker",
        )
    
    def load(self) -> None:
        """
        Load MOJO model synchronously.
        
        Call this during application startup, not during request handling.
        Uses daimojo for C++ runtime (no JVM required).
        """
        try:
            # Try C++ MOJO runtime first (recommended)
            from daimojo.model import Model
            self._model = Model(self.model_path)
            runtime = "daimojo (C++)"
        except ImportError:
            # Fallback to Java runtime
            import h2o
            from h2o.mojo import MojoModel
            h2o.init(verbose=False)
            self._model = MojoModel.load(self.model_path)
            runtime = "h2o (Java)"
        
        # Extract version from path or model metadata
        path = Path(self.model_path)
        self._model_version = path.parent.name
        
        # Initialize thread pool
        self._executor = self._create_executor()
        self._loaded = True
        
        print(f"Model loaded successfully using {runtime}")
        print(f"Model version: {self._model_version}")
        print(f"Thread pool size: {self.thread_pool_size}")
    
    async def load_async(self) -> None:
        """
        Load model asynchronously (wraps sync load).
        
        Use this if loading during an async context.
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.load)
    
    def _predict_sync(self, features: dict[str, Any]) -> dict[str, Any]:
        """
        Synchronous prediction (runs in thread pool).
        
        This method executes in a worker thread, not the event loop thread.
        """
        if not self._loaded:
            raise RuntimeError("Model not loaded")
        
        try:
            # daimojo C++ runtime
            import pandas as pd
            df = pd.DataFrame([features])
            result = self._model.predict(df)
            
            # Extract prediction
            if hasattr(result, 'iloc'):
                prediction = result.iloc[0].to_dict()
            else:
                prediction = result[0] if isinstance(result, list) else result
            
            return {"prediction": prediction}
            
        except ImportError:
            # h2o Java runtime fallback
            import h2o
            hf = h2o.H2OFrame([features])
            result = self._model.predict(hf)
            prediction = result.as_data_frame().iloc[0].to_dict()
            
            return {"prediction": prediction}
    
    async def predict_async(
        self, 
        features: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Async prediction that offloads CPU work to thread pool.
        
        PROC-02-01: This is the key pattern - using run_in_executor
        to move CPU-bound work off the event loop.
        
        Args:
            features: Input feature dictionary
            
        Returns:
            Prediction result dictionary
        """
        if not self._executor:
            raise RuntimeError("Predictor not initialized")
        
        loop = asyncio.get_event_loop()
        
        # Offload to thread pool - event loop remains responsive
        result = await loop.run_in_executor(
            self._executor,
            self._predict_sync,
            features,
        )
        
        result["model_version"] = self._model_version
        return result
    
    def hot_swap(self, new_model_path: str) -> None:
        """
        SCN-01-01: Atomic model swap for zero-downtime updates.
        
        Uses lock to prevent concurrent access during swap.
        Old model continues serving until new model is ready.
        """
        # Load new model first (old model still serving)
        try:
            from daimojo.model import Model
            new_model = Model(new_model_path)
        except ImportError:
            import h2o
            from h2o.mojo import MojoModel
            new_model = MojoModel.load(new_model_path)
        
        # Atomic swap with lock
        with self._lock:
            old_model = self._model
            self._model = new_model
            self._model_version = Path(new_model_path).parent.name
        
        # Old model will be garbage collected
        print(f"Model hot-swapped to version: {self._model_version}")
    
    async def hot_swap_async(self, new_model_path: str) -> None:
        """Async wrapper for hot swap."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.hot_swap, new_model_path)
    
    def shutdown(self) -> None:
        """Graceful shutdown of thread pool."""
        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None
        self._loaded = False
    
    async def health_check(self) -> dict[str, Any]:
        """Check predictor health status."""
        return {
            "loaded": self._loaded,
            "model_version": self._model_version,
            "model_path": self.model_path,
            "thread_pool_size": self.thread_pool_size,
            "thread_pool_active": self._executor is not None,
        }


# Global predictor instance (singleton pattern)
_predictor: Optional[MojoPredictor] = None


def get_predictor() -> MojoPredictor:
    """Get or create global predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = MojoPredictor()
    return _predictor


async def predictor_startup() -> None:
    """Initialize predictor during FastAPI startup."""
    predictor = get_predictor()
    await predictor.load_async()


async def predictor_shutdown() -> None:
    """Shutdown predictor during FastAPI shutdown."""
    global _predictor
    if _predictor:
        _predictor.shutdown()
        _predictor = None


# FastAPI dependency
async def get_predictor_dependency() -> MojoPredictor:
    """FastAPI dependency for predictor injection."""
    predictor = get_predictor()
    if not predictor.is_loaded:
        raise RuntimeError("Predictor not ready")
    return predictor


# Test harness
if __name__ == "__main__":
    import asyncio
    import time
    
    async def test():
        predictor = MojoPredictor(
            model_path="./test_model.mojo",
            thread_pool_size=4,
        )
        
        # Simulate model loading (would fail without actual model)
        print(f"Predictor health: {await predictor.health_check()}")
        
        # Test concurrent predictions (simulated)
        async def mock_predict(i):
            await asyncio.sleep(0.1)  # Simulate work
            return {"id": i, "prediction": 0.5}
        
        start = time.time()
        tasks = [mock_predict(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        print(f"Completed {len(results)} predictions in {elapsed:.3f}s")
    
    asyncio.run(test())
