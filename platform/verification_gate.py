"""
Verification Gate Checklist - Implementation Status

This module provides programmatic verification of the 4+1 View Model
implementation requirements from the Verification Gate Checklist.

Run with: python3 verification_gate.py
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def check_ssl_termination(platform_path: Path) -> Tuple[bool, str]:
    """PHY: Verify SSL termination is configured."""
    ssl_config = platform_path / "serving" / "ssl_termination.conf"
    if ssl_config.exists():
        content = ssl_config.read_text()
        if "ssl_protocols TLSv1.2 TLSv1.3" in content:
            return True, "TLS 1.2/1.3 configured in ssl_termination.conf"
    return False, "SSL termination config not found"


def check_executor_offloading(platform_path: Path) -> Tuple[bool, str]:
    """PROC: Verify blocking calls use run_in_executor."""
    serving_path = platform_path / "serving"
    pattern = re.compile(r"run_in_executor|ProcessPoolExecutor|ThreadPoolExecutor")
    
    for py_file in serving_path.glob("*.py"):
        content = py_file.read_text()
        if pattern.search(content):
            return True, f"Executor pattern found in {py_file.name}"
    return False, "No executor offloading pattern found"


def check_snapshot_isolation(platform_path: Path) -> Tuple[bool, str]:
    """LOG: Verify snapshot isolation for training data."""
    persistence_path = platform_path / "persistence"
    
    for py_file in persistence_path.glob("*.py"):
        content = py_file.read_text()
        if "created_at" in content and "snapshot" in content.lower():
            return True, f"Snapshot isolation pattern found in {py_file.name}"
    return False, "No snapshot isolation pattern found"


def check_testcontainers(skills_path: Path) -> Tuple[bool, str]:
    """DEV: Verify TDD with Testcontainers."""
    tdd_path = skills_path / "implementation-worker" / "assets" / "tdd"
    conftest = tdd_path / "conftest.py"
    
    if conftest.exists():
        content = conftest.read_text()
        if "PostgresContainer" in content:
            return True, "Testcontainers PostgreSQL fixtures configured"
    return False, "Testcontainers not configured"


def check_pydantic_contracts(platform_path: Path) -> Tuple[bool, str]:
    """DEV: Verify Pydantic models shared between components."""
    # Check if serving layer uses Pydantic
    serving_path = platform_path / "serving"
    has_pydantic = False
    
    for py_file in serving_path.glob("**/*.py"):
        content = py_file.read_text()
        if "BaseModel" in content and "pydantic" in content:
            has_pydantic = True
            break
    
    if has_pydantic:
        return True, "Pydantic models used in serving layer"
    return False, "Pydantic models not found"


def check_h2o_memory_split(skills_path: Path) -> Tuple[bool, str]:
    """PHY: Verify H2O 70/30 JVM/Native memory split."""
    k8s_path = skills_path / "implementation-worker" / "assets" / "k8s"
    statefulset = k8s_path / "h2o_statefulset.yaml"
    
    if statefulset.exists():
        content = statefulset.read_text()
        # Check for memory configuration comment and XMX setting
        if "70%" in content or "70/30" in content:
            if "H2O_JVM_XMX" in content:
                return True, "H2O memory split 70/30 configured"
    return False, "H2O memory configuration not found"


def check_readiness_probe(skills_path: Path) -> Tuple[bool, str]:
    """PHY: Verify readiness probe checks cluster consensus."""
    k8s_path = skills_path / "implementation-worker" / "assets" / "k8s"
    statefulset = k8s_path / "h2o_statefulset.yaml"
    
    if statefulset.exists():
        content = statefulset.read_text()
        if "cloud_healthy" in content and "cloud_size" in content:
            return True, "Readiness probe checks cluster consensus"
    return False, "Cluster consensus probe not configured"


def run_verification(base_path: Path) -> Dict[str, Tuple[bool, str]]:
    """Run all verification checks."""
    platform_path = base_path / "platform"
    skills_path = base_path / "skills"
    
    checks = {
        "SSL Termination (PHY)": check_ssl_termination(platform_path),
        "Executor Offloading (PROC)": check_executor_offloading(platform_path),
        "Snapshot Isolation (LOG)": check_snapshot_isolation(platform_path),
        "Testcontainers (DEV)": check_testcontainers(skills_path),
        "Pydantic Contracts (DEV)": check_pydantic_contracts(platform_path),
        "H2O Memory Split (PHY)": check_h2o_memory_split(skills_path),
        "Cluster Consensus Probe (PHY)": check_readiness_probe(skills_path),
    }
    
    return checks


def main():
    """Main entry point."""
    # Determine base path
    script_path = Path(__file__).resolve()
    base_path = script_path.parent.parent  # Go up from platform/ to agent-scaffolding/
    
    print("=" * 60)
    print("Verification Gate Checklist - 4+1 View Model")
    print("=" * 60)
    print()
    
    results = run_verification(base_path)
    
    passed = 0
    failed = 0
    
    for check_name, (status, message) in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {check_name}")
        print(f"   {message}")
        print()
        
        if status:
            passed += 1
        else:
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    # Exit with error code if any check failed
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
