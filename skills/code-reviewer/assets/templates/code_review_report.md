# Code Review Report Template

## Review Summary

| Field | Value |
|-------|-------|
| **PR Number** | #[PR_NUMBER] |
| **Author** | [AUTHOR] |
| **Branch** | [BRANCH] |
| **Date** | [DATE] |
| **Reviewer** | Code Reviewer Agent |

---

## Plan Alignment Status

| View | Status | Findings |
|------|--------|----------|
| Logical | ⬜ | 0 |
| Process | ⬜ | 0 |
| Development | ⬜ | 0 |
| Physical | ⬜ | 0 |
| Scenario | ⬜ | 0 |

**Legend:** ✅ Aligned | ⚠️ Warnings | ❌ Violations | ⬜ Not Applicable

---

## Findings by Severity

### 🔴 CRITICAL
_Findings that block PR merge._

| Task ID | View | Finding | File:Line |
|---------|------|---------|-----------|
| [TASK_ID] | [VIEW] | [DESCRIPTION] | `file.py:123` |

### 🟠 HIGH  
_Findings that should be addressed before merge._

| Task ID | View | Finding | File:Line |
|---------|------|---------|-----------|
| [TASK_ID] | [VIEW] | [DESCRIPTION] | `file.py:123` |

### 🟡 MEDIUM
_Findings that should be addressed in follow-up._

| Task ID | View | Finding | File:Line |
|---------|------|---------|-----------|
| [TASK_ID] | [VIEW] | [DESCRIPTION] | `file.py:123` |

### 🟢 LOW
_Suggestions for improvement._

| Task ID | View | Finding | File:Line |
|---------|------|---------|-----------|
| [TASK_ID] | [VIEW] | [DESCRIPTION] | `file.py:123` |

---

## Detailed Analysis

### Logical View (REV-LOG-01)

**Files Analyzed:**
- `[file1.py]`
- `[file2.py]`

**Checks Performed:**
- [ ] JSONB Indexing Verification (LOG-REV-01-01)
- [ ] Feature Time-Travel Compliance (LOG-REV-01-02)
- [ ] Mage Block Atomicity Check (LOG-REV-01-03)

**Notes:**
[Additional context or observations]

---

### Process View (REV-PROC-01)

**Files Analyzed:**
- `[file1.py]`
- `[file2.py]`

**Checks Performed:**
- [ ] Blocking Call Isolation (PROC-REV-01-01)
- [ ] DB Connection Pooling Gate (PROC-REV-01-02)
- [ ] Redis Caching Pattern Review (PROC-REV-01-03)

**Notes:**
[Additional context or observations]

---

### Development View (REV-DEV-01)

**Files Analyzed:**
- `[file1.py]`
- `[file2.py]`

**Checks Performed:**
- [ ] MOJO Mandate Enforcement (DEV-REV-01-01)
- [ ] H2O Version Pinning (DEV-REV-01-02)
- [ ] Monorepo Structure Check (DEV-REV-01-03)

**Notes:**
[Additional context or observations]

---

### Physical View (REV-PHY-01)

**Files Analyzed:**
- `[docker-compose.yml]`
- `[k8s/deployment.yaml]`

**Checks Performed:**
- [ ] Memory Split Verification (PHY-REV-01-01)
- [ ] Network Security Review (PHY-REV-01-02)
- [ ] Volume Persistence Check (PHY-REV-01-03)

**Notes:**
[Additional context or observations]

---

### Scenario View (REV-SCN-01)

**Files Analyzed:**
- `[tests/integration/]`

**Checks Performed:**
- [ ] Drift Detection Test Verification (SCN-REV-01-01)
- [ ] Zero-Downtime Swap Verification (SCN-REV-01-02)

**Notes:**
[Additional context or observations]

---

## Automated Scan Results

### detect_blocking_calls.py
```
[PASTE SCRIPT OUTPUT]
```

### validate_schema_migration.py
```
[PASTE SCRIPT OUTPUT]
```

### verify_mojo_artifact.py
```
[PASTE SCRIPT OUTPUT]
```

### check_memory_allocation.py
```
[PASTE SCRIPT OUTPUT]
```

---

## Decision

| Decision | Justification |
|----------|---------------|
| ⬜ **APPROVE** | No blocking findings |
| ⬜ **REQUEST CHANGES** | [N] HIGH/CRITICAL findings require resolution |
| ⬜ **BLOCK** | Architectural violations detected |

---

## Remediation Guidance

For each CRITICAL/HIGH finding, provide:

1. **Task ID**: [TASK_ID]
2. **Finding**: [Brief description]
3. **Current Code**: 
   ```python
   [Current problematic code]
   ```
4. **Recommended Fix**:
   ```python
   [Corrected code]
   ```
5. **Reference**: See `references/[relevant_doc].md`
