"""
Executor Offloading Pattern - PROC-01-01

This module implements the Process View pattern for isolating CPU-bound
ML inference from the async event loop.

The Problem:
    FastAPI uses asyncio for high-concurrency I/O operations.
    ML inference is CPU-bound and blocks the event loop.
    A single 100ms inference task reduces throughput to 10 req/sec.

The Solution:
    Offload blocking operations to a thread/process pool using
    asyncio.get_running_loop().run_in_executor()

TDD Task:
    Write test_concurrency_blocking.py that:
    1. Creates a dummy model with 1s sleep
    2. Fires 10 concurrent requests
    3. Asserts total time is ~1s (parallel), not 10s (sequential)
"""

import asyncio
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class InferenceExecutor:
    """
    Manages thread/process pool for CPU-bound inference tasks.
    
    This class ensures that ML model.predict() calls never block
    the asyncio event loop.
    
    Usage:
        executor = InferenceExecutor(max_workers=4)
        result = await executor.predict(model, input_data)
    """
    
    def __init__(
        self,
        max_workers: int = 4,
        use_processes: bool = False,
        queue_depth_limit: int = 100
    ):
        """
        Initialize the inference executor.
        
        Args:
            max_workers: Number of worker threads/processes
            use_processes: Use ProcessPoolExecutor (bypasses GIL entirely)
                          Use ThreadPoolExecutor for C++ extensions that release GIL
            queue_depth_limit: Maximum pending tasks before circuit breaker trips
        """
        self.max_workers = max_workers
        self.queue_depth_limit = queue_depth_limit
        self._pending_tasks = 0
        
        # Choose executor type based on inference characteristics
        # ProcessPoolExecutor: Pure Python models (complete GIL bypass)
        # ThreadPoolExecutor: C++ extensions like XGBoost (release GIL during compute)
        if use_processes:
            self._executor = ProcessPoolExecutor(max_workers=max_workers)
            logger.info(f"Using ProcessPoolExecutor with {max_workers} workers")
        else:
            self._executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="inference_worker"
            )
            logger.info(f"Using ThreadPoolExecutor with {max_workers} workers")
    
    async def predict(
        self,
        model: Any,
        input_data: Any,
        predict_method: str = "predict"
    ) -> Any:
        """
        Execute model prediction in the executor pool.
        
        This method is safe to call from async def route handlers.
        
        Args:
            model: The ML model object (H2O MOJO, sklearn, etc.)
            input_data: Input features for prediction
            predict_method: Name of the model's prediction method
            
        Returns:
            Prediction result from the model
            
        Raises:
            ServiceOverloadError: If queue depth exceeds limit
        """
        # Circuit breaker check
        if self._pending_tasks >= self.queue_depth_limit:
            raise ServiceOverloadError(
                f"Inference queue depth ({self._pending_tasks}) exceeds limit "
                f"({self.queue_depth_limit})"
            )
        
        self._pending_tasks += 1
        try:
            loop = asyncio.get_running_loop()
            
            # Get the prediction method
            predict_fn = getattr(model, predict_method)
            
            # Offload to executor - this is the critical pattern
            result = await loop.run_in_executor(
                self._executor,
                partial(predict_fn, input_data)
            )
            
            return result
        finally:
            self._pending_tasks -= 1
    
    async def predict_batch(
        self,
        model: Any,
        batch_data: list,
        predict_method: str = "predict"
    ) -> list:
        """
        Execute batch predictions concurrently.
        
        Distributes batch items across the worker pool.
        """
        tasks = [
            self.predict(model, item, predict_method)
            for item in batch_data
        ]
        return await asyncio.gather(*tasks)
    
    @property
    def queue_depth(self) -> int:
        """Current number of pending inference tasks."""
        return self._pending_tasks
    
    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor pool."""
        self._executor.shutdown(wait=wait)


class ServiceOverloadError(Exception):
    """Raised when inference queue is overloaded."""
    pass


# FastAPI Integration Example
"""
from fastapi import FastAPI, HTTPException, status
from contextlib import asynccontextmanager

app = FastAPI()
inference_executor: Optional[InferenceExecutor] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global inference_executor
    inference_executor = InferenceExecutor(max_workers=4)
    yield
    inference_executor.shutdown()

@app.post("/predict")
async def predict(request: PredictRequest):
    try:
        result = await inference_executor.predict(
            model=CURRENT_MODEL,
            input_data=request.features
        )
        return {"prediction": result}
    except ServiceOverloadError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily overloaded"
        )
"""


# Synchronous wrapper for non-async contexts
def run_in_executor_sync(
    func: Callable[..., T],
    *args,
    executor: Optional[ThreadPoolExecutor] = None,
    **kwargs
) -> T:
    """
    Run a blocking function in an executor from sync context.
    
    Useful for Mage blocks that need to offload heavy computation.
    """
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=1)
        should_shutdown = True
    else:
        should_shutdown = False
    
    try:
        future = executor.submit(func, *args, **kwargs)
        return future.result()
    finally:
        if should_shutdown:
            executor.shutdown(wait=False)
