#!/usr/bin/env python3
"""
Validate the structure of generated implementation plans.

This script checks that a plan document contains all required sections,
JTBD mappings, 4+1 View coverage, and verification steps.

Usage:
    python validate_plan_structure.py <plan_file.md>
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple


class ValidationResult(NamedTuple):
    """Result of a validation check."""
    passed: bool
    message: str


def validate_required_sections(content: str) -> list[ValidationResult]:
    """Check for required top-level sections."""
    required_sections = [
        "Overview",
        "Phase",
        "Task",
        "Verification",
    ]
    
    results = []
    for section in required_sections:
        pattern = rf"#+\s+.*{section}"
        if re.search(pattern, content, re.IGNORECASE):
            results.append(ValidationResult(True, f"Found section: {section}"))
        else:
            results.append(ValidationResult(False, f"Missing section: {section}"))
    
    return results


def validate_task_structure(content: str) -> list[ValidationResult]:
    """Check that tasks have required fields."""
    results = []
    
    # Find all task blocks
    task_pattern = r"###\s+Task\s+[\d.]+.*?(?=###|$)"
    tasks = re.findall(task_pattern, content, re.DOTALL)
    
    if not tasks:
        results.append(ValidationResult(False, "No tasks found"))
        return results
    
    results.append(ValidationResult(True, f"Found {len(tasks)} tasks"))
    
    required_fields = [
        ("Assignee", r"\*\*Assignee\*\*:"),
        ("Files", r"\*\*Files\*\*:"),
        ("Verification", r"\*\*Verification\*\*:"),
        ("Definition of Done", r"\*\*Definition of Done\*\*:"),
    ]
    
    for i, task in enumerate(tasks, 1):
        for field_name, field_pattern in required_fields:
            if re.search(field_pattern, task):
                results.append(ValidationResult(True, f"Task {i}: Has {field_name}"))
            else:
                results.append(ValidationResult(False, f"Task {i}: Missing {field_name}"))
    
    return results


def validate_jtbd_mapping(content: str) -> list[ValidationResult]:
    """Check for JTBD references."""
    results = []
    
    # Check for JTBD references
    jtbd_pattern = r"JTBD-\d+"
    jtbd_refs = re.findall(jtbd_pattern, content)
    
    if jtbd_refs:
        unique_refs = set(jtbd_refs)
        results.append(ValidationResult(True, f"Found JTBD references: {', '.join(sorted(unique_refs))}"))
    else:
        results.append(ValidationResult(False, "No JTBD references found (optional but recommended)"))
    
    return results


def validate_view_coverage(content: str) -> list[ValidationResult]:
    """Check for 4+1 architectural view mentions."""
    results = []
    
    views = {
        "Logical": r"\b(Logical|LOG)\b",
        "Process": r"\b(Process|PROC)\b",
        "Development": r"\b(Development|DEV)\b",
        "Physical": r"\b(Physical|PHY)\b",
        "Scenarios": r"\b(Scenario|validation|failure)\b",
    }
    
    found_views = []
    for view_name, pattern in views.items():
        if re.search(pattern, content, re.IGNORECASE):
            found_views.append(view_name)
    
    if len(found_views) >= 3:
        results.append(ValidationResult(True, f"Good view coverage: {', '.join(found_views)}"))
    else:
        results.append(ValidationResult(False, f"Limited view coverage: {', '.join(found_views) or 'None'}"))
    
    return results


def validate_verification_steps(content: str) -> list[ValidationResult]:
    """Check that verification steps include commands."""
    results = []
    
    # Look for code blocks in verification sections
    verification_pattern = r"\*\*Verification\*\*:.*?(?=\*\*|$)"
    verification_blocks = re.findall(verification_pattern, content, re.DOTALL)
    
    has_commands = False
    for block in verification_blocks:
        if re.search(r"`[^`]+`|```", block):
            has_commands = True
            break
    
    if has_commands:
        results.append(ValidationResult(True, "Verification steps include commands"))
    else:
        results.append(ValidationResult(False, "Verification steps should include executable commands"))
    
    return results


def main(plan_file: str) -> int:
    """Main validation function."""
    path = Path(plan_file)
    
    if not path.exists():
        print(f"Error: File not found: {plan_file}")
        return 1
    
    content = path.read_text()
    
    print(f"Validating: {plan_file}")
    print("=" * 60)
    
    all_results = []
    
    # Run all validations
    validators = [
        ("Required Sections", validate_required_sections),
        ("Task Structure", validate_task_structure),
        ("JTBD Mapping", validate_jtbd_mapping),
        ("View Coverage", validate_view_coverage),
        ("Verification Steps", validate_verification_steps),
    ]
    
    for name, validator in validators:
        print(f"\n{name}:")
        print("-" * 40)
        results = validator(content)
        all_results.extend(results)
        
        for result in results:
            status = "✓" if result.passed else "✗"
            print(f"  {status} {result.message}")
    
    # Summary
    passed = sum(1 for r in all_results if r.passed)
    total = len(all_results)
    
    print("\n" + "=" * 60)
    print(f"Summary: {passed}/{total} checks passed")
    
    # Return non-zero if any critical checks failed
    critical_failures = [r for r in all_results if not r.passed and "Missing section" in r.message]
    
    if critical_failures:
        print("\nCritical failures detected. Plan needs revision.")
        return 1
    
    print("\nPlan structure is valid.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_plan_structure.py <plan_file.md>")
        sys.exit(1)
    
    sys.exit(main(sys.argv[1]))
