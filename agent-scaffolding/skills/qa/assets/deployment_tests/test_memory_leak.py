"""
QA Skill - Memory Leak Detection Tests

Implements test template for task:
- CN-DEP-02: Memory Leak Detection on Reload

Monitors RSS memory during repeated model reloads to detect leaks.
"""

import gc
import os
import time
from typing import Callable, Optional

import pytest


# =============================================================================
# Configuration
# =============================================================================

# Number of reload iterations for leak detection
RELOAD_ITERATIONS = int(os.getenv("LEAK_TEST_ITERATIONS", "50"))

# Memory growth threshold (bytes)
MAX_MEMORY_GROWTH_MB = float(os.getenv("MAX_MEMORY_GROWTH_MB", "100"))

# Time between reloads (seconds)
RELOAD_INTERVAL = float(os.getenv("RELOAD_INTERVAL", "0.1"))


# =============================================================================
# Memory Monitoring Utilities
# =============================================================================


def get_process_memory_mb() -> float:
    """
    Get current process RSS memory in MB.
    
    Uses psutil if available, falls back to resource module.
    """
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    
    try:
        import resource
        # getrusage returns in KB on Linux, bytes on macOS
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is in KB on Linux, bytes on macOS
        import platform
        if platform.system() == "Darwin":
            return usage.ru_maxrss / (1024 * 1024)
        else:
            return usage.ru_maxrss / 1024
    except ImportError:
        pytest.skip("Neither psutil nor resource module available")
    
    return 0


def force_gc():
    """Force garbage collection."""
    gc.collect()
    gc.collect()
    gc.collect()


class MemoryTracker:
    """Track memory usage over time."""
    
    def __init__(self):
        self.samples: list[tuple[float, float]] = []  # (time, memory_mb)
        self.start_time = time.time()
    
    def sample(self):
        """Record current memory usage."""
        force_gc()
        memory = get_process_memory_mb()
        elapsed = time.time() - self.start_time
        self.samples.append((elapsed, memory))
    
    @property
    def initial_memory(self) -> float:
        """Get initial memory reading."""
        return self.samples[0][1] if self.samples else 0
    
    @property
    def final_memory(self) -> float:
        """Get final memory reading."""
        return self.samples[-1][1] if self.samples else 0
    
    @property
    def memory_growth(self) -> float:
        """Get memory growth from start to end."""
        return self.final_memory - self.initial_memory
    
    @property
    def max_memory(self) -> float:
        """Get maximum memory observed."""
        return max(m for _, m in self.samples) if self.samples else 0
    
    def get_trend(self) -> str:
        """Analyze memory trend."""
        if len(self.samples) < 3:
            return "insufficient_data"
        
        # Check if memory is monotonically increasing
        growth_count = 0
        for i in range(1, len(self.samples)):
            if self.samples[i][1] > self.samples[i-1][1]:
                growth_count += 1
        
        growth_ratio = growth_count / (len(self.samples) - 1)
        
        if growth_ratio > 0.8:
            return "increasing"
        elif growth_ratio < 0.2:
            return "decreasing"
        else:
            return "stable"


# =============================================================================
# Mock Model Reloader
# =============================================================================


class MockModelManager:
    """
    Mock model manager that simulates model loading/reloading.
    
    In a real scenario, this would wrap daimojo.MojoScorer.
    """
    
    def __init__(self, model_size_mb: float = 10):
        self.model_size_mb = model_size_mb
        self.model = None
        self.reload_count = 0
    
    def load_model(self):
        """Load a model (allocates memory)."""
        # Simulate model memory allocation
        self.model = bytearray(int(self.model_size_mb * 1024 * 1024))
        self.reload_count += 1
    
    def unload_model(self):
        """Unload current model (should free memory)."""
        self.model = None
    
    def reload_model(self):
        """Reload model (unload + load)."""
        self.unload_model()
        force_gc()
        self.load_model()
    
    def predict(self, features: list[float]) -> float:
        """Mock prediction."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        return 0.85


class LeakyModelManager(MockModelManager):
    """
    Model manager with intentional memory leak for testing.
    
    Each reload accumulates leaked memory.
    """
    
    def __init__(self, leak_size_mb: float = 1):
        super().__init__()
        self.leak_size_mb = leak_size_mb
        self._leaked_buffers: list[bytearray] = []
    
    def reload_model(self):
        """Reload with memory leak."""
        # This is the bug: we keep a reference to old buffer
        self._leaked_buffers.append(
            bytearray(int(self.leak_size_mb * 1024 * 1024))
        )
        super().reload_model()


# =============================================================================
# CN-DEP-02: Memory Leak Detection on Reload
# =============================================================================


class TestMemoryLeakDetection:
    """
    Context: daimojo allocates C++ memory. Python's GC might not
    immediately free C++ objects.
    
    Risk: OOM Kill. Repeated reloads increase RAM until container crashes.
    """
    
    def test_memory_stable_after_reloads(self):
        """
        Trigger model reload 50 times and monitor memory.
        
        Evidence: Memory usage stabilizes; old models are released.
        """
        manager = MockModelManager(model_size_mb=5)
        tracker = MemoryTracker()
        
        # Initial load
        manager.load_model()
        force_gc()
        tracker.sample()
        
        # Repeated reloads
        for i in range(RELOAD_ITERATIONS):
            manager.reload_model()
            
            # Sample every 10 iterations
            if i % 10 == 0:
                force_gc()
                tracker.sample()
        
        # Final sample
        force_gc()
        time.sleep(0.1)  # Allow for delayed cleanup
        force_gc()
        tracker.sample()
        
        # Check memory growth
        growth_mb = tracker.memory_growth
        
        assert growth_mb < MAX_MEMORY_GROWTH_MB, (
            f"Memory grew by {growth_mb:.1f}MB after {RELOAD_ITERATIONS} reloads. "
            f"Threshold: {MAX_MEMORY_GROWTH_MB}MB. Possible memory leak!"
        )
    
    def test_detects_memory_leak(self):
        """
        Negative test: Verify leak detection works with leaky manager.
        """
        manager = LeakyModelManager(leak_size_mb=2)
        tracker = MemoryTracker()
        
        manager.load_model()
        tracker.sample()
        
        # Each reload leaks 2MB
        for _ in range(10):
            manager.reload_model()
            tracker.sample()
        
        # Should detect the leak
        trend = tracker.get_trend()
        
        assert trend == "increasing", (
            f"Expected 'increasing' memory trend for leaky manager, got '{trend}'"
        )
        
        # Memory should have grown significantly
        expected_leak = 10 * 2  # 10 reloads * 2MB each
        assert tracker.memory_growth > expected_leak * 0.5, (
            f"Expected significant memory growth due to leak"
        )
    
    def test_memory_tracker_accuracy(self):
        """
        Verify memory tracker gives reasonable readings.
        """
        tracker = MemoryTracker()
        tracker.sample()
        
        # Allocate some memory
        data = [bytearray(1024 * 1024) for _ in range(10)]  # 10MB
        
        tracker.sample()
        
        # Memory should have increased
        assert tracker.memory_growth > 5, (
            "Memory tracker should detect 10MB allocation"
        )
        
        # Free memory
        del data
        force_gc()
        tracker.sample()
        
        # Memory should have decreased (or stabilized)
        # Note: Python doesn't always return memory to OS immediately
    
    @pytest.mark.parametrize("iterations", [10, 25, 50])
    def test_memory_at_different_iteration_counts(self, iterations: int):
        """
        Test memory behavior at different reload counts.
        """
        manager = MockModelManager(model_size_mb=2)
        
        initial_memory = get_process_memory_mb()
        manager.load_model()
        
        for _ in range(iterations):
            manager.reload_model()
        
        force_gc()
        final_memory = get_process_memory_mb()
        growth = final_memory - initial_memory
        
        # Memory growth should not scale with iterations
        # (indicates leak if it does)
        max_acceptable_growth = 50  # MB
        
        assert growth < max_acceptable_growth, (
            f"Memory grew {growth:.1f}MB after {iterations} reloads"
        )


class TestCppMemoryManagement:
    """
    Additional tests for C++ memory management edge cases.
    """
    
    def test_rapid_reload_cycle(self):
        """
        Test rapid successive reloads without delay.
        """
        manager = MockModelManager(model_size_mb=5)
        
        initial = get_process_memory_mb()
        
        # Very rapid reloads
        for _ in range(20):
            manager.reload_model()
            # No GC or sleep between reloads
        
        force_gc()
        time.sleep(0.5)  # Allow cleanup
        force_gc()
        
        final = get_process_memory_mb()
        growth = final - initial
        
        # Should still release memory despite rapid cycling
        assert growth < 50, f"Rapid reloads caused {growth:.1f}MB growth"
    
    def test_memory_with_predictions(self):
        """
        Test memory while making predictions during reloads.
        """
        manager = MockModelManager(model_size_mb=5)
        manager.load_model()
        
        initial = get_process_memory_mb()
        
        for i in range(20):
            # Make some predictions
            for _ in range(100):
                manager.predict([0.1, 0.2, 0.3])
            
            # Reload
            manager.reload_model()
        
        force_gc()
        final = get_process_memory_mb()
        
        assert final - initial < 50, "Memory leaked during predict+reload cycle"
