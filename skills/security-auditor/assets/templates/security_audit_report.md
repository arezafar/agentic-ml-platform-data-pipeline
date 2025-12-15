# Security Audit Report Template

## Executive Summary

| Field | Value |
|-------|-------|
| **Audit Date** | YYYY-MM-DD |
| **Auditor** | Security Auditor Agent |
| **Scope** | [Platform components audited] |
| **Overall Risk Level** | [Critical / High / Medium / Low] |
| **Pass Rate** | X/Y checks passed (Z%) |

---

## Findings Summary

| Severity | Count | Remediated |
|----------|-------|------------|
| 🔴 Critical | 0 | 0 |
| 🟠 High | 0 | 0 |
| 🟡 Medium | 0 | 0 |
| 🟢 Low | 0 | 0 |

---

## Critical Findings

### FINDING-001: [Title]

| Field | Value |
|-------|-------|
| **Severity** | 🔴 Critical |
| **Component** | [Affected component] |
| **View** | [Logical / Process / Development / Physical] |
| **Task ID** | [Related JTBD task] |

**Description**:
[Detailed description of the vulnerability]

**Evidence**:
```
[Code snippet, log output, or command output]
```

**Impact**:
- [Business impact]
- [Technical impact]

**Remediation**:
1. [Step 1]
2. [Step 2]

**Verification**:
```bash
# Command to verify fix
```

---

## High Findings

### FINDING-002: [Title]

[Same structure as Critical]

---

## View-by-View Audit Results

### Logical View

| Check | Status | Notes |
|-------|--------|-------|
| Schema Security | ✅/❌ | |
| Auth Model | ✅/❌ | |
| Data Flow | ✅/❌ | |

### Process View

| Check | Status | Notes |
|-------|--------|-------|
| Async Safety | ✅/❌ | |
| Rate Limiting | ✅/❌ | |
| Session Management | ✅/❌ | |

### Development View

| Check | Status | Notes |
|-------|--------|-------|
| Supply Chain | ✅/❌ | |
| Dependencies | ✅/❌ | |
| Secure Coding | ✅/❌ | |

### Physical View

| Check | Status | Notes |
|-------|--------|-------|
| Network Isolation | ✅/❌ | |
| Least Privilege | ✅/❌ | |
| Encryption | ✅/❌ | |

### Scenarios View

| Check | Status | Notes |
|-------|--------|-------|
| Incident Response | ✅/❌ | |
| Breach Containment | ✅/❌ | |

---

## Recommendations

### Immediate Actions (0-7 days)
1. [Action item]

### Short-term (1-4 weeks)
1. [Action item]

### Long-term (1-3 months)
1. [Action item]

---

## Appendix

### Tools Used
- trivy (container scanning)
- bandit (Python SAST)
- check_secrets_exposure.py
- scan_api_security.py

### References
- OWASP Top 10
- CIS Docker Benchmark
- NIST Cybersecurity Framework
