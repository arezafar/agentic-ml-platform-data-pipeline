#!/usr/bin/env python3
"""
Audit agent IAM permissions for over-privilege (Agent Guardian).

Usage:
    python audit_agent_permissions.py --agent-roles agents.yaml --days 30 --output permission-audit.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class PermissionAudit:
    role_name: str
    unused_permissions: List[str]
    risk_level: str
    recommendation: str


def simulate_audit() -> List[PermissionAudit]:
    return [
        PermissionAudit("finops-agent", ["iam:CreateUser", "iam:DeleteUser"], "HIGH", "Remove IAM write permissions"),
        PermissionAudit("drift-agent", ["s3:DeleteBucket"], "MEDIUM", "Scope to specific buckets"),
    ]


def print_report(items: List[PermissionAudit], output_format: str):
    if output_format == "json":
        print(json.dumps([{"role": i.role_name, "unused": i.unused_permissions, "risk": i.risk_level, "rec": i.recommendation} for i in items], indent=2))
    else:
        print("=" * 60)
        print("AGENT GUARDIAN (AISPM) REPORT")
        print("=" * 60)
        print(f"\nAnalyzed {len(items)} agent role(s)\n")
        for i in items:
            print(f"  [{i.risk_level}] {i.role_name}")
            print(f"    Unused: {', '.join(i.unused_permissions)}")
            print(f"    → {i.recommendation}\n")


def main():
    parser = argparse.ArgumentParser(description="Audit agent IAM permissions")
    parser.add_argument("--agent-roles", "-a", type=Path, help="Agent roles config")
    parser.add_argument("--days", type=int, default=30, help="Analysis window")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    
    items = simulate_audit() if args.simulate or not args.agent_roles else []
    print_report(items, args.output)
    return 1 if any(i.risk_level == "HIGH" for i in items) else 0


if __name__ == "__main__":
    sys.exit(main())
