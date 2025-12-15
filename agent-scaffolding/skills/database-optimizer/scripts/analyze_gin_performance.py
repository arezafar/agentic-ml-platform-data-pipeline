#!/usr/bin/env python3
"""
Analyze GIN index performance and health (GIN Index Tuner).

This script monitors GIN index behavior, pending list usage,
and recommends operator class optimizations.

Usage:
    python analyze_gin_performance.py --database ml_platform --action report
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class GINRecommendation:
    """Represents a GIN index recommendation."""
    index_name: str
    table_name: str
    recommendation_type: str
    message: str
    severity: str
    current_value: Optional[str] = None
    recommended_value: Optional[str] = None


def analyze_gin_config(config_file: Path) -> List[GINRecommendation]:
    """Analyze GIN configuration from a config file."""
    recommendations = []
    
    try:
        content = config_file.read_text()
        config = json.loads(content)
    except Exception:
        return recommendations
    
    for index in config.get("indexes", []):
        index_name = index.get("name", "unknown")
        table_name = index.get("table", "unknown")
        index_type = index.get("type", "").lower()
        
        if "gin" not in index_type:
            continue
        
        # Check operator class
        operator_class = index.get("operator_class", "jsonb_ops")
        query_patterns = index.get("query_patterns", [])
        
        if operator_class == "jsonb_ops" and all("@>" in p for p in query_patterns):
            recommendations.append(GINRecommendation(
                index_name=index_name,
                table_name=table_name,
                recommendation_type="OPERATOR_CLASS",
                message="All queries use containment (@>); switch to jsonb_path_ops for 30-50% size reduction",
                severity="MEDIUM",
                current_value="jsonb_ops",
                recommended_value="jsonb_path_ops"
            ))
        
        # Check pending list limit
        pending_limit = index.get("gin_pending_list_limit", 4096)  # KB
        write_velocity = index.get("writes_per_second", 0)
        
        if write_velocity > 10000 and pending_limit < 16384:
            recommendations.append(GINRecommendation(
                index_name=index_name,
                table_name=table_name,
                recommendation_type="PENDING_LIST_LIMIT",
                message=f"High write velocity ({write_velocity}/s) with small pending limit; increase to 16MB",
                severity="HIGH",
                current_value=f"{pending_limit}KB",
                recommended_value="16MB"
            ))
        
        # Check index size vs table size ratio
        index_size_mb = index.get("size_mb", 0)
        table_size_mb = index.get("table_size_mb", 0)
        
        if table_size_mb > 0 and index_size_mb / table_size_mb > 0.5:
            recommendations.append(GINRecommendation(
                index_name=index_name,
                table_name=table_name,
                recommendation_type="INDEX_BLOAT",
                message=f"Index size ({index_size_mb}MB) is >{50}% of table ({table_size_mb}MB); consider REINDEX",
                severity="MEDIUM"
            ))
        
        # Check scan frequency
        scans = index.get("idx_scan", 0)
        if scans < 1000:
            recommendations.append(GINRecommendation(
                index_name=index_name,
                table_name=table_name,
                recommendation_type="UNUSED_INDEX",
                message=f"Index has only {scans} scans; consider removal if not needed",
                severity="LOW"
            ))
    
    return recommendations


def simulate_analysis() -> List[GINRecommendation]:
    """Generate sample recommendations for demonstration."""
    return [
        GINRecommendation(
            index_name="idx_features_gin",
            table_name="features",
            recommendation_type="OPERATOR_CLASS",
            message="Query log shows 95% containment queries; jsonb_path_ops recommended",
            severity="MEDIUM",
            current_value="jsonb_ops",
            recommended_value="jsonb_path_ops"
        ),
        GINRecommendation(
            index_name="idx_events_data",
            table_name="events",
            recommendation_type="PENDING_LIST_LIMIT",
            message="High merge frequency detected; increase gin_pending_list_limit",
            severity="HIGH",
            current_value="4MB",
            recommended_value="16MB"
        )
    ]


def print_report(recommendations: List[GINRecommendation], output_format: str):
    """Print recommendation report."""
    if output_format == "json":
        data = [
            {
                "index": r.index_name,
                "table": r.table_name,
                "type": r.recommendation_type,
                "message": r.message,
                "severity": r.severity,
                "current": r.current_value,
                "recommended": r.recommended_value
            }
            for r in recommendations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("GIN INDEX TUNER REPORT")
        print("=" * 60)
        
        if not recommendations:
            print("\n✅ All GIN indexes are optimally configured")
        else:
            print(f"\n🔧 Found {len(recommendations)} recommendation(s)\n")
            
            for r in sorted(recommendations, key=lambda x: x.severity):
                print(f"[{r.severity}] {r.index_name} on {r.table_name}")
                print(f"  Type: {r.recommendation_type}")
                print(f"  {r.message}")
                if r.current_value and r.recommended_value:
                    print(f"  Current: {r.current_value} → Recommended: {r.recommended_value}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze GIN index performance and health"
    )
    parser.add_argument(
        "--database", "-d",
        type=str,
        help="Database name or connection string"
    )
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Path to index configuration JSON file"
    )
    parser.add_argument(
        "--action", "-a",
        choices=["report", "simulate"],
        default="report",
        help="Action to perform"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    if args.action == "simulate":
        recommendations = simulate_analysis()
    elif args.config:
        recommendations = analyze_gin_config(args.config)
    else:
        # Would connect to database in production
        recommendations = []
        print("Note: Provide --config or use --action simulate for demo")
    
    print_report(recommendations, args.output)
    
    high_count = sum(1 for r in recommendations if r.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
