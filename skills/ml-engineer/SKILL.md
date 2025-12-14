---
name: ml-engineer
description: Implement agentic ML pipelines using H2O AutoML, Mage orchestration, and MOJO deployment following the 8-step JTBD workflow.
version: 2.0.0
tech_stack:
  - Python 3.11+
  - H2O.ai AutoML
  - Mage (Orchestration)
  - MOJO artifacts
  - Docker
  - PostgreSQL
triggers:
  - "ML model"
  - "machine learning"
  - "H2O"
  - "AutoML"
  - "MOJO"
  - "model training"
  - "model serving"
  - "prediction"
  - "MLOps"
  - "agentic ML"
---

# ML Engineer Agent - JTBD Framework

## Role
The architect of autonomous ML systems for the Agentic ML Platform.

## Mandate
Design and deploy self-driving ML pipelines using the 8-step Jobs-to-be-Done (JTBD) framework, leveraging Mage for orchestration and H2O for distributed AutoML training.

---

## Agentic Patterns

| Pattern | Implementation |
|---------|----------------|
| **Planning** | `global_variables.yaml` - Dynamic configuration based on problem type |
| **Tool Use** | Mage orchestrates H2O cluster as external compute engine |
| **Reflection** | Sensors validate data quality; Monitor compares against thresholds |
| **Self-Correction** | Feedback loop triggers retraining with modified parameters |

---

## 8-Step JTBD Workflow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 1.DEFINE│───▶│ 2.LOCATE│───▶│3.PREPARE│───▶│4.CONFIRM│
└─────────┘    └─────────┘    └─────────┘    └────┬────┘
                                                   │
                                                   ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│8.CONCLUDE│◀──│7.MODIFY │◀──│6.MONITOR│◀──│5.EXECUTE│
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### Step 1: Define (Planning)
Establish problem scope, metrics, and constraints.
- **File**: `global_variables.yaml`
- **Actions**: Set `target_column`, `primary_metric`, `performance_threshold`

### Step 2: Locate (Data Ingestion)
Retrieve training data from Feature Store.
- **File**: `data_loaders/load_training_data.py`
- **Actions**: Parametric SQL, incremental extraction, zero-copy export

### Step 3: Prepare (Transformation)
Convert to H2OFrame with feature engineering.
- **File**: `transformers/prepare_h2o_frame.py`
- **Actions**: H2O init, Word2Vec for text, missing value imputation

### Step 4: Confirm (Validation)
Validate data quality before training.
- **File**: `sensors/validate_data_quality.py`
- **Actions**: Row count, null checks, drift detection

### Step 5: Execute (Training)
Run H2O AutoML.
- **File**: `custom/train_automl.py`
- **Actions**: Algorithm selection, cross-validation, leaderboard generation

### Step 6: Monitor (Evaluation)
Assess results against goals.
- **File**: `custom/evaluate_leaderboard.py`
- **Actions**: Threshold comparison, baseline check, SHAP generation

### Step 7: Modify (Feedback)
Self-correct based on monitoring.
- **File**: `custom/feedback_loop.py`
- **Actions**: Retry with modified params, escalate if max attempts exceeded

### Step 8: Conclude (Deployment)
Export MOJO and deploy to serving.
- **File**: `data_exporters/deploy_mojo.py`
- **Actions**: MOJO export, versioning, symlink update, container trigger

---

## Infrastructure

### Docker Stack
```bash
docker-compose -f assets/docker-compose.mlops.yml up -d
```

| Service | Purpose | Port |
|---------|---------|------|
| `mage-ai` | Orchestrator (Brain) | 6789 |
| `h2o-ai` | Compute Engine (Muscle) | 54321 |
| `postgres` | State Manager (Memory) | 5432 |
| `model-serving` | Production Endpoint | 8080 |

### Zero-Copy Data Flow
```
Mage → /data/exchange/train.csv → H2O imports directly
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `validate_mojo.py` | Validate MOJO artifact structure |
| `mojo_deployer.py` | CLI for MOJO deployment with versioning/rollback |

### Usage
```bash
# Deploy MOJO
python scripts/mojo_deployer.py deploy --mojo-path /models/model.mojo

# List versions
python scripts/mojo_deployer.py list-versions

# Rollback
python scripts/mojo_deployer.py rollback --version 20240115_120000
```

---

## Assets

| Asset | Purpose |
|-------|---------|
| `docker-compose.mlops.yml` | MLOps infrastructure stack |
| `mage_pipeline/` | Complete 8-step JTBD pipeline |
| `serving/Dockerfile` | MOJO serving container |
| `h2o_training_template.py` | Legacy training template |
| `model_card_template.md` | Model documentation template |

---

## Quick Start

```bash
# 1. Start infrastructure
cd skills/ml-engineer/assets
docker-compose -f docker-compose.mlops.yml up -d

# 2. Open Mage UI
open http://localhost:6789

# 3. Run pipeline
# Pipeline executes: Locate → Prepare → Confirm → Execute → Monitor → Modify → Conclude
```

---

## Platform Context

This agent operates within the **Machine Learning Layer**:
- **Orchestrator**: Mage controls pipeline flow
- **Compute**: H2O provides distributed AutoML
- **Serving**: MOJO enables low-latency inference
