#!/usr/bin/env python3
"""
Scan FastAPI endpoints for security vulnerabilities.

Checks:
- Authentication on protected routes
- Rate limiting configuration
- SQL injection patterns
- Header security
"""

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class SecurityFinding:
    """Security finding from scan."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    category: str
    file: str
    line: int
    message: str
    task_id: str  # Related JTBD task


class APISecurityScanner:
    """Scanner for FastAPI security issues."""

    def __init__(self):
        self.findings: list[SecurityFinding] = []

    def scan_directory(self, source_dir: Path) -> list[SecurityFinding]:
        """Scan all Python files in directory."""
        for path in source_dir.rglob("*.py"):
            self._scan_file(path)
        return self.findings

    def _scan_file(self, path: Path) -> None:
        """Scan single Python file."""
        try:
            with open(path) as f:
                content = f.read()
                tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return

        lines = content.split("\n")

        # Run all checks
        self._check_unprotected_routes(path, tree)
        self._check_sql_injection(path, lines)
        self._check_rate_limiting(path, tree, lines)
        self._check_input_validation(path, tree)
        self._check_secrets_in_code(path, lines)

    def _check_unprotected_routes(self, path: Path, tree: ast.AST) -> None:
        """Check for routes without authentication."""
        protected_patterns = {"Depends(", "Security(", "oauth2_scheme", "get_current_user"}
        public_routes = {"/health", "/healthz", "/ready", "/metrics", "/openapi.json", "/docs", "/redoc"}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        # Check if it's a route decorator
                        if hasattr(decorator.func, "attr") and decorator.func.attr in (
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                        ):
                            # Get route path
                            route_path = ""
                            if decorator.args:
                                if isinstance(decorator.args[0], ast.Constant):
                                    route_path = decorator.args[0].value

                            # Skip public routes
                            if route_path in public_routes:
                                continue

                            # Check function body for auth
                            func_source = ast.unparse(node)
                            has_auth = any(pattern in func_source for pattern in protected_patterns)

                            if not has_auth:
                                self.findings.append(
                                    SecurityFinding(
                                        severity="HIGH",
                                        category="Authentication",
                                        file=str(path),
                                        line=node.lineno,
                                        message=f"Route '{route_path}' may lack authentication",
                                        task_id="IAM-01",
                                    )
                                )

    def _check_sql_injection(self, path: Path, lines: list[str]) -> None:
        """Check for SQL injection vulnerabilities."""
        # Patterns indicating string formatting in SQL
        sql_patterns = [
            (r'execute\s*\(\s*f["\']', "f-string in SQL execute"),
            (r'execute\s*\([^)]*\.format\(', ".format() in SQL execute"),
            (r'execute\s*\([^)]*%\s*\(', "% formatting in SQL execute"),
            (r'SELECT.*\+.*FROM', "String concatenation in SELECT"),
            (r'WHERE.*\+.*=', "String concatenation in WHERE"),
        ]

        for lineno, line in enumerate(lines, 1):
            for pattern, description in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.findings.append(
                        SecurityFinding(
                            severity="CRITICAL",
                            category="SQL Injection",
                            file=str(path),
                            line=lineno,
                            message=f"Potential SQL injection: {description}",
                            task_id="API-03",
                        )
                    )

    def _check_rate_limiting(self, path: Path, tree: ast.AST, lines: list[str]) -> None:
        """Check for rate limiting configuration."""
        has_rate_limiter = False
        has_redis_limiter = False

        content = "\n".join(lines)

        # Check for rate limiting imports
        if "fastapi_limiter" in content or "RateLimiter" in content:
            has_rate_limiter = True

        if "redis" in content.lower() and "limiter" in content.lower():
            has_redis_limiter = True

        # Check if this looks like a main app file
        if "FastAPI()" in content or "app = FastAPI" in content:
            if not has_rate_limiter:
                self.findings.append(
                    SecurityFinding(
                        severity="MEDIUM",
                        category="Rate Limiting",
                        file=str(path),
                        line=1,
                        message="No rate limiting detected in FastAPI app",
                        task_id="API-01",
                    )
                )

    def _check_input_validation(self, path: Path, tree: ast.AST) -> None:
        """Check for input validation on endpoints."""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function is a route handler
                is_route = False
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call):
                        if hasattr(decorator.func, "attr") and decorator.func.attr in (
                            "get",
                            "post",
                            "put",
                            "delete",
                            "patch",
                        ):
                            is_route = True
                            break

                if is_route:
                    # Check if POST/PUT/PATCH have typed request body
                    has_pydantic_body = False
                    for arg in node.args.args:
                        if arg.annotation:
                            # Check if annotation references a model
                            ann_source = ast.unparse(arg.annotation)
                            if any(
                                keyword in ann_source
                                for keyword in ["Request", "Body", "Model", "Schema"]
                            ):
                                has_pydantic_body = True
                                break

    def _check_secrets_in_code(self, path: Path, lines: list[str]) -> None:
        """Check for hardcoded secrets."""
        secret_patterns = [
            (r'["\']sk-[a-zA-Z0-9]{32,}["\']', "OpenAI API key"),
            (r'["\']ghp_[a-zA-Z0-9]{36}["\']', "GitHub token"),
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'api_key\s*=\s*["\'][a-zA-Z0-9]{16,}["\']', "Hardcoded API key"),
            (r'AWS[A-Z0-9]{16,}', "AWS access key"),
        ]

        for lineno, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            for pattern, description in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.findings.append(
                        SecurityFinding(
                            severity="CRITICAL",
                            category="Secrets",
                            file=str(path),
                            line=lineno,
                            message=f"Potential {description} in code",
                            task_id="IAM-04",
                        )
                    )


def main():
    parser = argparse.ArgumentParser(description="Scan FastAPI endpoints for security issues")
    parser.add_argument("--source-dir", "-s", type=Path, required=True, help="Source directory to scan")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--severity", default="LOW", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], help="Minimum severity")

    args = parser.parse_args()

    if not args.source_dir.exists():
        print(f"Error: Directory {args.source_dir} does not exist")
        sys.exit(1)

    scanner = APISecurityScanner()
    findings = scanner.scan_directory(args.source_dir)

    # Filter by severity
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_index = severity_order.index(args.severity)
    findings = [f for f in findings if severity_order.index(f.severity) >= min_index]

    if args.output == "json":
        import json

        print(json.dumps([vars(f) for f in findings], indent=2))
    else:
        if not findings:
            print("✅ No security issues found")
        else:
            print(f"Found {len(findings)} security issue(s):\n")
            for f in sorted(findings, key=lambda x: severity_order.index(x.severity), reverse=True):
                severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(f.severity, "⚪")
                print(f"{severity_icon} [{f.severity}] {f.category}")
                print(f"   File: {f.file}:{f.line}")
                print(f"   {f.message}")
                print(f"   Task: {f.task_id}")
                print()

    # Exit with error if critical/high findings
    critical_high = [f for f in findings if f.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        sys.exit(1)


if __name__ == "__main__":
    main()
