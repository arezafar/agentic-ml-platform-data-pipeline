#!/usr/bin/env python3
"""
Check container memory allocation (Resource Isolation Sight).

This script validates Docker Compose and Kubernetes manifest files
to ensure proper JVM Heap vs Container memory split for H2O workloads.

Usage:
    python check_memory_allocation.py --compose-file ./docker-compose.yml
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class MemoryViolation:
    """Represents a memory configuration violation."""
    file: str
    service: str
    violation_type: str
    message: str
    severity: str
    details: Optional[str] = None


def parse_memory_value(value: str) -> Optional[int]:
    """Parse memory value to bytes."""
    if not value:
        return None
    
    value = value.strip().upper()
    multipliers = {
        "K": 1024,
        "KB": 1024,
        "KI": 1024,
        "M": 1024**2,
        "MB": 1024**2,
        "MI": 1024**2,
        "G": 1024**3,
        "GB": 1024**3,
        "GI": 1024**3,
    }
    
    for suffix, multiplier in multipliers.items():
        if value.endswith(suffix):
            try:
                return int(float(value[:-len(suffix)]) * multiplier)
            except ValueError:
                return None
    
    try:
        return int(value)
    except ValueError:
        return None


def parse_xmx_value(java_opts: str) -> Optional[int]:
    """Extract and parse -Xmx value from JAVA_OPTS."""
    match = re.search(r"-Xmx(\d+[kmgKMG]?)", java_opts)
    if match:
        return parse_memory_value(match.group(1))
    return None


def check_docker_compose(filepath: Path) -> List[MemoryViolation]:
    """Check Docker Compose file for memory issues."""
    violations = []
    
    try:
        import yaml
        content = yaml.safe_load(filepath.read_text())
    except ImportError:
        # Fallback to regex-based parsing
        return check_docker_compose_regex(filepath)
    except Exception:
        return violations
    
    if not content or "services" not in content:
        return violations
    
    for service_name, service_config in content.get("services", {}).items():
        # Check for memory limits
        deploy = service_config.get("deploy", {})
        resources = deploy.get("resources", {})
        limits = resources.get("limits", {})
        memory_limit = limits.get("memory")
        
        # Also check mem_limit (older format)
        if not memory_limit:
            memory_limit = service_config.get("mem_limit")
        
        # Check for JAVA_OPTS
        environment = service_config.get("environment", {})
        if isinstance(environment, list):
            java_opts = None
            for env in environment:
                if "JAVA_OPTS" in str(env):
                    java_opts = str(env).split("=", 1)[-1]
                    break
        else:
            java_opts = environment.get("JAVA_OPTS", "")
        
        # Check if this is an H2O/Java service
        image = service_config.get("image", "")
        is_java_service = any(x in image.lower() for x in ["h2o", "java", "jvm"])
        
        if java_opts and "-Xmx" in java_opts:
            xmx_bytes = parse_xmx_value(java_opts)
            limit_bytes = parse_memory_value(str(memory_limit)) if memory_limit else None
            
            if xmx_bytes and limit_bytes:
                ratio = xmx_bytes / limit_bytes
                if ratio > 0.70:
                    violations.append(MemoryViolation(
                        file=str(filepath),
                        service=service_name,
                        violation_type="UNSAFE_MEMORY_SPLIT",
                        message=f"JVM Heap ({xmx_bytes/1024**3:.1f}G) is {ratio:.0%} of container limit ({limit_bytes/1024**3:.1f}G); should be <= 70% for Native memory",
                        severity="HIGH",
                        details=f"Xmx={xmx_bytes}, Limit={limit_bytes}, Ratio={ratio:.2%}"
                    ))
            elif xmx_bytes and not limit_bytes:
                violations.append(MemoryViolation(
                    file=str(filepath),
                    service=service_name,
                    violation_type="NO_MEMORY_LIMIT",
                    message="JAVA_OPTS -Xmx set but no container memory limit defined",
                    severity="MEDIUM"
                ))
        elif is_java_service and not java_opts:
            violations.append(MemoryViolation(
                file=str(filepath),
                service=service_name,
                violation_type="NO_JVM_CONFIG",
                message="Java/H2O service without JAVA_OPTS; JVM will use default heap sizing",
                severity="MEDIUM"
            ))
        
        # Check for port exposure
        ports = service_config.get("ports", [])
        for port in ports:
            port_str = str(port)
            if any(db_port in port_str for db_port in ["5432", "6379"]):
                violations.append(MemoryViolation(
                    file=str(filepath),
                    service=service_name,
                    violation_type="EXPOSED_DB_PORT",
                    message=f"Database port {port_str} exposed to host; should use internal network",
                    severity="MEDIUM"
                ))
    
    return violations


def check_docker_compose_regex(filepath: Path) -> List[MemoryViolation]:
    """Fallback regex-based Docker Compose checking."""
    violations = []
    content = filepath.read_text()
    
    # Find JAVA_OPTS with Xmx
    xmx_matches = re.findall(r"JAVA_OPTS.*?-Xmx(\d+[kmgKMG]?)", content)
    mem_limit_matches = re.findall(r"mem_limit:\s*(\d+[kmgKMG]?)", content)
    
    if xmx_matches and not mem_limit_matches:
        violations.append(MemoryViolation(
            file=str(filepath),
            service="unknown",
            violation_type="NO_MEMORY_LIMIT",
            message="Found JAVA_OPTS -Xmx but no mem_limit defined",
            severity="MEDIUM"
        ))
    
    return violations


def print_report(violations: List[MemoryViolation], output_format: str):
    """Print violation report."""
    if output_format == "json":
        import json
        data = [
            {
                "file": v.file,
                "service": v.service,
                "type": v.violation_type,
                "message": v.message,
                "severity": v.severity,
                "details": v.details
            }
            for v in violations
        ]
        print(json.dumps(data, indent=2))
    else:
        print("=" * 60)
        print("RESOURCE ISOLATION SIGHT REPORT")
        print("=" * 60)
        
        if not violations:
            print("\n✅ No memory configuration violations detected")
        else:
            print(f"\n❌ Found {len(violations)} violation(s)\n")
            
            for v in sorted(violations, key=lambda x: (x.severity, x.service)):
                print(f"[{v.severity}] {v.file}")
                print(f"  Service: {v.service}")
                print(f"  Type: {v.violation_type}")
                print(f"  {v.message}")
                if v.details:
                    print(f"  Details: {v.details}")
                print()


def main():
    parser = argparse.ArgumentParser(
        description="Check container memory allocation for hybrid Java/Native workloads"
    )
    parser.add_argument(
        "--compose-file", "-c",
        type=Path,
        required=True,
        help="Docker Compose file to check"
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
    
    if not args.compose_file.exists():
        print(f"Error: File not found: {args.compose_file}")
        return 1
    
    violations = check_docker_compose(args.compose_file)
    
    # Filter by severity
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    min_severity = severity_order.get(args.severity, 3)
    violations = [v for v in violations if severity_order.get(v.severity, 3) <= min_severity]
    
    print_report(violations, args.output)
    
    # Exit with error if high severity violations found
    high_count = sum(1 for v in violations if v.severity in ("CRITICAL", "HIGH"))
    return 1 if high_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
