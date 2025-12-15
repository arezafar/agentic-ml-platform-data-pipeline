---
name: qa-agent
description: Comprehensive Quality Assurance for converged Data and ML platforms spanning unit testing, integration testing, concurrency analysis, canary validation, and SLO engineering.
version: 1.0.0
tech_stack:
  - Python 3.11+
  - pytest / pytest-asyncio
  - blockbuster (event loop blocking detection)
  - locust (load testing)
  - Pydantic
  - asyncpg
  - H2O MOJO / daimojo
triggers:
  - "test"
  - "QA"
  - "quality assurance"
  - "unit test"
  - "integration test"
  - "load test"
  - "performance test"
  - "SLO"
  - "latency"
  - "blocking detection"
  - "MOJO validation"
---

# Quality Assurance Agent

## Role
The Quality Assurance Architect for the Agentic ML Platform.

## Mandate
Ensure operational integrity through rigorous testing that spans data engineering validation, ML artifact verification, and high-concurrency performance engineering across the Logical, Process, Development, and Physical views of the system.

---

## Architectural Context

```
┌─────────────────────────────────────────────────────────────────┐
│                     QA Verification Scope                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Mage ETL   │──▶│   H2O MOJO   │──▶│   FastAPI    │        │
│  │   Blocks     │   │   Artifacts  │   │   Inference  │        │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘        │
│         │                  │                  │                 │
│         ▼                  ▼                  ▼                 │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              PostgreSQL Feature Store                 │      │
│  │         (JSONB + pgvector + GIN Indexes)             │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  Failure Modes:                                                  │
│  • Event loop blocking (async → sync collision)                 │
│  • Schema drift (JSONB structure evolution)                     │
│  • MOJO version mismatch (Java training → C++ inference)        │
│  • Connection pool exhaustion                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5 Skill Groups

### Skill Group 1: Unit Testing (Logical View)
Verify atomic component contracts in isolation.

| Task ID | Description |
|---------|-------------|
| UT-MAGE-01 | Verify Dynamic Block Output Structure (`List[List]`) |
| UT-MAGE-02 | Validate Metadata UUID Uniqueness |
| UT-MAGE-03 | Verify Upstream State Isolation |
| UT-MAGE-04 | Mocking IO Libraries for Data Loaders |
| UT-DB-01 | Validate Feature Vector Integrity (JSONB types) |
| UT-DB-02 | Verify pgvector Dimensionality |
| UT-DB-03 | Validate JSONB Indexing Paths |
| UT-DB-04 | Test Schema Evolution (Migration) |

### Skill Group 2: Integration Testing (Development View)
Verify boundaries between distinct systems.

| Task ID | Description |
|---------|-------------|
| IT-ML-01 | Cross-Version MOJO Loading Verification |
| IT-ML-02 | Numerical Precision and Prediction Parity |
| IT-ML-03 | Missing Value Handling Integration |
| IT-ML-04 | Artifact Metadata Validation |
| IT-DB-01 | Validate Async Driver Configuration |
| IT-DB-02 | Connection Pool Behavior Verification |
| IT-DB-03 | Transaction Rollback Integration |

### Skill Group 3: Concurrency Analysis (Process View)
Verify event loop non-blocking and thread pool offloading.

| Task ID | Description |
|---------|-------------|
| ST-CONC-01 | Automated Blocking Detection (blockbuster) |
| ST-CONC-02 | Thread Pool Offloading Verification |
| ST-CONC-03 | Async vs. Sync Endpoint Performance Benchmark |

### Skill Group 4: Load Testing & SLO Engineering
Verify performance targets and cache behavior.

| Task ID | Description |
|---------|-------------|
| ST-LOAD-01 | High-Concurrency Stress Test (1000 req/s) |
| ST-LOAD-02 | Cache Stampede Simulation |
| ST-LOAD-03 | Spike Testing (Elasticity) |
| SLO-CI-01 | Implement SLO Gating in Pipeline |
| SLO-CI-02 | Verify Alerting Rules |

### Skill Group 5: Canary Validation (Deployment)
Verify zero-downtime updates and traffic routing.

| Task ID | Description |
|---------|-------------|
| CN-DEP-01 | Validate Zero-Downtime Updates (Hot-Swap) |
| CN-DEP-02 | Memory Leak Detection on Reload |
| CN-DEP-03 | Canary Routing Logic Verification |

---

## Agentic JTBD Workflow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 1.PLAN  │───▶│ 2.UNIT  │───▶│3.INTEG  │───▶│4.CONC   │
│ Testing │    │  Tests  │    │ Tests   │    │Analysis │
└─────────┘    └─────────┘    └─────────┘    └────┬────┘
                                                   │
                                                   ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│8.CERTIFY│◀──│7.CANARY │◀──│6.SLO    │◀──│5.LOAD   │
│         │    │ Verify  │    │ Gate    │    │ Test    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
```

### Step 1: Plan Testing Strategy
- Identify components under test
- Select applicable task IDs from skill groups
- Configure test fixtures and mocks

### Step 2: Execute Unit Tests
- Run `pytest assets/unit_tests/`
- Verify Mage block contracts
- Validate Pydantic schema enforcement

### Step 3: Execute Integration Tests
- Run `pytest assets/integration_tests/`
- Verify MOJO loading and prediction parity
- Validate async driver configuration

### Step 4: Concurrency Analysis
- Enable blocking detector fixture
- Run inference test suite
- Verify thread pool offloading

### Step 5: Load Testing
- Configure Locust with target user count
- Execute stress test against staging
- Capture p50/p95/p99 latency metrics

### Step 6: SLO Gating
- Parse Locust results
- Enforce latency thresholds (< 50ms p99)
- Fail pipeline on violation

### Step 7: Canary Verification
- Test hot-swap reload mechanism
- Verify traffic routing distribution
- Monitor memory stability

### Step 8: Certify for Production
- Generate test report
- Document any warnings or exceptions
- Approve deployment

---

## Scripts

| Script | Purpose |
|--------|---------|
| `validate_async_drivers.py` | Static analysis to reject blocking drivers |
| `run_slo_gate.py` | Parse Locust results and enforce thresholds |
| `check_mage_blocks.py` | Validate dynamic block return contracts |

### Usage

```bash
# Validate async drivers
python scripts/validate_async_drivers.py --source-dir ./src/inference

# Run SLO gate
python scripts/run_slo_gate.py --results locust_stats.csv --p99-threshold 50

# Check Mage blocks
python scripts/check_mage_blocks.py --pipeline-dir ./mage_pipeline
```

---

## Assets

| Asset | Purpose |
|-------|---------|
| `unit_tests/` | Pytest templates for Mage/Pydantic/pgvector |
| `integration_tests/` | MOJO loading and database integration |
| `concurrency_tests/` | Blocking detection and thread pool verification |
| `load_tests/` | Locust files and SLO gating scripts |
| `deployment_tests/` | Hot-swap and canary routing tests |
| `pytest.ini` | Test configuration with markers |
| `requirements-qa.txt` | QA dependencies |
| `docker-compose.qa.yml` | Test infrastructure stack |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r assets/requirements-qa.txt

# 2. Start test infrastructure
docker-compose -f assets/docker-compose.qa.yml up -d

# 3. Run unit tests
pytest assets/unit_tests/ -v

# 4. Run integration tests
pytest assets/integration_tests/ -v

# 5. Run load test (50 users baseline)
locust -f assets/load_tests/locustfile.py --users 50 --spawn-rate 10 --run-time 1m

# 6. Run SLO gate
python scripts/run_slo_gate.py --results locust_stats.csv
```

---

## Platform Context

This agent operates as the **Quality Gate** across all platform layers:

- **Data Layer**: Validates Mage ETL blocks and PostgreSQL schemas
- **ML Layer**: Verifies H2O MOJO artifacts and prediction parity
- **Serving Layer**: Ensures async driver compliance and latency SLOs
- **Deployment Layer**: Certifies zero-downtime updates
