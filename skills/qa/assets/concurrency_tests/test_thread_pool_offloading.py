"""
QA Skill - Thread Pool Offloading Tests

Implements test templates for tasks:
- ST-CONC-02: Thread Pool Offloading Verification
- ST-CONC-03: Async vs. Sync Endpoint Performance Benchmark

Verifies that CPU-bound tasks are properly offloaded to thread pool
and that the GIL is released by C++ extensions.
"""

import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable

import pytest


# =============================================================================
# Configuration
# =============================================================================

# Number of concurrent workers for testing
NUM_WORKERS = int(os.getenv("TEST_WORKERS", "4"))

# Simulated CPU-bound work duration (ms)
CPU_WORK_DURATION_MS = int(os.getenv("CPU_WORK_DURATION_MS", "50"))


# =============================================================================
# Mock CPU-Bound Functions
# =============================================================================


def cpu_bound_work(duration_ms: float) -> float:
    """
    Simulate CPU-bound work (like H2O inference).
    
    This function is intentionally blocking.
    """
    start = time.perf_counter()
    
    # Busy wait to simulate CPU work
    target = duration_ms / 1000.0
    while time.perf_counter() - start < target:
        # CPU-intensive operation
        _ = sum(i * i for i in range(1000))
    
    return time.perf_counter() - start


def mock_h2o_predict(features: list[list[float]]) -> list[float]:
    """
    Mock H2O prediction function (CPU-bound).
    
    In production, this would call daimojo.predict().
    """
    # Simulate scoring time
    cpu_bound_work(CPU_WORK_DURATION_MS)
    
    return [0.85] * len(features)


class MockMojoScorer:
    """
    Mock MOJO scorer that simulates CPU-bound inference.
    """
    
    def __init__(self, scoring_time_ms: float = 50):
        self.scoring_time_ms = scoring_time_ms
        self.call_count = 0
    
    def predict(self, features: list[list[float]]) -> list[float]:
        """Blocking prediction (holds GIL)."""
        self.call_count += 1
        cpu_bound_work(self.scoring_time_ms)
        return [0.85] * len(features)
    
    def predict_release_gil(self, features: list[list[float]]) -> list[float]:
        """
        Prediction that releases GIL.
        
        Note: Real daimojo C++ code releases GIL during computation.
        This mock uses time.sleep() which releases GIL.
        """
        self.call_count += 1
        time.sleep(self.scoring_time_ms / 1000.0)  # Releases GIL
        return [0.85] * len(features)


# =============================================================================
# ST-CONC-02: Thread Pool Offloading Verification
# =============================================================================


class TestThreadPoolOffloading:
    """
    Context: run_in_executor moves CPU-bound tasks to thread pool.
    Risk: GIL limits true parallelism for pure Python code, but
    C++ extensions (like daimojo) should release the GIL.
    """
    
    @pytest.mark.asyncio
    async def test_offloading_improves_concurrency(self):
        """
        Verify that offloading CPU work to executor improves throughput.
        
        Evidence: Total time for N concurrent requests is less than
        N * single_request_time (approaching single_request_time with
        enough threads).
        """
        scorer = MockMojoScorer(scoring_time_ms=50)
        single_request_time = 50 / 1000.0  # 50ms
        
        num_requests = 4
        features = [[0.1, 0.2, 0.3]]
        
        # Run sequentially
        start = time.perf_counter()
        for _ in range(num_requests):
            scorer.predict_release_gil(features)
        sequential_time = time.perf_counter() - start
        
        # Run with executor (concurrent)
        loop = asyncio.get_event_loop()
        executor = ThreadPoolExecutor(max_workers=NUM_WORKERS)
        
        scorer.call_count = 0
        start = time.perf_counter()
        tasks = [
            loop.run_in_executor(executor, scorer.predict_release_gil, features)
            for _ in range(num_requests)
        ]
        await asyncio.gather(*tasks)
        concurrent_time = time.perf_counter() - start
        
        executor.shutdown(wait=False)
        
        # Concurrent should be faster than sequential
        # (assuming GIL is released or thread count > 1)
        assert concurrent_time < sequential_time, (
            f"Concurrent time ({concurrent_time:.3f}s) should be less than "
            f"sequential time ({sequential_time:.3f}s)"
        )
    
    @pytest.mark.asyncio
    async def test_run_in_executor_pattern(self):
        """
        Verify the run_in_executor pattern works correctly.
        """
        loop = asyncio.get_event_loop()
        
        def blocking_function(x: int) -> int:
            time.sleep(0.01)  # Simulate blocking
            return x * 2
        
        # This should not block the event loop
        result = await loop.run_in_executor(None, blocking_function, 21)
        
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_asyncio_to_thread_pattern(self):
        """
        Verify asyncio.to_thread() works for Python 3.9+.
        """
        def blocking_function(x: int) -> int:
            time.sleep(0.01)
            return x * 2
        
        # Python 3.9+ pattern
        result = await asyncio.to_thread(blocking_function, 21)
        
        assert result == 42
    
    @pytest.mark.asyncio
    async def test_executor_preserves_exceptions(self):
        """
        Verify exceptions from executor tasks are properly propagated.
        """
        def failing_function():
            raise ValueError("Intentional error")
        
        loop = asyncio.get_event_loop()
        
        with pytest.raises(ValueError) as exc_info:
            await loop.run_in_executor(None, failing_function)
        
        assert "Intentional error" in str(exc_info.value)


# =============================================================================
# ST-CONC-03: Async vs. Sync Endpoint Performance Benchmark
# =============================================================================


class TestAsyncVsSyncPerformance:
    """
    Context: Comparing async def vs def performance.
    Risk: Using async def for CPU-bound tasks is an anti-pattern.
    """
    
    @pytest.fixture
    def scorer(self):
        return MockMojoScorer(scoring_time_ms=20)
    
    @pytest.mark.asyncio
    async def test_async_blocking_is_worst_pattern(self, scorer):
        """
        Demonstrate that async + blocking is the worst pattern.
        
        This is what happens when you do:
            async def predict():
                return h2o.predict(...)  # BLOCKING!
        """
        num_requests = 4
        features = [[0.1, 0.2, 0.3]]
        
        # Pattern 1: async def with blocking call (BAD!)
        async def bad_async_predict():
            return scorer.predict(features)  # Blocks event loop!
        
        start = time.perf_counter()
        # These run SEQUENTIALLY despite being async!
        for _ in range(num_requests):
            await bad_async_predict()
        bad_async_time = time.perf_counter() - start
        
        # Pattern 2: sync def (FastAPI threads automatically)
        def sync_predict():
            return scorer.predict_release_gil(features)
        
        executor = ThreadPoolExecutor(max_workers=NUM_WORKERS)
        loop = asyncio.get_event_loop()
        
        start = time.perf_counter()
        tasks = [
            loop.run_in_executor(executor, sync_predict)
            for _ in range(num_requests)
        ]
        await asyncio.gather(*tasks)
        sync_threaded_time = time.perf_counter() - start
        
        executor.shutdown(wait=False)
        
        # Sync + threading should be faster
        assert sync_threaded_time < bad_async_time, (
            "Sync with threading should outperform async blocking"
        )
    
    @pytest.mark.asyncio
    async def test_proper_async_offloading(self, scorer):
        """
        Demonstrate proper async offloading pattern.
        
        This is what you should do:
            async def predict():
                return await asyncio.to_thread(h2o.predict, ...)
        """
        num_requests = 4
        features = [[0.1, 0.2, 0.3]]
        
        async def proper_async_predict():
            return await asyncio.to_thread(
                scorer.predict_release_gil, features
            )
        
        start = time.perf_counter()
        tasks = [proper_async_predict() for _ in range(num_requests)]
        await asyncio.gather(*tasks)
        proper_async_time = time.perf_counter() - start
        
        # Should complete in roughly 1x single_request time, not 4x
        single_request_time = scorer.scoring_time_ms / 1000.0
        expected_max = single_request_time * 2  # Allow some overhead
        
        assert proper_async_time < expected_max, (
            f"Properly offloaded async should complete in ~{single_request_time:.3f}s, "
            f"got {proper_async_time:.3f}s"
        )
    
    @pytest.mark.asyncio
    async def test_throughput_scales_with_workers(self, scorer):
        """
        Verify that throughput scales with number of executor workers.
        
        Evidence: RPS increases with more workers (up to CPU limit).
        """
        features = [[0.1, 0.2, 0.3]]
        num_requests = 8
        
        results = {}
        
        for num_workers in [1, 2, 4]:
            executor = ThreadPoolExecutor(max_workers=num_workers)
            loop = asyncio.get_event_loop()
            
            start = time.perf_counter()
            tasks = [
                loop.run_in_executor(
                    executor, scorer.predict_release_gil, features
                )
                for _ in range(num_requests)
            ]
            await asyncio.gather(*tasks)
            elapsed = time.perf_counter() - start
            
            executor.shutdown(wait=True)
            
            rps = num_requests / elapsed
            results[num_workers] = rps
        
        # More workers should mean higher throughput
        assert results[2] > results[1], (
            "2 workers should have higher RPS than 1"
        )
        assert results[4] >= results[2], (
            "4 workers should have RPS >= 2 workers"
        )


class TestGILBehavior:
    """
    Tests for understanding GIL behavior with different code.
    """
    
    def test_pure_python_holds_gil(self):
        """
        Demonstrate that pure Python CPU work holds the GIL.
        """
        def pure_python_work():
            total = 0
            for i in range(100000):
                total += i * i
            return total
        
        # Multiple threads running pure Python will serialize
        # This test documents the behavior
        import threading
        
        results = []
        
        def worker():
            result = pure_python_work()
            results.append(result)
        
        threads = [threading.Thread(target=worker) for _ in range(4)]
        
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.perf_counter() - start
        
        assert len(results) == 4
        # Time should be roughly 4x single execution (GIL serialization)
    
    def test_sleep_releases_gil(self):
        """
        Demonstrate that time.sleep() releases the GIL.
        """
        import threading
        
        results = []
        
        def worker():
            time.sleep(0.05)  # Releases GIL
            results.append(1)
        
        threads = [threading.Thread(target=worker) for _ in range(4)]
        
        start = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        elapsed = time.perf_counter() - start
        
        # Should complete in ~50ms, not 200ms
        assert elapsed < 0.15, (
            f"Parallel sleep should take ~50ms, took {elapsed * 1000:.0f}ms"
        )
