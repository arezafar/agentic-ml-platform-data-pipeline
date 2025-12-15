#!/usr/bin/env python3
"""
Verify MOJO artifact usage in ML pipelines.

Implements the "Artifact Integrity Scanner" superpower.
Scans Mage pipelines and Python code for MOJO vs POJO usage.

Usage:
    python verify_mojo_artifact.py --pipeline-dir ./mage_pipeline
    python verify_mojo_artifact.py --source-dir ./src --output json
"""

import argparse
import ast
import json
import re
import sys
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class ArtifactViolation:
    """A detected artifact integrity issue."""
    
    file: str
    line: int
    violation_type: str
    severity: str
    task_id: str
    message: str
    recommendation: str


# Forbidden artifact patterns
FORBIDDEN_PATTERNS = {
    "download_pojo": {
        "severity": "CRITICAL",
        "task_id": "DEV-REV-01-01",
        "message": "Using POJO export instead of MOJO",
        "recommendation": "Replace download_pojo() with download_mojo()",
    },
    "pickle.dump": {
        "severity": "CRITICAL",
        "task_id": "DEV-REV-01-01",
        "message": "Using pickle for model serialization",
        "recommendation": "Use model.download_mojo() for H2O models",
    },
    "pickle.dumps": {
        "severity": "CRITICAL",
        "task_id": "DEV-REV-01-01",
        "message": "Using pickle for model serialization",
        "recommendation": "Use model.download_mojo() for H2O models",
    },
    "joblib.dump": {
        "severity": "HIGH",
        "task_id": "DEV-REV-01-01",
        "message": "Using joblib for model serialization",
        "recommendation": "Use model.download_mojo() for H2O models",
    },
    "h2o.save_model": {
        "severity": "HIGH",
        "task_id": "DEV-REV-01-01",
        "message": "Using H2O binary save (not portable)",
        "recommendation": "Use model.download_mojo() for portable MOJO format",
    },
}


class ArtifactVisitor(ast.NodeVisitor):
    """AST visitor to check artifact export patterns."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.violations: list[ArtifactViolation] = []
        self.mojo_exports: list[int] = []  # Line numbers with valid exports
        self.has_h2o_import = False
    
    def visit_Import(self, node: ast.Import) -> None:
        """Track H2O imports."""
        for alias in node.names:
            if alias.name == 'h2o' or alias.name.startswith('h2o.'):
                self.has_h2o_import = True
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track H2O imports."""
        if node.module and (node.module == 'h2o' or node.module.startswith('h2o.')):
            self.has_h2o_import = True
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for artifact patterns."""
        call_str = self._get_call_string(node)
        
        # Check for forbidden patterns
        for pattern, info in FORBIDDEN_PATTERNS.items():
            if pattern in call_str:
                self.violations.append(ArtifactViolation(
                    file=self.filepath,
                    line=node.lineno,
                    violation_type=f"FORBIDDEN_{pattern.upper().replace('.', '_')}",
                    severity=info["severity"],
                    task_id=info["task_id"],
                    message=info["message"],
                    recommendation=info["recommendation"],
                ))
        
        # Track valid MOJO exports
        if 'download_mojo' in call_str:
            self.mojo_exports.append(node.lineno)
            
            # Verify get_genmodel_jar parameter for validation
            if 'get_genmodel_jar' not in call_str:
                self.violations.append(ArtifactViolation(
                    file=self.filepath,
                    line=node.lineno,
                    violation_type="MISSING_GENMODEL_JAR",
                    severity="LOW",
                    task_id="DEV-REV-01-01",
                    message="MOJO export missing get_genmodel_jar parameter",
                    recommendation="Add get_genmodel_jar=True to download_mojo() for validation",
                ))
        
        self.generic_visit(node)
    
    def _get_call_string(self, node: ast.Call) -> str:
        """Get string representation of call."""
        try:
            return ast.unparse(node)
        except Exception:
            return ""


class VersionChecker:
    """Check H2O version consistency."""
    
    def __init__(self):
        self.versions_found: dict[str, list[tuple[str, int]]] = {
            "requirements": [],
            "dockerfile": [],
            "pyproject": [],
        }
        self.violations: list[ArtifactViolation] = []
    
    def check_requirements(self, path: Path) -> None:
        """Check requirements.txt for pinned H2O version."""
        if not path.exists():
            return
        
        content = path.read_text()
        
        # Check for h2o package
        h2o_pattern = re.search(r'^h2o([=<>!~]+)?([\d.]+)?', content, re.MULTILINE)
        daimojo_pattern = re.search(r'^daimojo([=<>!~]+)?([\d.]+)?', content, re.MULTILINE)
        
        if h2o_pattern:
            if '==' not in (h2o_pattern.group(1) or ''):
                self.violations.append(ArtifactViolation(
                    file=str(path),
                    line=0,
                    violation_type="UNPINNED_H2O_VERSION",
                    severity="HIGH",
                    task_id="DEV-REV-01-02",
                    message="H2O version is not pinned exactly",
                    recommendation="Use h2o==X.X.X.X format for exact version pinning",
                ))
            else:
                self.versions_found["requirements"].append(
                    (h2o_pattern.group(2) or "unknown", 0)
                )
        
        if daimojo_pattern:
            if '==' not in (daimojo_pattern.group(1) or ''):
                self.violations.append(ArtifactViolation(
                    file=str(path),
                    line=0,
                    violation_type="UNPINNED_DAIMOJO_VERSION",
                    severity="HIGH",
                    task_id="DEV-REV-01-02",
                    message="daimojo version is not pinned exactly",
                    recommendation="Use daimojo==X.X.X format for exact version pinning",
                ))
    
    def check_dockerfile(self, path: Path) -> None:
        """Check Dockerfile for H2O version consistency."""
        if not path.exists():
            return
        
        content = path.read_text()
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for H2O image or download
            h2o_version = re.search(r'h2o[^\d]*([\d.]+)', line)
            if h2o_version:
                self.versions_found["dockerfile"].append(
                    (h2o_version.group(1), i)
                )
    
    def check_version_consistency(self) -> None:
        """Check that all versions are consistent."""
        all_versions = set()
        
        for source, versions in self.versions_found.items():
            for version, _ in versions:
                all_versions.add(version)
        
        if len(all_versions) > 1:
            self.violations.append(ArtifactViolation(
                file="project",
                line=0,
                violation_type="VERSION_MISMATCH",
                severity="CRITICAL",
                task_id="DEV-REV-01-02",
                message=f"Inconsistent H2O versions found: {all_versions}",
                recommendation="Ensure all H2O versions match across requirements.txt, Dockerfile, and runtime",
            ))


class MojoArtifactValidator:
    """Validator for MOJO artifact usage."""
    
    def __init__(self):
        self.violations: list[ArtifactViolation] = []
        self.files_scanned = 0
        self.mojo_exports_found = 0
    
    def scan_directory(self, source_dir: Path) -> list[ArtifactViolation]:
        """Scan directory for artifact issues."""
        for path in source_dir.rglob("*.py"):
            self._scan_python_file(path)
        
        # Check for version consistency
        self._check_versions(source_dir)
        
        # Check for actual MOJO files
        self._check_artifact_files(source_dir)
        
        return self.violations
    
    def _scan_python_file(self, path: Path) -> None:
        """Scan a Python file for artifact patterns."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return
        
        self.files_scanned += 1
        
        visitor = ArtifactVisitor(str(path))
        visitor.visit(tree)
        
        self.violations.extend(visitor.violations)
        self.mojo_exports_found += len(visitor.mojo_exports)
    
    def _check_versions(self, source_dir: Path) -> None:
        """Check version consistency."""
        checker = VersionChecker()
        
        # Check common locations
        for req_file in ["requirements.txt", "requirements-ml.txt", "requirements-train.txt"]:
            checker.check_requirements(source_dir / req_file)
            checker.check_requirements(source_dir.parent / req_file)
        
        for dockerfile in ["Dockerfile", "Dockerfile.train", "Dockerfile.inference"]:
            checker.check_dockerfile(source_dir / dockerfile)
            checker.check_dockerfile(source_dir.parent / dockerfile)
        
        checker.check_version_consistency()
        self.violations.extend(checker.violations)
    
    def _check_artifact_files(self, source_dir: Path) -> None:
        """Check for POJO .java files or invalid artifacts."""
        # Check for POJO files
        for java_file in source_dir.rglob("*.java"):
            if "model" in java_file.stem.lower() or "gbm" in java_file.stem.lower():
                self.violations.append(ArtifactViolation(
                    file=str(java_file),
                    line=0,
                    violation_type="POJO_ARTIFACT_FILE",
                    severity="CRITICAL",
                    task_id="DEV-REV-01-01",
                    message="Found POJO .java artifact file",
                    recommendation="Replace with MOJO .zip artifact",
                ))
        
        # Check for pickle files
        for pkl_file in source_dir.rglob("*.pkl"):
            self.violations.append(ArtifactViolation(
                file=str(pkl_file),
                line=0,
                violation_type="PICKLE_ARTIFACT_FILE",
                severity="CRITICAL",
                task_id="DEV-REV-01-01",
                message="Found pickle .pkl artifact file",
                recommendation="Replace with MOJO .zip artifact",
            ))
        
        # Validate MOJO files
        for zip_file in source_dir.rglob("*.zip"):
            self._validate_mojo_file(zip_file)
    
    def _validate_mojo_file(self, path: Path) -> None:
        """Validate that a .zip file is a valid MOJO."""
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                if 'model.ini' not in zf.namelist():
                    self.violations.append(ArtifactViolation(
                        file=str(path),
                        line=0,
                        violation_type="INVALID_MOJO",
                        severity="HIGH",
                        task_id="DEV-REV-01-01",
                        message="ZIP file does not appear to be a valid MOJO (missing model.ini)",
                        recommendation="Regenerate artifact using model.download_mojo()",
                    ))
        except zipfile.BadZipFile:
            pass  # Not a zip file, might be something else


def main():
    parser = argparse.ArgumentParser(
        description="Verify MOJO artifact usage in ML pipelines (Artifact Integrity Scanner)"
    )
    parser.add_argument(
        "--pipeline-dir", "-p",
        type=Path,
        help="Mage pipeline directory to scan"
    )
    parser.add_argument(
        "--source-dir", "-s",
        type=Path,
        help="Generic source directory to scan"
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
    
    source_dir = args.pipeline_dir or args.source_dir
    if not source_dir:
        print("Error: Must specify --pipeline-dir or --source-dir")
        sys.exit(1)
    
    if not source_dir.exists():
        print(f"Error: Directory {source_dir} does not exist")
        sys.exit(1)
    
    validator = MojoArtifactValidator()
    violations = validator.scan_directory(source_dir)
    
    # Filter by severity
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_index = severity_order.index(args.severity)
    violations = [v for v in violations if severity_order.index(v.severity) >= min_index]
    
    if args.output == "json":
        output = {
            "scanner": "verify_mojo_artifact",
            "superpower": "Artifact Integrity Scanner",
            "files_scanned": validator.files_scanned,
            "mojo_exports_found": validator.mojo_exports_found,
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"🔍 Artifact Integrity Scanner")
        print(f"   Scanned {validator.files_scanned} Python file(s)")
        print(f"   Found {validator.mojo_exports_found} valid MOJO export(s)\n")
        
        if not violations:
            print("✅ No artifact integrity issues detected")
        else:
            print(f"⚠️  Found {len(violations)} issue(s):\n")
            
            for v in sorted(violations, key=lambda x: severity_order.index(x.severity), reverse=True):
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[v.severity]
                print(f"{icon} [{v.severity}] {v.violation_type}")
                print(f"   File: {v.file}:{v.line}" if v.line else f"   File: {v.file}")
                print(f"   Message: {v.message}")
                print(f"   Fix: {v.recommendation}")
                print(f"   Task ID: {v.task_id}")
                print()
    
    # Exit with error if critical/high findings
    critical_high = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        sys.exit(1)


if __name__ == "__main__":
    main()
