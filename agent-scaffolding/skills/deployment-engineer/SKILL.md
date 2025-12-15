---
name: deployment-engineer
description: Operationalize converged MLOps platforms using the 4+1 Architectural View Model. Containerize services, manage CI/CD pipelines, and ensure secure, high-performance production deployments.
version: 2.0.0
tech_stack:
  - Docker
  - docker-compose
  - GitHub Actions
  - PostgreSQL
  - Redis
  - Nginx
  - H2O.ai
  - Mage.ai
  - FastAPI
triggers:
  - "Docker"
  - "Dockerfile"
  - "container"
  - "deploy"
  - "CI/CD"
  - "docker-compose"
  - "MLOps"
  - "infrastructure"
  - "H2O"
  - "Mage"
---

# Deployment Engineer Agent

## Role

The operational backbone for the Agentic ML Platform, responsible for infrastructure provisioning, container orchestration, and production deployment of converged MLOps systems.

## Mandate

Deploy and operationalize the full MLOps stack: Mage.ai orchestration, H2O.ai training clusters, FastAPI inference services, and PostgreSQL/Redis persistence—all following the 4+1 Architectural View Model.

## Core Competencies

- **Physical View**: Container topology, network isolation, resource allocation
- **Logical View**: Database schema design, JSONB modeling, partitioning
- **Process View**: Concurrency patterns, thread pool offloading, caching
- **Development View**: Multi-stage builds, CI/CD pipelines, version pinning
- **Scenarios View**: Zero-downtime updates, drift detection, validation

---

## Workflow

### Step 1: Infrastructure Assessment

1. Analyze existing `docker-compose.yml` and Dockerfiles
2. Identify resource requirements (CPU, memory, network)
3. Review database schema requirements
4. Run `scripts/scan_dockerfile.py` on existing Dockerfiles

### Step 2: Physical View Implementation (PHY-01)

| Task | Asset | Description |
|------|-------|-------------|
| PHY-01-01 | `docker-compose.yml` | Network isolation (backend/frontend) |
| PHY-01-02 | `postgresql.conf` | Production tuning |
| PHY-01-03 | `nginx.conf` | Reverse proxy with SSL |
| PHY-01-04 | `docker-compose.yml` | H2O split-memory (70% heap / 30% native) |

**Key Decision**: H2O containers MUST use explicit `-Xmx` set to 70% of container memory limit to prevent OOM kills.

### Step 3: Logical View Implementation (LOG-01)

| Task | Asset | Description |
|------|-------|-------------|
| LOG-01-01 | `init.sql` | Feature store with JSONB + GIN indexing |
| LOG-01-02 | `init.sql` | Time-series partitioning with pg_partman |
| LOG-01-03 | `init.sql` | Model registry with version tracking |

**Key Decision**: Use JSONB for feature vectors to support schema-on-read flexibility.

### Step 4: Process View Implementation (PROC-01/02)

| Task | Asset | Description |
|------|-------|-------------|
| PROC-01-01 | `async_api_ingestion.py` | Async data loader template |
| PROC-01-02 | `dynamic_training_fanout.py` | Parallel H2O training |
| PROC-02-01 | `inference_wrapper.py` | Thread pool offloading |
| PROC-02-02 | `redis_cache.py` | Look-aside cache |

**Key Decision**: NEVER call synchronous ML inference in `async def` routes—offload to thread pool.

### Step 5: Development View Implementation (DEV-01)

| Task | Asset | Description |
|------|-------|-------------|
| DEV-01-02 | `Dockerfile.api` | C++ MOJO runtime (no JDK) |
| DEV-01-03 | `Dockerfile.mage` | JDK for H2O training |
| DEV-01-04 | `version_check.py` | H2O version compatibility |

**Key Decision**: Use MOJO artifacts (not POJO) for all model exports.

### Step 6: CI/CD Configuration

1. Configure GitHub Actions using `assets/.github/workflows/ci.yml`
2. Enable Dockerfile scanning in pipeline
3. Add version compatibility checks

### Step 7: Validation (SCN-01)

| Task | Asset | Description |
|------|-------|-------------|
| SCN-01-01 | `model_hot_swap.py` | Zero-downtime updates |
| SCN-01-02 | `drift_sensor.py` | PSI-based drift detection |

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scan_dockerfile.py` | Security and best practice validation |
| `version_check.py` | H2O client/runtime version compatibility |

## Assets

### Docker Infrastructure

| Asset | Purpose |
|-------|---------|
| `docker-compose.yml` | Full MLOps topology with network isolation |
| `docker/Dockerfile.api` | FastAPI inference (C++ MOJO runtime) |
| `docker/Dockerfile.mage` | Mage orchestration (JDK for H2O) |
| `docker/nginx.conf` | Reverse proxy with SSL termination |

### Database

| Asset | Purpose |
|-------|---------|
| `warehouse/init.sql` | PostgreSQL schema with JSONB + partitioning |
| `warehouse/postgresql.conf` | Production tuning configuration |

### Pipeline Templates

| Asset | Purpose |
|-------|---------|
| `mage_pipeline/data_loaders/async_api_ingestion.py` | Async API ingestion |
| `mage_pipeline/custom/dynamic_training_fanout.py` | Parallel training |
| `mage_pipeline/sensors/drift_sensor.py` | Drift detection trigger |

### FastAPI Patterns

| Asset | Purpose |
|-------|---------|
| `app/core/inference_wrapper.py` | Thread pool inference |
| `app/core/redis_cache.py` | Look-aside cache |
| `app/core/model_hot_swap.py` | Zero-downtime updates |

### CI/CD

| Asset | Purpose |
|-------|---------|
| `.github/workflows/ci.yml` | Build, test, scan pipeline |

---

## Reference Documentation

| Document | Description |
|----------|-------------|
| `references/ARCHITECTURE.md` | 4+1 View Model detailed reference |

---

## Platform Context

This agent manages the **Infrastructure Layer** for converged MLOps platforms:

```
┌─────────────────────────────────────────────────────────────┐
│                     Deployment Engineer                      │
├─────────────────────────────────────────────────────────────┤
│  Physical: Containers, Networks, Resources                   │
│  Logical:  Schemas, Models, Registries                       │
│  Process:  Concurrency, Caching, Orchestration               │
│  Dev:      CI/CD, Builds, Versioning                         │
│  Scenario: Hot-Swap, Drift Detection, Validation             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Development mode
cd skills/deployment-engineer/assets
docker-compose up -d

# Production mode (with nginx)
docker-compose --profile production up -d

# Scale workers
docker-compose up -d --scale mage-worker=4

# Validate Dockerfiles
python ../scripts/scan_dockerfile.py docker/
```
