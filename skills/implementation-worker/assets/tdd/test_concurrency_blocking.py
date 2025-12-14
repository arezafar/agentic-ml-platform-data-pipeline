"""
Test Concurrency Blocking - PROC-01-01 TDD

This test suite validates that CPU-bound inference does NOT
block the async event loop.

Test Requirements:
    1. Create a blocking model (simulates CPU-bound inference)
    2. Fire concurrent requests
    3. Verify parallel execution (total time ≈ single request time)

Run with:
    pytest test_concurrency_blocking.py -v
"""

import pytest
import asyncio
import time
from typing import Any, List
from concurrent.futures import ThreadPoolExecutor

# Mark as async tests
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration
]


class BlockingModel:
    """
    Mock model that simulates CPU-bound inference.
    
    The predict() method blocks for the specified duration.
    """
    
    def __init__(self, block_seconds: float = 0.5):
        self.block_seconds = block_seconds
        self.predict_count = 0
    
    def predict(self, data: Any) -> dict:
        """Simulate CPU-bound inference with blocking sleep."""
        time.sleep(self.block_seconds)  # This is BLOCKING
        self.predict_count += 1
        return {"prediction": 0.75, "input": data}


class TestExecutorOffloading:
    """Test that executor offloading prevents event loop blocking."""
    
    async def test_sequential_is_slow(self):
        """
        Baseline: Sequential execution should be slow.
        
        This demonstrates the problem we're solving.
        """
        # Arrange
        model = BlockingModel(block_seconds=0.2)
        request_count = 5
        
        # Act - Sequential execution
        start = time.monotonic()
        results = []
        for i in range(request_count):
            result = model.predict({"id": i})
            results.append(result)
        elapsed = time.monotonic() - start
        
        # Assert - Should take ~1.0s (5 * 0.2s)
        assert len(results) == request_count
        assert elapsed >= 0.9  # Allow some margin
    
    async def test_executor_offloading_is_parallel(self):
        """
        Test: Using run_in_executor enables parallel execution.
        
        This is the solution pattern.
        """
        # Arrange
        model = BlockingModel(block_seconds=0.2)
        request_count = 5
        executor = ThreadPoolExecutor(max_workers=request_count)
        
        async def predict_async(data):
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                executor,
                model.predict,
                data
            )
        
        # Act - Parallel execution via executor
        start = time.monotonic()
        tasks = [predict_async({"id": i}) for i in range(request_count)]
        results = await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start
        
        # Assert - Should take ~0.2s (parallel), not 1.0s (sequential)
        assert len(results) == request_count
        assert elapsed < 0.5  # Much faster than sequential
        
        executor.shutdown(wait=False)
    
    async def test_inference_executor_class(self):
        """
        Test: InferenceExecutor class handles blocking correctly.
        
        Uses the actual implementation from patterns.
        """
        # Arrange
        from patterns import InferenceExecutor
        
        model = BlockingModel(block_seconds=0.1)
        executor = InferenceExecutor(max_workers=10, use_processes=False)
        request_count = 10
        
        # Act
        start = time.monotonic()
        tasks = [
            executor.predict(model, {"id": i})
            for i in range(request_count)
        ]
        results = await asyncio.gather(*tasks)
        elapsed = time.monotonic() - start
        
        # Assert
        assert len(results) == request_count
        # 10 requests at 0.1s each should take ~0.1s parallel, not 1.0s
        assert elapsed < 0.3
        
        executor.shutdown()


class TestCircuitBreaker:
    """Test circuit breaker protects against overload."""
    
    async def test_circuit_breaker_trips_on_queue_depth(self):
        """
        Test: Circuit breaker rejects requests when queue is full.
        """
        # Arrange
        from patterns import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerOpenError
        
        config = CircuitBreakerConfig(queue_depth_threshold=5)
        breaker = CircuitBreaker(config)
        
        # Simulate queue depth exceeding threshold
        for _ in range(config.queue_depth_threshold):
            breaker.increment_queue_depth()
        
        # Act & Assert
        with pytest.raises(CircuitBreakerOpenError):
            async with breaker.guard():
                pass  # Should not reach here
    
    async def test_circuit_breaker_allows_normal_traffic(self):
        """
        Test: Circuit breaker allows requests under threshold.
        """
        # Arrange
        from patterns import CircuitBreaker, CircuitBreakerConfig
        
        config = CircuitBreakerConfig(queue_depth_threshold=100)
        breaker = CircuitBreaker(config)
        
        # Act
        results = []
        for i in range(10):
            async with breaker.guard():
                results.append(i)
        
        # Assert
        assert len(results) == 10
        assert breaker.stats.successful_calls == 10
        assert breaker.stats.rejected_calls == 0


class TestConcurrencyIntegration:
    """Integration tests combining executor and circuit breaker."""
    
    async def test_high_concurrency_with_protection(self):
        """
        Test: System handles high concurrency with graceful degradation.
        
        Simulates realistic load with both executor offloading
        and circuit breaker protection.
        """
        # Arrange
        from patterns import InferenceExecutor, CircuitBreaker, CircuitBreakerConfig
        
        model = BlockingModel(block_seconds=0.05)
        executor = InferenceExecutor(max_workers=4)
        breaker = CircuitBreaker(CircuitBreakerConfig(queue_depth_threshold=20))
        
        async def protected_predict(data):
            async with breaker.guard():
                return await executor.predict(model, data)
        
        # Act - Fire many concurrent requests
        request_count = 30
        tasks = [protected_predict({"id": i}) for i in range(request_count)]
        
        # Some may fail due to circuit breaker
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Assert
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0  # Some requests succeeded
        
        executor.shutdown()


class TestEventLoopBlocking:
    """
    Test that confirms the problem: blocking the event loop.
    
    These tests demonstrate WHY executor offloading is necessary.
    """
    
    async def test_blocking_call_in_async_context(self):
        """
        Demonstrate: Blocking call in async context blocks everything.
        """
        # Arrange
        model = BlockingModel(block_seconds=0.3)
        other_tasks_completed = []
        
        async def blocking_inference():
            # BAD: Calling blocking function directly in async context
            # This blocks the event loop
            model.predict({"blocking": True})
        
        async def quick_task(task_id: int):
            await asyncio.sleep(0.01)  # Quick async operation
            other_tasks_completed.append(task_id)
        
        # Act - Start blocking task and quick tasks
        start = time.monotonic()
        
        # Note: The blocking call prevents quick tasks from running concurrently
        await blocking_inference()
        
        # These should have run during the blocking call if it wasn't blocking
        quick_ops = [quick_task(i) for i in range(5)]
        await asyncio.gather(*quick_ops)
        
        elapsed = time.monotonic() - start
        
        # Assert - Total time is blocking + quick, not parallel
        assert elapsed >= 0.3  # Blocking dominated
    
    async def test_non_blocking_with_executor(self):
        """
        Demonstrate: Executor allows true concurrency.
        """
        # Arrange
        model = BlockingModel(block_seconds=0.3)
        executor = ThreadPoolExecutor(max_workers=1)
        other_tasks_completed = []
        
        async def non_blocking_inference():
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(executor, model.predict, {"data": 1})
        
        async def quick_task(task_id: int):
            await asyncio.sleep(0.05)
            other_tasks_completed.append(task_id)
        
        # Act - Start both "concurrently"
        start = time.monotonic()
        
        await asyncio.gather(
            non_blocking_inference(),
            *[quick_task(i) for i in range(5)]
        )
        
        elapsed = time.monotonic() - start
        
        # Assert - Quick tasks completed during blocking operation
        assert len(other_tasks_completed) == 5
        # Total time is roughly max(blocking, quick), not sum
        assert elapsed < 0.4  # Close to 0.3s, not 0.3 + 0.25
        
        executor.shutdown(wait=False)
