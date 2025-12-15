#!/usr/bin/env python3
"""
Validate schema migrations for JSONB and GIN index compliance.

Implements the "Schema Drift Detector" superpower.
Scans Alembic/SQLAlchemy migration files for schema integrity issues.

Usage:
    python validate_schema_migration.py --migration-dir ./alembic/versions
    python validate_schema_migration.py --migration-file migration_001.py --output json
"""

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class SchemaViolation:
    """A detected schema integrity issue."""
    
    file: str
    line: int
    violation_type: str
    severity: str
    task_id: str
    message: str
    recommendation: str


class MigrationVisitor(ast.NodeVisitor):
    """AST visitor to analyze migration files."""
    
    def __init__(self, filepath: str, content: str):
        self.filepath = filepath
        self.content = content
        self.lines = content.split('\n')
        self.violations: list[SchemaViolation] = []
        self.jsonb_columns: list[tuple[int, str]] = []  # (line, column_name)
        self.gin_indexes: list[tuple[int, str]] = []  # (line, column_name)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to detect schema patterns."""
        call_str = self._get_call_string(node)
        
        # Check for JSON instead of JSONB
        if self._is_column_definition(node):
            self._check_json_type(node, call_str)
        
        # Track JSONB columns
        if 'JSONB' in call_str or 'jsonb' in call_str.lower():
            column_name = self._extract_column_name(node)
            if column_name:
                self.jsonb_columns.append((node.lineno, column_name))
        
        # Track GIN index creation
        if 'create_index' in call_str and 'gin' in call_str.lower():
            self.gin_indexes.append((node.lineno, call_str))
        
        # Check for unindexed extraction operators in raw SQL
        if self._contains_raw_sql(node):
            self._check_extraction_operators(node)
        
        self.generic_visit(node)
    
    def _get_call_string(self, node: ast.Call) -> str:
        """Get string representation of call."""
        try:
            return ast.unparse(node)
        except Exception:
            return ""
    
    def _is_column_definition(self, node: ast.Call) -> bool:
        """Check if this is a column definition."""
        call_str = self._get_call_string(node)
        return 'Column' in call_str or 'add_column' in call_str
    
    def _check_json_type(self, node: ast.Call, call_str: str) -> None:
        """Check for JSON instead of JSONB."""
        # Pattern: sa.JSON or JSON() without B
        if re.search(r'\bJSON\b(?!B)', call_str) and 'JSONB' not in call_str:
            self.violations.append(SchemaViolation(
                file=self.filepath,
                line=node.lineno,
                violation_type="WRONG_JSON_TYPE",
                severity="HIGH",
                task_id="LOG-REV-01-01",
                message="Using JSON type instead of JSONB",
                recommendation="Replace sa.JSON with JSONB from sqlalchemy.dialects.postgresql",
            ))
    
    def _extract_column_name(self, node: ast.Call) -> Optional[str]:
        """Extract column name from add_column or Column call."""
        if node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Constant):
                return str(first_arg.value)
        return None
    
    def _contains_raw_sql(self, node: ast.Call) -> bool:
        """Check if call contains raw SQL."""
        call_str = self._get_call_string(node)
        return 'execute' in call_str or 'text(' in call_str
    
    def _check_extraction_operators(self, node: ast.Call) -> None:
        """Check for unindexed ->> operators in WHERE clauses."""
        call_str = self._get_call_string(node)
        
        # Pattern: ->> in WHERE clause
        if re.search(r"WHERE.*->>'[^']+'\s*=", call_str, re.IGNORECASE):
            self.violations.append(SchemaViolation(
                file=self.filepath,
                line=node.lineno,
                violation_type="UNINDEXED_EXTRACTION",
                severity="MEDIUM",
                task_id="LOG-REV-01-01",
                message="Using ->> extraction operator in WHERE clause",
                recommendation="Use @> containment operator with GIN index, or create B-Tree index on extracted field",
            ))
    
    def finalize(self) -> None:
        """Check for missing GIN indexes on JSONB columns."""
        # Get column names with GIN indexes
        indexed_patterns = set()
        for _, index_str in self.gin_indexes:
            # Extract column name from index
            match = re.search(r"'(\w+)'", index_str)
            if match:
                indexed_patterns.add(match.group(1))
        
        # Check each JSONB column has an index
        for line, column_name in self.jsonb_columns:
            if column_name not in indexed_patterns:
                self.violations.append(SchemaViolation(
                    file=self.filepath,
                    line=line,
                    violation_type="MISSING_GIN_INDEX",
                    severity="HIGH",
                    task_id="LOG-REV-01-01",
                    message=f"JSONB column '{column_name}' has no GIN index",
                    recommendation=f"Add: op.create_index('ix_table_{column_name}_gin', 'table', ['{column_name}'], postgresql_using='gin')",
                ))


class SchemaMigrationValidator:
    """Validator for schema migrations."""
    
    def __init__(self):
        self.violations: list[SchemaViolation] = []
        self.files_scanned = 0
    
    def scan_directory(self, migration_dir: Path) -> list[SchemaViolation]:
        """Scan all migration files in directory."""
        for path in sorted(migration_dir.glob("*.py")):
            if path.name.startswith("__"):
                continue
            self._scan_file(path)
        return self.violations
    
    def scan_file(self, path: Path) -> list[SchemaViolation]:
        """Scan a single migration file."""
        self._scan_file(path)
        return self.violations
    
    def _scan_file(self, path: Path) -> None:
        """Scan a migration file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            self.violations.append(SchemaViolation(
                file=str(path),
                line=0,
                violation_type="PARSE_ERROR",
                severity="LOW",
                task_id="LOG-REV-01-01",
                message=f"Could not parse file: {e}",
                recommendation="Fix syntax errors in migration file",
            ))
            return
        
        self.files_scanned += 1
        
        # AST-based checks
        visitor = MigrationVisitor(str(path), content)
        visitor.visit(tree)
        visitor.finalize()
        self.violations.extend(visitor.violations)
        
        # Regex-based checks for patterns AST might miss
        self._regex_checks(path, content)
    
    def _regex_checks(self, path: Path, content: str) -> None:
        """Additional regex-based checks."""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for json type (case-insensitive but not jsonb)
            if re.search(r'\bjson\b(?!b)', line, re.IGNORECASE):
                if 'JSONB' not in line and 'jsonb' not in line:
                    if 'Column' in line or 'add_column' in line:
                        # Avoid duplicate if AST already caught it
                        if not any(v.line == i and v.violation_type == "WRONG_JSON_TYPE" 
                                   for v in self.violations):
                            self.violations.append(SchemaViolation(
                                file=str(path),
                                line=i,
                                violation_type="WRONG_JSON_TYPE",
                                severity="HIGH",
                                task_id="LOG-REV-01-01",
                                message="Possible JSON type instead of JSONB",
                                recommendation="Use JSONB for queryable JSON data",
                            ))
            
            # Check for missing temporal columns in feature tables
            if 'feature' in line.lower() and 'create_table' in line.lower():
                # Look ahead for event_time or valid_from
                table_block = '\n'.join(lines[i-1:min(i+20, len(lines))])
                if 'event_time' not in table_block and 'valid_from' not in table_block:
                    self.violations.append(SchemaViolation(
                        file=str(path),
                        line=i,
                        violation_type="MISSING_TEMPORAL_COLUMN",
                        severity="MEDIUM",
                        task_id="LOG-REV-01-02",
                        message="Feature table may be missing temporal column for time-travel",
                        recommendation="Add event_time or valid_from timestamp column",
                    ))


def main():
    parser = argparse.ArgumentParser(
        description="Validate schema migrations for JSONB/GIN compliance (Schema Drift Detector)"
    )
    parser.add_argument(
        "--migration-dir", "-d",
        type=Path,
        help="Directory containing migration files"
    )
    parser.add_argument(
        "--migration-file", "-f",
        type=Path,
        help="Single migration file to scan"
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
    
    if not args.migration_dir and not args.migration_file:
        print("Error: Must specify --migration-dir or --migration-file")
        sys.exit(1)
    
    validator = SchemaMigrationValidator()
    
    if args.migration_file:
        if not args.migration_file.exists():
            print(f"Error: File {args.migration_file} does not exist")
            sys.exit(1)
        violations = validator.scan_file(args.migration_file)
    else:
        if not args.migration_dir.exists():
            print(f"Error: Directory {args.migration_dir} does not exist")
            sys.exit(1)
        violations = validator.scan_directory(args.migration_dir)
    
    # Filter by severity
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_index = severity_order.index(args.severity)
    violations = [v for v in violations if severity_order.index(v.severity) >= min_index]
    
    if args.output == "json":
        output = {
            "scanner": "validate_schema_migration",
            "superpower": "Schema Drift Detector",
            "files_scanned": validator.files_scanned,
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"🔍 Schema Drift Detector Scan")
        print(f"   Scanned {validator.files_scanned} migration file(s)\n")
        
        if not violations:
            print("✅ No schema integrity issues detected")
        else:
            print(f"⚠️  Found {len(violations)} issue(s):\n")
            
            for v in sorted(violations, key=lambda x: severity_order.index(x.severity), reverse=True):
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[v.severity]
                print(f"{icon} [{v.severity}] {v.violation_type}")
                print(f"   File: {v.file}:{v.line}")
                print(f"   Message: {v.message}")
                print(f"   Fix: {v.recommendation}")
                print(f"   Task ID: {v.task_id}")
                print()
    
    # Exit with error if high/critical findings
    high_critical = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
    if high_critical:
        sys.exit(1)


if __name__ == "__main__":
    main()
