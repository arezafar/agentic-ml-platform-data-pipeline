#!/usr/bin/env python3
"""
QA Skill - Mage Block Validator

Validates Mage dynamic block contracts and configurations.

Implements task:
- UT-MAGE-01: Verify Dynamic Block Output Structure
- UT-MAGE-02: Validate Metadata UUID Uniqueness

Usage:
    python check_mage_blocks.py --pipeline-dir ./mage_pipeline
    python check_mage_blocks.py --pipeline-dir ./pipelines/ml_training --strict
"""

import argparse
import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional


# =============================================================================
# Configuration
# =============================================================================

# Mage block types
BLOCK_TYPES = ["data_loaders", "transformers", "data_exporters", "custom", "sensors"]

# Required metadata keys for dynamic blocks
REQUIRED_METADATA_KEYS = ["block_uuid"]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class BlockInfo:
    """Information about a Mage block."""
    file_path: str
    block_type: str
    block_name: str
    is_dynamic: bool
    has_reduce: bool
    returns_correct_structure: bool
    issues: list[str]


@dataclass
class ValidationResult:
    """Result of pipeline validation."""
    pipeline_path: str
    blocks: list[BlockInfo]
    passed: bool
    errors: list[str]
    warnings: list[str]


# =============================================================================
# AST Analysis
# =============================================================================


class MageBlockVisitor(ast.NodeVisitor):
    """Analyze Mage block Python files."""
    
    def __init__(self):
        self.has_execute_function = False
        self.has_dynamic_decorator = False
        self.has_reduce_decorator = False
        self.return_statements: list[ast.Return] = []
        self.issues: list[str] = []
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == "execute":
            self.has_execute_function = True
            
            # Check for decorators
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    if decorator.id == "dynamic":
                        self.has_dynamic_decorator = True
                    elif decorator.id == "reduce":
                        self.has_reduce_decorator = True
            
            # Collect return statements
            for child in ast.walk(node):
                if isinstance(child, ast.Return):
                    self.return_statements.append(child)
        
        self.generic_visit(node)
    
    def analyze_dynamic_return(self) -> bool:
        """
        Check if dynamic block returns correct structure.
        
        Expected: [data_list, metadata_list] where both are lists
        """
        if not self.has_dynamic_decorator:
            return True  # Not applicable
        
        for ret in self.return_statements:
            if ret.value is None:
                self.issues.append("Dynamic block has return without value")
                return False
            
            # Check if returning a list
            if isinstance(ret.value, ast.List):
                if len(ret.value.elts) != 2:
                    self.issues.append(
                        f"Dynamic block should return [data, metadata], "
                        f"got {len(ret.value.elts)} elements"
                    )
                    return False
            elif isinstance(ret.value, ast.Tuple):
                self.issues.append(
                    "Dynamic block should return list [data, metadata], not tuple"
                )
                return False
        
        return True


def analyze_block_file(file_path: Path) -> BlockInfo:
    """Analyze a single Mage block file."""
    issues = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except Exception as e:
        return BlockInfo(
            file_path=str(file_path),
            block_type="unknown",
            block_name=file_path.stem,
            is_dynamic=False,
            has_reduce=False,
            returns_correct_structure=False,
            issues=[f"Could not read file: {e}"],
        )
    
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return BlockInfo(
            file_path=str(file_path),
            block_type="unknown",
            block_name=file_path.stem,
            is_dynamic=False,
            has_reduce=False,
            returns_correct_structure=False,
            issues=[f"Syntax error: {e}"],
        )
    
    visitor = MageBlockVisitor()
    visitor.visit(tree)
    
    # Determine block type from path
    block_type = "unknown"
    for bt in BLOCK_TYPES:
        if bt in str(file_path):
            block_type = bt
            break
    
    # Check for execute function
    if not visitor.has_execute_function:
        issues.append("Block missing 'execute' function")
    
    # Analyze return structure for dynamic blocks
    returns_correct = visitor.analyze_dynamic_return()
    issues.extend(visitor.issues)
    
    return BlockInfo(
        file_path=str(file_path),
        block_type=block_type,
        block_name=file_path.stem,
        is_dynamic=visitor.has_dynamic_decorator,
        has_reduce=visitor.has_reduce_decorator,
        returns_correct_structure=returns_correct,
        issues=issues,
    )


# =============================================================================
# UUID Validation
# =============================================================================


def check_uuid_patterns(source: str) -> list[str]:
    """
    Check for UUID generation patterns in source code.
    
    Returns list of issues found.
    """
    issues = []
    
    # Check for hardcoded UUIDs in metadata
    hardcoded_uuid = re.findall(
        r'["\']block_uuid["\']\s*:\s*["\']([^"\']+)["\']',
        source
    )
    
    if hardcoded_uuid:
        # Check for uniqueness (within the file)
        if len(hardcoded_uuid) != len(set(hardcoded_uuid)):
            issues.append("Duplicate hardcoded block_uuid values detected")
        
        # Check for invalid characters
        valid_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        for uuid in hardcoded_uuid:
            if not valid_pattern.match(uuid):
                issues.append(
                    f"Invalid characters in block_uuid: '{uuid}'. "
                    "Use only alphanumeric, underscores, and hyphens."
                )
    
    return issues


# =============================================================================
# Pipeline Validation
# =============================================================================


def find_mage_blocks(pipeline_dir: Path) -> Generator[Path, None, None]:
    """Find all Mage block Python files in pipeline directory."""
    for block_type in BLOCK_TYPES:
        block_dir = pipeline_dir / block_type
        if block_dir.exists():
            for file in block_dir.glob("*.py"):
                if not file.name.startswith("__"):
                    yield file


def validate_pipeline(pipeline_dir: Path) -> ValidationResult:
    """Validate all blocks in a Mage pipeline."""
    blocks = []
    errors = []
    warnings = []
    
    # Check pipeline structure
    if not pipeline_dir.exists():
        return ValidationResult(
            pipeline_path=str(pipeline_dir),
            blocks=[],
            passed=False,
            errors=[f"Pipeline directory not found: {pipeline_dir}"],
            warnings=[],
        )
    
    metadata_json = pipeline_dir / "metadata.json"
    if not metadata_json.exists():
        warnings.append(f"Missing metadata.json in {pipeline_dir}")
    
    # Analyze blocks
    for block_path in find_mage_blocks(pipeline_dir):
        block = analyze_block_file(block_path)
        blocks.append(block)
        
        if block.issues:
            for issue in block.issues:
                if "error" in issue.lower() or "missing" in issue.lower():
                    errors.append(f"{block.block_name}: {issue}")
                else:
                    warnings.append(f"{block.block_name}: {issue}")
        
        # Check UUID patterns in file
        with open(block_path, "r") as f:
            uuid_issues = check_uuid_patterns(f.read())
            for issue in uuid_issues:
                errors.append(f"{block.block_name}: {issue}")
    
    # Check dynamic/reduce pairing
    dynamic_blocks = [b for b in blocks if b.is_dynamic]
    reduce_blocks = [b for b in blocks if b.has_reduce]
    
    if dynamic_blocks and not reduce_blocks:
        warnings.append(
            f"Found {len(dynamic_blocks)} dynamic block(s) but no @reduce block. "
            "Consider adding a reduce block to aggregate fan-out results."
        )
    
    passed = len(errors) == 0
    
    return ValidationResult(
        pipeline_path=str(pipeline_dir),
        blocks=blocks,
        passed=passed,
        errors=errors,
        warnings=warnings,
    )


# =============================================================================
# Output
# =============================================================================


def format_result(result: ValidationResult) -> str:
    """Format validation result for terminal output."""
    lines = [
        "=" * 60,
        "MAGE PIPELINE VALIDATION",
        "=" * 60,
        f"Pipeline: {result.pipeline_path}",
        f"Status: {'✅ PASSED' if result.passed else '❌ FAILED'}",
        "",
        f"Blocks analyzed: {len(result.blocks)}",
    ]
    
    # Block summary
    dynamic_count = sum(1 for b in result.blocks if b.is_dynamic)
    if dynamic_count > 0:
        lines.append(f"Dynamic blocks: {dynamic_count}")
    
    # Errors
    if result.errors:
        lines.extend(["", "ERRORS:"])
        for err in result.errors:
            lines.append(f"  ❌ {err}")
    
    # Warnings
    if result.warnings:
        lines.extend(["", "WARNINGS:"])
        for warn in result.warnings:
            lines.append(f"  ⚠️ {warn}")
    
    lines.append("=" * 60)
    
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Validate Mage pipeline blocks"
    )
    
    parser.add_argument(
        "--pipeline-dir",
        type=str,
        required=True,
        help="Path to Mage pipeline directory",
    )
    
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors",
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    
    args = parser.parse_args()
    
    pipeline_dir = Path(args.pipeline_dir)
    
    result = validate_pipeline(pipeline_dir)
    
    if args.json:
        import json
        output = {
            "pipeline": result.pipeline_path,
            "passed": result.passed,
            "blocks": [
                {
                    "file": b.file_path,
                    "type": b.block_type,
                    "name": b.block_name,
                    "is_dynamic": b.is_dynamic,
                    "issues": b.issues,
                }
                for b in result.blocks
            ],
            "errors": result.errors,
            "warnings": result.warnings,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_result(result))
    
    # Exit code
    if not result.passed:
        sys.exit(1)
    elif args.strict and result.warnings:
        print("\n⚠️ Failing due to --strict flag")
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
