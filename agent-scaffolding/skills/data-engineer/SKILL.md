---
name: data-engineer
description: Agentic Data Engineering with autonomous ETL/ELT, schema evolution, anomaly detection, and compliance governance using Mage OSS and H2O.
version: 2.0.0
superpower: writing-plans, subagent-driven-development
tech_stack:
  - Python 3.11+
  - Mage OSS
  - H2O.ai
  - PostgreSQL 15+
  - Docker
  - Airflow (optional)
  - dbt (optional)
triggers:
  - "pipeline"
  - "ETL"
  - "ELT"
  - "data pipeline"
  - "Mage"
  - "ingestion"
  - "transformation"
---

# Data Engineer Agent

## Role
The **Agent Architect** for the Agentic ML Platform—defining goals and guardrails while autonomous agents execute with statistical rigor and deterministic validation.

## Mandate
Build self-healing, self-optimizing data infrastructures that adapt to schema changes, detect anomalies, and enforce compliance without human intervention.

---

## Core Agent Skills (Filesystem-Based)

### etl-pipeline-architect
Modular, persistent capability for pipeline creation and validation.

| Component | Files | Purpose |
|-----------|-------|---------|
| **Validation Scripts** | `validate_dag.py` | Parse Python files for valid Airflow DAG objects |
| | `check_cyclic_dependencies.py` | Detect circular task dependencies |
| | `validate_pipeline.py` | Validate Mage pipeline structure |
| **Templates** | `airflow_dag_template.py` | Boilerplate with retries, SLA, logging |
| | `dbt_model_template.sql` | Standardized SQL transformations |
| | `pipeline_config_schema.json` | JSON schema for pipeline configs |
| | `mage_pipeline_template.py` | Mage pipeline boilerplate |

**Workflow:**
1. Analyze source/sink requirements
2. Select orchestration pattern (Mage or Airflow)
3. Scaffold DAG from template
4. Implement dbt transformations
5. Run validation scripts

---

## JTBD Domain 1: Intelligent Ingestion (The Gatekeeper)

> **Job:** Guarantee availability of raw data regardless of source volatility.

### Autonomous Schema Evolution
**Script:** `schema_sentinel.py`

- Detect upstream schema changes
- Calculate "Schema Delta" (new columns, type changes, removals)
- Execute `ALTER TABLE` or route to quarantine

```bash
python scripts/schema_sentinel.py --source batch.json --target schema.json --ddl
```

### Adaptive Protocol Negotiation
**Script:** `adaptive_protocol.py` (planned)

- Monitor API latency and error rates
- Dynamically adjust concurrency/backoff
- Store optimal parameters in long-term memory

---

## JTBD Domain 2: Autonomous Transformation (The Alchemist)

> **Job:** Ensure data is semantically correct and optimized for analytics.

### Semantic Anomaly Detection
**Script:** `anomaly_detector.py`

- H2O Isolation Forest for unsupervised detection
- "Circuit Breaker" pattern for quarantine routing
- Configurable thresholds

```bash
python scripts/anomaly_detector.py score --data batch.json --threshold 0.7 --circuit-breaker
```

### Context-Aware Imputation
**Script:** `smart_imputer.py` (planned)

- H2O GLRM/GBM for predictive filling
- Correlation-based value prediction
- Variance preservation

### Automated Feature Engineering
- Run H2O AutoML to identify feature interactions
- Generate permanent transformation blocks

---

## JTBD Domain 3: Resilient Orchestration (The Conductor)

> **Job:** Minimize MTTR and maximize resource efficiency.

### Self-Healing Dependencies
- Mage SensorBlocks with dynamic timeout
- Business criticality-based escalation
- Automatic retry with exponential backoff

### Automated Root Cause Analysis
**Script:** `rca_agent.py` (planned)

- Capture stderr and stack traces
- Synthesize context (Git diffs, Docker stats)
- LLM-powered fix recommendations

---

## JTBD Domain 4: Observability & Governance (The Auditor)

> **Job:** Maintain transparent, auditable, compliant data environment.

### Compliance Guardrails
**Script:** `compliance_guardian.py`

- PII detection (SSN, credit cards, emails)
- Policy-as-Code enforcement
- Pre-write validation with block/quarantine

```bash
python scripts/compliance_guardian.py scan --data batch.json --strict
```

### Reflection Loop & Documentation
- Auto-generate documentation on schema changes
- Commit docs to Git synchronously with code

---

## Meta-Skills (Control Plane)

### superpowers:writing-plans
Decomposes tasks into 2-5 minute atomic units with explicit verification steps.

### superpowers:subagent-driven-development
Enables context isolation—each task spawns a fresh subagent loading only relevant skills.

---

## Technical Prerequisites

### Docker Configuration
**Template:** `docker-compose.agentic.yml`

```yaml
services:
  mage:        # Cognitive Control Plane
  h2o:         # Analytical Muscle  
  postgres:    # Persistence Layer
```

**Key Patterns:**
- **Zero-Copy Transfer:** Shared volume (`/data_lake`) between Mage and H2O
- **Network Isolation:** User-defined bridge with service discovery
- **Resource Limits:** Memory caps prevent OOM kills

### Connection Protocol
```python
# In Mage blocks, connect to H2O via service name
import h2o
h2o.init(url="http://h2o-compute:54321")
```

---

## Scripts Reference

| Script | JTBD Domain | Purpose |
|--------|-------------|---------|
| `validate_pipeline.py` | Core | Validate Mage pipeline structure |
| `validate_dag.py` | Core | Validate Airflow DAG structure |
| `check_cyclic_dependencies.py` | Core | Detect circular dependencies |
| `schema_sentinel.py` | Ingestion | Autonomous schema evolution |
| `anomaly_detector.py` | Transformation | H2O-based anomaly detection |
| `compliance_guardian.py` | Governance | PII detection & policy enforcement |

---

## Assets Reference

| Asset | Purpose |
|-------|---------|
| `airflow_dag_template.py` | Production Airflow DAG boilerplate |
| `dbt_model_template.sql` | dbt SQL transformation template |
| `pipeline_config_schema.json` | JSON Schema for pipeline configs |
| `mage_pipeline_template.py` | Mage pipeline template |
| `mage_block_template.py` | Mage block templates |
| `docker-compose.agentic.yml` | Full agentic Docker stack |

---

## Platform Context

This agent operates across all platform layers:

| Layer | Role |
|-------|------|
| **Persistence** | PostgreSQL with JSONB for raw data store |
| **Orchestration** | Mage OSS as cognitive control plane |
| **ML** | H2O for profiling, anomaly detection, imputation |
| **Serving** | Feature delivery to FastAPI endpoints |
