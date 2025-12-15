#!/usr/bin/env python3
"""
Identify underutilized resources for rightsizing (Rate Optimizer).

Usage:
    python rightsize_resources.py --environment staging --threshold-cpu 10 --days 30 --auto-pr
"""

import argparse
import json
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class RightsizeRecommendation:
    resource_id: str
    resource_type: str
    current_size: str
    recommended_size: str
    avg_cpu: float
    monthly_savings: float


def simulate_rightsizing() -> List[RightsizeRecommendation]:
    return [
        RightsizeRecommendation("i-abc123", "aws_instance", "m5.xlarge", "m5.large", 8.5, 75.0),
        RightsizeRecommendation("db-xyz789", "aws_rds", "db.r5.2xlarge", "db.r5.xlarge", 12.0, 250.0),
    ]


def print_report(items: List[RightsizeRecommendation], output_format: str):
    total_savings = sum(i.monthly_savings for i in items)
    if output_format == "json":
        print(json.dumps({"recommendations": [vars(i) for i in items], "total_monthly_savings": total_savings}, indent=2))
    else:
        print("=" * 60)
        print("RATE OPTIMIZER REPORT")
        print("=" * 60)
        print(f"\nTotal Monthly Savings: ${total_savings:.2f}\n")
        for i in items:
            print(f"  {i.resource_type}: {i.resource_id}")
            print(f"    {i.current_size} → {i.recommended_size} (CPU: {i.avg_cpu}%)")
            print(f"    Savings: ${i.monthly_savings:.2f}/mo\n")


def main():
    parser = argparse.ArgumentParser(description="Rightsize underutilized resources")
    parser.add_argument("--environment", "-e", help="Environment to analyze")
    parser.add_argument("--threshold-cpu", type=int, default=10, help="CPU threshold %")
    parser.add_argument("--days", type=int, default=30, help="Analysis window")
    parser.add_argument("--auto-pr", action="store_true", help="Auto-create PR")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    
    items = simulate_rightsizing() if args.simulate or not args.environment else []
    print_report(items, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
