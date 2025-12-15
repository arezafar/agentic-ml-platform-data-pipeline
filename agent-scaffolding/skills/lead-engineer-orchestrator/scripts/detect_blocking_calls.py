#!/usr/bin/env python3
"""
Detect blocking calls in async functions (Async Non-Blocking Radar).

This script scans Python source files for synchronous/blocking calls
within async functions that would starve the FastAPI event loop.

Usage:
    python detect_blocking_calls.py --source-dir ./src/service
"""

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


# Blocking calls that should not appear in async functions
BLOCKING_CALLS = {
    # time module
    "time.sleep",
    # requests library (should use httpx)
    "requests.get",
    "requests.post",
    "requests.put",
    "requests.delete",
    "requests.patch",
    "requests.head",
    "requests.options",
    # H2O blocking calls
    "h2o.predict",
    "h2o.mojo_predict",
    # urllib
    "urllib.request.urlopen",
    # subprocess
    "subprocess.run",
    "subprocess.call",
    # file I/O without aiofiles
    "open",
}


@dataclass
class BlockingViolation:
    """Represents a blocking call violation."""
    file: str
    line: int
    function_name: str
    blocking_call: str
    severity: str


class AsyncBlockingVisitor(ast.NodeVisitor):
    """AST visitor to detect blocking calls in async functions."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: List[BlockingViolation] = []
        self.current_async_func = None
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function and check for blocking calls."""
        old_func = self.current_async_func
        self.current_async_func = node.name
        self.generic_visit(node)
        self.current_async_func = old_func
    
    def visit_Call(self, node: ast.Call):
        """Check if call is a blocking operation."""
        if self.current_async_func is None:
            self.generic_visit(node)
            return
        
        call_name = self._get_call_name(node)
        if call_name and self._is_blocking(call_name):
            severity = self._get_severity(call_name)
            self.violations.append(BlockingViolation(
                file=self.filepath,
                line=node.lineno,
                function_name=self.current_async_func,
                blocking_call=call_name,
                severity=severity
            ))
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the full call name from a Call node."""
        if isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        elif isinstance(node.func, ast.Name):
            return node.func.id
        return ""
    
    def _is_blocking(self, call_name: str) -> bool:
        """Check if call is a known blocking operation."""
        for blocking in BLOCKING_CALLS:
            if call_name == blocking or call_name.startswith(blocking + "."):
                return True
        return False
    
    def _get_severity(self, call_name: str) -> str:
        """Determine severity based on call type."""
        if "sleep" in call_name or "h2o" in call_name:
            return "CRITICAL"
        elif "requests" in call_name or "urllib" in call_name:
            return "HIGH"
        elif "subprocess" in call_name:
            return "HIGH"
        else:
            return "MEDIUM"


def scan_file(filepath: Path) -> List[BlockingViolation]:
    """Scan a single Python file for blocking calls."""
    try:
        content = filepath.read_text()
        tree = ast.parse(content)
        visitor = AsyncBlockingVisitor(str(filepath))
        visitor.visit(tree)
        return visitor.violations
    except SyntaxError:
        return []
    except Exception:
        return []


def scan_directory(source_dir: Path, severity_filter: str = "LOW") -> List[BlockingViolation]:
    """Scan all Python files in directory."""
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    min_severity = severity_order.get(severity_filter, 3)
    
    all_violations = []
    for filepath in source_dir.rglob("*.py"):
        violations = scan_file(filepath)
        for v in violations:
            if severity_order.get(v.severity, 3) <= min_severity:
                all_violations.append(v)
    
    return all_violations


def print_report(violations: List[BlockingViolation], output_format: str):
    """Print violation report."""
    if output_format == "json":
        import json
        data = [
            {
                "file": v.file,
                "line": v.line,
                "function": v.function_name,
                "blocking_call": v.blocking_call,
                "severity": v.severity
            }
            for v in violations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("ASYNC NON-BLOCKING RADAR REPORT")
        print("=" * 60)
        
        if not violations:
            print("\n✅ No blocking calls detected in async functions")
        else:
            print(f"\n❌ Found {len(violations)} blocking call(s)\n")
            
            for v in sorted(violations, key=lambda x: (x.severity, x.file)):
                print(f"[{v.severity}] {v.file}:{v.line}")
                print(f"  Function: async def {v.function_name}()")
                print(f"  Blocking call: {v.blocking_call}")
                print()


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
        print(f"Error: Directory not found: {args.source_dir}")
        return 1
    
    violations = scan_directory(args.source_dir, args.severity)
    print_report(violations, args.output)
    
    # Exit with error if critical or high violations found
    critical_count = sum(1 for v in violations if v.severity in ("CRITICAL", "HIGH"))
    return 1 if critical_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
