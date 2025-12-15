# Violation Report Template

Document individual architectural violations for tracking and remediation.

---

## Violation Details

| Field | Value |
|-------|-------|
| **Violation ID** | VIO-[YYYYMMDD]-[SEQ] |
| **Task ID** | [LOG/PROC/DEV/PHY/SCN]-REV-XX-XX |
| **View** | [Logical/Process/Development/Physical/Scenario] |
| **Severity** | 🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / 🟢 LOW |
| **Status** | 🔵 Open / 🟢 Resolved / ⚪ Won't Fix |

---

## Location

| Field | Value |
|-------|-------|
| **Repository** | [REPO_NAME] |
| **Branch** | [BRANCH_NAME] |
| **File** | `[path/to/file.py]` |
| **Line(s)** | [LINE_NUMBER] or [START_LINE-END_LINE] |
| **PR Link** | [PR_URL] |

---

## Description

### Summary
[Brief one-line description of the violation]

### Detailed Analysis
[Explanation of why this is a violation, including:
- The architectural constraint being violated
- The potential impact if not addressed
- The failure mode this would cause]

---

## Evidence

### Current Code
```python
# File: [path/to/file.py]
# Lines: [LINE_RANGE]

[Paste the violating code here]
```

### Detection Method
- [ ] Manual review
- [ ] `detect_blocking_calls.py`
- [ ] `validate_schema_migration.py`
- [ ] `verify_mojo_artifact.py`
- [ ] `check_memory_allocation.py`

### Tool Output
```
[Paste relevant tool output if applicable]
```

---

## Root Cause Analysis

### Why did this happen?
- [ ] Developer unfamiliarity with architectural constraints
- [ ] Missing documentation or training
- [ ] Copy-paste from outdated example
- [ ] Incremental change that accumulated debt
- [ ] Expediency under deadline pressure
- [ ] Other: [EXPLAIN]

### Contributing Factors
[Any additional context about why this violation occurred]

---

## Remediation

### Recommended Fix
```python
# File: [path/to/file.py]
# Lines: [LINE_RANGE]

[Paste the corrected code here]
```

### Verification Steps
1. [Step to verify the fix is correct]
2. [Step to verify no regressions]
3. [Run relevant validation script]

### References
- See `references/[relevant_doc].md` for detailed explanation
- See `checklists/[view]_view_review.md` for complete checklist

---

## Impact Assessment

### If Unresolved
- **Immediate**: [What happens now?]
- **Short-term**: [What happens in days/weeks?]
- **Long-term**: [What happens in months?]

### Blast Radius
- [ ] Isolated to single component
- [ ] Affects single service
- [ ] Affects multiple services
- [ ] System-wide impact

---

## Resolution

### Status Updates

| Date | Status | Notes |
|------|--------|-------|
| [DATE] | 🔵 Opened | Initial detection |
| [DATE] | 🟡 In Progress | Developer acknowledged |
| [DATE] | 🟢 Resolved | Fix merged in PR #XXX |

### Final Resolution
- **Resolved By**: [DEVELOPER_NAME]
- **Resolution PR**: [PR_URL]
- **Verification**: [How was the fix verified?]

---

## Prevention

### Systemic Improvements
- [ ] Add to automated linter rules
- [ ] Update documentation
- [ ] Add to onboarding training
- [ ] Create example code
- [ ] Other: [EXPLAIN]

### Follow-up Actions
| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [ACTION] | [OWNER] | [DATE] | ⬜ |
