#!/usr/bin/env python3
"""
Dialectical Reasoning Gate for architectural decisions.

This script enforces the mandatory thesis-antithesis-synthesis debate
for architectural decisions before implementation proceeds.

Usage:
    python dialectical_reasoning_gate.py --pr-description ./pr.txt --adrs ./adr/
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# Architectural conflicts that require dialectical synthesis
DIALECTICAL_TOPICS = {
    "artifact_strategy": {
        "thesis": "POJO allows direct Java integration",
        "antithesis": "POJO compilation overhead exceeds 64KB method limit",
        "synthesis": "MOJO mandate with C++ runtime for production",
        "keywords": ["pojo", "mojo", "download_pojo", "download_mojo", "artifact", "model export"]
    },
    "concurrency_model": {
        "thesis": "Async provides scalability for I/O operations",
        "antithesis": "ML inference is CPU-bound and blocks event loop",
        "synthesis": "run_in_executor offloading for blocking operations",
        "keywords": ["async", "blocking", "event loop", "h2o.predict", "run_in_executor", "thread pool"]
    },
    "consistency_model": {
        "thesis": "ACID transactions ensure data integrity",
        "antithesis": "Long-running model training locks tables",
        "synthesis": "Snapshot isolation with event_time for time-travel",
        "keywords": ["acid", "transaction", "snapshot", "isolation", "event_time", "feature store"]
    },
    "memory_allocation": {
        "thesis": "Maximize JVM heap for H2O performance",
        "antithesis": "XGBoost native buffers need off-heap memory",
        "synthesis": "60-70% JVM heap, remainder for native memory",
        "keywords": ["memory", "heap", "xmx", "native", "xgboost", "oom", "container limit"]
    },
    "schema_strategy": {
        "thesis": "Relational schema for query optimization",
        "antithesis": "Feature evolution requires schema flexibility",
        "synthesis": "Hybrid model with JSONB + GIN for sparse features",
        "keywords": ["jsonb", "relational", "schema", "gin", "index", "feature"]
    }
}


@dataclass
class ReasoningViolation:
    """Represents a missing dialectical synthesis."""
    topic: str
    thesis: str
    antithesis: str
    expected_synthesis: str
    severity: str
    message: str


def detect_topics_in_text(text: str) -> List[str]:
    """Detect which dialectical topics are relevant to the text."""
    text_lower = text.lower()
    relevant_topics = []
    
    for topic_id, topic_info in DIALECTICAL_TOPICS.items():
        for keyword in topic_info["keywords"]:
            if keyword.lower() in text_lower:
                if topic_id not in relevant_topics:
                    relevant_topics.append(topic_id)
                break
    
    return relevant_topics


def check_synthesis_in_adrs(adr_dir: Path, topic_id: str) -> bool:
    """Check if an ADR documents the synthesis for a topic."""
    if not adr_dir.exists():
        return False
    
    topic_info = DIALECTICAL_TOPICS[topic_id]
    synthesis_keywords = topic_info["synthesis"].lower().split()
    
    for adr_file in adr_dir.glob("*.md"):
        try:
            content = adr_file.read_text().lower()
            # Check if ADR discusses this topic and includes synthesis elements
            topic_mentioned = any(kw.lower() in content for kw in topic_info["keywords"])
            synthesis_covered = sum(1 for kw in synthesis_keywords if kw in content)
            
            if topic_mentioned and synthesis_covered >= 2:
                return True
        except Exception:
            continue
    
    return False


def check_synthesis_in_pr(pr_text: str, topic_id: str) -> bool:
    """Check if PR description includes dialectical reasoning."""
    pr_lower = pr_text.lower()
    topic_info = DIALECTICAL_TOPICS[topic_id]
    
    # Check for explicit reasoning markers
    reasoning_markers = [
        "considered", "chose", "because", "instead of",
        "trade-off", "tradeoff", "decision", "rationale",
        "thesis", "antithesis", "synthesis"
    ]
    
    has_reasoning = any(marker in pr_lower for marker in reasoning_markers)
    synthesis_keywords = topic_info["synthesis"].lower().split()
    synthesis_covered = sum(1 for kw in synthesis_keywords if kw in pr_lower)
    
    return has_reasoning and synthesis_covered >= 1


def validate_dialectical_reasoning(
    pr_text: str,
    adr_dir: Optional[Path] = None
) -> List[ReasoningViolation]:
    """Validate that all relevant topics have documented synthesis."""
    violations = []
    
    # Detect relevant topics
    relevant_topics = detect_topics_in_text(pr_text)
    
    for topic_id in relevant_topics:
        topic_info = DIALECTICAL_TOPICS[topic_id]
        
        # Check if synthesis is documented
        synthesis_in_pr = check_synthesis_in_pr(pr_text, topic_id)
        synthesis_in_adr = check_synthesis_in_adrs(adr_dir, topic_id) if adr_dir else False
        
        if not synthesis_in_pr and not synthesis_in_adr:
            violations.append(ReasoningViolation(
                topic=topic_id,
                thesis=topic_info["thesis"],
                antithesis=topic_info["antithesis"],
                expected_synthesis=topic_info["synthesis"],
                severity="HIGH" if topic_id in ("artifact_strategy", "concurrency_model") else "MEDIUM",
                message=f"PR touches '{topic_id}' but lacks documented dialectical synthesis"
            ))
    
    return violations


def print_report(violations: List[ReasoningViolation], output_format: str):
    """Print violation report."""
    if output_format == "json":
        import json
        data = [
            {
                "topic": v.topic,
                "thesis": v.thesis,
                "antithesis": v.antithesis,
                "expected_synthesis": v.expected_synthesis,
                "severity": v.severity,
                "message": v.message
            }
            for v in violations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("DIALECTICAL REASONING GATE REPORT")
        print("=" * 60)
        
        if not violations:
            print("\n✅ All architectural decisions have documented synthesis")
        else:
            print(f"\n❌ Found {len(violations)} undocumented dialectical conflict(s)\n")
            
            for v in sorted(violations, key=lambda x: x.severity):
                print(f"[{v.severity}] Topic: {v.topic}")
                print(f"  Thesis: {v.thesis}")
                print(f"  Antithesis: {v.antithesis}")
                print(f"  Expected Synthesis: {v.expected_synthesis}")
                print(f"  → {v.message}")
                print()
            
            print("To resolve: Document the synthesis in an ADR or the PR description.")
            print("Example: 'We chose MOJO over POJO because compilation overhead")
            print("         exceeds Java's 64KB method limit for large models.'")


def main():
    parser = argparse.ArgumentParser(
        description="Enforce dialectical reasoning gate for architectural decisions"
    )
    parser.add_argument(
        "--pr-description", "-p",
        type=Path,
        required=True,
        help="Path to PR description text file"
    )
    parser.add_argument(
        "--adrs", "-a",
        type=Path,
        default=None,
        help="Path to Architecture Decision Records directory"
    )
    parser.add_argument(
        "--output", "-o",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    if not args.pr_description.exists():
        print(f"Error: File not found: {args.pr_description}")
        return 1
    
    try:
        pr_text = args.pr_description.read_text()
    except Exception as e:
        print(f"Error reading PR description: {e}")
        return 1
    
    violations = validate_dialectical_reasoning(pr_text, args.adrs)
    print_report(violations, args.output)
    
    # Exit with error if high severity violations found
    high_count = sum(1 for v in violations if v.severity == "HIGH")
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
