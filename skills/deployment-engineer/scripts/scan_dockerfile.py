#!/usr/bin/env python3
"""
Dockerfile Security Scanner

Validates Dockerfile best practices and security including:
- No USER root in final stage
- No 'latest' image tags
- No sensitive port exposure
- Multi-stage build patterns
- Proper COPY vs ADD usage
- No secrets in build args

Usage:
    python scan_dockerfile.py <Dockerfile>
    python scan_dockerfile.py <directory> --recursive
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


class DockerfileScanError(Exception):
    """Custom exception for Dockerfile scanning errors."""
    pass


class DockerfileScanner:
    """Security and best practice scanner for Dockerfiles."""
    
    # Sensitive ports that should be reviewed
    SENSITIVE_PORTS = {
        22: 'SSH',
        23: 'Telnet',
        3389: 'RDP',
        5432: 'PostgreSQL',
        3306: 'MySQL',
        27017: 'MongoDB',
        6379: 'Redis',
    }
    
    # Allowed internal ports (typically fine to expose)
    ALLOWED_PORTS = {80, 443, 8000, 8080, 8443, 9000}
    
    # Instructions that should use specific forms
    SHELL_FORM_INSTRUCTIONS = {'RUN', 'CMD', 'ENTRYPOINT'}
    
    def __init__(self, dockerfile_path: Path):
        self.dockerfile_path = dockerfile_path
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.info: list[dict[str, Any]] = []
        self.lines: list[str] = []
        self.stages: list[dict[str, Any]] = []
        
    def scan(self) -> bool:
        """Run all security checks. Returns True if no errors."""
        try:
            self._load_dockerfile()
            self._parse_stages()
            
            self._check_base_images()
            self._check_user_directive()
            self._check_exposed_ports()
            self._check_copy_vs_add()
            self._check_secrets_in_args()
            self._check_multi_stage()
            self._check_healthcheck()
            self._check_shell_form()
            self._check_apt_get_patterns()
            
            return len(self.errors) == 0
        except Exception as e:
            self.errors.append({
                'line': 0,
                'code': 'E000',
                'message': f"Failed to parse Dockerfile: {e}",
            })
            return False
    
    def _load_dockerfile(self) -> None:
        """Load and preprocess Dockerfile content."""
        with open(self.dockerfile_path, 'r') as f:
            content = f.read()
        
        # Handle line continuations
        content = re.sub(r'\\\n\s*', ' ', content)
        self.lines = content.split('\n')
    
    def _parse_stages(self) -> None:
        """Parse multi-stage build stages."""
        current_stage = {'name': None, 'base': None, 'start_line': 1, 'instructions': []}
        
        for i, line in enumerate(self.lines, 1):
            line = line.strip()
            
            if not line or line.startswith('#'):
                continue
            
            # Parse FROM instruction
            from_match = re.match(
                r'^FROM\s+([^\s]+)(?:\s+[Aa][Ss]\s+(\S+))?',
                line,
                re.IGNORECASE
            )
            
            if from_match:
                if current_stage['base']:
                    self.stages.append(current_stage)
                
                base_image = from_match.group(1)
                stage_name = from_match.group(2)
                
                current_stage = {
                    'name': stage_name,
                    'base': base_image,
                    'start_line': i,
                    'instructions': [],
                }
            else:
                # Parse instruction
                inst_match = re.match(r'^(\w+)\s+(.*)', line)
                if inst_match:
                    current_stage['instructions'].append({
                        'instruction': inst_match.group(1).upper(),
                        'arguments': inst_match.group(2),
                        'line': i,
                    })
        
        if current_stage['base']:
            self.stages.append(current_stage)
    
    def _check_base_images(self) -> None:
        """Check for 'latest' tags and unversioned images."""
        for stage in self.stages:
            base = stage['base']
            line = stage['start_line']
            
            # Check for 'latest' tag
            if base.endswith(':latest') or ':latest@' in base:
                self.errors.append({
                    'line': line,
                    'code': 'E001',
                    'message': f"Avoid 'latest' tag: {base}. Use specific version for reproducibility.",
                })
            
            # Check for untagged images (implied :latest)
            elif ':' not in base and '@' not in base:
                self.warnings.append({
                    'line': line,
                    'code': 'W001',
                    'message': f"Image '{base}' has no tag. This implies ':latest'. Pin to a specific version.",
                })
            
            # Recommend slim/alpine variants
            if 'python:' in base and 'slim' not in base and 'alpine' not in base:
                self.info.append({
                    'line': line,
                    'code': 'I001',
                    'message': f"Consider using 'python:X.X-slim' instead of '{base}' for smaller images.",
                })
    
    def _check_user_directive(self) -> None:
        """Check that final stage doesn't run as root."""
        if not self.stages:
            return
        
        final_stage = self.stages[-1]
        has_user_switch = False
        last_user = 'root'
        last_user_line = 0
        
        for inst in final_stage['instructions']:
            if inst['instruction'] == 'USER':
                has_user_switch = True
                last_user = inst['arguments'].strip().split(':')[0]
                last_user_line = inst['line']
        
        if not has_user_switch:
            self.errors.append({
                'line': final_stage['start_line'],
                'code': 'E002',
                'message': "Final stage runs as root. Add 'USER nonroot' or similar for security.",
            })
        elif last_user.lower() in ('root', '0'):
            self.errors.append({
                'line': last_user_line,
                'code': 'E003',
                'message': "Final stage explicitly sets USER to root. Use a non-root user.",
            })
    
    def _check_exposed_ports(self) -> None:
        """Check for potentially sensitive port exposure."""
        for stage in self.stages:
            for inst in stage['instructions']:
                if inst['instruction'] == 'EXPOSE':
                    ports = re.findall(r'(\d+)', inst['arguments'])
                    
                    for port_str in ports:
                        port = int(port_str)
                        
                        if port in self.SENSITIVE_PORTS:
                            service = self.SENSITIVE_PORTS[port]
                            self.warnings.append({
                                'line': inst['line'],
                                'code': 'W002',
                                'message': f"Exposing sensitive port {port} ({service}). "
                                          "Ensure this is intentional and secured.",
                            })
    
    def _check_copy_vs_add(self) -> None:
        """Check for proper COPY vs ADD usage."""
        for stage in self.stages:
            for inst in stage['instructions']:
                if inst['instruction'] == 'ADD':
                    args = inst['arguments']
                    
                    # ADD is okay for URLs or tar extraction
                    if 'http://' in args or 'https://' in args:
                        continue
                    if '.tar' in args or '.gz' in args or '.bz2' in args:
                        continue
                    
                    self.warnings.append({
                        'line': inst['line'],
                        'code': 'W003',
                        'message': "Prefer COPY over ADD for local files. "
                                  "ADD has implicit tar extraction which may be unexpected.",
                    })
    
    def _check_secrets_in_args(self) -> None:
        """Check for potential secrets in build args or env vars."""
        secret_patterns = [
            (r'password', 'password'),
            (r'secret', 'secret'),
            (r'api[_-]?key', 'API key'),
            (r'token', 'token'),
            (r'private[_-]?key', 'private key'),
            (r'credential', 'credential'),
        ]
        
        for stage in self.stages:
            for inst in stage['instructions']:
                if inst['instruction'] in ('ARG', 'ENV'):
                    args = inst['arguments'].lower()
                    
                    for pattern, name in secret_patterns:
                        if re.search(pattern, args, re.IGNORECASE):
                            # Check if it's just a variable name without value
                            if '=' in inst['arguments']:
                                self.errors.append({
                                    'line': inst['line'],
                                    'code': 'E004',
                                    'message': f"Potential {name} in {inst['instruction']}. "
                                              "Use build secrets or runtime environment instead.",
                                })
                            else:
                                self.warnings.append({
                                    'line': inst['line'],
                                    'code': 'W004',
                                    'message': f"Variable name suggests {name}. "
                                              "Ensure value is not hardcoded.",
                                })
    
    def _check_multi_stage(self) -> None:
        """Check for multi-stage build usage in production configs."""
        if len(self.stages) < 2:
            self.info.append({
                'line': 1,
                'code': 'I002',
                'message': "Consider multi-stage builds to reduce final image size. "
                          "Separate build dependencies from runtime.",
            })
    
    def _check_healthcheck(self) -> None:
        """Check for HEALTHCHECK instruction."""
        has_healthcheck = False
        
        for stage in self.stages:
            for inst in stage['instructions']:
                if inst['instruction'] == 'HEALTHCHECK':
                    has_healthcheck = True
                    break
        
        if not has_healthcheck:
            self.info.append({
                'line': 1,
                'code': 'I003',
                'message': "No HEALTHCHECK instruction found. "
                          "Consider adding one for container orchestration.",
            })
    
    def _check_shell_form(self) -> None:
        """Check for shell form vs exec form in CMD/ENTRYPOINT."""
        for stage in self.stages:
            for inst in stage['instructions']:
                if inst['instruction'] in ('CMD', 'ENTRYPOINT'):
                    args = inst['arguments'].strip()
                    
                    # Exec form starts with [
                    if not args.startswith('['):
                        self.warnings.append({
                            'line': inst['line'],
                            'code': 'W005',
                            'message': f"{inst['instruction']} uses shell form. "
                                      "Consider exec form (JSON array) for proper signal handling.",
                        })
    
    def _check_apt_get_patterns(self) -> None:
        """Check for apt-get best practices."""
        for stage in self.stages:
            for inst in stage['instructions']:
                if inst['instruction'] == 'RUN':
                    args = inst['arguments']
                    
                    if 'apt-get' in args:
                        # Check for update && install pattern
                        if 'apt-get install' in args and 'apt-get update' not in args:
                            self.warnings.append({
                                'line': inst['line'],
                                'code': 'W006',
                                'message': "apt-get install without update in same RUN. "
                                          "Combine: 'apt-get update && apt-get install'",
                            })
                        
                        # Check for cache cleanup
                        if 'apt-get install' in args and 'rm -rf /var/lib/apt/lists/*' not in args:
                            self.info.append({
                                'line': inst['line'],
                                'code': 'I004',
                                'message': "Consider cleaning apt cache: 'rm -rf /var/lib/apt/lists/*'",
                            })
                        
                        # Check for -y flag
                        if 'apt-get install' in args and '-y' not in args:
                            self.warnings.append({
                                'line': inst['line'],
                                'code': 'W007',
                                'message': "apt-get install without -y flag may hang during build.",
                            })
    
    def get_report(self) -> str:
        """Generate a security scan report."""
        lines = [
            "=" * 60,
            "DOCKERFILE SECURITY SCAN REPORT",
            "=" * 60,
            f"File: {self.dockerfile_path}",
            f"Stages: {len(self.stages)}",
        ]
        
        if self.stages:
            stage_info = ', '.join(
                s['name'] or f"stage_{i}" for i, s in enumerate(self.stages)
            )
            lines.append(f"Stage names: {stage_info}")
        
        lines.append("")
        
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  ❌ Line {err['line']}: [{err['code']}] {err['message']}")
            lines.append("")
            
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  ⚠️  Line {warn['line']}: [{warn['code']}] {warn['message']}")
            lines.append("")
            
        if self.info:
            lines.append(f"INFO ({len(self.info)}):")
            for info in self.info:
                lines.append(f"  ℹ️  Line {info['line']}: [{info['code']}] {info['message']}")
            lines.append("")
            
        if not self.errors and not self.warnings:
            lines.append("✅ Dockerfile passes security scan!")
        elif not self.errors:
            lines.append("✅ No critical issues (warnings only)")
        else:
            lines.append("❌ Security scan FAILED")
            
        lines.append("=" * 60)
        return '\n'.join(lines)


def scan_file(filepath: Path, strict: bool = False) -> tuple[bool, DockerfileScanner]:
    """Scan a single Dockerfile."""
    scanner = DockerfileScanner(filepath)
    is_valid = scanner.scan()
    
    if strict and scanner.warnings:
        is_valid = False
    
    return is_valid, scanner


def scan_directory(
    dirpath: Path,
    recursive: bool = True,
    strict: bool = False,
) -> tuple[bool, list[DockerfileScanner]]:
    """Scan all Dockerfiles in a directory."""
    patterns = ['Dockerfile', 'Dockerfile.*', '*.dockerfile']
    files = []
    
    for pattern in patterns:
        if recursive:
            files.extend(dirpath.rglob(pattern))
        else:
            files.extend(dirpath.glob(pattern))
    
    all_valid = True
    scanners = []
    
    for filepath in files:
        is_valid, scanner = scan_file(filepath, strict)
        if not is_valid:
            all_valid = False
        scanners.append(scanner)
    
    return all_valid, scanners


def main():
    parser = argparse.ArgumentParser(
        description='Scan Dockerfiles for security issues'
    )
    parser.add_argument(
        'path',
        type=str,
        help='Path to Dockerfile or directory'
    )
    parser.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Recursively scan directories'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output results as JSON'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )
    
    args = parser.parse_args()
    
    path = Path(args.path)
    
    if not path.exists():
        print(f"Error: Path not found: {path}", file=sys.stderr)
        sys.exit(1)
    
    if path.is_file():
        is_valid, scanner = scan_file(path, args.strict)
        scanners = [scanner]
    else:
        is_valid, scanners = scan_directory(path, args.recursive, args.strict)
    
    if args.json:
        results = []
        for scanner in scanners:
            results.append({
                'file': str(scanner.dockerfile_path),
                'stages': len(scanner.stages),
                'errors': scanner.errors,
                'warnings': scanner.warnings,
                'info': scanner.info,
            })
        output = {
            'valid': is_valid,
            'files_scanned': len(scanners),
            'total_errors': sum(len(s.errors) for s in scanners),
            'total_warnings': sum(len(s.warnings) for s in scanners),
            'results': results,
        }
        print(json.dumps(output, indent=2))
    else:
        for scanner in scanners:
            print(scanner.get_report())
            print()
    
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
