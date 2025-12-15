#!/usr/bin/env python3
"""
Compliance Guardian - Policy-as-Code Enforcement

JTBD Domain 4: Observability & Governance (The Auditor)

Scans dataframes against Policy-as-Code rules before write operations.
Blocks and raises "Compliance Exception" on PII/policy violations.

Features:
- PII detection (SSN, credit cards, emails, etc.)
- Policy rule evaluation
- Compliance exceptions with audit trail
- Pre-write validation hooks

Usage:
    python compliance_guardian.py scan --data data.json --policies policies.json
    python compliance_guardian.py validate --schema schema.json --policies policies.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional


class PolicySeverity(Enum):
    """Severity levels for policy violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class PolicyAction(Enum):
    """Actions to take on policy violation."""
    ALLOW = "allow"       # Log and continue
    WARN = "warn"         # Warn and continue
    BLOCK = "block"       # Block operation
    REDACT = "redact"     # Redact sensitive data
    MASK = "mask"         # Mask partial data


@dataclass
class PolicyViolation:
    """Represents a policy violation."""
    policy_id: str
    policy_name: str
    column: Optional[str]
    row_index: Optional[int]
    value_sample: Optional[str]  # Masked sample
    severity: PolicySeverity
    action: PolicyAction
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            'policy_id': self.policy_id,
            'policy_name': self.policy_name,
            'column': self.column,
            'row_index': self.row_index,
            'value_sample': self.value_sample,
            'severity': self.severity.value,
            'action': self.action.value,
            'message': self.message,
            'timestamp': self.timestamp,
        }


@dataclass
class ComplianceResult:
    """Result of compliance check."""
    is_compliant: bool
    violations: list[PolicyViolation]
    total_records: int
    total_columns: int
    scan_duration_ms: float
    blocked: bool
    
    def to_dict(self) -> dict:
        return {
            'is_compliant': self.is_compliant,
            'blocked': self.blocked,
            'total_records': self.total_records,
            'total_columns': self.total_columns,
            'scan_duration_ms': round(self.scan_duration_ms, 2),
            'violation_count': len(self.violations),
            'violations': [v.to_dict() for v in self.violations],
        }


class PIIDetector:
    """Detects Personally Identifiable Information."""
    
    # Regex patterns for common PII
    PATTERNS = {
        'ssn': {
            'regex': r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b',
            'description': 'Social Security Number',
            'severity': PolicySeverity.CRITICAL,
        },
        'credit_card': {
            'regex': r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b',
            'description': 'Credit Card Number',
            'severity': PolicySeverity.CRITICAL,
        },
        'email': {
            'regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'description': 'Email Address',
            'severity': PolicySeverity.WARNING,
        },
        'phone': {
            'regex': r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'description': 'Phone Number',
            'severity': PolicySeverity.WARNING,
        },
        'ip_address': {
            'regex': r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            'description': 'IP Address',
            'severity': PolicySeverity.INFO,
        },
        'date_of_birth': {
            'regex': r'\b(?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12][0-9]|3[01])[-/](?:19|20)\d{2}\b',
            'description': 'Date of Birth',
            'severity': PolicySeverity.WARNING,
        },
    }
    
    # Sensitive column name patterns
    SENSITIVE_COLUMNS = {
        r'(?i)ssn': 'Social Security Number',
        r'(?i)social.*security': 'Social Security Number',
        r'(?i)password': 'Password',
        r'(?i)secret': 'Secret',
        r'(?i)api.*key': 'API Key',
        r'(?i)credit.*card': 'Credit Card',
        r'(?i)cvv': 'CVV',
        r'(?i)pin': 'PIN',
        r'(?i)birth.*date': 'Date of Birth',
        r'(?i)dob': 'Date of Birth',
    }
    
    def __init__(self, enabled_patterns: Optional[list[str]] = None):
        """Initialize PII detector.
        
        Args:
            enabled_patterns: Specific patterns to enable (None = all)
        """
        self.enabled_patterns = enabled_patterns or list(self.PATTERNS.keys())
        self.compiled_patterns = {}
        
        for name in self.enabled_patterns:
            if name in self.PATTERNS:
                self.compiled_patterns[name] = re.compile(
                    self.PATTERNS[name]['regex']
                )
        
        self.column_patterns = {
            re.compile(pattern): desc
            for pattern, desc in self.SENSITIVE_COLUMNS.items()
        }
    
    def scan_value(self, value: Any) -> list[tuple[str, str]]:
        """Scan a value for PII.
        
        Returns:
            List of (pattern_name, match) tuples
        """
        if not isinstance(value, str):
            value = str(value)
        
        findings = []
        for name, pattern in self.compiled_patterns.items():
            matches = pattern.findall(value)
            for match in matches:
                findings.append((name, self._mask_value(match)))
        
        return findings
    
    def scan_column_name(self, column: str) -> Optional[str]:
        """Check if column name suggests sensitive data.
        
        Returns:
            Description if sensitive, None otherwise
        """
        for pattern, description in self.column_patterns.items():
            if pattern.search(column):
                return description
        return None
    
    def _mask_value(self, value: str) -> str:
        """Mask a value for logging."""
        if len(value) <= 4:
            return '*' * len(value)
        return value[:2] + '*' * (len(value) - 4) + value[-2:]


class PolicyEngine:
    """Evaluates compliance policies."""
    
    def __init__(self, policies: list[dict]):
        """Initialize policy engine.
        
        Args:
            policies: List of policy definitions
        """
        self.policies = policies
        self.pii_detector = PIIDetector()
    
    def load_policies(self, filepath: str) -> None:
        """Load policies from JSON file."""
        with open(filepath) as f:
            self.policies = json.load(f)
    
    def evaluate(self, 
                 data: list[dict],
                 target_schema: Optional[str] = None) -> ComplianceResult:
        """Evaluate data against all policies.
        
        Args:
            data: Data records to evaluate
            target_schema: Target schema for write operation
            
        Returns:
            ComplianceResult with all violations
        """
        import time
        start = time.perf_counter()
        
        violations = []
        
        if not data:
            return ComplianceResult(
                is_compliant=True,
                violations=[],
                total_records=0,
                total_columns=0,
                scan_duration_ms=0,
                blocked=False,
            )
        
        columns = set(data[0].keys())
        
        # Check column names for sensitive patterns
        for col in columns:
            sensitive = self.pii_detector.scan_column_name(col)
            if sensitive:
                violations.append(PolicyViolation(
                    policy_id='PII-COL-001',
                    policy_name='Sensitive Column Name',
                    column=col,
                    row_index=None,
                    value_sample=None,
                    severity=PolicySeverity.WARNING,
                    action=PolicyAction.WARN,
                    message=f"Column '{col}' suggests {sensitive} data",
                ))
        
        # Check data values for PII
        for i, record in enumerate(data):
            for col, value in record.items():
                if value is None:
                    continue
                
                findings = self.pii_detector.scan_value(value)
                for pattern_name, masked in findings:
                    pattern_info = PIIDetector.PATTERNS[pattern_name]
                    violations.append(PolicyViolation(
                        policy_id=f'PII-VAL-{pattern_name.upper()}',
                        policy_name=f'PII Detection: {pattern_info["description"]}',
                        column=col,
                        row_index=i,
                        value_sample=masked,
                        severity=pattern_info['severity'],
                        action=PolicyAction.BLOCK if pattern_info['severity'] == PolicySeverity.CRITICAL else PolicyAction.WARN,
                        message=f"Detected {pattern_info['description']} in column '{col}'",
                    ))
        
        # Evaluate custom policies
        for policy in self.policies:
            policy_violations = self._evaluate_policy(policy, data, target_schema)
            violations.extend(policy_violations)
        
        duration = (time.perf_counter() - start) * 1000
        
        # Determine if blocked
        blocked = any(v.action == PolicyAction.BLOCK for v in violations)
        is_compliant = len(violations) == 0
        
        return ComplianceResult(
            is_compliant=is_compliant,
            violations=violations,
            total_records=len(data),
            total_columns=len(columns),
            scan_duration_ms=duration,
            blocked=blocked,
        )
    
    def _evaluate_policy(self,
                         policy: dict,
                         data: list[dict],
                         target_schema: Optional[str]) -> list[PolicyViolation]:
        """Evaluate a single policy."""
        violations = []
        
        policy_id = policy.get('id', 'UNKNOWN')
        policy_name = policy.get('name', 'Unnamed Policy')
        severity = PolicySeverity(policy.get('severity', 'warning'))
        action = PolicyAction(policy.get('action', 'warn'))
        
        # Schema-based rules
        if 'allowed_schemas' in policy:
            if target_schema and target_schema not in policy['allowed_schemas']:
                violations.append(PolicyViolation(
                    policy_id=policy_id,
                    policy_name=policy_name,
                    column=None,
                    row_index=None,
                    value_sample=None,
                    severity=severity,
                    action=action,
                    message=f"Write to schema '{target_schema}' not allowed. Permitted: {policy['allowed_schemas']}",
                ))
        
        # Column-based rules
        if 'forbidden_columns' in policy:
            if data:
                columns = set(data[0].keys())
                forbidden = set(policy['forbidden_columns']) & columns
                for col in forbidden:
                    violations.append(PolicyViolation(
                        policy_id=policy_id,
                        policy_name=policy_name,
                        column=col,
                        row_index=None,
                        value_sample=None,
                        severity=severity,
                        action=action,
                        message=f"Column '{col}' is forbidden by policy",
                    ))
        
        # Value range rules
        if 'value_rules' in policy:
            for rule in policy['value_rules']:
                col = rule.get('column')
                for i, record in enumerate(data):
                    if col not in record:
                        continue
                    value = record[col]
                    
                    # Min/max checks
                    if 'min' in rule and value is not None and value < rule['min']:
                        violations.append(PolicyViolation(
                            policy_id=policy_id,
                            policy_name=policy_name,
                            column=col,
                            row_index=i,
                            value_sample=str(value),
                            severity=severity,
                            action=action,
                            message=f"Value {value} below minimum {rule['min']}",
                        ))
                    
                    if 'max' in rule and value is not None and value > rule['max']:
                        violations.append(PolicyViolation(
                            policy_id=policy_id,
                            policy_name=policy_name,
                            column=col,
                            row_index=i,
                            value_sample=str(value),
                            severity=severity,
                            action=action,
                            message=f"Value {value} above maximum {rule['max']}",
                        ))
        
        return violations


class ComplianceException(Exception):
    """Raised when compliance check fails and blocks operation."""
    
    def __init__(self, result: ComplianceResult):
        self.result = result
        violations = result.violations
        super().__init__(
            f"Compliance check failed with {len(violations)} violation(s). "
            f"Operation blocked."
        )


def main():
    parser = argparse.ArgumentParser(description='Compliance Guardian - Policy Enforcement')
    subparsers = parser.add_subparsers(dest='command')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan data for compliance')
    scan_parser.add_argument('--data', required=True, help='Data file (JSON)')
    scan_parser.add_argument('--policies', help='Policy definitions (JSON)')
    scan_parser.add_argument('--target-schema', help='Target schema for write')
    scan_parser.add_argument('--json', action='store_true')
    scan_parser.add_argument('--strict', action='store_true', help='Block on any violation')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate schema against policies')
    validate_parser.add_argument('--schema', required=True, help='Schema file (JSON)')
    validate_parser.add_argument('--policies', help='Policy definitions (JSON)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load policies
    policies = []
    if hasattr(args, 'policies') and args.policies:
        with open(args.policies) as f:
            policies = json.load(f)
    
    engine = PolicyEngine(policies)
    
    if args.command == 'scan':
        with open(args.data) as f:
            data = json.load(f)
        
        if not isinstance(data, list):
            data = [data]
        
        result = engine.evaluate(
            data=data,
            target_schema=args.target_schema,
        )
        
        if args.strict and result.violations:
            result.blocked = True
        
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print("=" * 60)
            print("COMPLIANCE GUARDIAN REPORT")
            print("=" * 60)
            print(f"Records Scanned: {result.total_records}")
            print(f"Columns Scanned: {result.total_columns}")
            print(f"Duration: {result.scan_duration_ms:.2f}ms")
            print(f"Violations: {len(result.violations)}")
            print()
            
            if result.violations:
                by_severity = {}
                for v in result.violations:
                    by_severity.setdefault(v.severity.value, []).append(v)
                
                for sev in ['critical', 'error', 'warning', 'info']:
                    if sev in by_severity:
                        icon = {'critical': '🔴', 'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}[sev]
                        print(f"{sev.upper()}:")
                        for v in by_severity[sev]:
                            loc = f"[{v.column}]" if v.column else ""
                            row = f"row {v.row_index}" if v.row_index is not None else ""
                            print(f"  {icon} {v.policy_name} {loc} {row}")
                            print(f"     {v.message}")
                        print()
            
            if result.blocked:
                print("🛑 OPERATION BLOCKED - Compliance Exception")
            elif result.is_compliant:
                print("✅ COMPLIANT - Safe to proceed")
            else:
                print("⚠️  WARNINGS PRESENT - Review recommended")
            
            print("=" * 60)
        
        if result.blocked:
            sys.exit(1)
    
    sys.exit(0)


if __name__ == '__main__':
    main()
