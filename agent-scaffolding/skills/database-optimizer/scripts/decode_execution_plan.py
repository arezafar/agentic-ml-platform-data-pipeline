#!/usr/bin/env python3
"""
Decode and analyze execution plans (Plan Decoder).

This script parses EXPLAIN ANALYZE output to identify
query bottlenecks and recommend optimizations.

Usage:
    python decode_execution_plan.py --query-file slow_query.sql --output json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class PlanIssue:
    """Represents an issue found in an execution plan."""
    issue_type: str
    node_type: str
    message: str
    severity: str
    estimated_rows: Optional[int] = None
    actual_rows: Optional[int] = None
    buffer_hit_ratio: Optional[float] = None


def parse_explain_output(explain_text: str) -> List[PlanIssue]:
    """Parse EXPLAIN ANALYZE output for issues."""
    issues = []
    lines = explain_text.split("\n")
    
    for i, line in enumerate(lines):
        # Check for Seq Scan on large tables
        seq_scan_match = re.search(r"Seq Scan on (\w+).*rows=(\d+)", line)
        if seq_scan_match:
            table_name = seq_scan_match.group(1)
            rows = int(seq_scan_match.group(2))
            if rows > 1000000:
                issues.append(PlanIssue(
                    issue_type="SEQ_SCAN_LARGE_TABLE",
                    node_type="Seq Scan",
                    message=f"Sequential scan on {table_name} ({rows:,} rows); consider adding index",
                    severity="CRITICAL",
                    estimated_rows=rows
                ))
        
        # Check for estimation errors
        rows_match = re.search(r"rows=(\d+).*actual.*rows=(\d+)", line)
        if rows_match:
            estimated = int(rows_match.group(1))
            actual = int(rows_match.group(2))
            if estimated > 0:
                ratio = actual / estimated
                if ratio > 10 or ratio < 0.1:
                    issues.append(PlanIssue(
                        issue_type="ESTIMATION_ERROR",
                        node_type="any",
                        message=f"Row estimation error: estimated={estimated:,}, actual={actual:,} ({ratio:.1f}x)",
                        severity="HIGH",
                        estimated_rows=estimated,
                        actual_rows=actual
                    ))
        
        # Check for Nested Loop with large outer
        if "Nested Loop" in line:
            # Look ahead for the outer relation size
            for j in range(i+1, min(i+5, len(lines))):
                outer_match = re.search(r"actual.*rows=(\d+)", lines[j])
                if outer_match:
                    outer_rows = int(outer_match.group(1))
                    if outer_rows > 10000:
                        issues.append(PlanIssue(
                            issue_type="NESTED_LOOP_LARGE_OUTER",
                            node_type="Nested Loop",
                            message=f"Nested Loop with {outer_rows:,} outer rows; consider Hash Join",
                            severity="HIGH",
                            actual_rows=outer_rows
                        ))
                    break
        
        # Check buffer hit ratio
        buffer_match = re.search(r"Buffers: shared hit=(\d+)(?: read=(\d+))?", line)
        if buffer_match:
            hits = int(buffer_match.group(1))
            reads = int(buffer_match.group(2)) if buffer_match.group(2) else 0
            total = hits + reads
            if total > 0:
                hit_ratio = hits / total
                if hit_ratio < 0.99 and total > 1000:
                    issues.append(PlanIssue(
                        issue_type="LOW_BUFFER_HIT_RATIO",
                        node_type="buffer",
                        message=f"Buffer hit ratio {hit_ratio:.1%} (hits={hits:,}, reads={reads:,}); increase shared_buffers or optimize query",
                        severity="MEDIUM",
                        buffer_hit_ratio=hit_ratio
                    ))
        
        # Check for Bitmap Heap Scan (indicates low correlation)
        if "Bitmap Heap Scan" in line:
            issues.append(PlanIssue(
                issue_type="BITMAP_HEAP_SCAN",
                node_type="Bitmap Heap Scan",
                message="Bitmap Heap Scan indicates low index-heap correlation; consider CLUSTER",
                severity="LOW"
            ))
    
    return issues


def analyze_query_file(query_file: Path) -> List[PlanIssue]:
    """Analyze a file containing EXPLAIN ANALYZE output."""
    try:
        content = query_file.read_text()
        return parse_explain_output(content)
    except Exception as e:
        print(f"Error reading file: {e}")
        return []


def simulate_analysis() -> List[PlanIssue]:
    """Generate sample issues for demonstration."""
    return [
        PlanIssue(
            issue_type="SEQ_SCAN_LARGE_TABLE",
            node_type="Seq Scan",
            message="Sequential scan on features (5,000,000 rows); add GIN index on data column",
            severity="CRITICAL",
            estimated_rows=5000000
        ),
        PlanIssue(
            issue_type="ESTIMATION_ERROR",
            node_type="any",
            message="Row estimation error on JSONB filter: estimated=100, actual=50,000 (500x)",
            severity="HIGH",
            estimated_rows=100,
            actual_rows=50000
        ),
        PlanIssue(
            issue_type="LOW_BUFFER_HIT_RATIO",
            node_type="buffer",
            message="Buffer hit ratio 85% indicates working set exceeds shared_buffers",
            severity="MEDIUM",
            buffer_hit_ratio=0.85
        )
    ]


def print_report(issues: List[PlanIssue], output_format: str):
    """Print issue report."""
    if output_format == "json":
        data = [
            {
                "type": i.issue_type,
                "node": i.node_type,
                "message": i.message,
                "severity": i.severity,
                "estimated_rows": i.estimated_rows,
                "actual_rows": i.actual_rows,
                "buffer_hit_ratio": i.buffer_hit_ratio
            }
            for i in issues
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("PLAN DECODER REPORT")
        print("=" * 60)
        
        if not issues:
            print("\n✅ No significant issues found in execution plan")
        else:
            print(f"\n⚠️  Found {len(issues)} issue(s)\n")
            
            for i in sorted(issues, key=lambda x: ("CRITICAL", "HIGH", "MEDIUM", "LOW").index(x.severity)):
                print(f"[{i.severity}] {i.issue_type}")
                print(f"  Node: {i.node_type}")
                print(f"  {i.message}")
                if i.estimated_rows and i.actual_rows:
                    print(f"  Rows: estimated={i.estimated_rows:,}, actual={i.actual_rows:,}")
                if i.buffer_hit_ratio:
                    print(f"  Buffer Hit Ratio: {i.buffer_hit_ratio:.1%}")
                print()
            
            # Recommendations
            print("Recommendations:")
            if any(i.issue_type == "ESTIMATION_ERROR" for i in issues):
                print("• CREATE STATISTICS on JSONB expression filters")
            if any(i.issue_type == "SEQ_SCAN_LARGE_TABLE" for i in issues):
                print("• Add appropriate indexes for filtered columns")
            if any(i.issue_type == "LOW_BUFFER_HIT_RATIO" for i in issues):
                print("• Increase shared_buffers or optimize query to reduce working set")


def main():
    parser = argparse.ArgumentParser(
        description="Decode and analyze execution plans"
    )
    parser.add_argument(
        "--query-file", "-q",
        type=Path,
        help="Path to file containing EXPLAIN ANALYZE output"
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
        issues = simulate_analysis()
    elif args.query_file:
        issues = analyze_query_file(args.query_file)
    else:
        issues = []
        print("Note: Provide --query-file or use --simulate for demo")
    
    print_report(issues, args.output)
    
    critical_count = sum(1 for i in issues if i.severity == "CRITICAL")
    return 1 if critical_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
