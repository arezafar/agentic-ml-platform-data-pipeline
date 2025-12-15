#!/usr/bin/env python3
"""
Validate connection pool configuration (Concurrency Architect).

This script verifies that connection pool settings are appropriate
for the database capacity and application requirements.

Usage:
    python validate_connection_pool.py --app-config src/api/config.py --pg-version 15
"""

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class PoolIssue:
    """Represents a connection pool configuration issue."""
    issue_type: str
    message: str
    severity: str
    current_value: Optional[str] = None
    recommended_value: Optional[str] = None


def get_cpu_count() -> int:
    """Get the number of CPU cores."""
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def calculate_optimal_pool_size(cores: int, spindles: int = 1) -> int:
    """Calculate optimal pool size using the formula: (cores * 2) + spindles."""
    return (cores * 2) + spindles


def analyze_python_config(config_file: Path) -> List[PoolIssue]:
    """Analyze a Python configuration file for pool settings."""
    issues = []
    
    try:
        content = config_file.read_text()
    except Exception:
        return issues
    
    # Parse for asyncpg vs psycopg2
    if "psycopg2" in content and "async" in content.lower():
        issues.append(PoolIssue(
            issue_type="SYNC_DRIVER_IN_ASYNC",
            message="psycopg2 (sync driver) detected in async context; use asyncpg instead",
            severity="HIGH"
        ))
    
    # Check for pool size configuration
    pool_size_match = re.search(r"pool_size\s*[=:]\s*(\d+)", content)
    max_overflow_match = re.search(r"max_overflow\s*[=:]\s*(\d+)", content)
    
    cores = get_cpu_count()
    optimal_size = calculate_optimal_pool_size(cores)
    
    if pool_size_match:
        pool_size = int(pool_size_match.group(1))
        
        if pool_size > 50:
            issues.append(PoolIssue(
                issue_type="POOL_SIZE_TOO_LARGE",
                message=f"Pool size ({pool_size}) exceeds recommended maximum (50)",
                severity="HIGH",
                current_value=str(pool_size),
                recommended_value="50 or less"
            ))
        elif pool_size < optimal_size // 2:
            issues.append(PoolIssue(
                issue_type="POOL_SIZE_TOO_SMALL",
                message=f"Pool size ({pool_size}) may be insufficient for {cores} CPU cores",
                severity="MEDIUM",
                current_value=str(pool_size),
                recommended_value=str(optimal_size)
            ))
    else:
        issues.append(PoolIssue(
            issue_type="NO_POOL_SIZE",
            message="No explicit pool_size found; relying on defaults may cause issues",
            severity="LOW"
        ))
    
    # Check for min_size (asyncpg)
    if "asyncpg" in content:
        min_size_match = re.search(r"min_size\s*[=:]\s*(\d+)", content)
        if not min_size_match:
            issues.append(PoolIssue(
                issue_type="NO_MIN_SIZE",
                message="asyncpg pool without min_size; set min_size for connection warmup",
                severity="LOW"
            ))
    
    # Check for timeout configuration
    if "timeout" not in content.lower() and "connect_timeout" not in content.lower():
        issues.append(PoolIssue(
            issue_type="NO_TIMEOUT",
            message="No connection timeout configured; add timeout to prevent hanging",
            severity="MEDIUM"
        ))
    
    return issues


def analyze_yaml_config(config_file: Path) -> List[PoolIssue]:
    """Analyze a YAML configuration file for pool settings."""
    issues = []
    
    try:
        import yaml
        content = yaml.safe_load(config_file.read_text())
    except ImportError:
        # Fallback to regex
        return analyze_yaml_regex(config_file)
    except Exception:
        return issues
    
    # Check database configuration
    db_config = content.get("database", {})
    pool_size = db_config.get("pool_size")
    
    if pool_size and pool_size > 50:
        issues.append(PoolIssue(
            issue_type="POOL_SIZE_TOO_LARGE",
            message=f"Pool size ({pool_size}) exceeds recommended maximum",
            severity="HIGH",
            current_value=str(pool_size),
            recommended_value="50"
        ))
    
    return issues


def analyze_yaml_regex(config_file: Path) -> List[PoolIssue]:
    """Fallback regex-based YAML analysis."""
    issues = []
    
    try:
        content = config_file.read_text()
    except Exception:
        return issues
    
    pool_match = re.search(r"pool_size:\s*(\d+)", content)
    if pool_match:
        pool_size = int(pool_match.group(1))
        if pool_size > 50:
            issues.append(PoolIssue(
                issue_type="POOL_SIZE_TOO_LARGE",
                message=f"Pool size ({pool_size}) exceeds recommended maximum",
                severity="HIGH",
                current_value=str(pool_size),
                recommended_value="50"
            ))
    
    return issues


def simulate_analysis() -> List[PoolIssue]:
    """Generate sample issues for demonstration."""
    cores = get_cpu_count()
    optimal = calculate_optimal_pool_size(cores)
    
    return [
        PoolIssue(
            issue_type="POOL_SIZE_RECOMMENDATION",
            message=f"For {cores} CPU cores, optimal pool size is {optimal} connections",
            severity="INFO",
            current_value=f"{cores} cores",
            recommended_value=f"pool_size={optimal}"
        ),
        PoolIssue(
            issue_type="SYNC_DRIVER_IN_ASYNC",
            message="psycopg2 detected in FastAPI routes; migrate to asyncpg",
            severity="HIGH"
        ),
        PoolIssue(
            issue_type="NO_TIMEOUT",
            message="No connection timeout; add connect_timeout=10 to prevent hanging",
            severity="MEDIUM"
        )
    ]


def print_report(issues: List[PoolIssue], output_format: str):
    """Print issue report."""
    if output_format == "json":
        data = [
            {
                "type": i.issue_type,
                "message": i.message,
                "severity": i.severity,
                "current": i.current_value,
                "recommended": i.recommended_value
            }
            for i in issues
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("CONCURRENCY ARCHITECT REPORT")
        print("=" * 60)
        
        cores = get_cpu_count()
        optimal = calculate_optimal_pool_size(cores)
        print(f"\nSystem: {cores} CPU cores")
        print(f"Recommended pool size: {optimal} (formula: cores*2 + spindles)")
        
        if not issues:
            print("\n✅ Connection pool configuration looks good")
        else:
            print(f"\n🔌 Found {len(issues)} issue(s)\n")
            
            for i in sorted(issues, key=lambda x: ("HIGH", "MEDIUM", "LOW", "INFO").index(x.severity) if x.severity in ("HIGH", "MEDIUM", "LOW", "INFO") else 3):
                print(f"[{i.severity}] {i.issue_type}")
                print(f"  {i.message}")
                if i.current_value and i.recommended_value:
                    print(f"  Current: {i.current_value}")
                    print(f"  Recommended: {i.recommended_value}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate connection pool configuration"
    )
    parser.add_argument(
        "--app-config", "-c",
        type=Path,
        help="Path to application config file (Python or YAML)"
    )
    parser.add_argument(
        "--pg-version",
        type=int,
        default=15,
        help="PostgreSQL version (default: 15)"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run simulation for demonstration"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    if args.simulate:
        issues = simulate_analysis()
    elif args.app_config:
        if args.app_config.suffix == ".py":
            issues = analyze_python_config(args.app_config)
        elif args.app_config.suffix in (".yaml", ".yml"):
            issues = analyze_yaml_config(args.app_config)
        else:
            issues = []
            print(f"Unsupported config file type: {args.app_config.suffix}")
    else:
        issues = []
        cores = get_cpu_count()
        print(f"System has {cores} CPU cores")
        print(f"Optimal pool size: {calculate_optimal_pool_size(cores)}")
        print("\nProvide --app-config or use --simulate for full analysis")
    
    print_report(issues, args.output)
    
    high_count = sum(1 for i in issues if i.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
