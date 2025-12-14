#!/usr/bin/env python3
"""
Task Execution Validator

This script validates task assignments before execution by the
Implementation Worker.

Validates:
1. Task JSON structure
2. Required fields presence
3. Role mapping to valid skills
4. Verification steps format

Usage:
    python validate_task_execution.py task.json
    python validate_task_execution.py --stdin < task.json
"""

import argparse
import json
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ValidationResult(Enum):
    """Validation outcome."""
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class ValidationError:
    """Single validation error."""
    field: str
    message: str
    severity: ValidationResult


# Valid roles in the platform
VALID_ROLES = {
    "data-engineer",
    "db-architect",
    "ml-engineer",
    "fastapi-pro",
    "deployment-engineer",
}

# Required task fields
REQUIRED_FIELDS = {
    "id": str,
    "description": str,
    "assigned_role": str,
}

# Optional but recommended fields
RECOMMENDED_FIELDS = {
    "file_paths": list,
    "verification_steps": list,
    "definition_of_done": str,
    "epic": str,
    "priority": str,
}


def validate_task_structure(task: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate the basic structure of a task assignment.
    
    Args:
        task: Task dictionary to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    # Check required fields
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in task:
            errors.append(ValidationError(
                field=field,
                message=f"Required field '{field}' is missing",
                severity=ValidationResult.FAIL
            ))
        elif not isinstance(task[field], expected_type):
            errors.append(ValidationError(
                field=field,
                message=f"Field '{field}' should be {expected_type.__name__}",
                severity=ValidationResult.FAIL
            ))
    
    # Check recommended fields
    for field, expected_type in RECOMMENDED_FIELDS.items():
        if field not in task:
            errors.append(ValidationError(
                field=field,
                message=f"Recommended field '{field}' is missing",
                severity=ValidationResult.WARN
            ))
        elif not isinstance(task[field], expected_type):
            errors.append(ValidationError(
                field=field,
                message=f"Field '{field}' should be {expected_type.__name__}",
                severity=ValidationResult.WARN
            ))
    
    return errors


def validate_role(task: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate that the assigned role maps to a valid skill.
    
    Args:
        task: Task dictionary to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    role = task.get("assigned_role", "")
    
    if role and role not in VALID_ROLES:
        errors.append(ValidationError(
            field="assigned_role",
            message=f"Unknown role '{role}'. Valid roles: {VALID_ROLES}",
            severity=ValidationResult.FAIL
        ))
    
    return errors


def validate_verification_steps(task: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate verification steps format.
    
    Each step should have:
    - command: Shell command to run
    - expected_exit_code: Expected return code (default: 0)
    
    Args:
        task: Task dictionary to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    steps = task.get("verification_steps", [])
    
    if not steps:
        errors.append(ValidationError(
            field="verification_steps",
            message="No verification steps defined",
            severity=ValidationResult.WARN
        ))
        return errors
    
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(ValidationError(
                field=f"verification_steps[{i}]",
                message="Step should be a dictionary",
                severity=ValidationResult.FAIL
            ))
            continue
        
        if "command" not in step:
            errors.append(ValidationError(
                field=f"verification_steps[{i}].command",
                message="Step missing 'command' field",
                severity=ValidationResult.FAIL
            ))
    
    return errors


def validate_task(task: Dict[str, Any]) -> tuple[bool, List[ValidationError]]:
    """
    Run all validations on a task.
    
    Args:
        task: Task dictionary to validate
        
    Returns:
        Tuple of (is_valid, errors)
    """
    all_errors = []
    
    all_errors.extend(validate_task_structure(task))
    all_errors.extend(validate_role(task))
    all_errors.extend(validate_verification_steps(task))
    
    # Determine overall pass/fail
    has_failures = any(e.severity == ValidationResult.FAIL for e in all_errors)
    
    return (not has_failures, all_errors)


def print_report(errors: List[ValidationError], verbose: bool = True) -> None:
    """Print validation report."""
    if not errors:
        print("✅ All validations passed")
        return
    
    failures = [e for e in errors if e.severity == ValidationResult.FAIL]
    warnings = [e for e in errors if e.severity == ValidationResult.WARN]
    
    if failures:
        print(f"❌ {len(failures)} failures:")
        for e in failures:
            print(f"   FAIL: {e.field} - {e.message}")
    
    if warnings and verbose:
        print(f"⚠️  {len(warnings)} warnings:")
        for e in warnings:
            print(f"   WARN: {e.field} - {e.message}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate task execution assignments"
    )
    parser.add_argument(
        "task_file",
        nargs="?",
        help="Path to task JSON file"
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read task JSON from stdin"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only show failures, not warnings"
    )
    
    args = parser.parse_args()
    
    # Read task JSON
    if args.stdin:
        task_json = sys.stdin.read()
    elif args.task_file:
        task_path = Path(args.task_file)
        if not task_path.exists():
            print(f"Error: File not found: {args.task_file}", file=sys.stderr)
            sys.exit(2)
        task_json = task_path.read_text()
    else:
        parser.print_help()
        sys.exit(1)
    
    # Parse JSON
    try:
        task = json.loads(task_json)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        sys.exit(2)
    
    # Validate
    is_valid, errors = validate_task(task)
    print_report(errors, verbose=not args.quiet)
    
    # Exit code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
