#!/usr/bin/env python3
"""
Validate schema migrations for JSONB/GIN compliance (Schema Drift Detector).

This script analyzes Alembic migration files to ensure proper JSONB usage,
GIN indexing, and time-travel support for the Feature Store.

Usage:
    python validate_schema_migration.py --migration-dir ./alembic/versions
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class SchemaViolation:
    """Represents a schema violation."""
    file: str
    line: int
    violation_type: str
    message: str
    severity: str


def check_json_vs_jsonb(content: str, filepath: str) -> List[SchemaViolation]:
    """Check for JSON type usage (should be JSONB)."""
    violations = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        # Check for sa.JSON or JSON() without B
        if re.search(r"\bsa\.JSON\b(?!B)", line) or re.search(r"\bJSON\(\)(?!B)", line):
            violations.append(SchemaViolation(
                file=filepath,
                line=i,
                violation_type="JSON_NOT_JSONB",
                message="Use JSONB instead of JSON for GIN index support",
                severity="HIGH"
            ))
    
    return violations


def check_gin_indexes(content: str, filepath: str) -> List[SchemaViolation]:
    """Check for JSONB columns without GIN indexes."""
    violations = []
    
    # Find JSONB columns
    jsonb_columns = re.findall(r"sa\.Column\(['\"](\w+)['\"].*?(?:JSONB|jsonb)", content)
    
    # Check if GIN index exists for each
    for col in jsonb_columns:
        gin_pattern = rf"create_index.*{col}.*gin|GIN"
        if not re.search(gin_pattern, content, re.IGNORECASE):
            violations.append(SchemaViolation(
                file=filepath,
                line=0,  # Column-level, not line-specific
                violation_type="MISSING_GIN_INDEX",
                message=f"JSONB column '{col}' lacks GIN index for @> containment queries",
                severity="HIGH"
            ))
    
    return violations


def check_key_extraction_queries(content: str, filepath: str) -> List[SchemaViolation]:
    """Check for ->> operators in WHERE clauses without B-Tree index."""
    violations = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        # Check for ->> in execute statements
        if "->>" in line and ("WHERE" in line.upper() or "where" in line):
            violations.append(SchemaViolation(
                file=filepath,
                line=i,
                violation_type="UNINDEXED_KEY_EXTRACTION",
                message="Using ->> operator in WHERE clause without B-Tree index causes full table scan",
                severity="MEDIUM"
            ))
    
    return violations


def check_time_travel(content: str, filepath: str) -> List[SchemaViolation]:
    """Check for time-travel columns (event_time, valid_from)."""
    violations = []
    
    # Check if this looks like a feature table migration
    if "feature" in content.lower() or "Feature" in content:
        has_event_time = re.search(r"event_time|valid_from|created_at", content, re.IGNORECASE)
        if not has_event_time:
            violations.append(SchemaViolation(
                file=filepath,
                line=0,
                violation_type="MISSING_TIME_TRAVEL",
                message="Feature table lacks event_time/valid_from for snapshot isolation",
                severity="MEDIUM"
            ))
    
    return violations


def check_update_operations(content: str, filepath: str) -> List[SchemaViolation]:
    """Check for UPDATE operations on feature tables (should be append-only)."""
    violations = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        if re.search(r"\.update\(|UPDATE\s+\w*feature", line, re.IGNORECASE):
            violations.append(SchemaViolation(
                file=filepath,
                line=i,
                violation_type="NON_APPEND_UPDATE",
                message="Feature tables should be append-only; use INSERT for SCD Type 2",
                severity="MEDIUM"
            ))
    
    return violations


def validate_migration(filepath: Path) -> List[SchemaViolation]:
    """Validate a single migration file."""
    try:
        content = filepath.read_text()
    except Exception:
        return []
    
    violations = []
    str_path = str(filepath)
    
    violations.extend(check_json_vs_jsonb(content, str_path))
    violations.extend(check_gin_indexes(content, str_path))
    violations.extend(check_key_extraction_queries(content, str_path))
    violations.extend(check_time_travel(content, str_path))
    violations.extend(check_update_operations(content, str_path))
    
    return violations


def scan_migrations(migration_dir: Path, severity_filter: str = "LOW") -> List[SchemaViolation]:
    """Scan all migration files in directory."""
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    min_severity = severity_order.get(severity_filter, 3)
    
    all_violations = []
    for filepath in migration_dir.glob("*.py"):
        if filepath.name.startswith("_"):
            continue
        violations = validate_migration(filepath)
        for v in violations:
            if severity_order.get(v.severity, 3) <= min_severity:
                all_violations.append(v)
    
    return all_violations


def print_report(violations: List[SchemaViolation], output_format: str):
    """Print violation report."""
    if output_format == "json":
        import json
        data = [
            {
                "file": v.file,
                "line": v.line,
                "type": v.violation_type,
                "message": v.message,
                "severity": v.severity
            }
            for v in violations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("SCHEMA DRIFT DETECTOR REPORT")
        print("=" * 60)
        
        if not violations:
            print("\n✅ No schema violations detected")
        else:
            print(f"\n❌ Found {len(violations)} schema violation(s)\n")
            
            for v in sorted(violations, key=lambda x: (x.severity, x.file)):
                loc = f"{v.file}:{v.line}" if v.line > 0 else v.file
                print(f"[{v.severity}] {loc}")
                print(f"  Type: {v.violation_type}")
                print(f"  {v.message}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Validate schema migrations for JSONB/GIN compliance"
    )
    parser.add_argument(
        "--migration-dir", "-m",
        type=Path,
        required=True,
        help="Migration directory (e.g., alembic/versions)"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    parser.add_argument(
        "--severity",
        choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default="LOW",
        help="Minimum severity to report"
    )
    
    args = parser.parse_args()
    
    if not args.migration_dir.exists():
        print(f"Error: Directory not found: {args.migration_dir}")
        return 1
    
    violations = scan_migrations(args.migration_dir, args.severity)
    print_report(violations, args.output)
    
    # Exit with error if high severity violations found
    high_count = sum(1 for v in violations if v.severity in ("CRITICAL", "HIGH"))
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
