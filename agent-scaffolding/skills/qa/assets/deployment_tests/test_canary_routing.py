"""
QA Skill - Canary Routing Verification Tests

Implements test template for task:
- CN-DEP-03: Canary Routing Logic Verification

Verifies that traffic splitting works correctly during gradual rollout.
"""

import asyncio
import os
import random
import statistics
from collections import Counter
from typing import Optional

import pytest


# =============================================================================
# Configuration
# =============================================================================

# Default traffic split
STABLE_WEIGHT = float(os.getenv("STABLE_WEIGHT", "0.9"))  # 90%
CANARY_WEIGHT = float(os.getenv("CANARY_WEIGHT", "0.1"))  # 10%

# Statistical confidence
CONFIDENCE_LEVEL = float(os.getenv("CONFIDENCE_LEVEL", "0.95"))
SAMPLE_SIZE = int(os.getenv("SAMPLE_SIZE", "1000"))


# =============================================================================
# Mock Router
# =============================================================================


class MockCanaryRouter:
    """
    Mock canary router for testing traffic splitting logic.
    
    In production, this would be implemented by:
    - Kubernetes Ingress with annotations
    - Istio VirtualService
    - Application-level routing
    """
    
    def __init__(self, stable_weight: float = 0.9, canary_weight: float = 0.1):
        self.stable_weight = stable_weight
        self.canary_weight = canary_weight
        self.stable_version = "v1.0.0"
        self.canary_version = "v2.0.0"
        self.request_log: list[str] = []
    
    def route_request(self) -> dict:
        """
        Route a request to stable or canary based on weights.
        
        Returns response with model version header.
        """
        rand = random.random()
        
        if rand < self.canary_weight:
            version = self.canary_version
            target = "canary"
        else:
            version = self.stable_version
            target = "stable"
        
        self.request_log.append(target)
        
        return {
            "status": 200,
            "headers": {
                "X-Model-Version": version,
                "X-Routing-Target": target,
            },
            "prediction": 0.85,
        }
    
    def get_traffic_distribution(self) -> dict:
        """Get distribution of routed traffic."""
        counter = Counter(self.request_log)
        total = len(self.request_log)
        
        return {
            "stable": counter.get("stable", 0) / total if total > 0 else 0,
            "canary": counter.get("canary", 0) / total if total > 0 else 0,
            "total_requests": total,
        }
    
    def reset_logs(self):
        """Clear request logs."""
        self.request_log.clear()


# =============================================================================
# Statistical Helpers
# =============================================================================


def binomial_confidence_interval(
    successes: int,
    total: int,
    confidence: float = 0.95
) -> tuple[float, float]:
    """
    Calculate confidence interval for a binomial proportion.
    
    Uses Wilson score interval for better small-sample behavior.
    """
    if total == 0:
        return (0, 1)
    
    p = successes / total
    
    # Z-score for confidence level
    from math import sqrt
    z = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}.get(confidence, 1.96)
    
    # Wilson score interval
    denominator = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denominator
    spread = z * sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator
    
    return (max(0, center - spread), min(1, center + spread))


def is_proportion_within_tolerance(
    observed: float,
    expected: float,
    tolerance: float = 0.05
) -> bool:
    """Check if observed proportion is within tolerance of expected."""
    return abs(observed - expected) <= tolerance


# =============================================================================
# CN-DEP-03: Canary Routing Logic Verification
# =============================================================================


class TestCanaryRoutingLogic:
    """
    Context: Gradual rollout (traffic splitting).
    Risk: Routing logic failure (sending all traffic to canary).
    """
    
    @pytest.fixture
    def router(self):
        """Create fresh router for each test."""
        return MockCanaryRouter(
            stable_weight=STABLE_WEIGHT,
            canary_weight=CANARY_WEIGHT
        )
    
    def test_traffic_split_accuracy(self, router):
        """
        Configure 90/10 split and verify ~10% goes to canary.
        
        Evidence: Statistical verification of routing distribution.
        """
        # Send 1000 requests
        for _ in range(SAMPLE_SIZE):
            router.route_request()
        
        distribution = router.get_traffic_distribution()
        
        # Calculate confidence interval for canary percentage
        canary_count = int(distribution["canary"] * SAMPLE_SIZE)
        lower, upper = binomial_confidence_interval(
            canary_count, SAMPLE_SIZE, CONFIDENCE_LEVEL
        )
        
        # Expected canary rate should be within confidence interval
        expected_canary = CANARY_WEIGHT
        
        assert lower <= expected_canary <= upper or \
               is_proportion_within_tolerance(distribution["canary"], expected_canary, 0.03), (
            f"Canary traffic {distribution['canary']*100:.1f}% outside expected "
            f"range [{lower*100:.1f}%, {upper*100:.1f}%] for 10% target"
        )
    
    def test_canary_receives_traffic(self, router):
        """
        Verify canary actually receives some traffic.
        """
        for _ in range(100):
            router.route_request()
        
        distribution = router.get_traffic_distribution()
        
        assert distribution["canary"] > 0, (
            "Canary received no traffic - routing may be broken"
        )
    
    def test_stable_receives_majority(self, router):
        """
        Verify stable version receives majority of traffic.
        """
        for _ in range(SAMPLE_SIZE):
            router.route_request()
        
        distribution = router.get_traffic_distribution()
        
        assert distribution["stable"] > 0.85, (
            f"Stable should receive >85% traffic, got {distribution['stable']*100:.1f}%"
        )
    
    def test_version_headers_present(self, router):
        """
        Verify responses include version headers.
        """
        response = router.route_request()
        
        assert "X-Model-Version" in response["headers"], (
            "Missing X-Model-Version header"
        )
        assert "X-Routing-Target" in response["headers"], (
            "Missing X-Routing-Target header"
        )
    
    def test_version_matches_routing_target(self, router):
        """
        Verify version header matches routing target.
        """
        for _ in range(100):
            response = router.route_request()
            
            target = response["headers"]["X-Routing-Target"]
            version = response["headers"]["X-Model-Version"]
            
            if target == "stable":
                assert version == router.stable_version
            elif target == "canary":
                assert version == router.canary_version
    
    @pytest.mark.parametrize("stable_pct,canary_pct", [
        (1.0, 0.0),   # 100% stable (no canary)
        (0.95, 0.05), # 95/5 split
        (0.9, 0.1),   # 90/10 split
        (0.8, 0.2),   # 80/20 split
        (0.5, 0.5),   # 50/50 split
    ])
    def test_various_traffic_splits(self, stable_pct: float, canary_pct: float):
        """
        Test various traffic split configurations.
        """
        router = MockCanaryRouter(
            stable_weight=stable_pct,
            canary_weight=canary_pct
        )
        
        for _ in range(500):
            router.route_request()
        
        distribution = router.get_traffic_distribution()
        
        # Allow 5% tolerance for statistical variation
        assert is_proportion_within_tolerance(
            distribution["canary"], canary_pct, 0.05
        ), (
            f"Expected ~{canary_pct*100:.0f}% canary, "
            f"got {distribution['canary']*100:.1f}%"
        )


class TestCanaryRolloutScenarios:
    """
    Tests for complete canary rollout scenarios.
    """
    
    def test_progressive_rollout(self):
        """
        Simulate progressive canary rollout: 10% -> 25% -> 50% -> 100%
        """
        stages = [
            (0.9, 0.1),   # Stage 1: 10% canary
            (0.75, 0.25), # Stage 2: 25% canary
            (0.5, 0.5),   # Stage 3: 50% canary
            (0.0, 1.0),   # Stage 4: 100% canary (full rollout)
        ]
        
        for i, (stable_w, canary_w) in enumerate(stages):
            router = MockCanaryRouter(stable_w, canary_w)
            
            for _ in range(200):
                router.route_request()
            
            dist = router.get_traffic_distribution()
            
            assert is_proportion_within_tolerance(
                dist["canary"], canary_w, 0.08
            ), f"Stage {i+1} failed: expected {canary_w*100:.0f}% canary"
    
    def test_rollback_scenario(self):
        """
        Test rollback from canary to stable.
        """
        # Start with canary at 20%
        router = MockCanaryRouter(0.8, 0.2)
        
        for _ in range(100):
            router.route_request()
        
        initial_dist = router.get_traffic_distribution()
        assert initial_dist["canary"] > 0.1
        
        # Simulate rollback (100% to stable)
        router.canary_weight = 0.0
        router.stable_weight = 1.0
        router.reset_logs()
        
        for _ in range(100):
            router.route_request()
        
        final_dist = router.get_traffic_distribution()
        
        assert final_dist["canary"] == 0, (
            "After rollback, canary should receive 0% traffic"
        )
    
    def test_header_based_routing(self):
        """
        Test routing based on request headers (e.g., internal users).
        """
        class HeaderAwareRouter(MockCanaryRouter):
            def route_request(self, headers: Optional[dict] = None) -> dict:
                # Force canary for internal testers
                if headers and headers.get("X-Internal-Test") == "true":
                    self.request_log.append("canary")
                    return {
                        "status": 200,
                        "headers": {
                            "X-Model-Version": self.canary_version,
                            "X-Routing-Target": "canary",
                        },
                        "prediction": 0.85,
                    }
                
                return super().route_request()
        
        router = HeaderAwareRouter(0.9, 0.1)
        
        # Internal requests always go to canary
        for _ in range(10):
            response = router.route_request({"X-Internal-Test": "true"})
            assert response["headers"]["X-Routing-Target"] == "canary"
        
        # Normal requests follow weight distribution
        router.reset_logs()
        for _ in range(100):
            router.route_request()
        
        dist = router.get_traffic_distribution()
        assert dist["canary"] < 0.3  # ~10% expected
