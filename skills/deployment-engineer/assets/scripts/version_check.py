#!/usr/bin/env python3
"""
H2O Version Compatibility Checker
=============================================================================
DEV-01-03: Version Pinning Strategy Validator

Ensures that:
1. h2o client version in requirements matches h2o.jar version
2. daimojo version is compatible with MOJO export version
3. Dockerfile versions align with requirements

The H2O serialization format is tightly coupled to version.
A mismatch can cause silent model corruption or runtime failures.

Usage:
    python version_check.py --h2o-version 3.46.0.1
    python version_check.py --dockerfile-api Dockerfile.api --dockerfile-mage Dockerfile.mage
=============================================================================
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


class VersionChecker:
    """Validates H2O version compatibility across the stack."""
    
    # Known compatible version pairs
    COMPATIBLE_VERSIONS = {
        "3.46.0.1": {"daimojo": ["2.8.0", "2.8.1", "2.7.0"]},
        "3.44.0.3": {"daimojo": ["2.7.0", "2.6.0"]},
        "3.42.0.4": {"daimojo": ["2.6.0", "2.5.0"]},
    }
    
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
    
    def extract_version_from_requirements(
        self, 
        content: str, 
        package: str
    ) -> Optional[str]:
        """Extract version of a package from requirements.txt content."""
        patterns = [
            rf'^{package}==([0-9.]+)',           # exact: h2o==3.46.0.1
            rf'^{package}>=([0-9.]+)',           # minimum: h2o>=3.46.0.1
            rf'^{package}\[.*\]>=([0-9.]+)',     # extras: h2o[extra]>=3.46.0.1
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_version_from_dockerfile(
        self, 
        content: str, 
        package: str
    ) -> Optional[str]:
        """Extract version of a package from Dockerfile pip install."""
        patterns = [
            rf'{package}==([0-9.]+)',
            rf'{package}>=([0-9.]+)',
            rf'{package}\[.*\]>=([0-9.]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_image_version(self, content: str, image_prefix: str) -> Optional[str]:
        """Extract version tag from Docker image reference."""
        pattern = rf'{image_prefix}:([0-9.]+)'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None
    
    def check_h2o_compatibility(
        self,
        h2o_version: str,
        daimojo_version: Optional[str] = None,
    ) -> bool:
        """Check if h2o and daimojo versions are compatible."""
        if h2o_version not in self.COMPATIBLE_VERSIONS:
            self.warnings.append(
                f"H2O version {h2o_version} not in known compatibility matrix. "
                "Please verify manually."
            )
            return True  # Don't fail on unknown versions
        
        if daimojo_version:
            compatible = self.COMPATIBLE_VERSIONS[h2o_version].get("daimojo", [])
            if daimojo_version not in compatible:
                self.errors.append(
                    f"daimojo {daimojo_version} may not be compatible with "
                    f"h2o {h2o_version}. Compatible versions: {compatible}"
                )
                return False
        
        return True
    
    def check_dockerfile_versions(
        self,
        dockerfile_path: Path,
        expected_h2o: str,
    ) -> bool:
        """Check versions in a Dockerfile match expected."""
        if not dockerfile_path.exists():
            self.warnings.append(f"Dockerfile not found: {dockerfile_path}")
            return True
        
        content = dockerfile_path.read_text()
        
        # Check H2O version in pip install
        found_h2o = self.extract_version_from_dockerfile(content, "h2o")
        if found_h2o and found_h2o != expected_h2o:
            self.errors.append(
                f"{dockerfile_path.name}: h2o version {found_h2o} != expected {expected_h2o}"
            )
            return False
        
        # Check H2O image version
        image_version = self.extract_image_version(content, "h2oai/h2o-open-source-k8s")
        if image_version and image_version != expected_h2o:
            self.errors.append(
                f"{dockerfile_path.name}: H2O image version {image_version} != "
                f"expected {expected_h2o}"
            )
            return False
        
        return True
    
    def check_requirements_file(
        self,
        requirements_path: Path,
        expected_h2o: str,
    ) -> bool:
        """Check versions in requirements.txt match expected."""
        if not requirements_path.exists():
            self.warnings.append(f"Requirements file not found: {requirements_path}")
            return True
        
        content = requirements_path.read_text()
        
        found_h2o = self.extract_version_from_requirements(content, "h2o")
        if found_h2o and found_h2o != expected_h2o:
            self.errors.append(
                f"{requirements_path.name}: h2o version {found_h2o} != expected {expected_h2o}"
            )
            return False
        
        return True
    
    def report(self) -> bool:
        """Print report and return True if no errors."""
        print("=" * 60)
        print("H2O VERSION COMPATIBILITY CHECK")
        print("=" * 60)
        
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All version checks passed!")
        elif not self.errors:
            print("\n✅ No critical issues (warnings only)")
        else:
            print("\n❌ Version check FAILED")
        
        print("=" * 60)
        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Check H2O version compatibility across the MLOps stack"
    )
    parser.add_argument(
        "--h2o-version",
        type=str,
        default="3.46.0.1",
        help="Expected H2O version (default: 3.46.0.1)"
    )
    parser.add_argument(
        "--daimojo-version",
        type=str,
        help="daimojo version to check compatibility"
    )
    parser.add_argument(
        "--dockerfile-api",
        type=Path,
        help="Path to API Dockerfile"
    )
    parser.add_argument(
        "--dockerfile-mage",
        type=Path,
        help="Path to Mage Dockerfile"
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        help="Path to requirements.txt"
    )
    
    args = parser.parse_args()
    checker = VersionChecker()
    
    # Run checks
    checker.check_h2o_compatibility(args.h2o_version, args.daimojo_version)
    
    if args.dockerfile_api:
        checker.check_dockerfile_versions(args.dockerfile_api, args.h2o_version)
    
    if args.dockerfile_mage:
        checker.check_dockerfile_versions(args.dockerfile_mage, args.h2o_version)
    
    if args.requirements:
        checker.check_requirements_file(args.requirements, args.h2o_version)
    
    # Report and exit
    success = checker.report()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
