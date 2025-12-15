# Jobs-to-be-Done (JTBD) Framework

Template for mapping system requirements to architectural mandates.

---

## JTBD Statement Format

```
Given [SITUATION],
the system must [ARCHITECTURAL PATTERN],
to ensure [PERFORMANCE METRIC].
```

---

## Core Platform Jobs

### JTBD-01: Stack Decomposition

| Field | Value |
|-------|-------|
| **Situation** | The Mage/H2O/Postgres technology stack |
| **Pattern** | Decompose architecture using 4+1 View Model |
| **Metric** | Zero requirements overlooked |
| **Superpower** | Writing-Plans |
| **Target Views** | Logical, Development |

**Deliverables**:
- [ ] Logical View: Schema definitions
- [ ] Development View: Code structure
- [ ] Process View: Concurrency patterns
- [ ] Physical View: Infrastructure topology
- [ ] Scenarios View: Failure validations

---

### JTBD-02: Inference Scaling

| Field | Value |
|-------|-------|
| **Situation** | Request rate >1000 req/s |
| **Pattern** | Horizontal scaling with thread offloading |
| **Metric** | p99 latency <50ms |
| **Superpower** | Scalability Planning |
| **Target Views** | Process, Physical |

**Deliverables**:
- [ ] FastAPI DeploymentSet with HPA
- [ ] ThreadPoolExecutor for CPU-bound inference
- [ ] Redis look-aside cache
- [ ] Load test passing 1000 req/s

---

### JTBD-03: Feature Store Sharding

| Field | Value |
|-------|-------|
| **Situation** | Massive data growth (TBs of features) |
| **Pattern** | Hash-based sharding with application routing |
| **Metric** | Zero write bottlenecks, no index bloat |
| **Superpower** | Sequential-Thinking |
| **Target Views** | Logical, Physical |

**Sequential Steps**:
1. [ ] Profile Data: Cardinality analysis
2. [ ] Select Key: `entity_id` (high cardinality, immutable)
3. [ ] Design Routing: `Shard_Index = Hash(entity_id) % Total_Shards`
4. [ ] Plan Migration: Zero-downtime cutover

---

### JTBD-04: Persistence Guarantee

| Field | Value |
|-------|-------|
| **Situation** | Risk of node failure |
| **Pattern** | Streaming replication with automated failover |
| **Metric** | RPO=0 (Zero Data Loss) |
| **Superpower** | Scalability Planning |
| **Target Views** | Process, Physical |

**Deliverables**:
- [ ] Primary-Replica topology per shard
- [ ] Patroni/etcd consensus layer
- [ ] Failover <30 seconds
- [ ] WAL streaming with synchronous commit option

---

## Custom Job Template

### JTBD-{{ ID }}: {{ Title }}

| Field | Value |
|-------|-------|
| **Situation** | {{ context }} |
| **Pattern** | {{ architectural_pattern }} |
| **Metric** | {{ measurable_outcome }} |
| **Superpower** | Writing-Plans / Sequential-Thinking / Scalability Planning |
| **Target Views** | Logical / Process / Development / Physical / Scenarios |

**Deliverables**:
- [ ] {{ deliverable_1 }}
- [ ] {{ deliverable_2 }}

---

## Superpower-to-JTBD Mapping

| Superpower | Best For | Example Jobs |
|------------|----------|--------------|
| **Writing-Plans** | Decomposition, structure | JTBD-01 (Stack Decomposition) |
| **Sequential-Thinking** | Multi-step dependencies | JTBD-03 (Sharding Strategy) |
| **Scalability Planning** | Growth, redundancy | JTBD-02, JTBD-04 (Scaling, HA) |

---

## Verification Checklist

Before plan approval, verify:

- [ ] All 4 core JTBDs addressed
- [ ] Each JTBD maps to ≥1 superpower
- [ ] Target views specified for each job
- [ ] Metrics are quantifiable
- [ ] Deliverables have verification steps
