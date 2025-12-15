#!/usr/bin/env python3
"""
QA Skill - Async Driver Validator

Static analysis script to detect blocking database drivers
in inference code.

Implements task:
- IT-DB-01: Validate Async Driver Configuration

Usage:
    python validate_async_drivers.py --source-dir ./src/inference
    python validate_async_drivers.py --source-dir ./app --strict
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Generator


# =============================================================================
# Configuration
# =============================================================================

# Blocking imports that should be rejected in async code
BLOCKING_IMPORTS = {
    "psycopg2",
    "psycopg2.pool",
    "psycopg2.extras",
    "psycopg2.extensions",
    "mysql.connector",
    "pymysql",
    "sqlite3",
    "time.sleep",  # Direct sleep calls in async code
}

# Allowed async alternatives
ALLOWED_IMPORTS = {
    "asyncpg",
    "aiosqlite",
    "aiomysql",
    "sqlalchemy.ext.asyncio",
    "asyncio",
}

# Patterns that indicate blocking behavior
BLOCKING_PATTERNS = [
    r"psycopg2\.connect\(",
    r"\.execute\([^)]+\)$",  # Sync execute without await
    r"time\.sleep\(",
    r"requests\.(get|post|put|delete|patch)\(",
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Violation:
    """Represents a detected violation."""
    file_path: str
    line_number: int
    violation_type: str
    message: str
    severity: str  # 'error' or 'warning'


# =============================================================================
# AST Visitor for Import Analysis
# =============================================================================


class ImportVisitor(ast.NodeVisitor):
    """Visit AST nodes to find imports."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[Violation] = []
        self.has_async = False
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self._check_import(alias.name, node.lineno)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            full_import = f"{module}.{alias.name}" if module else alias.name
            self._check_import(full_import, node.lineno)
            self._check_import(module, node.lineno)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track presence of async functions."""
        self.has_async = True
        self.generic_visit(node)
    
    def visit_Await(self, node: ast.Await):
        """Track presence of await expressions."""
        self.has_async = True
        self.generic_visit(node)
    
    def _check_import(self, import_name: str, line_number: int):
        """Check if import is a blocking driver."""
        for blocking in BLOCKING_IMPORTS:
            if import_name.startswith(blocking.split(".")[0]) and \
               blocking in import_name or import_name == blocking.split(".")[0]:
                self.violations.append(Violation(
                    file_path=self.file_path,
                    line_number=line_number,
                    violation_type="blocking_import",
                    message=f"Blocking import detected: '{import_name}'. "
                            f"Use async alternative instead.",
                    severity="error",
                ))


class BlockingCallVisitor(ast.NodeVisitor):
    """Visit AST nodes to find blocking calls in async contexts."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.violations: list[Violation] = []
        self._in_async_context = False
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        old_context = self._in_async_context
        self._in_async_context = True
        self.generic_visit(node)
        self._in_async_context = old_context
    
    def visit_Call(self, node: ast.Call):
        if not self._in_async_context:
            self.generic_visit(node)
            return
        
        # Check for time.sleep calls
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "sleep":
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == "time":
                        self.violations.append(Violation(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            violation_type="blocking_call",
                            message="time.sleep() blocks the event loop. "
                                    "Use 'await asyncio.sleep()' instead.",
                            severity="error",
                        ))
        
        self.generic_visit(node)


# =============================================================================
# File Analysis
# =============================================================================


def find_python_files(
    source_dir: Path,
    exclude_patterns: list[str] | None = None
) -> Generator[Path, None, None]:
    """Find all Python files in directory."""
    exclude_patterns = exclude_patterns or ["__pycache__", ".git", "venv", ".venv"]
    
    for root, dirs, files in os.walk(source_dir):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_patterns]
        
        for file in files:
            if file.endswith(".py"):
                yield Path(root) / file


def analyze_file(file_path: Path) -> list[Violation]:
    """Analyze a single Python file for violations."""
    violations = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return [Violation(
            file_path=str(file_path),
            line_number=0,
            violation_type="read_error",
            message=f"Could not read file: {e}",
            severity="warning",
        )]
    
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [Violation(
            file_path=str(file_path),
            line_number=e.lineno or 0,
            violation_type="syntax_error",
            message=f"Syntax error: {e}",
            severity="warning",
        )]
    
    # Check imports
    import_visitor = ImportVisitor(str(file_path))
    import_visitor.visit(tree)
    violations.extend(import_visitor.violations)
    
    # Check blocking calls (only if file has async code)
    if import_visitor.has_async:
        call_visitor = BlockingCallVisitor(str(file_path))
        call_visitor.visit(tree)
        violations.extend(call_visitor.violations)
    
    # Pattern-based checks
    for i, line in enumerate(source.split("\n"), 1):
        for pattern in BLOCKING_PATTERNS:
            if re.search(pattern, line):
                violations.append(Violation(
                    file_path=str(file_path),
                    line_number=i,
                    violation_type="blocking_pattern",
                    message=f"Blocking pattern detected: {pattern}",
                    severity="warning",
                ))
    
    return violations


# =============================================================================
# Output Formatting
# =============================================================================


def format_violations(violations: list[Violation], format_type: str = "text") -> str:
    """Format violations for output."""
    if format_type == "json":
        import json
        return json.dumps([
            {
                "file": v.file_path,
                "line": v.line_number,
                "type": v.violation_type,
                "message": v.message,
                "severity": v.severity,
            }
            for v in violations
        ], indent=2)
    
    # Text format
    lines = []
    
    if not violations:
        lines.append("✅ No blocking driver violations found!")
        return "\n".join(lines)
    
    # Group by file
    by_file: dict[str, list[Violation]] = {}
    for v in violations:
        by_file.setdefault(v.file_path, []).append(v)
    
    for file_path, file_violations in sorted(by_file.items()):
        lines.append(f"\n📄 {file_path}")
        for v in sorted(file_violations, key=lambda x: x.line_number):
            icon = "❌" if v.severity == "error" else "⚠️"
            lines.append(f"  {icon} Line {v.line_number}: {v.message}")
    
    # Summary
    errors = sum(1 for v in violations if v.severity == "error")
    warnings = sum(1 for v in violations if v.severity == "warning")
    
    lines.append("\n" + "=" * 60)
    lines.append(f"Total: {errors} errors, {warnings} warnings")
    
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Validate async driver usage in Python code"
    )
    
    parser.add_argument(
        "--source-dir",
        type=str,
        required=True,
        help="Directory to analyze",
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    
    parser.add_argument(
        "--exclude",
        type=str,
        nargs="*",
        default=[],
        help="Patterns to exclude",
    )
    
    args = parser.parse_args()
    
    source_dir = Path(args.source_dir)
    
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(2)
    
    # Collect violations
    all_violations = []
    
    for file_path in find_python_files(source_dir, args.exclude):
        violations = analyze_file(file_path)
        all_violations.extend(violations)
    
    # Output
    format_type = "json" if args.json else "text"
    print(format_violations(all_violations, format_type))
    
    # Exit code
    errors = sum(1 for v in all_violations if v.severity == "error")
    warnings = sum(1 for v in all_violations if v.severity == "warning")
    
    if errors > 0:
        sys.exit(1)
    elif args.strict and warnings > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
