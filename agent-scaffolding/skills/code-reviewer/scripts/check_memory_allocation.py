#!/usr/bin/env python3
"""
Check container memory allocation configuration.

Implements the "Resource Isolation Sight" superpower.
Validates JVM Heap vs Container memory limits in Docker/K8s configurations.

Usage:
    python check_memory_allocation.py --compose-file ./docker-compose.yml
    python check_memory_allocation.py --k8s-dir ./k8s --output json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None


@dataclass
class MemoryViolation:
    """A detected memory configuration issue."""
    
    file: str
    service: str
    violation_type: str
    severity: str
    task_id: str
    message: str
    recommendation: str
    details: Optional[dict] = None


class DockerComposeValidator:
    """Validate memory configuration in Docker Compose files."""
    
    def __init__(self, filepath: str, content: dict):
        self.filepath = filepath
        self.content = content
        self.violations: list[MemoryViolation] = []
    
    def validate(self) -> list[MemoryViolation]:
        """Validate all services."""
        services = self.content.get('services', {})
        
        for service_name, service_config in services.items():
            self._validate_service(service_name, service_config)
        
        return self.violations
    
    def _validate_service(self, name: str, config: dict) -> None:
        """Validate a single service configuration."""
        # Get memory limit
        memory_limit = self._get_memory_limit(config)
        
        # Get JAVA_OPTS
        java_opts = self._get_java_opts(config)
        
        # Check for JVM services without memory configuration
        if self._is_jvm_service(config, name):
            if not memory_limit:
                self.violations.append(MemoryViolation(
                    file=self.filepath,
                    service=name,
                    violation_type="NO_MEMORY_LIMIT",
                    severity="HIGH",
                    task_id="PHY-REV-01-01",
                    message=f"JVM service '{name}' has no memory limit defined",
                    recommendation="Add deploy.resources.limits.memory",
                ))
            
            if java_opts:
                self._validate_heap_ratio(name, java_opts, memory_limit)
            elif memory_limit:
                self.violations.append(MemoryViolation(
                    file=self.filepath,
                    service=name,
                    violation_type="NO_XMX_DEFINED",
                    severity="MEDIUM",
                    task_id="PHY-REV-01-01",
                    message=f"JVM service '{name}' has memory limit but no -Xmx",
                    recommendation="Add JAVA_OPTS with -Xmx set to 70% of memory limit",
                ))
        
        # Check network configuration
        self._validate_network(name, config)
        
        # Check volume persistence
        self._validate_volumes(name, config)
    
    def _get_memory_limit(self, config: dict) -> Optional[int]:
        """Extract memory limit in MB."""
        # Docker Compose v3.x format
        deploy = config.get('deploy', {})
        resources = deploy.get('resources', {})
        limits = resources.get('limits', {})
        memory = limits.get('memory')
        
        # Also check legacy mem_limit
        if not memory:
            memory = config.get('mem_limit')
        
        if memory:
            return self._parse_memory_string(str(memory))
        return None
    
    def _get_java_opts(self, config: dict) -> Optional[str]:
        """Extract JAVA_OPTS from environment."""
        env = config.get('environment', [])
        
        if isinstance(env, list):
            for item in env:
                if isinstance(item, str) and item.startswith('JAVA_OPTS='):
                    return item.split('=', 1)[1]
        elif isinstance(env, dict):
            return env.get('JAVA_OPTS')
        
        return None
    
    def _is_jvm_service(self, config: dict, name: str) -> bool:
        """Check if service is likely a JVM service."""
        image = config.get('image', '')
        env = str(config.get('environment', []))
        
        jvm_indicators = ['h2o', 'java', 'jvm', 'spark', 'kafka', 'zookeeper', 'elasticsearch']
        
        for indicator in jvm_indicators:
            if indicator in image.lower() or indicator in name.lower():
                return True
            if 'JAVA_OPTS' in env or 'JAVA_HOME' in env:
                return True
        
        return False
    
    def _validate_heap_ratio(
        self,
        name: str,
        java_opts: str,
        memory_limit: Optional[int]
    ) -> None:
        """Validate JVM heap to container memory ratio."""
        heap_size = self._parse_xmx(java_opts)
        
        if not heap_size:
            return
        
        if not memory_limit:
            self.violations.append(MemoryViolation(
                file=self.filepath,
                service=name,
                violation_type="NO_MEMORY_LIMIT",
                severity="HIGH",
                task_id="PHY-REV-01-01",
                message=f"JVM service '{name}' has -Xmx but no container memory limit",
                recommendation="Add deploy.resources.limits.memory",
            ))
            return
        
        ratio = heap_size / memory_limit
        
        if ratio >= 0.9:
            self.violations.append(MemoryViolation(
                file=self.filepath,
                service=name,
                violation_type="HEAP_EQUALS_LIMIT",
                severity="CRITICAL",
                task_id="PHY-REV-01-01",
                message=f"JVM heap ({heap_size}MB) is {ratio:.0%} of container limit ({memory_limit}MB)",
                recommendation="Reduce -Xmx to 70% of container limit to leave room for native memory",
                details={"heap_mb": heap_size, "limit_mb": memory_limit, "ratio": ratio},
            ))
        elif ratio > 0.8:
            self.violations.append(MemoryViolation(
                file=self.filepath,
                service=name,
                violation_type="HEAP_TOO_LARGE",
                severity="HIGH",
                task_id="PHY-REV-01-01",
                message=f"JVM heap ({heap_size}MB) is {ratio:.0%} of container limit ({memory_limit}MB)",
                recommendation="Reduce -Xmx to 70% of container limit for safer margin",
                details={"heap_mb": heap_size, "limit_mb": memory_limit, "ratio": ratio},
            ))
        elif ratio > 0.7:
            self.violations.append(MemoryViolation(
                file=self.filepath,
                service=name,
                violation_type="HEAP_BORDERLINE",
                severity="MEDIUM",
                task_id="PHY-REV-01-01",
                message=f"JVM heap ({heap_size}MB) is {ratio:.0%} of container limit ({memory_limit}MB)",
                recommendation="Consider reducing to 70% for additional safety margin",
                details={"heap_mb": heap_size, "limit_mb": memory_limit, "ratio": ratio},
            ))
    
    def _validate_network(self, name: str, config: dict) -> None:
        """Validate network configuration for security."""
        ports = config.get('ports', [])
        
        # Check for exposed database/cache ports
        sensitive_ports = {
            '5432': 'PostgreSQL',
            '3306': 'MySQL',
            '6379': 'Redis',
            '27017': 'MongoDB',
        }
        
        for port_mapping in ports:
            port_str = str(port_mapping)
            for port, service in sensitive_ports.items():
                if port in port_str:
                    # Check if it's exposed to host (not just internal)
                    if ':' in port_str and not port_str.startswith('127.0.0.1'):
                        self.violations.append(MemoryViolation(
                            file=self.filepath,
                            service=name,
                            violation_type="SENSITIVE_PORT_EXPOSED",
                            severity="HIGH",
                            task_id="PHY-REV-01-02",
                            message=f"{service} port {port} is exposed to host network",
                            recommendation=f"Remove port mapping for {port}; use internal Docker network",
                        ))
    
    def _validate_volumes(self, name: str, config: dict) -> None:
        """Validate volume configuration for persistence."""
        volumes = config.get('volumes', [])
        
        # Services that should have persistent volumes
        stateful_services = ['postgres', 'mysql', 'redis', 'mage', 'db', 'database']
        
        is_stateful = any(s in name.lower() for s in stateful_services)
        
        if is_stateful and not volumes:
            self.violations.append(MemoryViolation(
                file=self.filepath,
                service=name,
                violation_type="NO_VOLUME_PERSISTENCE",
                severity="HIGH",
                task_id="PHY-REV-01-03",
                message=f"Stateful service '{name}' has no volumes configured",
                recommendation="Add named volume for data persistence",
            ))
        
        # Check for bind mounts vs named volumes
        for vol in volumes:
            vol_str = str(vol)
            if vol_str.startswith('./') or vol_str.startswith('/'):
                if ':' in vol_str:
                    self.violations.append(MemoryViolation(
                        file=self.filepath,
                        service=name,
                        violation_type="BIND_MOUNT_USED",
                        severity="LOW",
                        task_id="PHY-REV-01-03",
                        message=f"Using bind mount '{vol_str}' instead of named volume",
                        recommendation="Consider using named volumes for better portability",
                    ))
    
    def _parse_memory_string(self, memory: str) -> int:
        """Parse memory string to MB."""
        match = re.match(r'(\d+(?:\.\d+)?)\s*([gGmMkK])?[bB]?', memory)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or 'm').lower()
            if unit == 'g':
                return int(value * 1024)
            elif unit == 'k':
                return int(value / 1024)
            return int(value)
        return 0
    
    def _parse_xmx(self, java_opts: str) -> Optional[int]:
        """Extract -Xmx value in MB."""
        match = re.search(r'-Xmx(\d+(?:\.\d+)?)\s*([gGmMkK])?', java_opts)
        if match:
            value = float(match.group(1))
            unit = (match.group(2) or 'm').lower()
            if unit == 'g':
                return int(value * 1024)
            elif unit == 'k':
                return int(value / 1024)
            return int(value)
        return None


class MemoryAllocationChecker:
    """Check memory allocation in Docker/K8s configurations."""
    
    def __init__(self):
        self.violations: list[MemoryViolation] = []
        self.files_scanned = 0
    
    def scan_compose_file(self, path: Path) -> list[MemoryViolation]:
        """Scan a Docker Compose file."""
        if yaml is None:
            self.violations.append(MemoryViolation(
                file=str(path),
                service="N/A",
                violation_type="MISSING_YAML_LIBRARY",
                severity="LOW",
                task_id="PHY-REV-01-01",
                message="PyYAML not installed; cannot parse YAML files",
                recommendation="pip install pyyaml",
            ))
            return self.violations
        
        try:
            with open(path, 'r') as f:
                content = yaml.safe_load(f)
        except Exception as e:
            self.violations.append(MemoryViolation(
                file=str(path),
                service="N/A",
                violation_type="PARSE_ERROR",
                severity="LOW",
                task_id="PHY-REV-01-01",
                message=f"Could not parse file: {e}",
                recommendation="Fix YAML syntax errors",
            ))
            return self.violations
        
        self.files_scanned += 1
        
        validator = DockerComposeValidator(str(path), content)
        self.violations.extend(validator.validate())
        
        return self.violations
    
    def scan_directory(self, source_dir: Path) -> list[MemoryViolation]:
        """Scan directory for Docker Compose and K8s files."""
        # Docker Compose files
        compose_patterns = [
            'docker-compose.yml',
            'docker-compose.yaml',
            'docker-compose.*.yml',
            'docker-compose.*.yaml',
            'compose.yml',
            'compose.yaml',
        ]
        
        for pattern in compose_patterns:
            for path in source_dir.rglob(pattern):
                self.scan_compose_file(path)
        
        return self.violations


def main():
    parser = argparse.ArgumentParser(
        description="Check container memory allocation (Resource Isolation Sight)"
    )
    parser.add_argument(
        "--compose-file", "-c",
        type=Path,
        help="Docker Compose file to analyze"
    )
    parser.add_argument(
        "--source-dir", "-s",
        type=Path,
        help="Source directory to scan for compose/k8s files"
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
    
    if not args.compose_file and not args.source_dir:
        print("Error: Must specify --compose-file or --source-dir")
        sys.exit(1)
    
    checker = MemoryAllocationChecker()
    
    if args.compose_file:
        if not args.compose_file.exists():
            print(f"Error: File {args.compose_file} does not exist")
            sys.exit(1)
        violations = checker.scan_compose_file(args.compose_file)
    else:
        if not args.source_dir.exists():
            print(f"Error: Directory {args.source_dir} does not exist")
            sys.exit(1)
        violations = checker.scan_directory(args.source_dir)
    
    # Filter by severity
    severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    min_index = severity_order.index(args.severity)
    violations = [v for v in violations if severity_order.index(v.severity) >= min_index]
    
    if args.output == "json":
        output = {
            "scanner": "check_memory_allocation",
            "superpower": "Resource Isolation Sight",
            "files_scanned": checker.files_scanned,
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"🔍 Resource Isolation Sight Scan")
        print(f"   Scanned {checker.files_scanned} configuration file(s)\n")
        
        if not violations:
            print("✅ No resource configuration issues detected")
        else:
            print(f"⚠️  Found {len(violations)} issue(s):\n")
            
            for v in sorted(violations, key=lambda x: severity_order.index(x.severity), reverse=True):
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}[v.severity]
                print(f"{icon} [{v.severity}] {v.violation_type}")
                print(f"   File: {v.file}")
                print(f"   Service: {v.service}")
                print(f"   Message: {v.message}")
                if v.details:
                    for k, val in v.details.items():
                        print(f"   {k}: {val}")
                print(f"   Fix: {v.recommendation}")
                print(f"   Task ID: {v.task_id}")
                print()
    
    # Exit with error if critical/high findings
    critical_high = [v for v in violations if v.severity in ("CRITICAL", "HIGH")]
    if critical_high:
        sys.exit(1)


if __name__ == "__main__":
    main()
