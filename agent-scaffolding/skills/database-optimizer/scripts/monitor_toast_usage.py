#!/usr/bin/env python3
"""
Monitor TOAST table usage and compression efficiency (TOAST Whisperer).

This script analyzes TOAST storage overhead and recommends
STORAGE strategies and compression settings.

Usage:
    python monitor_toast_usage.py --table features --alert-threshold 0.15
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class TOASTRecommendation:
    """Represents a TOAST optimization recommendation."""
    table_name: str
    column_name: str
    recommendation_type: str
    message: str
    severity: str
    toast_ratio: Optional[float] = None


def analyze_toast_config(config_file: Path, alert_threshold: float) -> List[TOASTRecommendation]:
    """Analyze TOAST configuration from a config file."""
    recommendations = []
    
    try:
        content = config_file.read_text()
        config = json.loads(content)
    except Exception:
        return recommendations
    
    for table in config.get("tables", []):
        table_name = table.get("name", "unknown")
        table_size = table.get("size_bytes", 0)
        toast_size = table.get("toast_size_bytes", 0)
        
        if table_size > 0:
            toast_ratio = toast_size / table_size
            
            if toast_ratio > alert_threshold:
                recommendations.append(TOASTRecommendation(
                    table_name=table_name,
                    column_name="*",
                    recommendation_type="TOAST_OVERHEAD",
                    message=f"TOAST table is {toast_ratio:.1%} of main table size; exceeds {alert_threshold:.0%} threshold",
                    severity="HIGH",
                    toast_ratio=toast_ratio
                ))
        
        for column in table.get("columns", []):
            col_name = column.get("name")
            storage = column.get("storage", "extended")
            avg_size = column.get("avg_size_bytes", 0)
            access_freq = column.get("access_frequency", "high")
            
            # Check if frequently accessed column is toasted
            if avg_size > 2048 and access_freq == "high" and storage != "main":
                recommendations.append(TOASTRecommendation(
                    table_name=table_name,
                    column_name=col_name,
                    recommendation_type="STORAGE_STRATEGY",
                    message=f"Hot column '{col_name}' (avg {avg_size}B) uses {storage}; consider STORAGE MAIN to avoid TOAST lookups",
                    severity="MEDIUM"
                ))
            
            # Check compression
            compression = column.get("compression", "pglz")
            if avg_size > 10000 and compression == "pglz":
                recommendations.append(TOASTRecommendation(
                    table_name=table_name,
                    column_name=col_name,
                    recommendation_type="COMPRESSION",
                    message=f"Large column '{col_name}' uses pglz; lz4 offers faster decompression for hot data",
                    severity="LOW"
                ))
    
    return recommendations


def simulate_analysis(alert_threshold: float) -> List[TOASTRecommendation]:
    """Generate sample recommendations for demonstration."""
    return [
        TOASTRecommendation(
            table_name="features",
            column_name="*",
            recommendation_type="TOAST_OVERHEAD",
            message=f"TOAST table is 18% of main table; exceeds {alert_threshold:.0%} threshold",
            severity="HIGH",
            toast_ratio=0.18
        ),
        TOASTRecommendation(
            table_name="features",
            column_name="embedding_vector",
            recommendation_type="STORAGE_STRATEGY",
            message="Hot embedding column (avg 4KB) uses extended; STORAGE MAIN recommended",
            severity="MEDIUM"
        ),
        TOASTRecommendation(
            table_name="events",
            column_name="payload",
            recommendation_type="COMPRESSION",
            message="Large payload column uses pglz; consider lz4 for faster access",
            severity="LOW"
        )
    ]


def print_report(recommendations: List[TOASTRecommendation], output_format: str):
    """Print recommendation report."""
    if output_format == "json":
        data = [
            {
                "table": r.table_name,
                "column": r.column_name,
                "type": r.recommendation_type,
                "message": r.message,
                "severity": r.severity,
                "toast_ratio": r.toast_ratio
            }
            for r in recommendations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("TOAST WHISPERER REPORT")
        print("=" * 60)
        
        if not recommendations:
            print("\n✅ TOAST storage is within acceptable limits")
        else:
            print(f"\n💾 Found {len(recommendations)} recommendation(s)\n")
            
            for r in sorted(recommendations, key=lambda x: x.severity):
                loc = f"{r.table_name}" if r.column_name == "*" else f"{r.table_name}.{r.column_name}"
                print(f"[{r.severity}] {loc}")
                print(f"  Type: {r.recommendation_type}")
                print(f"  {r.message}")
                if r.toast_ratio:
                    print(f"  TOAST Ratio: {r.toast_ratio:.1%}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor TOAST table usage and compression efficiency"
    )
    parser.add_argument(
        "--table", "-t",
        type=str,
        help="Table name to analyze"
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to table configuration JSON file"
    )
    parser.add_argument(
        "--alert-threshold", "-a",
        type=float,
        default=0.15,
        help="TOAST ratio threshold for alerts (default: 0.15)"
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
        recommendations = simulate_analysis(args.alert_threshold)
    elif args.config:
        recommendations = analyze_toast_config(args.config, args.alert_threshold)
    else:
        recommendations = []
        print("Note: Provide --config or use --simulate for demo")
    
    print_report(recommendations, args.output)
    
    high_count = sum(1 for r in recommendations if r.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
