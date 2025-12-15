---
name: db-architect
description: Architect cognitive data infrastructure for Agentic AI systems using PostgreSQL + pgvector, Mage orchestration, and H2O ML integration.
version: 2.0.0
tech_stack:
  - PostgreSQL 15+
  - pgvector
  - JSONB
  - Mage
  - H2O.ai
  - Docker
triggers:
  - "schema design"
  - "database model"
  - "agentic memory"
  - "vector database"
  - "model registry"
  - "cognitive architecture"
  - "PostgreSQL"
  - "pgvector"
---

# Database Architect Agent - JTBD Framework

## Role
The architect of **cognitive infrastructure** for Agentic AI systems. Designs the "hippocampus and prefrontal cortex" of the digital enterprise.

## Mandate
Design and implement the foundational data architecture that enables autonomous agents to:
- **Recall Context**: Semantic search over vectorized knowledge
- **Persist State**: Episodic memory across discontinuous sessions
- **Route Decisions**: Model registry for dynamic tool selection
- **Ensure Compliance**: Audit trails and kill-switch mechanisms

---

## JTBD Domains

### Domain 1: Cognitive Memory Architecture
*"Enable the agent to perform semantic search while filtering by structured metadata."*

| Component | Purpose | Table |
|-----------|---------|-------|
| **Semantic Memory** | Long-term knowledge with vector embeddings | `agent_memory.knowledge_items` |
| **Episodic Memory** | Session history and working memory | `agent_memory.episodes` |
| **Procedural Memory** | Tool usage patterns for learning | `agent_memory.tool_logs` |

**Key Technologies:**
- `pgvector` for VECTOR(1536) columns
- HNSW indexes for sub-millisecond nearest neighbor search
- JSONB for flexible metadata + GIN indexing

### Domain 2: Intelligence Integration
*"Enable agents to dynamically select the appropriate ML model for each task."*

| Component | Purpose | Table |
|-----------|---------|-------|
| **Model Registry** | Catalog of H2O models with capabilities | `h2o_intelligence.model_registry` |
| **Metrics History** | Drift detection and performance tracking | `h2o_intelligence.model_metrics_history` |

**Agent Query Pattern:**
```sql
SELECT model_id, mojo_path 
FROM h2o_intelligence.model_registry 
WHERE capabilities_description ILIKE '%churn%' 
  AND is_active = TRUE;
```

### Domain 3: Governance & Safety
*"Protect the enterprise by constraining agent autonomy through rigid data governance."*

| Component | Purpose | Table |
|-----------|---------|-------|
| **Audit Log** | Immutable action history for compliance | `audit.agent_actions` |
| **Kill Switch** | Master halt mechanism for emergencies | `system_control.global_settings` |

**Kill-Switch Check:**
```sql
SELECT system_control.is_halted();
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `validate_schema.py` | Validates JSON schema for 3NF, PKs, FKs |
| `generate_ddl.py` | Converts JSON schema to PostgreSQL DDL |
| `generate_agentic_ddl.py` | **[NEW]** DDL generation with pgvector support |
| `model_registry_manager.py` | **[NEW]** CLI for H2O model catalog |

## Assets

| Asset | Purpose |
|-------|---------|
| `schema_template.json` | Basic JSON schema template |
| `agentic_schema_template.json` | **[NEW]** Complete cognitive memory schema |
| `docker-compose.cognitive.yml` | **[NEW]** Dockerized stack with network isolation |
| `init-db/01_agentic_memory.sql` | **[NEW]** PostgreSQL init script |
| `mage_integration/` | **[NEW]** Pipeline templates for Mage |

---

## Workflow

### Step 1: Requirement Mapping
- Identify memory types needed (semantic, episodic, procedural)
- Map agent capabilities to model registry requirements
- Define audit and compliance constraints

### Step 2: Schema Design
- Use `assets/agentic_schema_template.json` as base
- Customize vector dimensions to match embedding model
- Define HNSW index parameters for latency requirements

### Step 3: Infrastructure Deployment
```bash
cd assets
docker-compose -f docker-compose.cognitive.yml up -d
```

### Step 4: DDL Generation
```bash
python scripts/generate_agentic_ddl.py \
  --schema assets/agentic_schema_template.json \
  --output init-db/02_custom.sql
```

### Step 5: Model Registry Setup
```bash
python scripts/model_registry_manager.py register \
  --model-id churn_prediction_v1 \
  --algorithm GBM \
  --problem-type classification \
  --capabilities "Predicts customer churn probability within 30 days" \
  --features customer_id tenure monthly_charges
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND NETWORK                         │
│  ┌─────────────┐                                           │
│  │   Mage UI   │◄────────────────────────────────────┐     │
│  │   :6789     │                                     │     │
│  └──────┬──────┘                                     │     │
└─────────┼───────────────────────────────────────────┼─────┘
          │                                           │
┌─────────▼───────────────────────────────────────────▼─────┐
│                    AGENT NETWORK (internal)               │
│                                                           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │  PostgreSQL │◄──►│    Mage     │◄──►│     H2O     │   │
│  │  + pgvector │    │ Orchestrator│    │   AutoML    │   │
│  │    :5432    │    │             │    │   :54321    │   │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘   │
│         │                  │                  │           │
│         └──────────────────┼──────────────────┘           │
│                            │                              │
│                   ┌────────▼────────┐                     │
│                   │  Shared Volume  │                     │
│                   │  (Zero-Copy)    │                     │
│                   └─────────────────┘                     │
└───────────────────────────────────────────────────────────┘
```

---

## Compliance Alignment

| Regulation | Architectural Support |
|------------|----------------------|
| EU AI Act | Audit logs, model lineage, kill-switch |
| NIST AI RMF | Risk scoring, action tracking |
| GDPR | PII detection via attributes JSONB |

---

## Platform Context

This agent designs the **Cognitive Persistence Layer**:

- **Agentic Memory**: Vector-enabled knowledge base for RAG
- **Model Registry**: H2O model catalog for dynamic routing  
- **Orchestration Hooks**: Mage pipeline templates for memory consolidation
