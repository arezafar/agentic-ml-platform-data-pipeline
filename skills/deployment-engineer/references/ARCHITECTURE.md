# 4+1 Architectural View Model - Deployment Engineer Reference

Comprehensive reference documentation for the Converged MLOps Platform deployment.

## Table of Contents

1. [Concurrency Strategy](#concurrency-strategy)
2. [Artifact Strategy (MOJO vs POJO)](#artifact-strategy)
3. [Split-Memory Allocation](#split-memory-allocation)
4. [Network Topology](#network-topology)
5. [Version Compatibility](#version-compatibility)

---

## Concurrency Strategy

### The Problem: GIL and Event Loop Blocking

FastAPI uses Python's `asyncio` event loop for high concurrency. However, ML inference is CPU-bound:

```
┌─────────────────────────────────────────────────────────────┐
│                    Event Loop (Single Thread)               │
├─────────────────────────────────────────────────────────────┤
│  Request 1 ──► await db.query() ──► (suspended, loop free)  │
│  Request 2 ──► h2o.predict()    ──► BLOCKED! 🔴             │
│  Request 3 ──► waiting...       ──► can't proceed           │
└─────────────────────────────────────────────────────────────┘
```

### The Solution: Thread Pool Offloading

```python
# ❌ BAD: Blocks event loop
@app.post("/predict")
async def predict(features: dict):
    return model.predict(features)  # CPU-bound, blocks everything

# ✅ GOOD: Offloads to thread pool
@app.post("/predict")
async def predict(features: dict):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, model.predict, features)

# ✅ ALSO GOOD: FastAPI auto-offloads def routes
@app.post("/predict")
def predict(features: dict):  # Note: def, not async def
    return model.predict(features)  # Auto-offloaded to thread pool
```

### Implementation

See: [inference_wrapper.py](file:///Users/theali/Documents/Agentic%20ML%20Platform%20and%20Pipelines/agent-scaffolding/skills/deployment-engineer/assets/app/core/inference_wrapper.py)

---

## Artifact Strategy

### MOJO vs POJO Comparison

| Feature | POJO | MOJO |
|---------|------|------|
| **Format** | Java source code | Serialized binary |
| **Compilation** | Required at runtime | None required |
| **Size Limit** | 64KB method limit | No practical limit |
| **Runtime** | Requires JDK | C++ or Java |
| **Startup** | Slow (compilation) | Fast (deserialization) |

### Why MOJO is Mandatory

1. **Large Models**: Stacked Ensembles exceed POJO limits
2. **C++ Runtime**: No JVM in inference container = smaller image
3. **Portability**: Version-agnostic serialization

### Export Pattern

```python
# Training container (has JDK)
model = h2o.automl.get_best_model()
mojo_path = model.save_mojo(path="/models/staging/v1.2.3")

# Inference container (C++ only)
from daimojo.model import Model
predictor = Model("/models/production/model.mojo")
```

---

## Split-Memory Allocation

### The OOM Problem

```
Container Limit: 12GB
JVM Heap (-Xmx): 12GB
XGBoost Native:  2GB needed ──► OOM Kill! 💀
```

### The 70/30 Rule

Allocate **70% to JVM Heap**, reserve **30% for native memory**:

```yaml
# docker-compose.yml
h2o-ai:
  environment:
    JAVA_OPTS: >-
      -Xmx8g      # 70% of 12GB
      -Xms4g      # Initial heap
      -XX:+UseG1GC
  deploy:
    resources:
      limits:
        memory: 12G  # Container limit
```

### Memory Breakdown

| Component | Allocation | Purpose |
|-----------|------------|---------|
| JVM Heap | 8GB (70%) | H2O frames, model training |
| Native Memory | 3GB (25%) | XGBoost, OpenBLAS |
| OS Overhead | 1GB (5%) | Thread stacks, buffers |

---

## Network Topology

### Zero-Trust Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND-NET (Exposed)                  │
│  ┌─────────────────┐                                        │
│  │  nginx-gateway  │ ◄── External Traffic (80/443)          │
│  │  (SSL Termination)                                       │
│  └────────┬────────┘                                        │
└───────────┼─────────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────────┐
│                     BACKEND-NET (Internal)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   FastAPI    │  │    Mage      │  │    H2O       │       │
│  │  (Inference) │  │ (Orchestrate)│  │  (Training)  │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │               │
│  ┌──────▼─────────────────▼─────────────────▼───────┐       │
│  │              PostgreSQL / Redis                   │       │
│  │              (State / Cache)                      │       │
│  └───────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Key Isolation Rules

1. **backend-net**: `internal: true` - no external access
2. **Only nginx exposed**: All traffic through reverse proxy
3. **Service discovery**: Hostnames via Docker DNS

---

## Version Compatibility

### Critical Alignment Requirements

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Mage Container │     │  H2O Container  │     │ FastAPI Container│
│  h2o==3.46.0.1  │ ══► │  jar:3.46.0.1   │ ══► │ daimojo==2.8.0  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        ▲                       ▲                       ▲
        └───────────────────────┴───────────────────────┘
                    MUST MATCH (±minor version)
```

### Version Check Script

```bash
python scripts/version_check.py \
  --h2o-version 3.46.0.1 \
  --dockerfile-api docker/Dockerfile.api \
  --dockerfile-mage docker/Dockerfile.mage
```

### Compatible Version Matrix

| H2O Version | daimojo Versions | Notes |
|-------------|------------------|-------|
| 3.46.0.1 | 2.8.x, 2.7.x | Current recommended |
| 3.44.0.3 | 2.7.x, 2.6.x | Stable |
| 3.42.0.4 | 2.6.x, 2.5.x | Legacy |

---

## Quick Reference

### File Locations

| Component | Path |
|-----------|------|
| Docker Compose | `assets/docker-compose.yml` |
| API Dockerfile | `assets/docker/Dockerfile.api` |
| Mage Dockerfile | `assets/docker/Dockerfile.mage` |
| Nginx Config | `assets/docker/nginx.conf` |
| SQL Schema | `assets/warehouse/init.sql` |
| PG Config | `assets/warehouse/postgresql.conf` |
| Inference Wrapper | `assets/app/core/inference_wrapper.py` |
| Redis Cache | `assets/app/core/redis_cache.py` |
| Hot-Swap Manager | `assets/app/core/model_hot_swap.py` |
| Drift Sensor | `assets/mage_pipeline/sensors/drift_sensor.py` |
| CI/CD Workflow | `assets/.github/workflows/ci.yml` |

### Commands

```bash
# Development
docker-compose up -d

# Production (with nginx)
docker-compose --profile production up -d

# Scale workers
docker-compose up -d --scale mage-worker=4

# Check Dockerfile security
python scripts/scan_dockerfile.py assets/docker/

# Check version compatibility
python assets/scripts/version_check.py --h2o-version 3.46.0.1
```
