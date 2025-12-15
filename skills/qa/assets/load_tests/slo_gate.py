"""
QA Skill - SLO Gate Script

Implements task:
- SLO-CI-01: Implement SLO Gating in Pipeline

Parses Locust results and enforces latency thresholds.
Designed for CI/CD integration to fail builds on SLO violations.

Usage:
    python slo_gate.py --results locust_stats.csv
    python slo_gate.py --results locust_stats.csv --p99-threshold 50 --error-rate 0.01
    python slo_gate.py --results locust_stats.csv --json-output results.json
"""

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_P99_THRESHOLD_MS = float(os.getenv("SLO_P99_THRESHOLD_MS", "50"))
DEFAULT_ERROR_RATE_THRESHOLD = float(os.getenv("SLO_ERROR_RATE", "0.01"))
DEFAULT_MIN_REQUESTS = int(os.getenv("SLO_MIN_REQUESTS", "100"))


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class SLOResult:
    """Result of SLO evaluation."""
    passed: bool
    p50_ms: float
    p95_ms: float
    p99_ms: float
    error_rate: float
    total_requests: int
    failures: int
    rps: float
    violations: list[str]


@dataclass
class EndpointStats:
    """Statistics for a single endpoint."""
    name: str
    num_requests: int
    num_failures: int
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    rps: float


# =============================================================================
# Locust Stats Parser
# =============================================================================


def parse_locust_stats(csv_path: Path) -> list[EndpointStats]:
    """
    Parse Locust stats CSV file.
    
    Expected format (from locust --csv=results):
    - results_stats.csv: Request statistics
    
    Columns:
    Type,Name,Request Count,Failure Count,Median Response Time,
    Average Response Time,Min Response Time,Max Response Time,
    Average Content Size,Requests/s,Failures/s,50%,66%,75%,80%,90%,95%,98%,99%,99.9%,99.99%,100%
    """
    stats = []
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Skip aggregated row
            if row.get('Name') == 'Aggregated':
                continue
            
            try:
                endpoint = EndpointStats(
                    name=row.get('Name', 'unknown'),
                    num_requests=int(row.get('Request Count', 0)),
                    num_failures=int(row.get('Failure Count', 0)),
                    median_response_time=float(row.get('50%', 0) or 0),
                    p95_response_time=float(row.get('95%', 0) or 0),
                    p99_response_time=float(row.get('99%', 0) or 0),
                    avg_response_time=float(row.get('Average Response Time', 0) or 0),
                    min_response_time=float(row.get('Min Response Time', 0) or 0),
                    max_response_time=float(row.get('Max Response Time', 0) or 0),
                    rps=float(row.get('Requests/s', 0) or 0),
                )
                stats.append(endpoint)
            except (ValueError, KeyError) as e:
                print(f"Warning: Failed to parse row: {e}", file=sys.stderr)
                continue
    
    return stats


def parse_locust_stats_history(csv_path: Path) -> list[EndpointStats]:
    """
    Alternative parser for Locust stats_history.csv format.
    """
    # Implementation for history format if needed
    return parse_locust_stats(csv_path)


# =============================================================================
# SLO Evaluation
# =============================================================================


def evaluate_slo(
    stats: list[EndpointStats],
    p99_threshold_ms: float = DEFAULT_P99_THRESHOLD_MS,
    error_rate_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
    min_requests: int = DEFAULT_MIN_REQUESTS,
    critical_endpoints: Optional[list[str]] = None,
) -> SLOResult:
    """
    Evaluate SLO compliance from Locust statistics.
    
    Args:
        stats: List of endpoint statistics
        p99_threshold_ms: Maximum allowed p99 latency
        error_rate_threshold: Maximum allowed error rate (0.01 = 1%)
        min_requests: Minimum requests to consider valid
        critical_endpoints: Endpoints that must meet SLO (None = all)
    
    Returns:
        SLOResult with pass/fail and details
    """
    violations = []
    
    # Filter to critical endpoints if specified
    if critical_endpoints:
        stats = [s for s in stats if s.name in critical_endpoints]
    
    if not stats:
        return SLOResult(
            passed=False,
            p50_ms=0,
            p95_ms=0,
            p99_ms=0,
            error_rate=0,
            total_requests=0,
            failures=0,
            rps=0,
            violations=["No matching endpoint statistics found"],
        )
    
    # Aggregate metrics
    total_requests = sum(s.num_requests for s in stats)
    total_failures = sum(s.num_failures for s in stats)
    
    if total_requests < min_requests:
        violations.append(
            f"Insufficient requests: {total_requests} < {min_requests} minimum"
        )
    
    # Weighted averages for latency
    if total_requests > 0:
        p50_ms = sum(s.median_response_time * s.num_requests for s in stats) / total_requests
        p95_ms = sum(s.p95_response_time * s.num_requests for s in stats) / total_requests
        p99_ms = sum(s.p99_response_time * s.num_requests for s in stats) / total_requests
        error_rate = total_failures / total_requests
        total_rps = sum(s.rps for s in stats)
    else:
        p50_ms = p95_ms = p99_ms = 0
        error_rate = 1.0  # No requests = 100% failure
        total_rps = 0
    
    # Check p99 latency
    if p99_ms > p99_threshold_ms:
        violations.append(
            f"P99 latency {p99_ms:.1f}ms exceeds threshold {p99_threshold_ms}ms"
        )
    
    # Check error rate
    if error_rate > error_rate_threshold:
        violations.append(
            f"Error rate {error_rate*100:.2f}% exceeds threshold {error_rate_threshold*100:.2f}%"
        )
    
    # Check individual endpoints
    for stat in stats:
        if stat.p99_response_time > p99_threshold_ms * 1.5:  # Allow 50% headroom per endpoint
            violations.append(
                f"Endpoint '{stat.name}' p99 {stat.p99_response_time:.1f}ms is high"
            )
    
    return SLOResult(
        passed=len(violations) == 0,
        p50_ms=p50_ms,
        p95_ms=p95_ms,
        p99_ms=p99_ms,
        error_rate=error_rate,
        total_requests=total_requests,
        failures=total_failures,
        rps=total_rps,
        violations=violations,
    )


# =============================================================================
# Output Formatters
# =============================================================================


def format_terminal_output(result: SLOResult) -> str:
    """Format SLO result for terminal output."""
    lines = [
        "=" * 60,
        "SLO GATE EVALUATION",
        "=" * 60,
        "",
        f"Status: {'✅ PASSED' if result.passed else '❌ FAILED'}",
        "",
        "METRICS:",
        f"  Total Requests: {result.total_requests:,}",
        f"  Failures: {result.failures:,}",
        f"  Error Rate: {result.error_rate * 100:.2f}%",
        f"  RPS: {result.rps:.1f}",
        "",
        "LATENCY:",
        f"  P50: {result.p50_ms:.1f}ms",
        f"  P95: {result.p95_ms:.1f}ms",
        f"  P99: {result.p99_ms:.1f}ms",
    ]
    
    if result.violations:
        lines.extend([
            "",
            "VIOLATIONS:",
        ])
        for v in result.violations:
            lines.append(f"  ❌ {v}")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


def format_json_output(result: SLOResult) -> str:
    """Format SLO result as JSON."""
    return json.dumps({
        "passed": result.passed,
        "metrics": {
            "total_requests": result.total_requests,
            "failures": result.failures,
            "error_rate": result.error_rate,
            "rps": result.rps,
        },
        "latency": {
            "p50_ms": result.p50_ms,
            "p95_ms": result.p95_ms,
            "p99_ms": result.p99_ms,
        },
        "violations": result.violations,
    }, indent=2)


def format_github_actions_output(result: SLOResult) -> str:
    """Format output for GitHub Actions annotations."""
    lines = []
    
    if result.passed:
        lines.append(f"::notice::SLO Gate Passed - P99: {result.p99_ms:.1f}ms")
    else:
        for v in result.violations:
            lines.append(f"::error::{v}")
    
    # Set output variables
    lines.append(f"::set-output name=passed::{str(result.passed).lower()}")
    lines.append(f"::set-output name=p99_ms::{result.p99_ms:.1f}")
    lines.append(f"::set-output name=error_rate::{result.error_rate:.4f}")
    
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="SLO Gate - Evaluate load test results against SLO thresholds"
    )
    
    parser.add_argument(
        "--results",
        type=str,
        required=True,
        help="Path to Locust results CSV file (e.g., results_stats.csv)",
    )
    
    parser.add_argument(
        "--p99-threshold",
        type=float,
        default=DEFAULT_P99_THRESHOLD_MS,
        help=f"P99 latency threshold in ms (default: {DEFAULT_P99_THRESHOLD_MS})",
    )
    
    parser.add_argument(
        "--error-rate",
        type=float,
        default=DEFAULT_ERROR_RATE_THRESHOLD,
        help=f"Error rate threshold (default: {DEFAULT_ERROR_RATE_THRESHOLD})",
    )
    
    parser.add_argument(
        "--min-requests",
        type=int,
        default=DEFAULT_MIN_REQUESTS,
        help=f"Minimum requests required (default: {DEFAULT_MIN_REQUESTS})",
    )
    
    parser.add_argument(
        "--endpoints",
        type=str,
        nargs="*",
        help="Specific endpoints to evaluate (default: all)",
    )
    
    parser.add_argument(
        "--json-output",
        type=str,
        help="Write JSON results to file",
    )
    
    parser.add_argument(
        "--github-actions",
        action="store_true",
        help="Output in GitHub Actions format",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal output",
    )
    
    args = parser.parse_args()
    
    # Parse results
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"Error: Results file not found: {results_path}", file=sys.stderr)
        sys.exit(2)
    
    stats = parse_locust_stats(results_path)
    
    if not stats:
        print("Error: No statistics found in results file", file=sys.stderr)
        sys.exit(2)
    
    # Evaluate SLO
    result = evaluate_slo(
        stats,
        p99_threshold_ms=args.p99_threshold,
        error_rate_threshold=args.error_rate,
        min_requests=args.min_requests,
        critical_endpoints=args.endpoints,
    )
    
    # Output results
    if not args.quiet:
        print(format_terminal_output(result))
    
    if args.github_actions:
        print(format_github_actions_output(result))
    
    if args.json_output:
        with open(args.json_output, 'w') as f:
            f.write(format_json_output(result))
        if not args.quiet:
            print(f"\nJSON results written to: {args.json_output}")
    
    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
