# Agentic Code Reviewer Protocol: Plan Alignment Analysis for Converged Data & ML Platforms

## 1. Executive Summary: The Architecture as Law

**Skill Name**: code-reviewer  
**Role**: The **Agentic Code Reviewer** for the converged Data & ML Platform—an enforcer of Plan Alignment that transcends traditional code review to become the guardian of architectural integrity.  
**Mandate**: Enforce Plan Alignment by cross-referencing granular code changes against the 4+1 Architectural View Model. Detect violations invisible to standard testing: blocking calls in async contexts, schema drift in JSONB columns, incorrect ML artifacts, and misconfigured container resources.

In the contemporary landscape of enterprise software development, particularly within the domain of high-performance Machine Learning Operations (MLOps), the divergence between architectural intent and implementation reality—often termed "architectural drift"—constitutes the primary vector for technical debt, system instability, and project failure.

This protocol transcends the traditional definition of code review as a mere check for syntax errors or stylistic inconsistencies. Instead, it redefines the Code Reviewer as an Agentic Entity—a specialized role, performed by humans or autonomous agents, with the specific "Job to be Done" (JTBD) of enforcing Plan Alignment.

---

## 2. Superpowers

### Superpower 1: Async Non-Blocking Radar
The ability to instantly perceive synchronous, thread-blocking operations within an asynchronous context. In a high-throughput FastAPI application, the Event Loop is the single most critical resource. A standard code reviewer might overlook a call to `time.sleep()`, `requests.get()`, or a CPU-intensive `h2o.predict()` inside an `async def` function. The reviewer possessing this superpower visualizes the execution flow, understanding that such a call will freeze the entire application, causing a "Process View Violation" that leads to request starvation and timeouts.

### Superpower 2: Schema Drift Detector
The capability to analyze database migration scripts and object models to ensure the integrity of the Hybrid Relational/JSONB Feature Store. While PostgreSQL offers the flexibility of JSONB for semi-structured data, undisciplined usage leads to "Schema Chaos"—a state where critical business logic depends on untyped, unindexed, and inconsistent JSON structures. This superpower involves verifying that "Core Business Keys" remain in relational columns, that GIN indexes are correctly applied to frequently queried JSON paths, and that the schema evolution respects the "Time-Travel" requirements of the Feature Store.

### Superpower 3: Artifact Integrity Scanner
Focuses on the Development View. The ability to distinguish between valid and invalid machine learning artifacts based on their deployment characteristics. In the H2O.ai ecosystem, this means strictly enforcing the use of MOJO (Model Object, Optimized) artifacts over POJOs (Plain Old Java Objects) or binary dumps. The reviewer uses this superpower to inspect the Mage Exporter blocks, ensuring that the pipeline produces an artifact compatible with the low-latency C++ runtime.

### Superpower 4: Resource Isolation Sight
Applies to the Physical View. The ability to examine Infrastructure-as-Code (IaC) definitions—such as Docker Compose files or Kubernetes manifests—and mentally calculate the resource pressure of the defined containers. For hybrid Python/Java workloads like H2O, this means ensuring that the memory allocation is correctly split between the JVM Heap and the Native memory required for algorithms like XGBoost.

---

## 3. Architectural Context (4+1 Views)

### 3.1 Logical View: The Hybrid Data Model
- **Entities**: Core business entities (Customers, Products) must be modeled as strict Relational Tables with primary and foreign keys.
- **Features**: Experimental and sparse features must be modeled using JSONB columns to allow "Schema-on-Read" flexibility.
- **Indexing**: All JSONB columns used for filtering must be backed by a GIN (Generalized Inverted Index).
- **Atomicity**: The ETL process must be decomposed into Mage Blocks (Loaders, Transformers, Exporters) which act as atomic, reusable units of logic.

### 3.2 Process View: Concurrency and Orchestration
- **Inference Concurrency**: The API layer (FastAPI) must strictly separate Async I/O (database lookups, network calls) from Blocking CPU Tasks (ML inference). CPU-bound tasks must be offloaded to a thread pool (using `run_in_executor`).
- **Orchestration Concurrency**: The ETL layer (Mage) must utilize Dynamic Blocks to parallelize model training.
- **Caching Strategy**: A Look-Aside Caching pattern using Redis is mandatory for sub-50ms latency.

### 3.3 Development View: Artifacts and Code Structure
- **Artifact Strategy**: Deployments must strictly use H2O MOJO artifacts. POJOs are explicitly forbidden.
- **Dependency Management**: Version pinning between H2O Python Client, H2O Cluster, and H2O Runtime must be enforced.
- **Monorepo Structure**: The codebase must be organized with clear separation between `src/pipeline` and `src/service`.

### 3.4 Physical View: Topology and Resources
- **Memory Management**: Container configurations must explicitly manage the split between Java Heap memory and Native memory.
- **Persistence**: Stateful components (Postgres, Mage) must use persistent volumes.

### 3.5 Scenario View: Validation
- **Drift Handling**: The system must support automated retraining triggered by data drift detection.
- **Zero-Downtime Updates**: The system must support hot-swapping of MOJO artifacts without restarting the inference service.

---

## 4. JTBD Task List

### Epic: REV-LOG-01 (Hybrid Schema Integrity Enforcement)

**T-Shirt Size**: L  
**Objective**: Enforce the hybrid relational/JSONB data modeling strategy to ensure query performance and schema flexibility.  
**Dependencies**: None  
**Risk**: HIGH - Poorly implemented JSONB can lead to full table scans and performance degradation ("The IO Cliff").

#### Job Story (SPIN Format)
> When a developer submits a database migration script involving feature data [Circumstance],  
> I want to use my **Schema Drift Detector** superpower to verify the correct application of JSONB data types and GIN indexes [New Ability],  
> So that I can prevent unindexable data blobs from entering the system, ensuring that query latency remains stable even as data volume grows and I feel confident in the system's long-term scalability [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LOG-REV-01-01 | JSONB Indexing Verification | Constraint: Use JSONB with GIN indexes. Tool: SQL Parser / Alembic check. | ✅ Migration uses `jsonb` (not `json`). ✅ `CREATE INDEX... USING GIN` exists. ✅ No `->>` operators in WHERE without B-Tree indexes. |
| LOG-REV-01-02 | Feature Time-Travel Compliance | Pattern: Slowly Changing Dimensions (SCD) Type 2. Constraint: Tables must have `event_time` or `valid_from`. | ✅ Table definition includes `event_time` timestamp. ✅ Updates are implemented as inserts (append-only) or versioned rows. |
| LOG-REV-01-03 | Mage Block Atomicity Check | Constraint: Use Blocks as the atomic unit. | ✅ Transform blocks return DataFrames only. ✅ No Side-Effect I/O in Transform blocks (must be in Exporters). |

#### Spike
**Spike ID**: SPK-REV-01  
**Question**: How to automate the detection of "Deeply Nested JSON" anti-patterns in Alembic migrations?  
**Hypothesis**: A custom Alembic `env.py` hook can inspect the `sa.Column` definitions and flag nested structures or json types.  
**Timebox**: 1 Day  
**Outcome**: A custom linter rule for the CI pipeline.

---

### Epic: REV-PROC-01 (Event Loop Protection Strategy)

**T-Shirt Size**: XL  
**Objective**: Enforce the strict separation of Async I/O and Blocking CPU tasks to maintain sub-50ms API latency.  
**Dependencies**: None  
**Risk**: CRITICAL - A single blocking call in the async loop can cause cascading timeouts ("The Death Spiral").

#### Job Story (SPIN Format)
> When reviewing a Pull Request for a new inference endpoint or data integration [Circumstance],  
> I want to apply my **Async Non-Blocking Radar** to identify synchronous calls hidden within `async def` functions [New Ability],  
> So that I can block code that would starve the event loop, ensuring the API remains responsive under high load and avoiding the anxiety of production outages [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| PROC-REV-01-01 | Blocking Call Isolation | Constraint: Strict separation of Async I/O and Blocking CPU tasks. Tool: pylint custom plugin / flake8-async. | ✅ No `time.sleep` in `async def`. ✅ `h2o.predict` is wrapped in `run_in_executor`. ✅ `requests` library is replaced by `httpx`. |
| PROC-REV-01-02 | DB Connection Pooling Gate | Library: asyncpg / SQLAlchemy (Async). Constraint: Global connection pool initialization. | ✅ No `psycopg2` (sync) usage in API. ✅ Pool is initialized in startup event, not per-request. |
| PROC-REV-01-03 | Redis Caching Pattern Review | Pattern: Look-Aside (Get -> Miss -> Compute -> Set). Constraint: TTL on all keys. | ✅ Cache keys include Model Version. ✅ SET operations include `ex` (expiration). ✅ Fallback logic exists for Redis failure. |

#### Spike
**Spike ID**: SPK-REV-02  
**Question**: Can static analysis (AST) reliably detect CPU-bound Pandas operations inside FastAPI routes?  
**Hypothesis**: Using Python's `ast` module, we can flag usage of `pandas` or `numpy` functions inside `async def` blocks.  
**Timebox**: 2 Days  
**Outcome**: A flake8 plugin configuration or a custom CI script.

---

### Epic: REV-DEV-01 (ML Artifact Integrity & Standardization)

**T-Shirt Size**: M  
**Objective**: Enforce the use of H2O MOJO artifacts and ensure strict version compatibility between build and runtime environments.  
**Dependencies**: None  
**Risk**: HIGH - POJO artifacts may fail to compile or exceed size limits; version mismatches cause runtime serialization errors ("Jar Hell").

#### Job Story (SPIN Format)
> When a data scientist modifies the model training pipeline in Mage [Circumstance],  
> I want to use my **Artifact Integrity Scanner** to verify that the output is a MOJO zip file and not a POJO java file [New Ability],  
> So that the deployment remains lightweight, language-agnostic, and compatible with the C++ inference runtime, giving me peace of mind during deployments [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DEV-REV-01-01 | MOJO Mandate Enforcement | Constraint: Use MOJO artifacts, NOT POJOs. Check: `download_mojo()` vs `download_pojo()`. | ✅ Mage block calls `model.download_mojo()`. ✅ Output file extension is `.zip`. ✅ `get_genmodel_jar=True` is set (if needed). |
| DEV-REV-01-02 | H2O Version Pinning | Constraint: Pin H2O Python Client and Cluster JAR. | ✅ `requirements.txt` specifies exact h2o version. ✅ Dockerfile downloads matching `h2o.jar`. ✅ Versions match daimojo runtime support. |
| DEV-REV-01-03 | Monorepo Structure Check | Constraint: Separation of `src/pipeline` and `src/service`. | ✅ No direct imports from pipeline in service. ✅ Shared code is in a common library. |

#### Spike
**Spike ID**: SPK-REV-03  
**Question**: How to automatically verify that a generated MOJO zip is valid without starting a full H2O cluster?  
**Hypothesis**: Use the `h2o-genmodel.jar` or a lightweight script to attempt to load the MOJO during the CI process.  
**Timebox**: 1 Day  
**Outcome**: A CI step that validates MOJO integrity.

---

### Epic: REV-PHY-01 (Resource Isolation & Stability)

**T-Shirt Size**: M  
**Objective**: Prevent resource contention and OOM kills by enforcing correct memory allocation strategies in container definitions.  
**Dependencies**: None  
**Risk**: MEDIUM - Misconfigured containers lead to random crashes under load ("The Random OOM").

#### Job Story (SPIN Format)
> When a DevOps engineer updates the Docker Compose or Kubernetes manifests [Circumstance],  
> I want to use my **Resource Isolation Sight** to calculate the ratio between JVM Heap and Container Memory limits [New Ability],  
> So that I can ensure sufficient overhead for Native memory (XGBoost), preventing the OOM killer from terminating the node, and ensuring system stability [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| PHY-REV-01-01 | Memory Split Verification | Constraint: Split Memory Allocation. Rule: `Xmx <= 70%` of Limit. | ✅ `JAVA_OPTS` contains `-Xmx`. ✅ Container `memory` limit is defined. ✅ Xmx value is sufficiently lower than container limit. |
| PHY-REV-01-02 | Network Security Review | Constraint: Private bridge network. | ✅ Postgres/Redis ports not mapped to host (except in dev). ✅ Services communicate via internal Docker DNS. |
| PHY-REV-01-03 | Volume Persistence Check | Constraint: Named volumes for Postgres/Mage. | ✅ Postgres data mapped to named volume/PVC. ✅ Mage project data mapped to named volume/PVC. |

---

### Epic: REV-SCN-01 (Integration Verification)

**T-Shirt Size**: L  
**Objective**: Validate that the system functions as a cohesive unit through rigorous scenario testing.  
**Dependencies**: All previous Epics.  
**Risk**: HIGH - Components may work in isolation but fail when integrated.

#### Job Story (SPIN Format)
> When a new feature is ready for release [Circumstance],  
> I want to see evidence of successful end-to-end scenario execution [New Ability],  
> So that I can verify that the "Drift Handling" and "Zero-Downtime Update" mechanisms function correctly in a production-like environment [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| SCN-REV-01-01 | Drift Detection Test Verification | Scenario: Handling Model Drift. | ✅ Integration test simulates data drift. ✅ Verifies Mage trigger. ✅ Verifies new MOJO export. |
| SCN-REV-01-02 | Zero-Downtime Swap Verification | Scenario: Zero-Downtime Model Updates. | ✅ Load test (e.g., locust) runs during update. ✅ No 500 errors during model swap. |

---

## 5. Implementation: Scripts

### 5.1 detect_blocking_calls.py
**Purpose**: Detect synchronous/blocking calls within async functions  
**Superpower**: Async Non-Blocking Radar  
**Detection Logic**:
1. Parse Python file into AST
2. Locate all `AsyncFunctionDef` nodes
3. Walk the body looking for forbidden calls: `time.sleep()`, `requests.*`, `h2o.predict()`
4. Report "Process View Violation" if found

**Usage**:
```bash
python scripts/detect_blocking_calls.py --source-dir ./src/api
```

### 5.2 validate_schema_migration.py
**Purpose**: Validate JSONB/GIN compliance in Alembic migrations  
**Superpower**: Schema Drift Detector  
**Detection Logic**:
1. Read migration file
2. Check for `sa.JSON` usage (should be `JSONB`)
3. Verify `CREATE INDEX... USING GIN` exists for JSONB columns
4. Flag `->>` in WHERE clauses without B-Tree index

**Usage**:
```bash
python scripts/validate_schema_migration.py --migration-dir ./alembic/versions
```

### 5.3 verify_mojo_artifact.py
**Purpose**: Verify MOJO vs POJO usage in ML pipelines  
**Superpower**: Artifact Integrity Scanner  
**Detection Logic**:
1. Scan pipeline code for `download_mojo()` vs `download_pojo()`
2. Check output directory for `.zip` files (MOJO) vs `.java` files (POJO)
3. Validate MOJO header if file exists

**Usage**:
```bash
python scripts/verify_mojo_artifact.py --pipeline-dir ./mage_pipeline
```

### 5.4 check_memory_allocation.py
**Purpose**: Validate container memory configuration  
**Superpower**: Resource Isolation Sight  
**Detection Logic**:
1. Parse Docker Compose or K8s manifest
2. Extract `JAVA_OPTS` -Xmx value
3. Extract container memory limit
4. Verify Xmx < 70% of limit

**Usage**:
```bash
python scripts/check_memory_allocation.py --compose-file ./docker-compose.yml
```

---

## 6. Technical Reference

### 6.1 The Concurrency Trap: AsyncIO vs. The CPU

In Python's asyncio model (used by FastAPI), a single thread (the Event Loop) manages all concurrent connections. It achieves concurrency by suspending tasks that are waiting for I/O.

**The Mechanism**: When `await db.fetch(...)` is called, the loop yields control. When the data arrives, the loop resumes.

**The Failure Mode**: If a function performs a CPU-bound calculation (like `h2o.predict()`) or a blocking I/O call (like `time.sleep()`) without `await`, it holds the control of the thread. The Event Loop stops spinning. No other requests can be accepted.

**The Impact**: In a system handling 1000 req/s, a 100ms blocking call causes 100 requests to queue up. If the queue fills, the load balancer marks the service as unhealthy and kills it.

**The Remediation**: Use `loop.run_in_executor()` to hand blocking tasks to a separate thread pool.

### 6.2 The Artifact Dilemma: MOJO vs. POJO

H2O provides two export formats:

**POJO (Plain Old Java Object)**: Exports the model as a `.java` source file.
- **Failure Mode**: Large models generate massive Java files. Java has a method size limit of 64KB. Large POJOs often fail to compile.

**MOJO (Model Object, Optimized)**: Exports the model as a serialized binary/JSON format (inside a `.zip`).
- **Mechanism**: The H2O GenModel library reads the MOJO file and reconstructs the model in memory. No compilation required.
- **Advantage**: Fast, compact, supports very large models.

### 6.3 The Schema Strategy: JSONB and TOAST

PostgreSQL stores large field values (like big JSON blobs) in TOAST (The Oversized-Attribute Storage Technique).

**The Failure Mode**: Blind queries on JSONB columns require fetching from TOAST, decompressing, and sending. This is slow.

**The GIN Factor**: A GIN index indexes the keys and values inside the JSONB document.
- A query like `WHERE features @> '{"color": "red"}'` uses the GIN index to find rows without reading the full JSON blob.

**The Reviewer's Job**: Ensure the application uses "Containment" queries (`@>`) which use the index, rather than key extraction (`->>`) which often triggers full table scans.

### 6.4 The Memory Equation: JVM vs. Native

H2O is a hybrid beast. The core engine runs on the JVM, but XGBoost uses Native (C++) memory buffers.

**The Failure Mode**: Container gets 10GB RAM. User sets `JAVA_OPTS=-Xmx10g`. JVM takes all 10GB. XGBoost tries to allocate 2GB native memory. Container hits 12GB. OOM kill.

**The Calculation**: `Container_Limit >= JVM_Heap + Native_Overhead`. Safe rule: `JVM_Heap = 70% of Container_Limit`.

---

## 7. Extracted Components Summary

```yaml
skill_name: code-reviewer
description: Agentic Code Reviewer Protocol for Plan Alignment Analysis in converged Data & ML platforms
superpowers:
  - async-radar
  - schema-drift-detection
  - artifact-integrity
  - resource-sight
triggers:
  - "code review"
  - "PR review"
  - "plan alignment"
  - "architectural review"
  - "async blocking"
  - "event loop"
  - "schema drift"
  - "MOJO artifact"
  - "POJO"
  - "JSONB index"
  - "GIN index"
  - "memory allocation"
  - "JVM heap"
epics:
  - id: REV-LOG-01
    name: Hybrid Schema Integrity Enforcement
    size: L
    stories: 3
    spike: SPK-REV-01
  - id: REV-PROC-01
    name: Event Loop Protection Strategy
    size: XL
    stories: 3
    spike: SPK-REV-02
  - id: REV-DEV-01
    name: ML Artifact Integrity & Standardization
    size: M
    stories: 3
    spike: SPK-REV-03
  - id: REV-PHY-01
    name: Resource Isolation & Stability
    size: M
    stories: 3
    spike: null
  - id: REV-SCN-01
    name: Integration Verification
    size: L
    stories: 2
    spike: null
scripts:
  - name: detect_blocking_calls.py
    superpower: async-radar
  - name: validate_schema_migration.py
    superpower: schema-drift-detection
  - name: verify_mojo_artifact.py
    superpower: artifact-integrity
  - name: check_memory_allocation.py
    superpower: resource-sight
checklists:
  - logical_view_review.md
  - process_view_review.md
  - development_view_review.md
  - physical_view_review.md
  - scenario_view_review.md
references:
  - async_concurrency.md
  - mojo_vs_pojo.md
  - jsonb_indexing.md
  - jvm_memory.md
```
