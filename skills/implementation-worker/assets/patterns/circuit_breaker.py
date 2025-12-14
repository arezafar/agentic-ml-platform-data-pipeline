"""
Circuit Breaker Pattern - PROC-01-02

This module implements the Process View pattern for overload protection
in the FastAPI inference service.

The Problem:
    Under extreme load, the inference queue grows unbounded.
    Eventually, all requests timeout, wasting resources.
    The system enters a cascading failure mode.

The Solution:
    Monitor queue depth and trip the circuit breaker.
    Return 503 Service Unavailable immediately.
    Allow the system to recover before accepting new requests.

Key States:
    CLOSED: Normal operation, requests flow through
    OPEN: Overloaded, requests rejected immediately
    HALF_OPEN: Testing if system has recovered
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for the circuit breaker."""
    # Queue depth thresholds
    queue_depth_threshold: int = 100
    
    # Failure rate thresholds
    failure_rate_threshold: float = 0.5  # 50% failure rate
    min_calls_for_rate: int = 10  # Minimum calls before rate calculation
    
    # Timing
    open_duration_seconds: float = 30.0  # How long to stay open
    half_open_max_calls: int = 3  # Test calls in half-open state
    
    # Sliding window
    window_size_seconds: float = 60.0  # Time window for failure rate


@dataclass
class CircuitBreakerStats:
    """Statistics for monitoring circuit breaker behavior."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    state_changes: int = 0
    last_state_change: Optional[float] = None
    
    @property
    def failure_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls


class CircuitBreaker:
    """
    Circuit breaker for protecting inference services.
    
    Monitors queue depth and failure rates, automatically
    rejecting requests when the system is overloaded.
    
    Usage:
        breaker = CircuitBreaker(config)
        
        async def predict(request):
            async with breaker.guard():
                return await inference_executor.predict(model, request)
    """
    
    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._opened_at: Optional[float] = None
        self._half_open_calls = 0
        self._current_queue_depth = 0
        self._lock = asyncio.Lock()
        
        # Sliding window for failure rate
        self._recent_calls: list = []
    
    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Current statistics."""
        return self._stats
    
    @property
    def queue_depth(self) -> int:
        """Current queue depth."""
        return self._current_queue_depth
    
    async def guard(self):
        """
        Context manager for protected operations.
        
        Usage:
            async with breaker.guard():
                result = await some_operation()
        """
        return CircuitBreakerGuard(self)
    
    async def _check_state(self) -> bool:
        """
        Check if request should be allowed through.
        
        Returns True if request can proceed, False if rejected.
        """
        async with self._lock:
            now = time.time()
            
            # Clean old entries from sliding window
            self._clean_window(now)
            
            if self._state == CircuitState.CLOSED:
                # Check queue depth
                if self._current_queue_depth >= self.config.queue_depth_threshold:
                    self._trip_open(now, "queue_depth_exceeded")
                    return False
                
                # Check failure rate
                if self._should_trip_on_failures():
                    self._trip_open(now, "failure_rate_exceeded")
                    return False
                
                return True
            
            elif self._state == CircuitState.OPEN:
                # Check if we should transition to half-open
                if self._opened_at and (now - self._opened_at) >= self.config.open_duration_seconds:
                    self._transition_to_half_open(now)
                    return True  # Allow test request
                
                # Still open, reject
                self._stats.rejected_calls += 1
                return False
            
            elif self._state == CircuitState.HALF_OPEN:
                # Allow limited test requests
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                
                # Too many test requests, reject
                self._stats.rejected_calls += 1
                return False
        
        return False
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            now = time.time()
            self._recent_calls.append(("success", now))
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Successful test, close the circuit
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self._transition_to_closed(now)
    
    async def _record_failure(self) -> None:
        """Record a failed call."""
        async with self._lock:
            now = time.time()
            self._recent_calls.append(("failure", now))
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            
            if self._state == CircuitState.HALF_OPEN:
                # Test failed, reopen circuit
                self._trip_open(now, "half_open_failure")
    
    def _should_trip_on_failures(self) -> bool:
        """Check if failure rate exceeds threshold."""
        if len(self._recent_calls) < self.config.min_calls_for_rate:
            return False
        
        failures = sum(1 for status, _ in self._recent_calls if status == "failure")
        rate = failures / len(self._recent_calls)
        
        return rate >= self.config.failure_rate_threshold
    
    def _trip_open(self, now: float, reason: str) -> None:
        """Transition to OPEN state."""
        logger.warning(f"Circuit breaker OPEN: {reason}")
        self._state = CircuitState.OPEN
        self._opened_at = now
        self._stats.state_changes += 1
        self._stats.last_state_change = now
    
    def _transition_to_half_open(self, now: float) -> None:
        """Transition to HALF_OPEN state."""
        logger.info("Circuit breaker HALF_OPEN: testing recovery")
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        self._stats.state_changes += 1
        self._stats.last_state_change = now
    
    def _transition_to_closed(self, now: float) -> None:
        """Transition to CLOSED state."""
        logger.info("Circuit breaker CLOSED: recovered")
        self._state = CircuitState.CLOSED
        self._opened_at = None
        self._half_open_calls = 0
        self._stats.state_changes += 1
        self._stats.last_state_change = now
    
    def _clean_window(self, now: float) -> None:
        """Remove old entries from sliding window."""
        cutoff = now - self.config.window_size_seconds
        self._recent_calls = [
            (status, ts) for status, ts in self._recent_calls
            if ts >= cutoff
        ]
    
    def increment_queue_depth(self) -> None:
        """Called when a request enters the queue."""
        self._current_queue_depth += 1
    
    def decrement_queue_depth(self) -> None:
        """Called when a request leaves the queue."""
        self._current_queue_depth = max(0, self._current_queue_depth - 1)


class CircuitBreakerGuard:
    """Context manager for circuit breaker protection."""
    
    def __init__(self, breaker: CircuitBreaker):
        self.breaker = breaker
        self._allowed = False
    
    async def __aenter__(self):
        self._allowed = await self.breaker._check_state()
        if not self._allowed:
            raise CircuitBreakerOpenError("Circuit breaker is open")
        
        self.breaker.increment_queue_depth()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.breaker.decrement_queue_depth()
        
        if exc_type is None:
            await self.breaker._record_success()
        else:
            await self.breaker._record_failure()
        
        # Don't suppress the exception
        return False


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker rejects a request."""
    pass


# FastAPI Integration
"""
from fastapi import FastAPI, HTTPException, status

breaker = CircuitBreaker(CircuitBreakerConfig(queue_depth_threshold=100))

@app.post("/predict")
async def predict(request: PredictRequest):
    try:
        async with breaker.guard():
            return await inference_executor.predict(model, request.features)
    except CircuitBreakerOpenError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
            headers={"Retry-After": "30"}
        )

@app.get("/health/circuit")
async def circuit_health():
    return {
        "state": breaker.state.value,
        "queue_depth": breaker.queue_depth,
        "stats": {
            "total_calls": breaker.stats.total_calls,
            "rejected_calls": breaker.stats.rejected_calls,
            "failure_rate": breaker.stats.failure_rate
        }
    }
"""
