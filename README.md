# Agentic ML Platform - Agent Scaffolding

A multi-agent development system using Anthropic's Agent Skills architecture for an ML platform with PostgreSQL, Mage OSS, H2O.ai, and FastAPI.

## Architecture

```
agent-scaffolding/
├── skills/                     # Agent skill packages
│   ├── data-engineer/          # ETL/ELT with Mage OSS
│   ├── db-architect/           # PostgreSQL schema design
│   ├── ml-engineer/            # H2O AutoML + MOJO
│   ├── fastapi-pro/            # Async API development
│   ├── deployment-engineer/    # Docker containerization
│   ├── architectural-planner/  # Meta: Plan generation
│   └── implementation-worker/  # Meta: Task execution
├── platform/                   # Platform layer configs
└── README.md
```

## Agent Roles

| Agent | Layer | Specialization |
|-------|-------|----------------|
| **Data Engineer** | Orchestration | Mage OSS pipelines, ETL/ELT |
| **Database Architect** | Persistence | PostgreSQL 15+, JSONB, partitioning |
| **ML Engineer** | ML | H2O AutoML, MOJO artifacts |
| **FastAPI Pro** | Serving | Async APIs, Pydantic, asyncpg |
| **Deployment Engineer** | Infrastructure | Docker multi-stage, security |
| **Architectural Planner** | Meta | Plan decomposition, orchestration |
| **Implementation Worker** | Meta | Polymorphic task execution |

## Tech Stack

- **Python 3.11+**: Runtime
- **PostgreSQL 15+**: Persistence (JSONB, partitioning)
- **Mage OSS**: Orchestration
- **H2O.ai**: ML/AutoML with MOJO export
- **FastAPI**: Serving layer
- **Docker**: Containerization

## Quick Start

### 1. Validate a Skill

```bash
# Validate Mage pipeline
python skills/data-engineer/scripts/validate_pipeline.py <pipeline_path>

# Validate PostgreSQL schema
python skills/db-architect/scripts/validate_schema.py <schema.json>

# Generate DDL from schema
python skills/db-architect/scripts/generate_ddl.py <schema.json> --output schema.sql

# Validate H2O MOJO artifact
python skills/ml-engineer/scripts/validate_mojo.py <model.zip>

# Lint FastAPI endpoints
python skills/fastapi-pro/scripts/lint_endpoints.py <api_directory>

# Scan Dockerfile for security
python skills/deployment-engineer/scripts/scan_dockerfile.py <Dockerfile>
```

### 2. Use Templates

Each skill includes templates in `assets/`:

```bash
# Mage pipeline templates
skills/data-engineer/assets/mage_pipeline_template.py
skills/data-engineer/assets/mage_block_template.py

# PostgreSQL schema template
skills/db-architect/assets/schema_template.json

# H2O training template
skills/ml-engineer/assets/h2o_training_template.py

# FastAPI project structure
skills/fastapi-pro/assets/fastapi_project_template/

# Docker templates
skills/deployment-engineer/assets/Dockerfile.template
skills/deployment-engineer/assets/docker-compose.yml
```

## Skill Structure

Each agent skill follows the standard Agent Skills directory structure:

```
skills/{agent-name}/
├── SKILL.md        # Instructions and metadata
├── scripts/        # Validation and utility scripts
├── assets/         # Templates and config files
└── references/     # Documentation and best practices
```

## Meta-Agents

### Architectural Planner
Utilizes `superpowers:writing-plans` to decompose requirements into structured plans:
- Generates `PLAN.md` with phases and tasks
- Assigns roles to each task
- Defines verification steps and DoD

### Implementation Worker
Utilizes `superpowers:subagent-driven-development` for task execution:
- Loads specialist skill per task
- Maintains context isolation
- Reports back to coordinator

## Platform Layers

| Layer | Component | Technology |
|-------|-----------|------------|
| **Persistence** | Raw Data Store | PostgreSQL + JSONB |
| | Feature Store | PostgreSQL + Partitioning |
| | Model Registry | PostgreSQL |
| **Orchestration** | Pipelines | Mage OSS |
| **ML** | Training | H2O AutoML |
| | Artifacts | MOJO format |
| **Serving** | API | FastAPI + asyncpg |
| | Inference | H2O MOJO runtime |
| **Infrastructure** | Containers | Docker |

## Placeholders

The following are marked as placeholders for future expansion:
- Detailed role instructions in SKILL.md files
- `superpowers:writing-plans` integration
- `superpowers:subagent-driven-development` integration

## License

MIT
