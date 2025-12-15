# 4+1 Architectural View Model Reference

## Overview

The Implementation Worker skill follows the 4+1 Architectural View Model to ensure comprehensive coverage of all system concerns.

```
                    ┌─────────────────────┐
                    │    Scenarios (+1)    │
                    │   Use Case Driven   │
                    └─────────┬───────────┘
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Logical │ │ Process │ │   Dev   │ │Physical │
   │  View   │ │  View   │ │  View   │ │  View   │
   └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## View Definitions

### Logical View (LOG)
**Concern**: Functional requirements, data structures, object interactions

**Key Questions**:
- What data entities exist?
- How do they relate to each other?
- What are the invariants?

**Assets**:
- `assets/schemas/feature_store.py` - JSONB hybrid schema
- `assets/schemas/model_registry.py` - Model lifecycle tracking
- `assets/alembic/` - Database migrations

---

### Process View (PROC)
**Concern**: Concurrency, synchronization, runtime behavior

**Key Questions**:
- What processes/threads exist?
- How do they communicate?
- Where are the bottlenecks?

**Critical Decisions**:

| Pattern | Rationale |
|---------|-----------|
| `run_in_executor` | Isolates CPU-bound inference from event loop |
| Dynamic Blocks | Enables parallel training without code duplication |
| Circuit Breaker | Prevents cascade failures under load |

**Assets**:
- `assets/patterns/executor_offloading.py`
- `assets/patterns/mage_dynamic_block.py`
- `assets/patterns/circuit_breaker.py`

---

### Development View (DEV)
**Concern**: Code organization, build system, testing

**Key Questions**:
- How is code organized?
- How are dependencies managed?
- How is quality enforced?

**Monorepo Structure**:
```
/
├── src/
│   ├── etl/                # Mage pipelines
│   ├── api/                # FastAPI app
│   └── shared/             # Contracts
├── tests/
│   ├── integration/        # Testcontainers
│   └── unit/               # Pure unit tests
└── pyproject.toml
```

**Assets**:
- `assets/contracts/feature_vector.py` - Shared Pydantic models
- `assets/tdd/conftest.py` - Testcontainers fixtures
- `assets/monorepo_structure/` - Reference layout

---

### Physical View (PHY)
**Concern**: Infrastructure, deployment, resource allocation

**Key Questions**:
- Where does code run?
- How are resources allocated?
- How do components discover each other?

**H2O Memory Split** (Critical):
```
Container Memory: 16Gi
├── JVM Heap (-Xmx): 11Gi (70%)
└── Native (XGBoost): 5Gi (30%)
```

**Kubernetes Patterns**:
- StatefulSet for stable network identities
- Headless Service for peer discovery
- PodDisruptionBudget for availability

**Assets**:
- `assets/k8s/h2o_statefulset.yaml`
- `assets/k8s/readiness_probe.py`

---

### Scenarios View (+1)
**Concern**: End-to-end validation through use cases

**Key Scenarios**:

#### Scenario A: Time-Series Walk-Forward Training
```
1. Mage loads historical data
2. Mage generates temporal splits (Jan→Feb, Jan-Feb→Mar, etc.)
3. Dynamic blocks spawn parallel H2O jobs
4. Each job trains on its split
5. Results aggregated for ensemble
```

**Validation**:
```python
# For every split
assert max(train_dates) < min(test_dates)
```

#### Scenario B: Zero-Downtime Model Updates
```
1. New MOJO uploaded to storage
2. Mage triggers POST /admin/reload-model
3. FastAPI loads new model in background
4. Atomic swap of CURRENT_MODEL reference
5. Old model garbage collected
```

**Validation**:
```python
# Fire 100Hz requests during reload
async with httpx.AsyncClient() as client:
    for _ in range(1000):
        response = await client.post("/predict", json=data)
        assert response.status_code == 200  # No 500s
```

---

## Implementation Backlog Summary

### Epic LOG-01: Hybrid Feature Store Schema
| Story | Status | Description |
|-------|--------|-------------|
| LOG-01-01 | ✅ | FeatureStore with JSONB + GIN |
| LOG-01-02 | ✅ | ModelRegistry with FK constraints |

### Epic PROC-01: Async Inference Pipeline
| Story | Status | Description |
|-------|--------|-------------|
| PROC-01-01 | ✅ | Executor offloading pattern |
| PROC-01-02 | ✅ | Circuit breaker implementation |

### Epic PROC-02: Mage ETL Orchestration
| Story | Status | Description |
|-------|--------|-------------|
| PROC-02-01 | ✅ | Dynamic block fan-out |

### Epic DEV-01: CI/CD & Contracts
| Story | Status | Description |
|-------|--------|-------------|
| DEV-01-01 | ✅ | Shared Pydantic contracts |
| DEV-01-02 | ✅ | TDD fixtures with Testcontainers |

### Epic PHY-01: Kubernetes Topology
| Story | Status | Description |
|-------|--------|-------------|
| PHY-01-01 | ✅ | H2O StatefulSet with headless service |
| PHY-01-02 | ✅ | Custom readiness probe |

---

## Verification Gate Checklist

Before any deployment:

- [ ] **Security**: Is SSL termination configured?
- [ ] **Concurrency**: Are blocking calls wrapped in `run_in_executor`?
- [ ] **Consistency**: Is training data queried with snapshot isolation?
- [ ] **Testing**: Do integration tests use Testcontainers?
- [ ] **Contracts**: Are Pydantic models shared between producer/consumer?
- [ ] **Memory**: Is H2O memory split 70% JVM / 30% native?
- [ ] **Probes**: Does readiness probe check cluster consensus?

---

## Dialectical Decisions

| Topic | Thesis | Antithesis | Synthesis |
|-------|--------|------------|-----------|
| Model Format | POJO simplicity | JVM limits, py4j overhead | **MOJO mandated** |
| Concurrency | Pure async | GIL blocks inference | **Executor isolation** |
| Data Consistency | Live queries | Training on shifting data | **Snapshot isolation** |
| Indexing | Fast writes | Slow JSONB queries | **GIN with mitigations** |
| Cluster Identity | Deployment | Unstable pod IPs | **StatefulSet** |

---

## References

- [H2O MOJO Documentation](https://docs.h2o.ai/h2o/latest-stable/h2o-docs/productionizing.html)
- [PostgreSQL JSONB Indexing](https://www.postgresql.org/docs/current/datatype-json.html#JSON-INDEXING)
- [Kubernetes StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/)
- [FastAPI Concurrency](https://fastapi.tiangolo.com/async/)
