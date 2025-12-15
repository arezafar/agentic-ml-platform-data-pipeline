#!/usr/bin/env python3
"""
Verify MOJO artifact usage in ML pipelines (Artifact Integrity Scanner).

This script scans Mage pipeline code to ensure MOJO artifacts are used
instead of POJOs, and validates artifact integrity.

Usage:
    python verify_mojo_artifact.py --pipeline-dir ./src/pipeline
"""

import argparse
import re
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ArtifactViolation:
    """Represents an artifact violation."""
    file: str
    line: int
    violation_type: str
    message: str
    severity: str


def check_pojo_usage(content: str, filepath: str) -> List[ArtifactViolation]:
    """Check for download_pojo() usage (should be download_mojo())."""
    violations = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        if "download_pojo" in line:
            violations.append(ArtifactViolation(
                file=filepath,
                line=i,
                violation_type="POJO_USAGE",
                message="Use download_mojo() instead of download_pojo() to avoid Jar Hell",
                severity="CRITICAL"
            ))
    
    return violations


def check_mojo_configuration(content: str, filepath: str) -> List[ArtifactViolation]:
    """Check for proper MOJO configuration."""
    violations = []
    
    # Check if download_mojo is used
    if "download_mojo" in content:
        # Check for get_genmodel_jar if needed
        if "genmodel" not in content.lower() and "get_genmodel_jar" not in content:
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "download_mojo" in line:
                    violations.append(ArtifactViolation(
                        file=filepath,
                        line=i,
                        violation_type="MISSING_GENMODEL",
                        message="Consider get_genmodel_jar=True for inference runtime",
                        severity="LOW"
                    ))
                    break
    
    return violations


def check_artifact_extension(content: str, filepath: str) -> List[ArtifactViolation]:
    """Check for correct artifact file extensions."""
    violations = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        # Check for .java file outputs (POJO indicator)
        if re.search(r"\.java['\"]", line) and "model" in line.lower():
            violations.append(ArtifactViolation(
                file=filepath,
                line=i,
                violation_type="JAVA_ARTIFACT",
                message="Java artifact detected; MOJO should produce .zip files",
                severity="HIGH"
            ))
    
    return violations


def check_version_pinning(content: str, filepath: str) -> List[ArtifactViolation]:
    """Check for H2O version pinning."""
    violations = []
    
    # Check if h2o is imported without version check
    if "import h2o" in content:
        if "h2o.__version__" not in content and "version" not in content.lower():
            violations.append(ArtifactViolation(
                file=filepath,
                line=0,
                violation_type="NO_VERSION_CHECK",
                message="No H2O version check; may cause train/inference mismatch",
                severity="MEDIUM"
            ))
    
    return violations


def validate_mojo_file(mojo_path: Path) -> Optional[ArtifactViolation]:
    """Validate a MOJO zip file structure."""
    try:
        if not mojo_path.suffix == ".zip":
            return ArtifactViolation(
                file=str(mojo_path),
                line=0,
                violation_type="INVALID_EXTENSION",
                message=f"MOJO should have .zip extension, got {mojo_path.suffix}",
                severity="HIGH"
            )
        
        with zipfile.ZipFile(mojo_path, 'r') as zf:
            names = zf.namelist()
            # MOJO files should contain model.ini
            if not any("model.ini" in n for n in names):
                return ArtifactViolation(
                    file=str(mojo_path),
                    line=0,
                    violation_type="INVALID_MOJO",
                    message="MOJO zip missing model.ini; may be corrupted or POJO",
                    severity="CRITICAL"
                )
    except zipfile.BadZipFile:
        return ArtifactViolation(
            file=str(mojo_path),
            line=0,
            violation_type="CORRUPT_ARTIFACT",
            message="Invalid zip file; artifact may be corrupted",
            severity="CRITICAL"
        )
    except Exception:
        pass
    
    return None


def scan_pipeline(pipeline_dir: Path, severity_filter: str = "LOW") -> List[ArtifactViolation]:
    """Scan pipeline directory for artifact issues."""
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    min_severity = severity_order.get(severity_filter, 3)
    
    all_violations = []
    
    # Scan Python files
    for filepath in pipeline_dir.rglob("*.py"):
        try:
            content = filepath.read_text()
        except Exception:
            continue
        
        str_path = str(filepath)
        all_violations.extend(check_pojo_usage(content, str_path))
        all_violations.extend(check_mojo_configuration(content, str_path))
        all_violations.extend(check_artifact_extension(content, str_path))
        all_violations.extend(check_version_pinning(content, str_path))
    
    # Scan for MOJO files and validate them
    for mojo_file in pipeline_dir.rglob("*.zip"):
        if "model" in mojo_file.name.lower() or "mojo" in mojo_file.name.lower():
            violation = validate_mojo_file(mojo_file)
            if violation:
                all_violations.append(violation)
    
    # Filter by severity
    filtered = [v for v in all_violations if severity_order.get(v.severity, 3) <= min_severity]
    return filtered


def print_report(violations: List[ArtifactViolation], output_format: str):
    """Print violation report."""
    if output_format == "json":
        import json
        data = [
            {
                "file": v.file,
                "line": v.line,
                "type": v.violation_type,
                "message": v.message,
                "severity": v.severity
            }
            for v in violations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("ARTIFACT INTEGRITY SCANNER REPORT")
        print("=" * 60)
        
        if not violations:
            print("\n✅ No artifact violations detected")
        else:
            print(f"\n❌ Found {len(violations)} artifact violation(s)\n")
            
            for v in sorted(violations, key=lambda x: (x.severity, x.file)):
                loc = f"{v.file}:{v.line}" if v.line > 0 else v.file
                print(f"[{v.severity}] {loc}")
                print(f"  Type: {v.violation_type}")
                print(f"  {v.message}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Verify MOJO artifact usage in ML pipelines"
    )
    parser.add_argument(
        "--pipeline-dir", "-p",
        type=Path,
        required=True,
        help="Pipeline directory to scan"
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
    
    if not args.pipeline_dir.exists():
        print(f"Error: Directory not found: {args.pipeline_dir}")
        return 1
    
    violations = scan_pipeline(args.pipeline_dir, args.severity)
    print_report(violations, args.output)
    
    # Exit with error if critical violations found
    critical_count = sum(1 for v in violations if v.severity == "CRITICAL")
    return 1 if critical_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
