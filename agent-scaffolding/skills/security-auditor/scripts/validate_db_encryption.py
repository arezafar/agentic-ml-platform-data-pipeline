#!/usr/bin/env python3
"""
Validate database connection encryption settings.

Checks:
- SSL/TLS mode in connection strings
- Certificate verification
- Encryption in transit configuration
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse


@dataclass
class EncryptionFinding:
    """Database encryption finding."""

    severity: str
    database: str
    issue: str
    recommendation: str
    task_id: str


class DatabaseEncryptionValidator:
    """Validator for database encryption settings."""

    def __init__(self):
        self.findings: list[EncryptionFinding] = []

    def validate_connection_string(self, conn_string: str, source: str = "unknown") -> list[EncryptionFinding]:
        """Validate a database connection string for encryption."""
        findings = []

        # Parse URL
        try:
            parsed = urlparse(conn_string)
        except Exception:
            return findings

        scheme = parsed.scheme.lower()
        query_params = parse_qs(parsed.query)

        # PostgreSQL validation
        if scheme in ("postgres", "postgresql", "postgresql+asyncpg"):
            sslmode = query_params.get("sslmode", [None])[0]

            if sslmode is None:
                findings.append(
                    EncryptionFinding(
                        severity="HIGH",
                        database="PostgreSQL",
                        issue=f"No sslmode specified in connection string ({source})",
                        recommendation="Add sslmode=verify-full to connection string",
                        task_id="DATA-01",
                    )
                )
            elif sslmode == "disable":
                findings.append(
                    EncryptionFinding(
                        severity="CRITICAL",
                        database="PostgreSQL",
                        issue=f"SSL explicitly disabled ({source})",
                        recommendation="Change sslmode=disable to sslmode=verify-full",
                        task_id="DATA-01",
                    )
                )
            elif sslmode in ("allow", "prefer"):
                findings.append(
                    EncryptionFinding(
                        severity="MEDIUM",
                        database="PostgreSQL",
                        issue=f"Weak sslmode={sslmode} allows unencrypted connections ({source})",
                        recommendation="Use sslmode=verify-full for mandatory encryption",
                        task_id="DATA-01",
                    )
                )
            elif sslmode == "require":
                findings.append(
                    EncryptionFinding(
                        severity="LOW",
                        database="PostgreSQL",
                        issue=f"sslmode=require doesn't verify server certificate ({source})",
                        recommendation="Consider sslmode=verify-full for certificate verification",
                        task_id="DATA-01",
                    )
                )
            # verify-ca and verify-full are acceptable

        # Redis validation
        elif scheme == "redis":
            findings.append(
                EncryptionFinding(
                    severity="MEDIUM",
                    database="Redis",
                    issue=f"Using unencrypted redis:// scheme ({source})",
                    recommendation="Use rediss:// for TLS-encrypted Redis connections",
                    task_id="DATA-01",
                )
            )

        # MySQL validation
        elif scheme in ("mysql", "mysql+pymysql", "mysql+aiomysql"):
            ssl_mode = query_params.get("ssl_mode", [None])[0]
            ssl_disabled = query_params.get("ssl_disabled", ["false"])[0]

            if ssl_disabled.lower() == "true":
                findings.append(
                    EncryptionFinding(
                        severity="CRITICAL",
                        database="MySQL",
                        issue=f"SSL explicitly disabled ({source})",
                        recommendation="Remove ssl_disabled=true and configure SSL",
                        task_id="DATA-01",
                    )
                )
            elif ssl_mode is None:
                findings.append(
                    EncryptionFinding(
                        severity="HIGH",
                        database="MySQL",
                        issue=f"No ssl_mode specified ({source})",
                        recommendation="Add ssl_mode=VERIFY_IDENTITY for certificate verification",
                        task_id="DATA-01",
                    )
                )

        self.findings.extend(findings)
        return findings

    def scan_env_file(self, env_path: Path) -> list[EncryptionFinding]:
        """Scan .env file for database connection strings."""
        if not env_path.exists():
            print(f"Warning: {env_path} does not exist")
            return []

        db_url_patterns = [
            r"DATABASE_URL",
            r"DB_URL",
            r"POSTGRES_URL",
            r"POSTGRESQL_URL",
            r"REDIS_URL",
            r"MYSQL_URL",
            r"SQLALCHEMY_DATABASE_URI",
        ]

        pattern = re.compile(rf"({'|'.join(db_url_patterns)})\s*=\s*(.+)", re.IGNORECASE)

        findings = []
        with open(env_path) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if line.startswith("#"):
                    continue

                match = pattern.match(line)
                if match:
                    var_name = match.group(1)
                    conn_string = match.group(2).strip("'\"")
                    source = f"{env_path.name}:{lineno} ({var_name})"
                    findings.extend(self.validate_connection_string(conn_string, source))

        return findings

    def scan_python_files(self, source_dir: Path) -> list[EncryptionFinding]:
        """Scan Python files for hardcoded connection strings."""
        conn_pattern = re.compile(
            r'["\'](?:postgres(?:ql)?|mysql|redis|rediss)(?:\+[a-z]+)?://[^"\']+["\']',
            re.IGNORECASE,
        )

        findings = []
        for path in source_dir.rglob("*.py"):
            try:
                with open(path) as f:
                    content = f.read()
            except (IOError, UnicodeDecodeError):
                continue

            for match in conn_pattern.finditer(content):
                conn_string = match.group(0).strip("'\"")
                # Find line number
                lineno = content[: match.start()].count("\n") + 1
                source = f"{path.name}:{lineno}"
                findings.extend(self.validate_connection_string(conn_string, source))

        return findings

    def check_environment(self) -> list[EncryptionFinding]:
        """Check current environment variables for DB connections."""
        db_vars = [
            "DATABASE_URL",
            "DB_URL",
            "POSTGRES_URL",
            "REDIS_URL",
            "MYSQL_URL",
        ]

        findings = []
        for var in db_vars:
            value = os.environ.get(var)
            if value:
                findings.extend(self.validate_connection_string(value, f"env:{var}"))

        return findings


def main():
    parser = argparse.ArgumentParser(description="Validate database encryption settings")
    parser.add_argument("--env-file", "-e", type=Path, help=".env file to scan")
    parser.add_argument("--source-dir", "-s", type=Path, help="Source directory to scan")
    parser.add_argument("--check-env", action="store_true", help="Check current environment variables")
    parser.add_argument("--connection-string", "-c", help="Single connection string to validate")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    if not any([args.env_file, args.source_dir, args.check_env, args.connection_string]):
        parser.error("At least one of --env-file, --source-dir, --check-env, or --connection-string is required")

    validator = DatabaseEncryptionValidator()
    all_findings = []

    # Validate single connection string
    if args.connection_string:
        all_findings.extend(validator.validate_connection_string(args.connection_string, "command-line"))

    # Scan .env file
    if args.env_file:
        print(f"📋 Scanning env file: {args.env_file}\n")
        all_findings.extend(validator.scan_env_file(args.env_file))

    # Scan source directory
    if args.source_dir:
        print(f"📂 Scanning source directory: {args.source_dir}\n")
        all_findings.extend(validator.scan_python_files(args.source_dir))

    # Check environment
    if args.check_env:
        print("🔍 Checking environment variables\n")
        all_findings.extend(validator.check_environment())

    if args.output == "json":
        import json

        print(json.dumps([vars(f) for f in all_findings], indent=2))
    else:
        if not all_findings:
            print("✅ All database connections use proper encryption")
        else:
            severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            print(f"Found {len(all_findings)} encryption issue(s):\n")

            for f in sorted(all_findings, key=lambda x: severity_order.index(x.severity), reverse=True):
                severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(f.severity, "⚪")
                print(f"{severity_icon} [{f.severity}] {f.database}")
                print(f"   Issue: {f.issue}")
                print(f"   Fix: {f.recommendation}")
                print(f"   Task: {f.task_id}")
                print()

    # Exit with error if critical/high findings
    critical_high = [f for f in all_findings if f.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        print(f"❌ Found {len(critical_high)} critical/high encryption issue(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
