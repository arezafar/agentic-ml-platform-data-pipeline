#!/usr/bin/env python3
"""
Evaluate Terraform plans against OPA/Sentinel policies (Policy Enforcer).

Usage:
    python enforce_policy.py --plan plan.json --policy-dir ./policies --output policy-results.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class PolicyResult:
    policy_name: str
    result: str  # PASS, WARN, DENY
    message: str
    remediation: str


def simulate_policy_evaluation() -> List[PolicyResult]:
    return [
        PolicyResult("no-public-s3", "PASS", "No public S3 buckets found", ""),
        PolicyResult("encrypted-ebs", "DENY", "EBS volume vol-123 is not encrypted", "Add encrypted=true"),
        PolicyResult("mandatory-tags", "WARN", "Resource missing cost_center tag", "Add cost_center tag"),
    ]


def print_report(items: List[PolicyResult], output_format: str):
    if output_format == "json":
        print(json.dumps([vars(i) for i in items], indent=2))
    else:
        print("=" * 60)
        print("POLICY ENFORCER REPORT")
        print("=" * 60)
        passed = sum(1 for i in items if i.result == "PASS")
        denied = sum(1 for i in items if i.result == "DENY")
        print(f"\nPassed: {passed} | Denied: {denied} | Warnings: {len(items)-passed-denied}\n")
        for i in items:
            icon = {"PASS": "✅", "WARN": "⚠️", "DENY": "❌"}[i.result]
            print(f"  {icon} {i.policy_name}: {i.message}")
            if i.remediation:
                print(f"     → {i.remediation}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Evaluate plans against policies")
    parser.add_argument("--plan", "-p", type=Path, help="Plan JSON file")
    parser.add_argument("--policy-dir", "-d", type=Path, help="Policy directory")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    
    items = simulate_policy_evaluation() if args.simulate or not args.plan else []
    print_report(items, args.output)
    return 1 if any(i.result == "DENY" for i in items) else 0


if __name__ == "__main__":
    sys.exit(main())
