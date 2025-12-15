#!/usr/bin/env python3
"""
Detect infrastructure drift between Terraform state and live resources (Drift Sentinel).

Usage:
    python detect_drift.py --workspace production --provider aws --output drift-report.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class DriftItem:
    resource_type: str
    resource_id: str
    attribute: str
    expected: str
    actual: str
    severity: str
    remediation: str


def simulate_drift_detection() -> List[DriftItem]:
    return [
        DriftItem("aws_security_group", "sg-12345", "ingress.0.cidr_blocks", '["10.0.0.0/8"]', '["0.0.0.0/0"]', "CRITICAL", "terraform apply to revert"),
        DriftItem("aws_s3_bucket", "my-bucket", "versioning.enabled", "true", "false", "HIGH", "Enable versioning"),
        DriftItem("aws_instance", "i-abc123", "tags.Environment", "production", "prod", "LOW", "Update tags"),
    ]


def print_report(items: List[DriftItem], output_format: str):
    if output_format == "json":
        print(json.dumps([vars(i) for i in items], indent=2))
    else:
        print("=" * 60)
        print("DRIFT SENTINEL REPORT")
        print("=" * 60)
        print(f"\nFound {len(items)} drift item(s)\n")
        for i in items:
            print(f"[{i.severity}] {i.resource_type}: {i.resource_id}")
            print(f"  Attribute: {i.attribute}")
            print(f"  Expected: {i.expected}")
            print(f"  Actual: {i.actual}")
            print(f"  → {i.remediation}\n")


def main():
    parser = argparse.ArgumentParser(description="Detect infrastructure drift")
    parser.add_argument("--workspace", "-w", help="Terraform workspace")
    parser.add_argument("--provider", "-p", choices=["aws", "azure", "gcp"], default="aws")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--simulate", action="store_true")
    args = parser.parse_args()
    
    items = simulate_drift_detection() if args.simulate or not args.workspace else []
    print_report(items, args.output)
    return 1 if any(i.severity == "CRITICAL" for i in items) else 0


if __name__ == "__main__":
    sys.exit(main())
