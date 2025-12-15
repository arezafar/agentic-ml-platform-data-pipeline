---
description: Run all skill validation scripts to verify the scaffolding works
---

# Validate All Skills

This workflow runs `--help` on all validation scripts to verify they are properly configured and have no import or syntax errors.

## Prerequisites
- Python 3.11+ installed (accessible as `python3`)
- No external dependencies required for `--help` validation

## Steps

### 1. Verify Security Auditor Scripts
// turbo
```bash
cd /Users/theali/Documents/Agentic\ ML\ Platform\ and\ Pipelines
python3 agent-scaffolding/skills/security-auditor/scripts/scan_api_security.py --help
python3 agent-scaffolding/skills/security-auditor/scripts/check_secrets_exposure.py --help
python3 agent-scaffolding/skills/security-auditor/scripts/validate_container_deps.py --help
python3 agent-scaffolding/skills/security-auditor/scripts/validate_db_encryption.py --help
```

### 2. Verify Code Reviewer Scripts
// turbo
```bash
python3 agent-scaffolding/skills/code-reviewer/scripts/detect_blocking_calls.py --help
python3 agent-scaffolding/skills/code-reviewer/scripts/validate_schema_migration.py --help
python3 agent-scaffolding/skills/code-reviewer/scripts/verify_mojo_artifact.py --help
python3 agent-scaffolding/skills/code-reviewer/scripts/check_memory_allocation.py --help
```

### 3. Verify QA Scripts
// turbo
```bash
python3 agent-scaffolding/skills/qa/scripts/validate_async_drivers.py --help
python3 agent-scaffolding/skills/qa/scripts/run_slo_gate.py --help
python3 agent-scaffolding/skills/qa/scripts/check_mage_blocks.py --help
```

### 4. Verify ML Engineer Scripts
// turbo
```bash
python3 agent-scaffolding/skills/ml-engineer/scripts/validate_mojo.py --help
python3 agent-scaffolding/skills/ml-engineer/scripts/mojo_deployer.py --help
```

### 5. Verify FastAPI Pro Scripts
// turbo
```bash
python3 agent-scaffolding/skills/fastapi-pro/scripts/lint_endpoints.py --help
```

### 6. Verify Deployment Engineer Scripts
// turbo
```bash
python3 agent-scaffolding/skills/deployment-engineer/scripts/scan_dockerfile.py --help
```

### 7. Verify Database Architect Scripts
// turbo
```bash
python3 agent-scaffolding/skills/db-architect/scripts/validate_schema.py --help
python3 agent-scaffolding/skills/db-architect/scripts/generate_ddl.py --help
python3 agent-scaffolding/skills/db-architect/scripts/generate_agentic_ddl.py --help
```

### 8. Verify Data Engineer Scripts
// turbo
```bash
python3 agent-scaffolding/skills/data-engineer/scripts/validate_pipeline.py --help
python3 agent-scaffolding/skills/data-engineer/scripts/validate_dag.py --help
```

### 9. Verify Architectural Planner Scripts
// turbo
```bash
python3 agent-scaffolding/skills/architectural-planner/scripts/validate_plan_structure.py --help
python3 agent-scaffolding/skills/architectural-planner/scripts/check_jtbd_coverage.py --help
```

### 10. Verify Implementation Worker Scripts
// turbo
```bash
python3 agent-scaffolding/skills/implementation-worker/scripts/check_tdd_compliance.py --help
python3 agent-scaffolding/skills/implementation-worker/scripts/validate_task_execution.py --help
```

## Success Criteria
All scripts should display their help message without errors. Any errors indicate:
- Missing imports
- Syntax errors
- Python version incompatibility
