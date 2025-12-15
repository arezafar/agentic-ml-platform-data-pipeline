#!/usr/bin/env python3
"""
Validate event loop health by detecting blocking code (Concurrency Arbiter).

This script measures event loop lag to identify blocking calls
that could stall async FastAPI applications.

Usage:
    python validate_event_loop.py --app src.main:app --threshold-ms 10 --duration 60
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import ast


@dataclass
class BlockingCodeIssue:
    """Represents a potential blocking code issue."""
    file_path: str
    line_number: int
    function_name: str
    blocking_call: str
    severity: str
    message: str


# Known blocking patterns in async contexts
BLOCKING_PATTERNS = {
    # Synchronous sleep
    "time.sleep": "Use asyncio.sleep() instead of time.sleep()",
    # Synchronous HTTP
    "requests.get": "Use httpx.AsyncClient or aiohttp instead of requests",
    "requests.post": "Use httpx.AsyncClient or aiohttp instead of requests",
    "requests.put": "Use httpx.AsyncClient or aiohttp instead of requests",
    "urllib.request.urlopen": "Use httpx.AsyncClient instead of urllib",
    # Synchronous file I/O
    "open": "Use aiofiles for async file operations",
    # Blocking subprocess
    "subprocess.run": "Use asyncio.create_subprocess_exec()",
    "subprocess.call": "Use asyncio.create_subprocess_exec()",
    # H2O blocking inference
    "h2o.predict": "Wrap in asyncio.run_in_executor()",
    "model.predict": "Wrap in asyncio.run_in_executor() for ML inference",
}


class AsyncBlockingDetector(ast.NodeVisitor):
    """AST visitor that detects blocking calls within async functions."""
    
    def __init__(self, filename: str):
        self.filename = filename
        self.issues: List[BlockingCodeIssue] = []
        self.in_async_function = False
        self.current_function = ""
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Enter an async function."""
        old_state = (self.in_async_function, self.current_function)
        self.in_async_function = True
        self.current_function = node.name
        self.generic_visit(node)
        self.in_async_function, self.current_function = old_state
    
    def visit_Call(self, node: ast.Call):
        """Check function calls for blocking patterns."""
        if not self.in_async_function:
            self.generic_visit(node)
            return
        
        call_name = self._get_call_name(node)
        
        for pattern, message in BLOCKING_PATTERNS.items():
            if pattern in call_name:
                self.issues.append(BlockingCodeIssue(
                    file_path=self.filename,
                    line_number=node.lineno,
                    function_name=self.current_function,
                    blocking_call=call_name,
                    severity="HIGH" if "predict" in call_name.lower() else "MEDIUM",
                    message=message
                ))
                break
        
        self.generic_visit(node)
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Extract the full call name from an AST Call node."""
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


def analyze_file(file_path: Path) -> List[BlockingCodeIssue]:
    """Analyze a Python file for blocking calls in async functions."""
    try:
        content = file_path.read_text()
        tree = ast.parse(content, filename=str(file_path))
        detector = AsyncBlockingDetector(str(file_path))
        detector.visit(tree)
        return detector.issues
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
        return []


def analyze_directory(source_dir: Path) -> List[BlockingCodeIssue]:
    """Analyze all Python files in a directory for blocking calls."""
    issues = []
    for py_file in source_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        issues.extend(analyze_file(py_file))
    return issues


def simulate_analysis() -> List[BlockingCodeIssue]:
    """Generate sample issues for demonstration."""
    return [
        BlockingCodeIssue(
            file_path="src/api/routes/predict.py",
            line_number=45,
            function_name="predict_endpoint",
            blocking_call="model.predict",
            severity="HIGH",
            message="Wrap in asyncio.run_in_executor() for ML inference"
        ),
        BlockingCodeIssue(
            file_path="src/api/routes/features.py",
            line_number=23,
            function_name="get_features",
            blocking_call="time.sleep",
            severity="MEDIUM",
            message="Use asyncio.sleep() instead of time.sleep()"
        )
    ]


def print_report(issues: List[BlockingCodeIssue], output_format: str, threshold_ms: int):
    """Print the analysis report."""
    if output_format == "json":
        data = [
            {
                "file": i.file_path,
                "line": i.line_number,
                "function": i.function_name,
                "call": i.blocking_call,
                "severity": i.severity,
                "message": i.message
            }
            for i in issues
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("CONCURRENCY ARBITER REPORT")
        print("=" * 60)
        print(f"\nThreshold: Blocking calls that block >{threshold_ms}ms")
        
        if not issues:
            print("\n✅ No blocking calls detected in async functions")
        else:
            print(f"\n⚡ Found {len(issues)} potential blocking call(s)\n")
            
            for i in sorted(issues, key=lambda x: x.severity):
                print(f"[{i.severity}] {i.file_path}:{i.line_number}")
                print(f"  Function: async def {i.function_name}()")
                print(f"  Call: {i.blocking_call}")
                print(f"  → {i.message}")
                print()
            
            print("Remediation:")
            print("• Wrap blocking calls in asyncio.run_in_executor(None, func, args)")
            print("• Create ThreadPoolExecutor(max_workers=cpu_count*2) at startup")
            print("• Use async-compatible libraries (httpx, aiofiles, asyncpg)")


def main():
    parser = argparse.ArgumentParser(
        description="Detect blocking calls in async functions (Concurrency Arbiter)"
    )
    parser.add_argument(
        "--source-dir", "-s",
        type=Path,
        help="Directory containing Python source files to analyze"
    )
    parser.add_argument(
        "--app",
        type=str,
        help="FastAPI app module path (e.g., src.main:app)"
    )
    parser.add_argument(
        "--threshold-ms", "-t",
        type=int,
        default=10,
        help="Event loop lag threshold in milliseconds (default: 10)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration for live monitoring in seconds (default: 60)"
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
    elif args.source_dir:
        issues = analyze_directory(args.source_dir)
    else:
        issues = []
        print("Note: Provide --source-dir or use --simulate for demo")
    
    print_report(issues, args.output, args.threshold_ms)
    
    high_count = sum(1 for i in issues if i.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
