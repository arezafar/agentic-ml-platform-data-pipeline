#!/usr/bin/env python3
"""
Scan codebase for exposed secrets and credentials.

Checks:
- Hardcoded API keys
- Passwords in code
- Private keys
- Connection strings with credentials
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Pattern


@dataclass
class SecretFinding:
    """Secret exposure finding."""

    severity: str
    category: str
    file: str
    line: int
    match: str
    message: str


# Patterns for detecting secrets (pattern, category, severity, description)
SECRET_PATTERNS: list[tuple[Pattern, str, str, str]] = [
    # API Keys
    (re.compile(r'["\']sk-[a-zA-Z0-9]{32,}["\']'), "OpenAI API Key", "CRITICAL", "OpenAI API key detected"),
    (re.compile(r'["\']ghp_[a-zA-Z0-9]{36}["\']'), "GitHub Token", "CRITICAL", "GitHub personal access token detected"),
    (re.compile(r'["\']gho_[a-zA-Z0-9]{36}["\']'), "GitHub OAuth", "CRITICAL", "GitHub OAuth token detected"),
    (re.compile(r'["\']github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}["\']'), "GitHub PAT", "CRITICAL", "GitHub fine-grained PAT detected"),
    (re.compile(r'AKIA[0-9A-Z]{16}'), "AWS Access Key", "CRITICAL", "AWS access key ID detected"),
    (re.compile(r'["\'][0-9a-zA-Z/+]{40}["\']'), "AWS Secret Key", "HIGH", "Possible AWS secret access key"),
    (re.compile(r'["\']xox[baprs]-[0-9a-zA-Z]{10,}["\']'), "Slack Token", "CRITICAL", "Slack token detected"),
    (re.compile(r'["\']AIza[0-9A-Za-z\-_]{35}["\']'), "Google API Key", "CRITICAL", "Google API key detected"),
    
    # Database connection strings
    (re.compile(r'postgres(?:ql)?://[^:]+:[^@]+@'), "PostgreSQL URL", "CRITICAL", "PostgreSQL connection string with password"),
    (re.compile(r'mysql://[^:]+:[^@]+@'), "MySQL URL", "CRITICAL", "MySQL connection string with password"),
    (re.compile(r'mongodb(?:\+srv)?://[^:]+:[^@]+@'), "MongoDB URL", "CRITICAL", "MongoDB connection string with password"),
    (re.compile(r'redis://:[^@]+@'), "Redis URL", "HIGH", "Redis connection string with password"),
    
    # Generic patterns
    (re.compile(r'password\s*[=:]\s*["\'][^"\']{8,}["\']', re.IGNORECASE), "Password", "HIGH", "Hardcoded password detected"),
    (re.compile(r'secret\s*[=:]\s*["\'][^"\']{8,}["\']', re.IGNORECASE), "Secret", "HIGH", "Hardcoded secret detected"),
    (re.compile(r'api[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9]{16,}["\']', re.IGNORECASE), "API Key", "HIGH", "Hardcoded API key detected"),
    (re.compile(r'auth[_-]?token\s*[=:]\s*["\'][^"\']{16,}["\']', re.IGNORECASE), "Auth Token", "HIGH", "Hardcoded auth token detected"),
    
    # Private keys
    (re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'), "Private Key", "CRITICAL", "Private key detected in code"),
    (re.compile(r'-----BEGIN PGP PRIVATE KEY BLOCK-----'), "PGP Key", "CRITICAL", "PGP private key detected"),
    
    # JWT secrets
    (re.compile(r'jwt[_-]?secret\s*[=:]\s*["\'][^"\']{16,}["\']', re.IGNORECASE), "JWT Secret", "CRITICAL", "Hardcoded JWT secret detected"),
]

# Files/directories to exclude
EXCLUDE_PATTERNS = [
    "*.pyc",
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "*.min.js",
    "*.lock",
    "package-lock.json",
    "poetry.lock",
    "*.test.py",
    "test_*.py",
    "*_test.py",
]

# Allow-listed patterns (false positives)
ALLOW_LIST = [
    r'os\.environ\.get\(["\']', # Environment variable access
    r'os\.getenv\(["\']',
    r'settings\.',
    r'config\.',
    r'example',
    r'placeholder',
    r'your[_-]?api[_-]?key',
    r'<your[_-]',
    r'xxx+',
    r'\*{3,}',
]


class SecretsScanner:
    """Scanner for exposed secrets in codebase."""

    def __init__(self, allow_patterns: list[str] = None):
        self.findings: list[SecretFinding] = []
        self.allow_patterns = [re.compile(p, re.IGNORECASE) for p in (allow_patterns or ALLOW_LIST)]

    def scan_directory(self, source_dir: Path) -> list[SecretFinding]:
        """Scan all files in directory for secrets."""
        for path in source_dir.rglob("*"):
            if path.is_file() and self._should_scan(path):
                self._scan_file(path)
        return self.findings

    def _should_scan(self, path: Path) -> bool:
        """Check if file should be scanned."""
        # Check exclude patterns
        for pattern in EXCLUDE_PATTERNS:
            if path.match(pattern):
                return False

        # Only scan text files
        text_extensions = {
            ".py", ".js", ".ts", ".json", ".yaml", ".yml",
            ".toml", ".ini", ".cfg", ".conf", ".env",
            ".sh", ".bash", ".zsh", ".md", ".txt",
            ".html", ".xml", ".dockerfile", ""
        }

        return path.suffix.lower() in text_extensions or path.name.lower() in ("dockerfile", ".env", ".env.example")

    def _scan_file(self, path: Path) -> None:
        """Scan single file for secrets."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except (IOError, OSError):
            return

        for lineno, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            # Check allow list
            if any(p.search(line) for p in self.allow_patterns):
                continue

            # Check secret patterns
            for pattern, category, severity, message in SECRET_PATTERNS:
                match = pattern.search(line)
                if match:
                    # Redact the actual secret
                    matched_text = match.group(0)
                    redacted = self._redact(matched_text)

                    self.findings.append(
                        SecretFinding(
                            severity=severity,
                            category=category,
                            file=str(path),
                            line=lineno,
                            match=redacted,
                            message=message,
                        )
                    )

    def _redact(self, text: str) -> str:
        """Redact secret value for safe display."""
        if len(text) <= 10:
            return "*" * len(text)
        return text[:4] + "*" * (len(text) - 8) + text[-4:]


def scan_env_files(source_dir: Path) -> list[SecretFinding]:
    """Specifically scan .env files for secrets."""
    findings = []

    for env_file in source_dir.rglob(".env*"):
        if env_file.is_file() and not env_file.name.endswith(".example"):
            findings.append(
                SecretFinding(
                    severity="HIGH",
                    category="Env File",
                    file=str(env_file),
                    line=0,
                    match=env_file.name,
                    message=f"Non-example .env file found: {env_file.name}. Ensure it's in .gitignore.",
                )
            )

    return findings


def main():
    parser = argparse.ArgumentParser(description="Scan codebase for exposed secrets")
    parser.add_argument("--source-dir", "-s", type=Path, required=True, help="Source directory to scan")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--severity", default="LOW", choices=["CRITICAL", "HIGH", "MEDIUM", "LOW"], help="Minimum severity")

    args = parser.parse_args()

    if not args.source_dir.exists():
        print(f"Error: Directory {args.source_dir} does not exist")
        sys.exit(1)

    scanner = SecretsScanner()
    findings = scanner.scan_directory(args.source_dir)

    # Also check for .env files
    findings.extend(scan_env_files(args.source_dir))

    # Filter by severity
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_index = severity_order.index(args.severity)
    findings = [f for f in findings if severity_order.index(f.severity) >= min_index]

    if args.output == "json":
        import json

        print(json.dumps([vars(f) for f in findings], indent=2))
    else:
        if not findings:
            print("✅ No secrets detected in codebase")
        else:
            print(f"🚨 Found {len(findings)} potential secret(s):\n")

            for f in sorted(findings, key=lambda x: severity_order.index(x.severity), reverse=True):
                severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(f.severity, "⚪")
                print(f"{severity_icon} [{f.severity}] {f.category}")
                print(f"   File: {f.file}:{f.line}")
                print(f"   Match: {f.match}")
                print(f"   {f.message}")
                print()

    # Exit with error if critical/high findings
    critical_high = [f for f in findings if f.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        print(f"\n❌ Found {len(critical_high)} critical/high severity secret(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
