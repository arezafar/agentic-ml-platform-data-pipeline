#!/usr/bin/env python3
"""
Optimize hybrid schema by analyzing JSONB key usage (Hybrid Schema Engineer).

This script analyzes JSONB column usage patterns and generates
column extraction DDL for frequently accessed keys.

Usage:
    python optimize_hybrid_schema.py --schema ml_features --threshold 0.8
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class SchemaRecommendation:
    """Represents a schema optimization recommendation."""
    table_name: str
    column_name: str
    recommendation_type: str
    message: str
    severity: str
    ddl: Optional[str] = None


def analyze_jsonb_keys(schema_file: Path) -> List[SchemaRecommendation]:
    """Analyze JSONB schema for optimization opportunities."""
    recommendations = []
    
    try:
        content = schema_file.read_text()
        schema = json.loads(content)
    except json.JSONDecodeError:
        return recommendations
    except FileNotFoundError:
        return recommendations
    
    for table in schema.get("tables", []):
        table_name = table.get("name", "unknown")
        
        for column in table.get("columns", []):
            col_name = column.get("name")
            col_type = column.get("type", "").lower()
            
            if "jsonb" in col_type or "json" in col_type:
                # Check for key patterns
                sample_keys = column.get("sample_keys", [])
                
                for key in sample_keys:
                    # Check key length
                    if len(key) > 3:
                        recommendations.append(SchemaRecommendation(
                            table_name=table_name,
                            column_name=col_name,
                            recommendation_type="KEY_ABBREVIATION",
                            message=f"Key '{key}' exceeds 3 characters; abbreviate to reduce storage overhead",
                            severity="MEDIUM"
                        ))
                    
                    # Check for extraction candidates
                    access_ratio = column.get("access_ratios", {}).get(key, 0)
                    if access_ratio > 0.8:
                        recommendations.append(SchemaRecommendation(
                            table_name=table_name,
                            column_name=col_name,
                            recommendation_type="COLUMN_EXTRACTION",
                            message=f"Key '{key}' accessed in {access_ratio:.0%} of queries; promote to relational column",
                            severity="HIGH",
                            ddl=f"ALTER TABLE {table_name} ADD COLUMN {key} TEXT GENERATED ALWAYS AS ({col_name} ->> '{key}') STORED;"
                        ))
    
    return recommendations


def analyze_migration_file(migration_file: Path) -> List[SchemaRecommendation]:
    """Analyze an Alembic migration for schema issues."""
    recommendations = []
    
    try:
        content = migration_file.read_text()
    except Exception:
        return recommendations
    
    import re
    
    # Check for JSON vs JSONB
    if re.search(r"\bsa\.JSON\b(?!B)", content):
        recommendations.append(SchemaRecommendation(
            table_name="migration",
            column_name="",
            recommendation_type="JSON_NOT_JSONB",
            message="Use JSONB instead of JSON for GIN index support",
            severity="HIGH"
        ))
    
    # Check for long key names in JSONB literals
    jsonb_keys = re.findall(r"'([a-zA-Z_][a-zA-Z0-9_]{3,})':", content)
    for key in set(jsonb_keys):
        if len(key) > 3:
            recommendations.append(SchemaRecommendation(
                table_name="migration",
                column_name="",
                recommendation_type="KEY_ABBREVIATION",
                message=f"JSONB key '{key}' exceeds 3 characters in migration",
                severity="LOW"
            ))
    
    return recommendations


def print_report(recommendations: List[SchemaRecommendation], output_format: str):
    """Print recommendation report."""
    if output_format == "json":
        data = [
            {
                "table": r.table_name,
                "column": r.column_name,
                "type": r.recommendation_type,
                "message": r.message,
                "severity": r.severity,
                "ddl": r.ddl
            }
            for r in recommendations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("HYBRID SCHEMA ENGINEER REPORT")
        print("=" * 60)
        
        if not recommendations:
            print("\n✅ No schema optimization opportunities detected")
        else:
            print(f"\n📊 Found {len(recommendations)} recommendation(s)\n")
            
            for r in sorted(recommendations, key=lambda x: x.severity):
                print(f"[{r.severity}] {r.table_name}.{r.column_name}")
                print(f"  Type: {r.recommendation_type}")
                print(f"  {r.message}")
                if r.ddl:
                    print(f"  DDL: {r.ddl}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze and optimize hybrid relational/JSONB schemas"
    )
    parser.add_argument(
        "--schema", "-s",
        type=Path,
        help="Path to schema JSON file or migration directory"
    )
    parser.add_argument(
        "--threshold", "-t",
        type=float,
        default=0.8,
        help="Access ratio threshold for column extraction (default: 0.8)"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    recommendations = []
    
    if args.schema:
        if args.schema.is_file():
            if args.schema.suffix == ".json":
                recommendations = analyze_jsonb_keys(args.schema)
            elif args.schema.suffix == ".py":
                recommendations = analyze_migration_file(args.schema)
        elif args.schema.is_dir():
            for f in args.schema.glob("*.py"):
                recommendations.extend(analyze_migration_file(f))
    
    print_report(recommendations, args.output)
    
    # Exit with error if high severity recommendations exist
    high_count = sum(1 for r in recommendations if r.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
