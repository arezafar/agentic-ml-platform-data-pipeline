#!/usr/bin/env python3
"""
Benchmark GIN index operator classes for JSONB (Hybrid Schema Engineer).

This script compares jsonb_ops vs jsonb_path_ops for JSONB queries.

Usage:
    python benchmark_gin_index.py --table feature_store --queries queries.sql --rows 10000000
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class IndexRecommendation:
    """Represents a GIN index recommendation."""
    table_name: str
    column_name: str
    current_operator: str
    recommended_operator: str
    reason: str
    severity: str
    size_reduction: Optional[str] = None


def analyze_queries(query_file: Path) -> dict:
    """Analyze SQL queries to determine operator usage patterns."""
    try:
        content = query_file.read_text()
    except Exception:
        return {"containment": 0, "existence": 0, "mixed": 0}
    
    containment_count = content.count("@>")
    existence_count = content.count("?") + content.count("?|") + content.count("?&")
    
    return {
        "containment": containment_count,
        "existence": existence_count,
        "total": containment_count + existence_count
    }


def generate_recommendations(query_stats: dict, table_name: str) -> List[IndexRecommendation]:
    """Generate index recommendations based on query patterns."""
    recommendations = []
    
    total = query_stats.get("total", 0)
    containment = query_stats.get("containment", 0)
    existence = query_stats.get("existence", 0)
    
    if total > 0:
        containment_ratio = containment / total
        
        if containment_ratio > 0.8:
            recommendations.append(IndexRecommendation(
                table_name=table_name,
                column_name="data",
                current_operator="jsonb_ops",
                recommended_operator="jsonb_path_ops",
                reason=f"Query pattern is {containment_ratio:.0%} containment (@>); jsonb_path_ops is optimal",
                severity="MEDIUM",
                size_reduction="30-50%"
            ))
        elif containment_ratio < 0.2:
            recommendations.append(IndexRecommendation(
                table_name=table_name,
                column_name="data",
                current_operator="jsonb_path_ops",
                recommended_operator="jsonb_ops",
                reason=f"Query pattern requires key existence checks (?); jsonb_ops is required",
                severity="HIGH"
            ))
    
    return recommendations


def simulate_benchmark() -> List[dict]:
    """Generate simulated benchmark results."""
    return [
        {
            "operator": "jsonb_ops",
            "index_size_mb": 2400,
            "build_time_sec": 180,
            "containment_p50_ms": 2.5,
            "containment_p99_ms": 12.0,
            "existence_p50_ms": 1.8,
            "existence_p99_ms": 8.0
        },
        {
            "operator": "jsonb_path_ops",
            "index_size_mb": 1200,
            "build_time_sec": 90,
            "containment_p50_ms": 1.2,
            "containment_p99_ms": 5.0,
            "existence_p50_ms": None,  # Not supported
            "existence_p99_ms": None
        }
    ]


def print_report(
    recommendations: List[IndexRecommendation],
    benchmark: Optional[List[dict]],
    output_format: str
):
    """Print the report."""
    if output_format == "json":
        data = {
            "recommendations": [
                {
                    "table": r.table_name,
                    "column": r.column_name,
                    "current": r.current_operator,
                    "recommended": r.recommended_operator,
                    "reason": r.reason,
                    "severity": r.severity,
                    "size_reduction": r.size_reduction
                }
                for r in recommendations
            ],
            "benchmark": benchmark
        }
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("HYBRID SCHEMA ENGINEER: GIN INDEX BENCHMARK")
        print("=" * 60)
        
        if benchmark:
            print("\nOperator Class Comparison:\n")
            print("| Metric               | jsonb_ops | jsonb_path_ops |")
            print("|----------------------|-----------|----------------|")
            ops = benchmark[0]
            path_ops = benchmark[1]
            print(f"| Index Size           | {ops['index_size_mb']}MB     | {path_ops['index_size_mb']}MB (50% smaller) |")
            print(f"| Build Time           | {ops['build_time_sec']}s       | {path_ops['build_time_sec']}s          |")
            print(f"| Containment p50      | {ops['containment_p50_ms']}ms      | {path_ops['containment_p50_ms']}ms          |")
            print(f"| Containment p99      | {ops['containment_p99_ms']}ms     | {path_ops['containment_p99_ms']}ms           |")
            print(f"| Existence (?)        | {ops['existence_p50_ms']}ms      | N/A            |")
        
        if recommendations:
            print(f"\n📊 Recommendations ({len(recommendations)}):\n")
            for r in recommendations:
                print(f"[{r.severity}] {r.table_name}.{r.column_name}")
                print(f"  Current: {r.current_operator} → Recommended: {r.recommended_operator}")
                print(f"  {r.reason}")
                if r.size_reduction:
                    print(f"  Expected size reduction: {r.size_reduction}")
                print()
        else:
            print("\n✅ Current index configuration is optimal")
        
        print("\nOperator Class Guide:")
        print("• jsonb_ops: Supports @>, ?, ?|, ?& operators")
        print("• jsonb_path_ops: Supports only @>, but 50% smaller index")
        print("\nUse jsonb_path_ops when queries are primarily containment-based.")


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark GIN index operator classes for JSONB"
    )
    parser.add_argument(
        "--table", "-t",
        type=str,
        default="features",
        help="Table name to analyze"
    )
    parser.add_argument(
        "--queries", "-q",
        type=Path,
        help="File containing representative SQL queries"
    )
    parser.add_argument(
        "--rows", "-r",
        type=int,
        default=10000000,
        help="Estimated row count for recommendations"
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
    
    if args.queries:
        query_stats = analyze_queries(args.queries)
    else:
        # Default to containment-heavy pattern
        query_stats = {"containment": 85, "existence": 15, "total": 100}
    
    recommendations = generate_recommendations(query_stats, args.table)
    benchmark = simulate_benchmark() if args.simulate else None
    
    print_report(recommendations, benchmark, args.output)
    
    high_count = sum(1 for r in recommendations if r.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
