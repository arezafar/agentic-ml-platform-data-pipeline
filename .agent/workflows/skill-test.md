---
description: Test a specific skill's validation scripts with sample data
---

# Skill Test Workflow

Test a specific skill by running its validation scripts against sample data or with `--help`.

## Usage
Replace `{skill-name}` with one of:
- `security-auditor`
- `code-reviewer`
- `qa`
- `ml-engineer`
- `fastapi-pro`
- `deployment-engineer`
- `db-architect`
- `data-engineer`
- `architectural-planner`
- `implementation-worker`

## Steps

### 1. Navigate to Project Root
```bash
cd /Users/theali/Documents/Agentic\ ML\ Platform\ and\ Pipelines
```

### 2. List Available Scripts for the Skill
// turbo
```bash
ls -la agent-scaffolding/skills/{skill-name}/scripts/
```

### 3. View Skill Documentation
// turbo
```bash
cat agent-scaffolding/skills/{skill-name}/SKILL.md | head -100
```

### 4. Run Script with Help
// turbo
```bash
python3 agent-scaffolding/skills/{skill-name}/scripts/{script-name}.py --help
```

### 5. Run Script with Sample Data (if available)
Replace with actual paths to test data:
```bash
python3 agent-scaffolding/skills/{skill-name}/scripts/{script-name}.py --source-dir ./sample-data
```

## Skill-Specific Examples

### Security Auditor
```bash
# Scan API endpoints for security issues
python3 agent-scaffolding/skills/security-auditor/scripts/scan_api_security.py --source-dir ./src/api

# Check for exposed secrets
python3 agent-scaffolding/skills/security-auditor/scripts/check_secrets_exposure.py --source-dir ./
```

### Code Reviewer
```bash
# Detect blocking calls in async functions
python3 agent-scaffolding/skills/code-reviewer/scripts/detect_blocking_calls.py --source-dir ./src/api

# Validate schema migrations
python3 agent-scaffolding/skills/code-reviewer/scripts/validate_schema_migration.py --migration-dir ./alembic/versions
```

### QA
```bash
# Validate async driver usage
python3 agent-scaffolding/skills/qa/scripts/validate_async_drivers.py --source-dir ./src/inference

# Run SLO gate
python3 agent-scaffolding/skills/qa/scripts/run_slo_gate.py --results locust_stats.csv --p99-threshold 50
```

### ML Engineer
```bash
# Validate MOJO artifact
python3 agent-scaffolding/skills/ml-engineer/scripts/validate_mojo.py model.zip
```

### Deployment
```bash
# Scan Dockerfile for security
python3 agent-scaffolding/skills/deployment-engineer/scripts/scan_dockerfile.py Dockerfile
```
