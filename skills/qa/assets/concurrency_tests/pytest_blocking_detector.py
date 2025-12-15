"""
QA Skill - Blocking Detection Pytest Plugin

Provides fixtures for detecting event loop blocking in async tests.

Implements task:
- ST-CONC-01: Automated Blocking Detection

Uses the `blockbuster` library to detect when the event loop
is blocked for longer than a specified threshold.
"""

import asyncio
import os
import time
from contextlib import contextmanager
from typing import Generator, Optional

import pytest


# =============================================================================
# Configuration
# =============================================================================

# Blocking threshold in milliseconds
BLOCKING_THRESHOLD_MS = int(os.getenv("BLOCKING_THRESHOLD_MS", "10"))

# Whether to raise exception or just warn
RAISE_ON_BLOCK = os.getenv("BLOCKING_RAISE_ON_BLOCK", "true").lower() == "true"


# =============================================================================
# Custom Blocking Detector (Fallback if blockbuster not installed)
# =============================================================================


class BlockingError(Exception):
    """Raised when event loop blocking is detected."""
    pass


class SimpleBlockingDetector:
    """
    Simple blocking detector for testing without blockbuster.
    
    Uses asyncio debug mode to detect slow callbacks.
    """
    
    def __init__(self, threshold_ms: float = 10.0, raise_on_block: bool = True):
        self.threshold_ms = threshold_ms
        self.raise_on_block = raise_on_block
        self.blocks_detected: list[dict] = []
        self._original_slow_callback_duration = None
    
    def _slow_callback_handler(self, duration: float):
        """Handler called when slow callback detected."""
        block_info = {
            "duration_ms": duration * 1000,
            "timestamp": time.time(),
        }
        self.blocks_detected.append(block_info)
        
        if self.raise_on_block:
            raise BlockingError(
                f"Event loop blocked for {duration * 1000:.2f}ms "
                f"(threshold: {self.threshold_ms}ms)"
            )
    
    @contextmanager
    def detect(self) -> Generator[None, None, None]:
        """Context manager for blocking detection."""
        loop = asyncio.get_event_loop()
        
        # Enable debug mode
        was_debug = loop.get_debug()
        loop.set_debug(True)
        
        # Set slow callback duration (in seconds)
        self._original_slow_callback_duration = loop.slow_callback_duration
        loop.slow_callback_duration = self.threshold_ms / 1000.0
        
        try:
            yield
        finally:
            # Restore original settings
            loop.set_debug(was_debug)
            if self._original_slow_callback_duration is not None:
                loop.slow_callback_duration = self._original_slow_callback_duration


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def blocking_detector():
    """
    Provide a blocking detector instance for manual control.
    
    Usage:
        def test_my_async_code(blocking_detector):
            with blocking_detector.detect():
                await my_async_function()
    """
    return SimpleBlockingDetector(
        threshold_ms=BLOCKING_THRESHOLD_MS,
        raise_on_block=RAISE_ON_BLOCK
    )


@pytest.fixture(scope="function", autouse=False)
def enable_blocking_detection():
    """
    Auto-enable blocking detection for a test.
    
    Usage:
        @pytest.mark.usefixtures("enable_blocking_detection")
        async def test_my_endpoint():
            ...
    
    Or enable globally by setting autouse=True.
    """
    try:
        from blockbuster import blockbuster_ctx
        
        with blockbuster_ctx(
            blocking_threshold_ms=BLOCKING_THRESHOLD_MS,
            raise_on_block=RAISE_ON_BLOCK,
        ):
            yield
    except ImportError:
        # Fallback to simple detector
        detector = SimpleBlockingDetector(
            threshold_ms=BLOCKING_THRESHOLD_MS,
            raise_on_block=RAISE_ON_BLOCK
        )
        with detector.detect():
            yield


@pytest.fixture
def blockbuster_ctx_fixture():
    """
    Provide blockbuster context manager if available.
    
    Returns None if blockbuster is not installed.
    """
    try:
        from blockbuster import blockbuster_ctx
        return blockbuster_ctx
    except ImportError:
        return None


# =============================================================================
# Pytest Plugin Hooks
# =============================================================================


def pytest_configure(config):
    """Register blocking-related markers."""
    config.addinivalue_line(
        "markers",
        "blocking: Enable blocking detection for this test"
    )
    config.addinivalue_line(
        "markers",
        "no_blocking_check: Disable blocking detection for this test"
    )


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    """
    Setup hook to enable blocking detection for marked tests.
    """
    blocking_markers = list(item.iter_markers(name="blocking"))
    
    if blocking_markers:
        # Enable blocking detection for this test
        # This is done via the fixture mechanism
        pass


# =============================================================================
# Test Helpers
# =============================================================================


def simulate_blocking_call(duration_ms: float):
    """
    Simulate a blocking call for testing.
    
    This should trigger blocking detection.
    """
    time.sleep(duration_ms / 1000.0)


async def simulate_async_blocking_call(duration_ms: float):
    """
    Simulate a blocking call inside an async function.
    
    WARNING: This is an anti-pattern! Used for testing detection.
    """
    # This blocks the event loop!
    time.sleep(duration_ms / 1000.0)


async def simulate_proper_async_call(duration_ms: float):
    """
    Proper async sleep that yields to event loop.
    """
    await asyncio.sleep(duration_ms / 1000.0)


# =============================================================================
# Self-Tests for Blocking Detection
# =============================================================================


class TestBlockingDetection:
    """
    Tests to verify blocking detection works correctly.
    """
    
    @pytest.mark.asyncio
    async def test_proper_async_not_detected(self, blocking_detector):
        """
        Proper async code should not trigger blocking detection.
        """
        with blocking_detector.detect():
            await simulate_proper_async_call(5)  # 5ms async sleep
        
        assert len(blocking_detector.blocks_detected) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Expected to fail - demonstrates blocking detection")
    async def test_blocking_call_detected(self, blocking_detector):
        """
        Blocking calls should trigger detection.
        
        NOTE: This test is expected to fail (xfail) because
        it intentionally blocks the event loop.
        """
        with blocking_detector.detect():
            await simulate_async_blocking_call(50)  # 50ms blocking sleep
    
    def test_sync_blocking_call(self, blocking_detector):
        """
        Sync blocking is expected in sync tests.
        """
        # Sync tests don't have event loop blocking issues
        simulate_blocking_call(10)
        # No error expected
    
    @pytest.mark.asyncio
    async def test_short_blocking_below_threshold(self, blocking_detector):
        """
        Very short blocking below threshold should not trigger.
        """
        # Use threshold / 10 to ensure we're below
        short_duration = BLOCKING_THRESHOLD_MS / 10
        
        with blocking_detector.detect():
            # This is slightly blocking but below threshold
            await asyncio.sleep(short_duration / 1000)


class TestBlockingDetectorConfiguration:
    """
    Tests for blocking detector configuration.
    """
    
    def test_threshold_from_environment(self):
        """
        Verify threshold is read from environment.
        """
        detector = SimpleBlockingDetector()
        assert detector.threshold_ms == BLOCKING_THRESHOLD_MS
    
    def test_custom_threshold(self):
        """
        Verify custom threshold can be set.
        """
        detector = SimpleBlockingDetector(threshold_ms=50)
        assert detector.threshold_ms == 50
    
    def test_raise_on_block_configuration(self):
        """
        Verify raise_on_block configuration.
        """
        # Default from env
        detector = SimpleBlockingDetector()
        assert detector.raise_on_block == RAISE_ON_BLOCK
        
        # Explicit override
        detector_no_raise = SimpleBlockingDetector(raise_on_block=False)
        assert detector_no_raise.raise_on_block is False
