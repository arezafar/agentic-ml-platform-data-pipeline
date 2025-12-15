#!/usr/bin/env python3
"""
Detect blocking calls in async functions.

Implements the "Async Non-Blocking Radar" superpower.
Scans Python files for synchronous/blocking calls inside async def functions.

Usage:
    python detect_blocking_calls.py --source-dir ./src/api
    python detect_blocking_calls.py --source-dir ./src --output json
"""

import argparse
import ast
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class BlockingViolation:
    """A detected blocking call in async context."""
    
    file: str
    line: int
    function: str
    blocking_call: str
    category: str
    severity: str
    task_id: str
    message: str


# Deny list of blocking calls by category
BLOCKING_CALLS = {
    # Sleep operations
    "time.sleep": ("sleep", "CRITICAL", "Blocks event loop completely"),
    "threading.Event.wait": ("sleep", "CRITICAL", "Blocks event loop"),
    
    # Sync HTTP clients
    "requests.get": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "requests.post": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "requests.put": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "requests.delete": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "requests.patch": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "requests.head": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "requests.request": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    "urllib.request.urlopen": ("http", "CRITICAL", "Use httpx.AsyncClient instead"),
    
    # Sync database drivers
    "psycopg2.connect": ("database", "CRITICAL", "Use asyncpg instead"),
    "pymysql.connect": ("database", "CRITICAL", "Use aiomysql instead"),
    "sqlite3.connect": ("database", "HIGH", "Use aiosqlite instead"),
    
    # ML inference (CPU-bound)
    "h2o.predict": ("ml", "CRITICAL", "Wrap in run_in_executor"),
    "model.predict": ("ml", "HIGH", "Wrap in run_in_executor"),
    "sklearn.predict": ("ml", "HIGH", "Wrap in run_in_executor"),
    
    # File I/O
    "open": ("file_io", "MEDIUM", "Use aiofiles for large files"),
}

# Imports that indicate sync library usage
SYNC_IMPORT_WARNINGS = {
    "requests": "Consider using httpx for async HTTP",
    "psycopg2": "Consider using asyncpg for async PostgreSQL",
    "pymysql": "Consider using aiomysql for async MySQL",
}


class AsyncBlockingVisitor(ast.NodeVisitor):
    """AST visitor to detect blocking calls in async functions."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[BlockingViolation] = []
        self.warnings: list[str] = []
        self.current_async_function: Optional[str] = None
        self.imported_modules: set[str] = set()
    
    def visit_Import(self, node: ast.Import) -> None:
        """Track imported modules."""
        for alias in node.names:
            module = alias.name.split('.')[0]
            self.imported_modules.add(module)
            if module in SYNC_IMPORT_WARNINGS:
                self.warnings.append(
                    f"Line {node.lineno}: {SYNC_IMPORT_WARNINGS[module]}"
                )
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track imported modules."""
        if node.module:
            module = node.module.split('.')[0]
            self.imported_modules.add(module)
            if module in SYNC_IMPORT_WARNINGS:
                self.warnings.append(
                    f"Line {node.lineno}: {SYNC_IMPORT_WARNINGS[module]}"
                )
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Enter an async function context."""
        previous_function = self.current_async_function
        self.current_async_function = node.name
        self.generic_visit(node)
        self.current_async_function = previous_function
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check if a call is blocking."""
        if self.current_async_function is None:
            self.generic_visit(node)
            return
        
        call_name = self._get_call_name(node)
        if call_name:
            self._check_blocking_call(node, call_name)
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the full name of a function call."""
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
            parts.reverse()
            return '.'.join(parts)
        return None
    
    def _check_blocking_call(self, node: ast.Call, call_name: str) -> None:
        """Check if a call name matches the blocking list."""
        # Check exact match
        if call_name in BLOCKING_CALLS:
            category, severity, message = BLOCKING_CALLS[call_name]
            self._add_violation(node, call_name, category, severity, message)
            return
        
        # Check partial match (e.g., "model.predict" matches "*.predict")
        for pattern, (category, severity, message) in BLOCKING_CALLS.items():
            if pattern.endswith(call_name.split('.')[-1]):
                # Check if it's a known blocking pattern
                if call_name.endswith('.predict') and 'await' not in self._get_context(node):
                    self._add_violation(node, call_name, category, severity, message)
                    return
    
    def _get_context(self, node: ast.Call) -> str:
        """Get source context around the node (placeholder)."""
        return ""
    
    def _add_violation(
        self,
        node: ast.Call,
        call_name: str,
        category: str,
        severity: str,
        message: str
    ) -> None:
        """Add a violation to the list."""
        task_id = {
            "sleep": "PROC-REV-01-01",
            "http": "PROC-REV-01-01",
            "database": "PROC-REV-01-02",
            "ml": "PROC-REV-01-01",
            "file_io": "PROC-REV-01-01",
        }.get(category, "PROC-REV-01-01")
        
        self.violations.append(BlockingViolation(
            file=self.filepath,
            line=node.lineno,
            function=self.current_async_function or "unknown",
            blocking_call=call_name,
            category=category,
            severity=severity,
            task_id=task_id,
            message=message,
        ))


class BlockingCallDetector:
    """Scanner for blocking calls in async Python code."""
    
    def __init__(self):
        self.violations: list[BlockingViolation] = []
        self.warnings: list[str] = []
        self.files_scanned = 0
    
    def scan_directory(self, source_dir: Path) -> list[BlockingViolation]:
        """Scan all Python files in directory."""
        for path in source_dir.rglob("*.py"):
            self._scan_file(path)
        return self.violations
    
    def scan_file(self, path: Path) -> list[BlockingViolation]:
        """Scan a single file."""
        self._scan_file(path)
        return self.violations
    
    def _scan_file(self, path: Path) -> None:
        """Scan a Python file for blocking calls."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            self.warnings.append(f"Could not parse {path}: {e}")
            return
        
        self.files_scanned += 1
        visitor = AsyncBlockingVisitor(str(path))
        visitor.visit(tree)
        
        self.violations.extend(visitor.violations)
        self.warnings.extend(visitor.warnings)


def main():
    parser = argparse.ArgumentParser(
        description="Detect blocking calls in async functions (Async Non-Blocking Radar)"
    )
    parser.add_argument(
        "--source-dir", "-s",
        type=Path,
        required=True,
        help="Source directory to scan"
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
    
    if not args.source_dir.exists():
        print(f"Error: Directory {args.source_dir} does not exist")
        sys.exit(1)
    
    detector = BlockingCallDetector()
    violations = detector.scan_directory(args.source_dir)
    
    # Filter by severity
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_index = severity_order.index(args.severity)
    violations = [v for v in violations if severity_order.index(v.severity) >= min_index]
    
    if args.output == "json":
        output = {
            "scanner": "detect_blocking_calls",
            "superpower": "Async Non-Blocking Radar",
            "files_scanned": detector.files_scanned,
            "violations": [asdict(v) for v in violations],
            "warnings": detector.warnings,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"🔍 Async Non-Blocking Radar Scan")
        print(f"   Scanned {detector.files_scanned} files\n")
        
        if not violations:
            print("✅ No blocking calls detected in async functions")
        else:
            print(f"⚠️  Found {len(violations)} blocking call(s):\n")
            
            for v in sorted(violations, key=lambda x: severity_order.index(x.severity), reverse=True):
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[v.severity]
                print(f"{icon} [{v.severity}] {v.category}")
                print(f"   File: {v.file}:{v.line}")
                print(f"   Function: async def {v.function}()")
                print(f"   Call: {v.blocking_call}")
                print(f"   Message: {v.message}")
                print(f"   Task ID: {v.task_id}")
                print()
        
        if detector.warnings:
            print("\n📝 Warnings:")
            for w in detector.warnings:
                print(f"   {w}")
    
    # Exit with error if critical/high findings
    critical_high = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        sys.exit(1)


if __name__ == "__main__":
    main()
