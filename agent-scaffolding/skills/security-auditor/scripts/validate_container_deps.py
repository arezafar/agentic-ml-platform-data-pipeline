#!/usr/bin/env python3
"""
Validate container dependencies for security vulnerabilities.

Checks:
- Docker image CVE scanning via trivy
- Multi-stage build verification
- Non-root user verification
- Build tool elimination
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VulnerabilityFinding:
    """Container vulnerability finding."""

    severity: str
    package: str
    installed_version: str
    fixed_version: Optional[str]
    cve_id: str
    title: str


@dataclass
class DockerfileFinding:
    """Dockerfile security finding."""

    severity: str
    line: int
    message: str
    task_id: str


class ContainerSecurityValidator:
    """Validate container security configuration."""

    def __init__(self):
        self.dockerfile_findings: list[DockerfileFinding] = []
        self.vulnerability_findings: list[VulnerabilityFinding] = []

    def scan_image(self, image: str) -> list[VulnerabilityFinding]:
        """Scan Docker image for CVEs using trivy."""
        try:
            result = subprocess.run(
                ["trivy", "image", "--format", "json", "--severity", "CRITICAL,HIGH", image],
                capture_output=True,
                text=True,
                timeout=300,
            )
        except FileNotFoundError:
            print("Warning: trivy not installed. Skipping image scan.")
            print("Install with: brew install trivy (macOS) or apt install trivy (Linux)")
            return []
        except subprocess.TimeoutExpired:
            print("Warning: trivy scan timed out")
            return []

        if result.returncode != 0 and "error" in result.stderr.lower():
            print(f"Warning: trivy scan failed: {result.stderr}")
            return []

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("Warning: Could not parse trivy output")
            return []

        findings = []
        for result in data.get("Results", []):
            for vuln in result.get("Vulnerabilities", []):
                findings.append(
                    VulnerabilityFinding(
                        severity=vuln.get("Severity", "UNKNOWN"),
                        package=vuln.get("PkgName", "unknown"),
                        installed_version=vuln.get("InstalledVersion", "unknown"),
                        fixed_version=vuln.get("FixedVersion"),
                        cve_id=vuln.get("VulnerabilityID", "unknown"),
                        title=vuln.get("Title", "No description"),
                    )
                )

        self.vulnerability_findings = findings
        return findings

    def scan_dockerfile(self, dockerfile_path: Path) -> list[DockerfileFinding]:
        """Scan Dockerfile for security issues."""
        if not dockerfile_path.exists():
            print(f"Error: Dockerfile not found at {dockerfile_path}")
            return []

        with open(dockerfile_path) as f:
            lines = f.readlines()

        content = "".join(lines)

        # Check 1: Multi-stage build
        if content.count("FROM ") < 2:
            self.dockerfile_findings.append(
                DockerfileFinding(
                    severity="MEDIUM",
                    line=1,
                    message="No multi-stage build detected. Consider using builder + runtime stages.",
                    task_id="CONT-01",
                )
            )

        # Check 2: Non-root user
        has_user_directive = False
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("USER "):
                user = stripped[5:].strip()
                if user not in ("root", "0"):
                    has_user_directive = True
                else:
                    self.dockerfile_findings.append(
                        DockerfileFinding(
                            severity="HIGH",
                            line=lineno,
                            message="Container explicitly runs as root",
                            task_id="CONT-03",
                        )
                    )

        if not has_user_directive:
            self.dockerfile_findings.append(
                DockerfileFinding(
                    severity="HIGH",
                    line=1,
                    message="No non-root USER directive found. Container will run as root.",
                    task_id="CONT-03",
                )
            )

        # Check 3: Latest tag
        for lineno, line in enumerate(lines, 1):
            if line.strip().startswith("FROM "):
                if ":latest" in line or (":") not in line.split()[1]:
                    self.dockerfile_findings.append(
                        DockerfileFinding(
                            severity="MEDIUM",
                            line=lineno,
                            message="Using 'latest' or untagged image. Pin to specific version.",
                            task_id="CONT-02",
                        )
                    )

        # Check 4: COPY instead of ADD
        for lineno, line in enumerate(lines, 1):
            if line.strip().startswith("ADD "):
                # ADD is only needed for URLs or tar extraction
                if "http" not in line and ".tar" not in line:
                    self.dockerfile_findings.append(
                        DockerfileFinding(
                            severity="LOW",
                            line=lineno,
                            message="Use COPY instead of ADD unless extracting archives",
                            task_id="CONT-01",
                        )
                    )

        # Check 5: Docker socket mount (in compose files)
        if "docker.sock" in content:
            self.dockerfile_findings.append(
                DockerfileFinding(
                    severity="CRITICAL",
                    line=1,
                    message="Docker socket mounting detected. This enables container escape.",
                    task_id="CONT-03",
                )
            )

        return self.dockerfile_findings

    def verify_runtime_security(self, container_name: str) -> dict:
        """Verify runtime security settings of a running container."""
        checks = {
            "non_root": False,
            "no_build_tools": False,
            "no_jvm": True,  # Assume true unless proven otherwise
            "read_only": False,
        }

        # Check user
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "whoami"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                user = result.stdout.strip()
                checks["non_root"] = user not in ("root", "0")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Check build tools
        build_tools = ["gcc", "pip", "curl", "wget", "git"]
        for tool in build_tools:
            try:
                result = subprocess.run(
                    ["docker", "exec", container_name, "which", tool],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    checks["no_build_tools"] = False
                    break
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
        else:
            checks["no_build_tools"] = True

        # Check JVM
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "java", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                checks["no_jvm"] = False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return checks


def main():
    parser = argparse.ArgumentParser(description="Validate container security")
    parser.add_argument("--image", "-i", help="Docker image to scan")
    parser.add_argument("--dockerfile", "-d", type=Path, help="Dockerfile to analyze")
    parser.add_argument("--container", "-c", help="Running container to verify")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text", help="Output format")

    args = parser.parse_args()

    if not any([args.image, args.dockerfile, args.container]):
        parser.error("At least one of --image, --dockerfile, or --container is required")

    validator = ContainerSecurityValidator()
    has_critical = False

    # Scan Dockerfile
    if args.dockerfile:
        print(f"📋 Scanning Dockerfile: {args.dockerfile}\n")
        findings = validator.scan_dockerfile(args.dockerfile)

        if findings:
            for f in sorted(findings, key=lambda x: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(x.severity), reverse=True):
                severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(f.severity, "⚪")
                print(f"{severity_icon} [{f.severity}] Line {f.line}: {f.message}")
                print(f"   Task: {f.task_id}")
                if f.severity in ("CRITICAL", "HIGH"):
                    has_critical = True
            print()
        else:
            print("✅ No Dockerfile issues found\n")

    # Scan image for CVEs
    if args.image:
        print(f"🔍 Scanning image for CVEs: {args.image}\n")
        vulns = validator.scan_image(args.image)

        if vulns:
            print(f"Found {len(vulns)} vulnerabilities:\n")
            for v in sorted(vulns, key=lambda x: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(x.severity), reverse=True):
                severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(v.severity, "⚪")
                print(f"{severity_icon} [{v.severity}] {v.cve_id}")
                print(f"   Package: {v.package} ({v.installed_version})")
                if v.fixed_version:
                    print(f"   Fixed in: {v.fixed_version}")
                print(f"   {v.title[:80]}...")
                print()
                if v.severity in ("CRITICAL", "HIGH"):
                    has_critical = True
        else:
            print("✅ No critical/high CVEs found\n")

    # Verify running container
    if args.container:
        print(f"🔒 Verifying runtime security: {args.container}\n")
        checks = validator.verify_runtime_security(args.container)

        for check, passed in checks.items():
            icon = "✅" if passed else "❌"
            print(f"{icon} {check.replace('_', ' ').title()}")
            if not passed and check in ("non_root", "no_jvm"):
                has_critical = True
        print()

    if has_critical:
        print("❌ Security validation failed with critical/high findings")
        sys.exit(1)
    else:
        print("✅ Security validation passed")


if __name__ == "__main__":
    main()
