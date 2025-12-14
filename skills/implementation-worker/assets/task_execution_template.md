# Task Execution Log

## Task Information

| Field | Value |
|-------|-------|
| **Task ID** | {{ task_id }} |
| **Description** | {{ task_description }} |
| **Assigned Role** | {{ assigned_role }} |
| **Skill Loaded** | {{ skill_path }} |
| **Started At** | {{ start_time }} |
| **Completed At** | {{ end_time }} |
| **Duration** | {{ duration }} |

---

## Input Context

### Dependencies
{{ dependency_list }}

### Referenced Files
{{ referenced_files }}

---

## Execution Steps

### Step 1: Skill Loading
```
Loaded: {{ skill_path }}
Instructions parsed: {{ instruction_count }} sections
Assets available: {{ assets_available }}
Scripts available: {{ scripts_available }}
```

### Step 2: File Generation

| File | Action | Status |
|------|--------|--------|
{{ file_actions_table }}

### Step 3: Verification

#### Command Executed
```bash
{{ verification_command }}
```

#### Output
```
{{ verification_output }}
```

#### Exit Code
{{ exit_code }}

---

## Result

### Status: {{ status }}

### Artifacts Created
{{ artifacts_list }}

### Issues Encountered
{{ issues_list }}

### Notes
{{ notes }}

---

## Handoff to Coordinator

```json
{
  "task_id": "{{ task_id }}",
  "status": "{{ status }}",
  "artifacts": {{ artifacts_json }},
  "verification": {
    "command": "{{ verification_command }}",
    "exit_code": {{ exit_code }},
    "passed": {{ verification_passed }}
  },
  "duration_seconds": {{ duration_seconds }},
  "notes": "{{ notes }}"
}
```
