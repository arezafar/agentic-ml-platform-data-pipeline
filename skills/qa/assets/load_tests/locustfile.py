"""
QA Skill - Locust Load Testing Configuration

Implements test templates for tasks:
- ST-LOAD-01: High-Concurrency Stress Test
- ST-LOAD-02: Cache Stampede Simulation
- ST-LOAD-03: Spike Testing (Elasticity)

Locust is preferred because it allows defining user behavior
in Python code, making it adaptable to ML inference requests.

Usage:
    locust -f locustfile.py --host http://localhost:8000

    # Headless mode with specific user count
    locust -f locustfile.py --headless --users 100 --spawn-rate 10 --run-time 1m

    # Generate CSV report
    locust -f locustfile.py --headless --users 1000 --spawn-rate 50 --run-time 5m --csv results
"""

import json
import os
import random
import time
from typing import Any, Optional

from locust import HttpUser, between, constant, events, task
from locust.runners import MasterRunner


# =============================================================================
# Configuration
# =============================================================================

# API endpoints
PREDICT_ENDPOINT = os.getenv("PREDICT_ENDPOINT", "/api/v1/predict")
HEALTH_ENDPOINT = os.getenv("HEALTH_ENDPOINT", "/health")
RELOAD_ENDPOINT = os.getenv("RELOAD_ENDPOINT", "/admin/reload-model")

# SLO thresholds
P99_LATENCY_MS = int(os.getenv("P99_LATENCY_MS", "50"))
TARGET_RPS = int(os.getenv("TARGET_RPS", "1000"))

# Feature vector configuration
NUM_FEATURES = int(os.getenv("NUM_FEATURES", "10"))


# =============================================================================
# Test Data Generators
# =============================================================================


def generate_random_features(num_features: int = NUM_FEATURES) -> list[float]:
    """Generate random feature vector for testing."""
    return [random.random() for _ in range(num_features)]


def generate_fixed_features() -> list[float]:
    """Generate fixed feature vector for cache testing."""
    return [0.5] * NUM_FEATURES


def generate_batch_request(batch_size: int = 10) -> dict:
    """Generate batch prediction request."""
    return {
        "features": [generate_random_features() for _ in range(batch_size)],
        "request_id": f"batch_{time.time_ns()}",
    }


# =============================================================================
# FastAPI User Definition
# =============================================================================


class FastAPIInferenceUser(HttpUser):
    """
    Simulates a user making inference requests to the FastAPI service.
    
    Implements realistic user behavior with think time between requests.
    """
    
    # Wait time between requests (think time)
    wait_time = between(0.1, 0.5)  # 100-500ms between requests
    
    # Request weights (relative frequency)
    weight = 1
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Optional: Perform any setup (e.g., authentication)
        self.request_count = 0
        self.model_version = None
    
    @task(10)
    def predict_single(self):
        """
        ST-LOAD-01: High-concurrency single prediction request.
        
        Weight 10 = Most common request type.
        """
        payload = {
            "features": generate_random_features(),
            "request_id": f"single_{time.time_ns()}",
        }
        
        with self.client.post(
            PREDICT_ENDPOINT,
            json=payload,
            catch_response=True,
            name="predict_single"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Validate response structure
                    if "prediction" not in data:
                        response.failure("Missing 'prediction' in response")
                    else:
                        # Track model version for canary testing
                        self.model_version = response.headers.get("X-Model-Version")
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 503:
                response.failure("Service unavailable")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
        
        self.request_count += 1
    
    @task(3)
    def predict_batch(self):
        """
        Batch prediction request.
        
        Weight 3 = Less common than single predictions.
        """
        payload = generate_batch_request(batch_size=10)
        
        with self.client.post(
            PREDICT_ENDPOINT + "/batch",
            json=payload,
            catch_response=True,
            name="predict_batch"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    predictions = data.get("predictions", [])
                    if len(predictions) != 10:
                        response.failure(
                            f"Expected 10 predictions, got {len(predictions)}"
                        )
                    else:
                        response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
    
    @task(1)
    def health_check(self):
        """
        Health check request.
        
        Weight 1 = Occasional health checks.
        """
        with self.client.get(
            HEALTH_ENDPOINT,
            name="health_check"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")


# =============================================================================
# ST-LOAD-02: Cache Stampede Simulation
# =============================================================================


class CacheStampedeUser(HttpUser):
    """
    Simulates cache stampede (thundering herd) scenario.
    
    All users request the same resource simultaneously when cache expires.
    """
    
    wait_time = constant(0)  # No wait - maximum pressure
    weight = 0  # Disabled by default
    
    # Fixed feature vector for cache key
    FIXED_FEATURES = [0.5] * NUM_FEATURES
    
    @task
    def stampede_request(self):
        """
        Send identical requests to trigger cache stampede.
        
        All requests use same features = same cache key.
        """
        payload = {
            "features": self.FIXED_FEATURES,
            "request_id": f"stampede_{time.time_ns()}",
        }
        
        with self.client.post(
            PREDICT_ENDPOINT,
            json=payload,
            catch_response=True,
            name="stampede_request"
        ) as response:
            if response.status_code == 200:
                # Check if this was a cache hit
                cache_status = response.headers.get("X-Cache-Status", "unknown")
                if cache_status == "HIT":
                    response.success()
                elif cache_status == "MISS":
                    # This is expected for first request
                    response.success()
                else:
                    response.success()  # Still successful
            elif response.status_code == 429:
                response.failure("Rate limited during stampede")
            else:
                response.failure(f"Status {response.status_code}")


# =============================================================================
# ST-LOAD-03: Spike Testing
# =============================================================================


class SpikeTestUser(HttpUser):
    """
    User for spike testing - sudden traffic burst.
    
    Used to test auto-scaling and cold-start recovery.
    """
    
    wait_time = constant(0.01)  # Very fast requests during spike
    weight = 0  # Disabled by default, enable for spike tests
    
    @task
    def spike_request(self):
        """High-frequency request during spike."""
        payload = {
            "features": generate_random_features(),
            "request_id": f"spike_{time.time_ns()}",
        }
        
        start = time.time()
        
        with self.client.post(
            PREDICT_ENDPOINT,
            json=payload,
            catch_response=True,
            name="spike_request"
        ) as response:
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code == 200:
                if latency_ms > P99_LATENCY_MS * 2:
                    # During spike, allow 2x normal latency
                    response.failure(f"Spike latency too high: {latency_ms:.0f}ms")
                else:
                    response.success()
            elif response.status_code == 503:
                # Service overwhelmed - expected during spike
                response.failure("Service unavailable during spike")


# =============================================================================
# Event Handlers
# =============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    print(f"Starting load test against {environment.host}")
    print(f"Target: {TARGET_RPS} RPS with p99 < {P99_LATENCY_MS}ms")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test ends."""
    if environment.runner is not None:
        stats = environment.runner.stats
        
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        
        for entry in stats.entries.values():
            print(f"\n{entry.name}:")
            print(f"  Requests: {entry.num_requests}")
            print(f"  Failures: {entry.num_failures}")
            print(f"  Median: {entry.median_response_time:.0f}ms")
            print(f"  P95: {entry.get_response_time_percentile(0.95):.0f}ms")
            print(f"  P99: {entry.get_response_time_percentile(0.99):.0f}ms")
            print(f"  RPS: {entry.total_rps:.1f}")
        
        print("\n" + "=" * 60)


@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response: Any,
    exception: Optional[Exception],
    **kwargs
):
    """Called for every request (can be used for custom metrics)."""
    # Log slow requests for debugging
    if response_time > P99_LATENCY_MS:
        # Could log to external system here
        pass


# =============================================================================
# Custom Load Shapes
# =============================================================================


class StepLoadShape:
    """
    Custom load shape for step-wise ramp-up.
    
    Usage in locustfile:
        from locust import LoadTestShape
        
        class StepLoadShape(LoadTestShape):
            ...
    """
    
    step_time = 60  # Time per step in seconds
    step_load = 100  # Users to add per step
    max_users = 1000
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time > self.step_time * (self.max_users / self.step_load):
            return None  # Stop test
        
        current_step = min(
            int(run_time / self.step_time) + 1,
            self.max_users // self.step_load
        )
        
        return (current_step * self.step_load, self.step_load)


class SpikeLoadShape:
    """
    Custom load shape for spike testing.
    
    Sudden jump from low to high traffic, then recovery.
    """
    
    baseline_users = 100
    spike_users = 2000
    spike_duration = 10  # seconds
    recovery_time = 60  # seconds to monitor recovery
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 30:
            # Warm-up phase
            return (self.baseline_users, 10)
        elif run_time < 30 + self.spike_duration:
            # Spike phase
            return (self.spike_users, self.spike_users)  # Instant spike
        elif run_time < 30 + self.spike_duration + self.recovery_time:
            # Recovery phase
            return (self.baseline_users, 100)
        else:
            return None  # Stop test


# =============================================================================
# CLI Entry Point
# =============================================================================


if __name__ == "__main__":
    import sys
    from locust.main import main
    
    sys.exit(main())
