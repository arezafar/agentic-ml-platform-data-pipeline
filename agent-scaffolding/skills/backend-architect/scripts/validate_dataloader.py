#!/usr/bin/env python3
"""
Validate GraphQL DataLoader usage to detect N+1 queries (GraphQL Optimizer).

This script analyzes GraphQL schema and resolvers to identify
missing DataLoader implementations that cause N+1 query patterns.

Usage:
    python validate_dataloader.py --schema src/graphql/schema.py --queries test_queries.graphql
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class DataLoaderIssue:
    """Represents a potential N+1 query issue."""
    resolver_name: str
    file_path: str
    line_number: int
    issue_type: str
    message: str
    severity: str


# Patterns that suggest N+1 queries
N_PLUS_ONE_PATTERNS = [
    # Direct database call in resolver without batching
    (r"\.get\s*\(", "Direct .get() call suggests individual fetches"),
    (r"session\.query\s*\(", "Session query in resolver without DataLoader"),
    (r"SELECT\s+.*\s+FROM", "Raw SQL in resolver - should use DataLoader"),
    (r"for\s+.*\s+in\s+.*:\s*\n\s+.*\.fetch", "Loop with fetch suggests N+1"),
]

# Patterns that indicate proper DataLoader usage
DATALOADER_PATTERNS = [
    r"DataLoader",
    r"dataloader",
    r"\.load\s*\(",
    r"\.load_many\s*\(",
    r"batch_load",
]


class ResolverAnalyzer(ast.NodeVisitor):
    """AST visitor that analyzes GraphQL resolver patterns."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[DataLoaderIssue] = []
        self.in_resolver = False
        self.current_resolver = ""
        self.has_dataloader = False
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function for resolver patterns."""
        # Check if this looks like a resolver 
        is_resolver = (
            node.name.startswith("resolve_") or
            any(d.attr == "field" if isinstance(d, ast.Attribute) else False 
                for d in node.decorator_list if isinstance(d, ast.Call))
        )
        
        if is_resolver:
            self.in_resolver = True
            self.current_resolver = node.name
            
            # Check function body for patterns
            source = ast.get_source_segment
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    call_name = self._get_call_name(child)
                    
                    # Check for direct database calls
                    if any(pattern in call_name.lower() for pattern in 
                           ["session.query", "session.execute", ".get(", ".filter("]):
                        # Check if DataLoader is present
                        if not self._has_dataloader_in_scope(node):
                            self.issues.append(DataLoaderIssue(
                                resolver_name=node.name,
                                file_path=self.filename,
                                line_number=child.lineno,
                                issue_type="MISSING_DATALOADER",
                                message=f"Database call in resolver without DataLoader: {call_name}",
                                severity="HIGH"
                            ))
            
            self.in_resolver = False
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Extract call name from AST node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""
    
    def _has_dataloader_in_scope(self, node: ast.FunctionDef) -> bool:
        """Check if DataLoader is used in the function."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if any(p in call_name.lower() for p in ["dataloader", ".load", ".load_many"]):
                    return True
        return False


def analyze_schema_file(file_path: Path) -> List[DataLoaderIssue]:
    """Analyze a Python schema file for N+1 patterns."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content, filename=str(file_path))
        analyzer = ResolverAnalyzer(str(file_path))
        analyzer.visit(tree)
        return analyzer.issues
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []


def analyze_directory(source_dir: Path) -> List[DataLoaderIssue]:
    """Analyze all Python files for N+1 patterns."""
    issues = []
    for py_file in source_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        # Look for GraphQL-related files
        content = py_file.read_text()
        if any(p in content for p in ["strawberry", "graphene", "resolver", "Query", "Mutation"]):
            issues.extend(analyze_schema_file(py_file))
    return issues


def simulate_analysis() -> List[DataLoaderIssue]:
    """Generate sample issues for demonstration."""
    return [
        DataLoaderIssue(
            resolver_name="resolve_user_features",
            file_path="src/graphql/resolvers/features.py",
            line_number=45,
            issue_type="MISSING_DATALOADER",
            message="Database query inside loop - use DataLoader.load_many()",
            severity="HIGH"
        ),
        DataLoaderIssue(
            resolver_name="resolve_predictions",
            file_path="src/graphql/resolvers/predictions.py",
            line_number=23,
            issue_type="N_PLUS_ONE",
            message="50 entity query causes 50 SQL statements; batch with DataLoader",
            severity="HIGH"
        )
    ]


def print_report(issues: List[DataLoaderIssue], output_format: str):
    """Print the analysis report."""
    if output_format == "json":
        data = [
            {
                "resolver": i.resolver_name,
                "file": i.file_path,
                "line": i.line_number,
                "type": i.issue_type,
                "message": i.message,
                "severity": i.severity
            }
            for i in issues
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("GRAPHQL OPTIMIZER: N+1 QUERY DETECTION")
        print("=" * 60)
        
        if not issues:
            print("\n✅ No N+1 query patterns detected")
            print("   All resolvers appear to use DataLoader correctly")
        else:
            print(f"\n⚠️  Found {len(issues)} potential N+1 pattern(s)\n")
            
            for i in issues:
                print(f"[{i.severity}] {i.file_path}:{i.line_number}")
                print(f"  Resolver: {i.resolver_name}")
                print(f"  Issue: {i.issue_type}")
                print(f"  → {i.message}")
                print()
            
            print("Remediation:")
            print("1. Create DataLoader for each entity type")
            print("2. Replace direct .get() with loader.load(id)")
            print("3. Batch multiple IDs with loader.load_many(ids)")
            print("\nExample:")
            print("  # Before (N+1)")
            print("  for id in entity_ids:")
            print("      entity = session.query(Entity).get(id)")
            print("")
            print("  # After (Batched)")
            print("  entities = await entity_loader.load_many(entity_ids)")


def main():
    parser = argparse.ArgumentParser(
        description="Detect N+1 query patterns in GraphQL resolvers"
    )
    parser.add_argument(
        "--schema", "-s",
        type=Path,
        help="Path to GraphQL schema/resolver file or directory"
    )
    parser.add_argument(
        "--queries", "-q",
        type=Path,
        help="Path to GraphQL query file for testing"
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
    elif args.schema:
        if args.schema.is_file():
            issues = analyze_schema_file(args.schema)
        else:
            issues = analyze_directory(args.schema)
    else:
        issues = []
        print("Note: Provide --schema or use --simulate for demo")
    
    print_report(issues, args.output)
    
    high_count = sum(1 for i in issues if i.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
