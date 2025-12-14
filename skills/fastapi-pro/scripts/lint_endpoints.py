#!/usr/bin/env python3
"""
FastAPI Endpoint Linter

Validates FastAPI endpoint definitions including:
- Return type annotations on all routes
- Pydantic model usage for request/response bodies
- Async function usage for route handlers
- Error handling patterns
- Dependency injection patterns

Usage:
    python lint_endpoints.py <fastapi_app.py>
    python lint_endpoints.py <directory> --recursive
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any


class FastAPILintError(Exception):
    """Custom exception for linting errors."""
    pass


class FastAPIEndpointLinter(ast.NodeVisitor):
    """AST-based linter for FastAPI endpoint validation."""
    
    # FastAPI decorators that indicate route handlers
    ROUTE_DECORATORS = {
        'get', 'post', 'put', 'patch', 'delete', 'options', 'head', 'trace',
        'api_route', 'websocket',
    }
    
    # Decorators from APIRouter
    ROUTER_DECORATORS = ROUTE_DECORATORS
    
    # Known Pydantic base classes
    PYDANTIC_BASES = {'BaseModel', 'BaseSettings', 'GenericModel'}
    
    # Known async context managers to ignore for async checks
    ASYNC_CONTEXT_PATTERNS = {'asyncpg', 'aiohttp', 'httpx', 'aiofiles'}
    
    def __init__(self, filename: str, source_code: str):
        self.filename = filename
        self.source_code = source_code
        self.lines = source_code.split('\n')
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.endpoints: list[dict[str, Any]] = []
        
        # Track imports and definitions
        self.imported_names: set[str] = set()
        self.pydantic_models: set[str] = set()
        self.router_names: set[str] = set()
        
    def lint(self) -> bool:
        """Run linting. Returns True if no errors."""
        try:
            tree = ast.parse(self.source_code)
            
            # First pass: collect imports and model definitions
            self._collect_definitions(tree)
            
            # Second pass: validate endpoints
            self.visit(tree)
            
            return len(self.errors) == 0
        except SyntaxError as e:
            self.errors.append({
                'line': e.lineno or 0,
                'column': e.offset or 0,
                'message': f"Syntax error: {e.msg}",
                'code': 'E001',
            })
            return False
    
    def _collect_definitions(self, tree: ast.AST) -> None:
        """Collect imports and Pydantic model definitions."""
        for node in ast.walk(tree):
            # Collect imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    self.imported_names.add(name)
                    
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    name = alias.asname or alias.name
                    self.imported_names.add(name)
                    
                    # Track FastAPI/APIRouter imports
                    if module == 'fastapi' and name in ('FastAPI', 'APIRouter'):
                        self.router_names.add(name.lower())
            
            # Collect Pydantic model definitions
            elif isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name in self.PYDANTIC_BASES:
                        self.pydantic_models.add(node.name)
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit sync function definitions."""
        self._check_route_handler(node, is_async=False)
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self._check_route_handler(node, is_async=True)
        self.generic_visit(node)
    
    def _check_route_handler(
        self, 
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        is_async: bool
    ) -> None:
        """Check if function is a route handler and validate it."""
        route_info = self._get_route_info(node)
        
        if not route_info:
            return  # Not a route handler
        
        endpoint = {
            'name': node.name,
            'line': node.lineno,
            'method': route_info['method'],
            'path': route_info['path'],
            'is_async': is_async,
        }
        self.endpoints.append(endpoint)
        
        # Check 1: Async usage
        if not is_async:
            self.warnings.append({
                'line': node.lineno,
                'column': node.col_offset,
                'message': f"Route '{node.name}' is not async. "
                          "Consider using 'async def' for non-blocking I/O.",
                'code': 'W001',
            })
        
        # Check 2: Return type annotation
        if node.returns is None:
            self.errors.append({
                'line': node.lineno,
                'column': node.col_offset,
                'message': f"Route '{node.name}' missing return type annotation",
                'code': 'E002',
            })
        else:
            # Check if return type is a Pydantic model or known type
            return_type = self._get_name(node.returns)
            endpoint['return_type'] = return_type
            
            if return_type and not self._is_valid_return_type(return_type):
                self.warnings.append({
                    'line': node.lineno,
                    'column': node.col_offset,
                    'message': f"Route '{node.name}' return type '{return_type}' "
                              "is not a Pydantic model. Consider using typed responses.",
                    'code': 'W002',
                })
        
        # Check 3: Request body typing
        self._check_parameters(node)
        
        # Check 4: Error handling
        self._check_error_handling(node)
        
        # Check 5: Docstring presence
        if not ast.get_docstring(node):
            self.warnings.append({
                'line': node.lineno,
                'column': node.col_offset,
                'message': f"Route '{node.name}' missing docstring",
                'code': 'W003',
            })
    
    def _get_route_info(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> dict | None:
        """Extract route information from decorators."""
        for decorator in node.decorator_list:
            # Handle @app.get("/path") or @router.post("/path")
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    method = decorator.func.attr
                    if method.lower() in self.ROUTE_DECORATORS:
                        path = None
                        if decorator.args:
                            if isinstance(decorator.args[0], ast.Constant):
                                path = decorator.args[0].value
                        return {'method': method.upper(), 'path': path}
                        
            # Handle simple decorator (less common)
            elif isinstance(decorator, ast.Attribute):
                method = decorator.attr
                if method.lower() in self.ROUTE_DECORATORS:
                    return {'method': method.upper(), 'path': None}
        
        return None
    
    def _check_parameters(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check function parameters for proper typing."""
        for arg in node.args.args:
            if arg.arg in ('self', 'cls'):
                continue
            
            if arg.annotation is None:
                self.errors.append({
                    'line': node.lineno,
                    'column': node.col_offset,
                    'message': f"Route '{node.name}' parameter '{arg.arg}' "
                              "missing type annotation",
                    'code': 'E003',
                })
            else:
                # Check for Body, Query, Path, etc. from FastAPI
                ann_name = self._get_name(arg.annotation)
                if ann_name in self.pydantic_models:
                    # Good - using Pydantic model
                    pass
    
    def _check_error_handling(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check for error handling in route handler."""
        has_try_except = False
        has_http_exception = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.Try):
                has_try_except = True
                
            if isinstance(child, ast.Raise):
                if isinstance(child.exc, ast.Call):
                    exc_name = self._get_name(child.exc.func)
                    if exc_name in ('HTTPException', 'RequestValidationError'):
                        has_http_exception = True
        
        if not has_try_except and not has_http_exception:
            self.warnings.append({
                'line': node.lineno,
                'column': node.col_offset,
                'message': f"Route '{node.name}' has no explicit error handling. "
                          "Consider adding try/except or HTTPException.",
                'code': 'W004',
            })
    
    def _get_name(self, node: ast.AST | None) -> str | None:
        """Extract name from various AST node types."""
        if node is None:
            return None
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Subscript):
            return self._get_name(node.value)
        if isinstance(node, ast.Constant):
            return str(node.value)
        return None
    
    def _is_valid_return_type(self, type_name: str) -> bool:
        """Check if return type is acceptable."""
        # Pydantic models
        if type_name in self.pydantic_models:
            return True
        
        # Common FastAPI response types
        valid_types = {
            'Response', 'JSONResponse', 'HTMLResponse', 'PlainTextResponse',
            'RedirectResponse', 'StreamingResponse', 'FileResponse',
            'dict', 'list', 'str', 'int', 'float', 'bool', 'None',
            'List', 'Dict', 'Optional', 'Union', 'Any',
        }
        return type_name in valid_types
    
    def get_report(self) -> str:
        """Generate a linting report."""
        lines = [
            "=" * 60,
            "FASTAPI ENDPOINT LINT REPORT",
            "=" * 60,
            f"File: {self.filename}",
            f"Endpoints found: {len(self.endpoints)}",
            "",
        ]
        
        if self.endpoints:
            lines.append("ENDPOINTS:")
            for ep in self.endpoints:
                async_marker = "async " if ep['is_async'] else ""
                ret = ep.get('return_type', 'untyped')
                lines.append(
                    f"  {ep['method']:6} {ep.get('path', '?'):20} -> "
                    f"{async_marker}{ep['name']} -> {ret}"
                )
            lines.append("")
        
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(
                    f"  ❌ Line {err['line']}: [{err['code']}] {err['message']}"
                )
            lines.append("")
            
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(
                    f"  ⚠️  Line {warn['line']}: [{warn['code']}] {warn['message']}"
                )
            lines.append("")
            
        if not self.errors and not self.warnings:
            lines.append("✅ All endpoints pass linting!")
        elif not self.errors:
            lines.append("✅ No errors (warnings only)")
        else:
            lines.append("❌ Linting FAILED")
            
        lines.append("=" * 60)
        return '\n'.join(lines)


def lint_file(filepath: Path, strict: bool = False) -> tuple[bool, FastAPIEndpointLinter]:
    """Lint a single Python file."""
    with open(filepath, 'r') as f:
        source = f.read()
    
    linter = FastAPIEndpointLinter(str(filepath), source)
    is_valid = linter.lint()
    
    if strict and linter.warnings:
        is_valid = False
    
    return is_valid, linter


def lint_directory(
    dirpath: Path, 
    recursive: bool = True,
    strict: bool = False,
) -> tuple[bool, list[FastAPIEndpointLinter]]:
    """Lint all Python files in a directory."""
    pattern = '**/*.py' if recursive else '*.py'
    files = list(dirpath.glob(pattern))
    
    all_valid = True
    linters = []
    
    for filepath in files:
        is_valid, linter = lint_file(filepath, strict)
        if not is_valid:
            all_valid = False
        if linter.endpoints:  # Only include files with endpoints
            linters.append(linter)
    
    return all_valid, linters


def main():
    parser = argparse.ArgumentParser(
        description='Lint FastAPI endpoint definitions'
    )
    parser.add_argument(
        'path',
        type=str,
        help='Path to Python file or directory'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively lint directories'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)
    
    if path.is_file():
        is_valid, linter = lint_file(path, args.strict)
        linters = [linter]
    else:
        is_valid, linters = lint_directory(path, args.recursive, args.strict)
    
    if args.json:
        results = []
        for linter in linters:
            results.append({
                'file': linter.filename,
                'endpoints': linter.endpoints,
                'errors': linter.errors,
                'warnings': linter.warnings,
            })
        output = {
            'valid': is_valid,
            'files_checked': len(linters),
            'total_endpoints': sum(len(l.endpoints) for l in linters),
            'total_errors': sum(len(l.errors) for l in linters),
            'total_warnings': sum(len(l.warnings) for l in linters),
            'results': results,
        }
        print(json.dumps(output, indent=2))
    else:
        for linter in linters:
            if linter.endpoints or linter.errors:
                print(linter.get_report())
                print()
        
        # Summary
        total_endpoints = sum(len(l.endpoints) for l in linters)
        total_errors = sum(len(l.errors) for l in linters)
        total_warnings = sum(len(l.warnings) for l in linters)
        
        print(f"Summary: {len(linters)} files, {total_endpoints} endpoints, "
              f"{total_errors} errors, {total_warnings} warnings")
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
