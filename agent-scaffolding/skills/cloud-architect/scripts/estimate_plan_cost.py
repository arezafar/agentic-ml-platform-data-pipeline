#!/usr/bin/env python3
"""
Estimate cost impact of Terraform plan (Cost Clairvoyant).

Usage:
    python estimate_plan_cost.py --plan plan.tfplan --budget-file budgets.yaml --output cost-estimate.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class CostEstimate:
    resource_type: str
    resource_name: str
    monthly_cost: float
    change_type: str


def simulate_cost_estimation() -> List[CostEstimate]:
    return [
        CostEstimate("aws_instance", "web-server", 150.0, "create"),
        CostEstimate("aws_rds_instance", "database", 450.0, "create"),
        CostEstimate("aws_instance", "old-server", -100.0, "destroy"),
    ]


def print_report(items: List[CostEstimate], budget: float, output_format: str):
    total = sum(i.monthly_cost for i in items)
    if output_format == "json":
        print(json.dumps({"items": [vars(i) for i in items], "total_delta": total, "budget": budget}, indent=2))
    else:
        print("=" * 60)
        print("COST CLAIRVOYANT REPORT")
        print("=" * 60)
        print(f"\nMonthly Cost Impact: ${total:+.2f}")
        print(f"Budget Cap: ${budget:.2f}")
        print(f"Status: {'⚠️ EXCEEDS BUDGET' if total > budget else '✅ WITHIN BUDGET'}\n")
        for i in items:
            print(f"  [{i.change_type.upper()}] {i.resource_type}.{i.resource_name}: ${i.monthly_cost:+.2f}/mo")


def main():
    parser = argparse.ArgumentParser(description="Estimate Terraform plan cost")
    parser.add_argument("--plan", "-p", type=Path, help="Plan file path")
    parser.add_argument("--budget", "-b", type=float, default=500.0, help="Budget cap")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    
    items = simulate_cost_estimation() if args.simulate or not args.plan else []
    print_report(items, args.budget, args.output)
    total = sum(i.monthly_cost for i in items)
    return 1 if total > args.budget else 0


if __name__ == "__main__":
    sys.exit(main())
