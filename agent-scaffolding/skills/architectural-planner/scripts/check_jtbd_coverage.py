#!/usr/bin/env python3
"""
Check JTBD (Jobs-to-be-Done) coverage in requirements or plan documents.

This script verifies that all core platform jobs are addressed and
correctly mapped to superpowers and architectural views.

Usage:
    python check_jtbd_coverage.py <document.md>
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple


# Core platform jobs that must be addressed
CORE_JOBS = {
    "JTBD-01": {
        "name": "Stack Decomposition",
        "superpower": "Writing-Plans",
        "views": ["Logical", "Development"],
    },
    "JTBD-02": {
        "name": "Scale Inference",
        "superpower": "Scalability Planning",
        "views": ["Process", "Physical"],
    },
    "JTBD-03": {
        "name": "Shard Feature Store",
        "superpower": "Sequential-Thinking",
        "views": ["Logical", "Physical"],
    },
    "JTBD-04": {
        "name": "Ensure Persistence",
        "superpower": "Scalability Planning",
        "views": ["Process", "Physical"],
    },
}


class JTBDReference(NamedTuple):
    """A JTBD reference found in the document."""
    job_id: str
    context: str
    line_number: int


def find_jtbd_references(content: str) -> list[JTBDReference]:
    """Find all JTBD references in the document."""
    references = []
    lines = content.split("\n")
    
    for i, line in enumerate(lines, 1):
        matches = re.finditer(r"JTBD-\d+", line)
        for match in matches:
            # Get context (surrounding text)
            start = max(0, match.start() - 50)
            end = min(len(line), match.end() + 50)
            context = line[start:end].strip()
            
            references.append(JTBDReference(
                job_id=match.group(),
                context=context,
                line_number=i,
            ))
    
    return references


def check_coverage(references: list[JTBDReference]) -> dict:
    """Check which core jobs are covered."""
    found_jobs = {ref.job_id for ref in references}
    
    coverage = {}
    for job_id, job_info in CORE_JOBS.items():
        coverage[job_id] = {
            "found": job_id in found_jobs,
            "name": job_info["name"],
            "superpower": job_info["superpower"],
            "views": job_info["views"],
        }
    
    return coverage


def check_superpower_alignment(content: str) -> list[str]:
    """Check if superpowers are mentioned appropriately."""
    issues = []
    superpowers = ["Writing-Plans", "Sequential-Thinking", "Scalability Planning"]
    
    for sp in superpowers:
        # Case-insensitive search
        pattern = sp.replace("-", r"[\s-]?")
        if not re.search(pattern, content, re.IGNORECASE):
            issues.append(f"Superpower '{sp}' not mentioned in document")
    
    return issues


def check_view_alignment(content: str) -> list[str]:
    """Check if architectural views are mentioned."""
    issues = []
    views = ["Logical", "Process", "Development", "Physical", "Scenario"]
    
    view_counts = {}
    for view in views:
        count = len(re.findall(rf"\b{view}\b", content, re.IGNORECASE))
        view_counts[view] = count
    
    missing = [v for v, c in view_counts.items() if c == 0]
    if missing:
        issues.append(f"Missing view references: {', '.join(missing)}")
    
    return issues


def main(document_path: str) -> int:
    """Main function to check JTBD coverage."""
    path = Path(document_path)
    
    if not path.exists():
        print(f"Error: File not found: {document_path}")
        return 1
    
    content = path.read_text()
    
    print(f"Checking JTBD Coverage: {document_path}")
    print("=" * 60)
    
    # Find all JTBD references
    references = find_jtbd_references(content)
    
    print(f"\nFound {len(references)} JTBD references")
    if references:
        print("-" * 40)
        for ref in references:
            print(f"  Line {ref.line_number}: {ref.job_id}")
            print(f"    Context: ...{ref.context}...")
    
    # Check coverage
    print("\n\nCore Job Coverage:")
    print("-" * 40)
    coverage = check_coverage(references)
    
    all_covered = True
    for job_id, info in coverage.items():
        status = "✓" if info["found"] else "✗"
        all_covered = all_covered and info["found"]
        print(f"  {status} {job_id}: {info['name']}")
        if not info["found"]:
            print(f"      Superpower: {info['superpower']}")
            print(f"      Views: {', '.join(info['views'])}")
    
    # Check superpower alignment
    print("\n\nSuperpower Alignment:")
    print("-" * 40)
    sp_issues = check_superpower_alignment(content)
    if sp_issues:
        for issue in sp_issues:
            print(f"  ✗ {issue}")
    else:
        print("  ✓ All superpowers mentioned")
    
    # Check view alignment
    print("\n\nView Alignment:")
    print("-" * 40)
    view_issues = check_view_alignment(content)
    if view_issues:
        for issue in view_issues:
            print(f"  ✗ {issue}")
    else:
        print("  ✓ All views mentioned")
    
    # Summary
    print("\n" + "=" * 60)
    
    issues_count = len(sp_issues) + len(view_issues)
    missing_jobs = sum(1 for info in coverage.values() if not info["found"])
    
    if all_covered and issues_count == 0:
        print("✓ Full JTBD coverage achieved!")
        return 0
    else:
        print(f"✗ Incomplete coverage:")
        print(f"  - Missing core jobs: {missing_jobs}")
        print(f"  - Alignment issues: {issues_count}")
        return 1


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Check JTBD coverage in requirements or plan documents",
        epilog="Checks for: core JTBD job references, superpower mentions, architectural view coverage"
    )
    parser.add_argument(
        "document",
        type=str,
        help="Path to plan or requirements markdown file"
    )
    
    args = parser.parse_args()
    sys.exit(main(args.document))
