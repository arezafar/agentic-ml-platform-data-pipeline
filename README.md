# Agentic ML Platform - Agent Scaffolding

A multi-agent development system using Anthropic's Agent Skills architecture for an ML platform with PostgreSQL, Mage OSS, H2O.ai, and FastAPI.

## Architecture

```
agent-scaffolding/
├── skills/                         # Agent skill packages (13 skills)
│   ├── architectural-planner/      # Meta: Plan decomposition, 4+1 views
│   ├── backend-architect/          # Async inference, circuit breakers, GraphQL
│   ├── code-reviewer/              # Plan alignment, async/schema analysis
│   ├── data-engineer/              # ETL/ELT with Mage OSS
│   ├── database-optimizer/         # JSONB/GIN tuning, WAL orchestration
│   ├── db-architect/               # PostgreSQL schema design
│   ├── deployment-engineer/        # Docker containerization
│   ├── fastapi-pro/                # Async API development
│   ├── implementation-worker/      # Meta: Task execution
│   ├── lead-engineer-orchestrator/ # Dialectical reasoning, orchestration
│   ├── ml-engineer/                # H2O AutoML + MOJO
│   ├── qa/                         # Testing, concurrency, SLO
│   └── security-auditor/           # IAM, API hardening, CVE scanning
├── platform/                       # Platform layer configs
└── README.md
```

## Agent Roles

| Agent | Layer | Specialization |
|-------|-------|----------------|
| **Architectural Planner** | Meta | Plan decomposition, 4+1 architectural views, JTBD framework |
| **Backend Architect** | Serving | Event loop protection, circuit breakers, split memory, GraphQL |
| **Code Reviewer** | Meta | Plan alignment, async blocking detection, schema drift analysis |
| **Data Engineer** | Orchestration | Mage OSS pipelines, ETL/ELT, dynamic blocks |
| **Database Architect** | Persistence | PostgreSQL 15+, JSONB/GIN, partitioning, feature store |
| **Database Optimizer** | Persistence | JSONB key tuning, GIN health, WAL orchestration, query plans |
| **Deployment Engineer** | Infrastructure | Docker multi-stage, K8s manifests, security hardening |
| **FastAPI Pro** | Serving | Async APIs, Pydantic, asyncpg, circuit breaker |
| **Implementation Worker** | Meta | Polymorphic task execution, TDD compliance |
| **Lead Engineer Orchestrator** | Meta | Dialectical reasoning, 4+1 View enforcement, architectural governance |
| **ML Engineer** | ML | H2O AutoML, MOJO artifacts, model registry |
| **QA** | Testing | Unit/integration/load testing, concurrency, SLO gating |
| **Security Auditor** | Security | OAuth2/OIDC, rate limiting, CVE scanning, secrets audit |

## Tech Stack

- **Python 3.11+**: Runtime
- **PostgreSQL 15+**: Persistence (JSONB, partitioning, GIN indexes)
- **Mage OSS**: Orchestration
- **H2O.ai**: ML/AutoML with MOJO export
- **FastAPI**: Serving layer (asyncpg, Redis caching)
- **Docker/Kubernetes**: Containerization

## Quick Start

### 1. Validate a Skill

```bash
# Data Engineering - Validate Mage pipeline
python agent-scaffolding/skills/data-engineer/scripts/validate_pipeline.py <pipeline_path>

# Database - Validate PostgreSQL schema
python agent-scaffolding/skills/db-architect/scripts/validate_schema.py <schema.json>

# Database - Generate DDL from schema
python agent-scaffolding/skills/db-architect/scripts/generate_ddl.py <schema.json> --output schema.sql

# ML Engineering - Validate H2O MOJO artifact
python agent-scaffolding/skills/ml-engineer/scripts/validate_mojo.py <model.zip>

# FastAPI - Lint endpoints for async safety
python agent-scaffolding/skills/fastapi-pro/scripts/lint_endpoints.py <api_directory>

# Deployment - Scan Dockerfile for security
python agent-scaffolding/skills/deployment-engineer/scripts/scan_dockerfile.py <Dockerfile>

# Code Review - Detect blocking calls in async functions
python agent-scaffolding/skills/code-reviewer/scripts/detect_blocking_calls.py --source-dir ./src/api

# Code Review - Validate schema migrations
python agent-scaffolding/skills/code-reviewer/scripts/validate_schema_migration.py --migration-dir ./alembic/versions

# QA - Validate async drivers
python agent-scaffolding/skills/qa/scripts/validate_async_drivers.py --source-dir ./src/inference

# QA - Run SLO gate
python agent-scaffolding/skills/qa/scripts/run_slo_gate.py --results locust_stats.csv --p99-threshold 50

# Security - Scan API for vulnerabilities
python agent-scaffolding/skills/security-auditor/scripts/scan_api_security.py --source-dir ./src/api

# Security - Check for exposed secrets
python agent-scaffolding/skills/security-auditor/scripts/check_secrets_exposure.py --source-dir ./
```

### 2. Use Templates

Each skill includes templates in `assets/`:

```bash
# Data Engineering
agent-scaffolding/skills/data-engineer/assets/mage_pipeline_template.py
agent-scaffolding/skills/data-engineer/assets/mage_block_template.py

# Database Architecture
agent-scaffolding/skills/db-architect/assets/schema_template.json

# ML Engineering
agent-scaffolding/skills/ml-engineer/assets/h2o_training_template.py
agent-scaffolding/skills/ml-engineer/assets/mage_pipeline/

# FastAPI
agent-scaffolding/skills/fastapi-pro/assets/fastapi_project_template/
agent-scaffolding/skills/fastapi-pro/assets/app/

# Deployment
agent-scaffolding/skills/deployment-engineer/assets/Dockerfile.template
agent-scaffolding/skills/deployment-engineer/assets/docker-compose.yml

# Code Review
agent-scaffolding/skills/code-reviewer/assets/templates/code_review_report.md
agent-scaffolding/skills/code-reviewer/assets/checklists/

# QA
agent-scaffolding/skills/qa/assets/pytest.ini
agent-scaffolding/skills/qa/assets/unit_tests/
agent-scaffolding/skills/qa/assets/integration_tests/
agent-scaffolding/skills/qa/assets/load_tests/

# Security
agent-scaffolding/skills/security-auditor/assets/templates/security_audit_report.md
agent-scaffolding/skills/security-auditor/assets/checklists/
```

## Skill Structure

Each agent skill follows the standard Agent Skills directory structure:

```
skills/{agent-name}/
├── SKILL.md        # Instructions and metadata (JTBD, superpowers, triggers)
├── scripts/        # Validation and utility scripts
├── assets/         # Templates, configs, and test fixtures
└── references/     # Documentation and best practices
```

## Meta-Agents

### Architectural Planner
Utilizes `superpowers:writing-plans` and `superpowers:sequential-thinking` to decompose requirements:
- Generates plans using JTBD (Jobs-to-be-Done) framework
- Maps tasks to 4+1 Architectural Views (Logical, Process, Development, Physical, Scenarios)
- Defines verification steps and Definition of Done
- Applies dialectical reasoning for technology decisions

### Implementation Worker
Utilizes `superpowers:subagent-driven-development` for task execution:
- Loads specialist skill per task type
- Maintains context isolation between tasks
- Enforces Iron Law of TDD (test-driven development)
- Reports back to coordinator with artifacts

### Code Reviewer
Utilizes 4 superpowers for plan alignment:
- **Async Non-Blocking Radar**: Detect blocking calls in async contexts
- **Schema Drift Detector**: Verify JSONB/GIN compliance in migrations
- **Artifact Integrity Scanner**: Validate MOJO vs POJO usage
- **Resource Isolation Sight**: Container memory and network analysis

### QA Agent
Spans all platform layers with:
- Unit testing (Mage blocks, Pydantic schemas, pgvector)
- Integration testing (MOJO loading, asyncpg, transactions)
- Concurrency analysis (blocking detection, thread pool verification)
- Load testing (Locust, SLO gating)
- Canary validation (hot-swap, memory leak detection)

### Security Auditor
Active defense across 5 domains:
- **IAM**: OAuth2/OIDC, scope-based access, session revocation
- **API Hardening**: Rate limiting, JSON schema validation, injection prevention
- **Container Security**: Multi-stage builds, CVE scanning, non-root users
- **Data Privacy**: Encryption, PII masking, role segregation
- **MLOps Security**: Model signing, pickle elimination, input guardrails

## Platform Layers

| Layer | Component | Technology |
|-------|-----------|------------|
| **Persistence** | Raw Data Store | PostgreSQL + JSONB |
| | Feature Store | PostgreSQL + Partitioning + GIN |
| | Model Registry | PostgreSQL |
| **Orchestration** | Pipelines | Mage OSS (dynamic blocks) |
| **ML** | Training | H2O AutoML |
| | Artifacts | MOJO format |
| **Serving** | API | FastAPI + asyncpg |
| | Inference | H2O MOJO runtime (C++) |
| | Caching | Redis (look-aside pattern) |
| **Infrastructure** | Containers | Docker / Kubernetes |
| **Security** | AuthN/AuthZ | OAuth2/OIDC, JWT |

## License

MIT
