"""
Patterns Package - Process View (PROC)

This package contains concurrency and orchestration patterns
from the 4+1 Architectural View Model.

Key Patterns:
- executor_offloading.py: Thread pool isolation for CPU-bound inference
- mage_dynamic_block.py: Parallel training fan-out
- circuit_breaker.py: Overload protection

Usage:
    from patterns import InferenceExecutor, CircuitBreaker
    
    executor = InferenceExecutor(max_workers=4)
    breaker = CircuitBreaker()
"""

from .executor_offloading import (
    InferenceExecutor,
    ServiceOverloadError,
    run_in_executor_sync,
)
from .mage_dynamic_block import (
    TrainingSplitConfig,
    generate_walk_forward_splits,
    generate_rolling_splits,
    validate_splits_no_leakage,
    estimate_parallel_jobs,
)
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerGuard,
    CircuitBreakerOpenError,
    CircuitState,
)

__all__ = [
    # Executor Offloading
    "InferenceExecutor",
    "ServiceOverloadError",
    "run_in_executor_sync",
    # Dynamic Blocks
    "TrainingSplitConfig",
    "generate_walk_forward_splits",
    "generate_rolling_splits",
    "validate_splits_no_leakage",
    "estimate_parallel_jobs",
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerGuard",
    "CircuitBreakerOpenError",
    "CircuitState",
]
