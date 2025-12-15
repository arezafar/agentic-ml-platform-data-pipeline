#!/usr/bin/env python3
"""
QA Skill - SLO Gate Runner

Wrapper script for running SLO gating in CI/CD pipelines.
Designed to be called directly or as a GitHub Action step.

Implements task:
- SLO-CI-01: Implement SLO Gating in Pipeline

Usage:
    python run_slo_gate.py --results locust_stats.csv
    python run_slo_gate.py --results locust_stats.csv --p99-threshold 50
    
    # In CI/CD
    python run_slo_gate.py --results results_stats.csv --github-actions
"""

import argparse
import os
import sys
from pathlib import Path

# Import the SLO gate implementation from assets
# This allows the script to be run from the skills directory
SCRIPT_DIR = Path(__file__).parent
LOAD_TESTS_DIR = SCRIPT_DIR.parent / "assets" / "load_tests"

sys.path.insert(0, str(LOAD_TESTS_DIR))

try:
    from slo_gate import (
        DEFAULT_ERROR_RATE_THRESHOLD,
        DEFAULT_MIN_REQUESTS,
        DEFAULT_P99_THRESHOLD_MS,
        EndpointStats,
        SLOResult,
        evaluate_slo,
        format_github_actions_output,
        format_json_output,
        format_terminal_output,
        parse_locust_stats,
    )
except ImportError:
    print("Error: Could not import slo_gate module from assets/load_tests/")
    print(f"Looked in: {LOAD_TESTS_DIR}")
    sys.exit(2)


def main():
    """Run SLO gate with command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run SLO gate validation on Locust results"
    )
    
    parser.add_argument(
        "--results",
        type=str,
        required=True,
        help="Path to Locust results CSV file",
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
        help="Specific endpoints to evaluate",
    )
    
    parser.add_argument(
        "--json-output",
        type=str,
        help="Write JSON results to file",
    )
    
    parser.add_argument(
        "--github-actions",
        action="store_true",
        help="Output for GitHub Actions",
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal output",
    )
    
    args = parser.parse_args()
    
    # Validate results file
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"❌ Error: Results file not found: {results_path}")
        sys.exit(2)
    
    # Parse and evaluate
    print(f"📊 Loading results from: {results_path}")
    stats = parse_locust_stats(results_path)
    
    if not stats:
        print("❌ Error: No statistics found in results file")
        sys.exit(2)
    
    print(f"📈 Found {len(stats)} endpoint(s)")
    
    result = evaluate_slo(
        stats,
        p99_threshold_ms=args.p99_threshold,
        error_rate_threshold=args.error_rate,
        min_requests=args.min_requests,
        critical_endpoints=args.endpoints,
    )
    
    # Output
    if not args.quiet:
        print(format_terminal_output(result))
    
    if args.github_actions:
        print(format_github_actions_output(result))
    
    if args.json_output:
        with open(args.json_output, 'w') as f:
            f.write(format_json_output(result))
        print(f"\n📝 JSON results written to: {args.json_output}")
    
    # Exit
    if result.passed:
        print("\n✅ SLO Gate: PASSED")
        sys.exit(0)
    else:
        print("\n❌ SLO Gate: FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
