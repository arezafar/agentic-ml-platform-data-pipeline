#!/usr/bin/env python3
"""
TDD Compliance Checker

This script verifies that implementation files have corresponding test files,
enforcing the Iron Law of TDD.

Checks:
1. Every .py file in src/ has a corresponding test_*.py
2. Test files use Testcontainers for integration tests
3. Pytest fixtures follow the expected patterns

Usage:
    python check_tdd_compliance.py src/ tests/
    python check_tdd_compliance.py --strict src/ tests/
"""

import argparse
import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


@dataclass
class ComplianceResult:
    """Result of TDD compliance check."""
    implementation_files: int
    test_files: int
    coverage_ratio: float
    missing_tests: List[str]
    testcontainer_files: List[str]
    issues: List[str]


def find_python_files(directory: Path, prefix: str = "") -> Set[str]:
    """
    Find all Python files in a directory.
    
    Args:
        directory: Directory to search
        prefix: Prefix filter (e.g., "test_")
        
    Returns:
        Set of file paths (relative to directory)
    """
    files = set()
    
    if not directory.exists():
        return files
    
    for path in directory.rglob("*.py"):
        if path.name.startswith("__"):
            continue
        if prefix and not path.name.startswith(prefix):
            continue
        if not prefix and path.name.startswith("test_"):
            continue
        
        # Get relative path
        rel_path = str(path.relative_to(directory))
        files.add(rel_path)
    
    return files


def get_expected_test_name(impl_file: str) -> str:
    """
    Convert implementation file path to expected test file path.
    
    Args:
        impl_file: Path like "schemas/feature_store.py"
        
    Returns:
        Expected test path like "test_feature_store.py"
    """
    path = Path(impl_file)
    return f"test_{path.name}"


def check_testcontainers_usage(test_file: Path) -> bool:
    """
    Check if a test file uses Testcontainers.
    
    Args:
        test_file: Path to test file
        
    Returns:
        True if Testcontainers is used
    """
    try:
        content = test_file.read_text()
        
        # Check for Testcontainers imports
        indicators = [
            "testcontainers",
            "PostgresContainer",
            "RedisContainer",
            "DockerContainer",
            "@requires_testcontainers",
        ]
        
        for indicator in indicators:
            if indicator in content:
                return True
        
        return False
    except Exception:
        return False


def check_fixture_patterns(test_file: Path) -> List[str]:
    """
    Check for expected pytest fixture patterns.
    
    Args:
        test_file: Path to test file
        
    Returns:
        List of issues found
    """
    issues = []
    
    try:
        content = test_file.read_text()
        tree = ast.parse(content)
        
        # Check for fixture usage
        has_fixtures = any(
            isinstance(node, ast.FunctionDef) and
            any(
                isinstance(dec, ast.Name) and dec.id == "fixture"
                for dec in node.decorator_list
            )
            for node in ast.walk(tree)
        )
        
        # Check for proper async test markers
        has_async_tests = any(
            isinstance(node, ast.AsyncFunctionDef) and
            node.name.startswith("test_")
            for node in ast.walk(tree)
        )
        
        if has_async_tests:
            if "pytest.mark.asyncio" not in content:
                issues.append(f"{test_file.name}: async tests without pytest.mark.asyncio")
        
    except SyntaxError:
        issues.append(f"{test_file.name}: syntax error, cannot parse")
    except Exception as e:
        issues.append(f"{test_file.name}: error analyzing: {e}")
    
    return issues


def check_compliance(
    impl_dir: Path,
    test_dir: Path,
    strict: bool = False
) -> ComplianceResult:
    """
    Check TDD compliance between implementation and test directories.
    
    Args:
        impl_dir: Implementation source directory
        test_dir: Test directory
        strict: If True, require 100% coverage
        
    Returns:
        ComplianceResult with findings
    """
    # Find all files
    impl_files = find_python_files(impl_dir)
    test_files = find_python_files(test_dir, prefix="test_")
    
    # Check coverage
    missing_tests = []
    for impl_file in impl_files:
        expected_test = get_expected_test_name(impl_file)
        
        # Check if any test file matches
        has_test = any(
            test.endswith(expected_test) or expected_test in test
            for test in test_files
        )
        
        if not has_test:
            missing_tests.append(impl_file)
    
    # Check for Testcontainers usage
    testcontainer_files = []
    for test_file in test_files:
        test_path = test_dir / test_file
        if test_path.exists() and check_testcontainers_usage(test_path):
            testcontainer_files.append(test_file)
    
    # Collect issues
    issues = []
    
    for test_file in test_files:
        test_path = test_dir / test_file
        if test_path.exists():
            issues.extend(check_fixture_patterns(test_path))
    
    # Calculate coverage
    if impl_files:
        coverage_ratio = (len(impl_files) - len(missing_tests)) / len(impl_files)
    else:
        coverage_ratio = 1.0
    
    return ComplianceResult(
        implementation_files=len(impl_files),
        test_files=len(test_files),
        coverage_ratio=coverage_ratio,
        missing_tests=missing_tests,
        testcontainer_files=testcontainer_files,
        issues=issues
    )


def print_report(result: ComplianceResult, strict: bool = False) -> bool:
    """
    Print compliance report.
    
    Args:
        result: Compliance check result
        strict: If True, fail on any missing tests
        
    Returns:
        True if compliant
    """
    print("=" * 60)
    print("TDD Compliance Report")
    print("=" * 60)
    
    print(f"\nImplementation files: {result.implementation_files}")
    print(f"Test files: {result.test_files}")
    print(f"Coverage ratio: {result.coverage_ratio:.1%}")
    
    if result.testcontainer_files:
        print(f"\n✅ Testcontainers used in {len(result.testcontainer_files)} files:")
        for f in result.testcontainer_files[:5]:
            print(f"   - {f}")
        if len(result.testcontainer_files) > 5:
            print(f"   ... and {len(result.testcontainer_files) - 5} more")
    else:
        print("\n⚠️  No Testcontainers usage detected")
    
    if result.missing_tests:
        print(f"\n❌ Missing tests for {len(result.missing_tests)} files:")
        for f in result.missing_tests[:10]:
            print(f"   - {f}")
        if len(result.missing_tests) > 10:
            print(f"   ... and {len(result.missing_tests) - 10} more")
    
    if result.issues:
        print(f"\n⚠️  Issues found ({len(result.issues)}):")
        for issue in result.issues[:10]:
            print(f"   - {issue}")
    
    print("\n" + "=" * 60)
    
    # Determine pass/fail
    if strict:
        passed = result.coverage_ratio == 1.0 and not result.issues
    else:
        passed = result.coverage_ratio >= 0.5
    
    if passed:
        print("✅ TDD compliance check PASSED")
    else:
        print("❌ TDD compliance check FAILED")
    
    return passed


def main():
    parser = argparse.ArgumentParser(
        description="Check TDD compliance between source and test directories"
    )
    parser.add_argument(
        "impl_dir",
        type=Path,
        help="Implementation source directory"
    )
    parser.add_argument(
        "test_dir",
        type=Path,
        help="Test directory"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Require 100% test coverage"
    )
    
    args = parser.parse_args()
    
    # Validate directories
    if not args.impl_dir.exists():
        print(f"Error: Implementation directory not found: {args.impl_dir}")
        sys.exit(2)
    
    if not args.test_dir.exists():
        print(f"Warning: Test directory not found: {args.test_dir}")
        # Create empty result
        result = ComplianceResult(
            implementation_files=len(find_python_files(args.impl_dir)),
            test_files=0,
            coverage_ratio=0.0,
            missing_tests=list(find_python_files(args.impl_dir)),
            testcontainer_files=[],
            issues=["Test directory does not exist"]
        )
    else:
        result = check_compliance(args.impl_dir, args.test_dir, args.strict)
    
    passed = print_report(result, args.strict)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
