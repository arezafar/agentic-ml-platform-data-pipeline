# Skill Specification Template

Use this template to create a new skill specification. Save as specs/{skill-name}.md.

---

## 1. Executive Summary

**Skill Name**: backend-architect  
**Role**: The **Backend Architect Agent** for Converged Data Warehouse & ML Prediction Platforms—an enforcer of concurrency discipline and runtime harmony that transcends naive component integration to become the guardian of event loop integrity and cross-language memory allocation.  
**Mandate**: Design and implement high-reliability, low-latency inference services that orchestrate complex ML workflows, arbitrating between the asynchronous I/O-bound nature of FastAPI and the synchronous CPU-bound intensity of H2O predictive modeling, while eliminating Training-Serving Skew through unified artifact repositories and strongly typed schemas.

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: Concurrency Arbiter
The ability to perceive and resolve the fundamental dissonance between Python's asyncio event loop and blocking ML inference. The Agent visualizes thread contention down to the millisecond, understanding that a 50ms blocking prediction call on the main thread cascades into load balancer timeouts under 20 RPS. It enforces strict "Offloading Patterns" via `run_in_executor`, preventing the event loop blockage that turns responsive APIs into unresponsive failures.

### Superpower 2: Split-Memory Architect
The capability to design and enforce hybrid Python/Java memory allocation within containerized environments. The Agent understands the JVM Heap vs. Native Memory paradox—when a 16GB container allocates 15GB to `-Xmx`, XGBoost's native memory allocation triggers OOM kills. It enforces the 70/30 split formula, reserving headroom for off-heap computation and preventing the silent crashes that plague hybrid ML runtimes.

### Superpower 3: Hybrid Schema Engineer
The power to design PostgreSQL schemas that balance ACID guarantees with schema flexibility for iterative data science. The Agent perceives the friction between rigid relational columns and evolving feature sets, implementing JSONB columns with `jsonb_path_ops` GIN indexes for high-performance containment queries. It prevents the "migration lock" that occurs when adding columns to 100M+ row tables.

### Superpower 4: Fan-Out Governor
The ability to orchestrate parallel ML training without resource exhaustion. The Agent visualizes Dynamic Block execution in Mage.ai, understanding that uncontrolled fan-out (100 parallel tasks × 4GB each) crashes Kubernetes nodes. It calculates safe concurrency limits via `max_parallel_blocks`, acting as a semaphore that matches parallelism to cluster capacity.

### Superpower 5: GraphQL Optimizer
The capability to design efficient GraphQL schemas that prevent N+1 query explosions and complexity attacks. The Agent implements DataLoaders to coalesce 50 individual queries into single batched SQL, defines custom JSON Scalars for flexible JSONB mapping, and enforces query depth limits to prevent resource exhaustion from deeply nested requests.

### Superpower 6: Circuit Breaker Strategist
The power to design fault-tolerant systems that degrade gracefully rather than fail catastrophically. The Agent perceives dependency health across Redis, PostgreSQL, and remote scoring services, implementing three-state circuit breakers (Closed → Open → Half-Open) with cascading fallback strategies that maintain API responsiveness during backend outages.

### Superpower 7: Artifact Immutability Guardian
The ability to eliminate Training-Serving Skew through version pinning and immutable builds. The Agent enforces that H2O MOJO artifacts, Python client versions, and `daimojo` JARs are locked to identical version strings across training (Mage) and inference (FastAPI) containers, preventing the serialization drift that causes silent model load failures.

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- **Hybrid Schema Mandate**: Immutable identifiers (`entity_id`, `event_timestamp`) must be relational columns; dynamic features must reside in JSONB columns with `jsonb_path_ops` GIN indexes
- **Feature Versioning**: FeatureStore must track `feature_version` alongside data; schema changes are additive, never destructive
- **Model Registry**: All MOJO artifacts must be linked to `git_commit_sha` and S3 URIs for full traceability
- **Pydantic Contracts**: All data entering persistence layer must validate against shared Pydantic models used by both Training and Serving

### 3.2 Process View
- **Event Loop Protection**: All blocking ML inference calls must be wrapped in `asyncio.run_in_executor` or `run_in_threadpool`; main thread blocking >10ms fails CI
- **Fan-Out Semaphore**: Dynamic Blocks must configure `max_parallel_blocks` to match cluster memory capacity; formula: `floor(node_memory / task_memory)`
- **Circuit Breaker States**: All external dependencies (Redis, PostgreSQL, scoring services) must be wrapped with `fail_max=5`, `reset_timeout=60s` breakers
- **Fallback Cascade**: Cache miss → DB fallback → Default response; no circuit failure returns 500 error

### 3.3 Development View
- **Monorepo Structure**: `/src/shared` contains Pydantic models consumed by both Mage (training) and FastAPI (serving) components
- **GraphQL Schema Design**: Custom JSON Scalar for `dynamic_features`; DataLoaders mandatory for all relation resolvers
- **Version Pinning**: Single `versions.env` file defines H2O client, `daimojo`, and `h2o-genmodel` JAR versions for all containers
- **Query Complexity Limits**: Strawberry middleware enforces max query depth to prevent resource exhaustion

### 3.4 Physical View
- **Split Memory Formula**: JVM `-Xmx` = 70% of container limit; remaining 30% reserved for XGBoost native memory + Python overhead
- **StatefulSet Topology**: H2O clusters deployed as StatefulSets with Headless Service for stable network identity (`h2o-0`, `h2o-1`)
- **Inference Deployment**: FastAPI services as stateless Deployments with HPA; no local state, horizontal scaling enabled
- **Container Sizing**: Training containers sized for burst (16GB+); Inference containers sized for steady-state (4-8GB)

### 3.5 Scenario View
- **Latency Spike Detection**: System must auto-detect when inference latency exceeds 50ms and trace to event loop blocking vs. model complexity
- **OOM Prevention**: Pre-flight memory calculation before fan-out execution; reject if projected allocation exceeds 80% node capacity
- **Graceful Degradation**: During Redis outage, API continues serving with increased latency (DB fallback) rather than errors
- **Zero-Downtime Model Updates**: MOJO artifact swaps via feature flags; old model serves until new model warmup completes

---

## 4. JTBD Task List

### Epic: BA-LOG-01 (Feature Store & Model Registry)

**T-Shirt Size**: L  
**Objective**: Define the storage layer supporting hybrid relational/JSONB features and immutable model versioning.  
**Dependencies**: None  
**Risk**: HIGH - Poor schema design causes migration locks on large tables and index bloat degrading inference latency.

#### Job Story (SPIN Format)
> When data scientists need to add new experimental features without causing production database migrations [Circumstance],  
> I want to apply my **Hybrid Schema Engineer** superpower to design JSONB columns with optimized GIN indexes [New Ability],  
> So that feature iteration happens at the speed of thought while inference queries maintain sub-50ms latency, feeling confident the schema scales to billions of rows [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| BA-LOG-01 | FeatureStore Hybrid Schema | Constraint: Relational columns for `entity_id`, `event_timestamp`; JSONB for `dynamic_features`. Index: GIN with `jsonb_path_ops` | ✅ Containment queries (@>) use index scan. ✅ Adding new features requires no migration. ✅ Index size <20% of table size |
| BA-LOG-02 | Pydantic Feature Validation | Pattern: Shared `/src/shared/models.py` consumed by Mage and FastAPI. Tool: Pydantic v2 with strict mode | ✅ Invalid features rejected at ingestion. ✅ Training and Serving use identical validation. ✅ Schema drift detected in CI |
| BA-LOG-03 | Model Registry Design | Constraint: `ModelRegistry` table with MOJO S3 URI, `git_commit_sha`, `h2o_version`, `created_at`. Immutable records | ✅ Every deployed model traceable to commit. ✅ Rollback possible to any previous version. ✅ Version mismatch alerts in monitoring |

#### Spike
**Spike ID**: SPK-BA-LOG-01  
**Question**: What is the optimal GIN index configuration for mixed existence checks and containment queries on JSONB?  
**Hypothesis**: `jsonb_path_ops` outperforms default `jsonb_ops` for containment-heavy workloads by 40%+ with smaller index size  
**Timebox**: 2 Days  
**Outcome**: Benchmark report comparing index types on 10M row feature table with production query patterns

---

### Epic: BA-PROC-01 (Async Inference Engine)

**T-Shirt Size**: XL  
**Objective**: Implement high-throughput inference that protects the asyncio event loop from blocking ML computations.  
**Dependencies**: BA-LOG-01  
**Risk**: CRITICAL - Event loop blocking causes cascading failures, pod kills, and complete service unavailability under load.

#### Job Story (SPIN Format)
> When the inference API must handle 1000+ concurrent requests while each H2O prediction takes 50ms [Circumstance],  
> I want to use my **Concurrency Arbiter** superpower to offload blocking calls to thread pools [New Ability],  
> So that the event loop remains responsive to heartbeats and new connections, ensuring the system survives load spikes without degradation [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| BA-PROC-01 | Blocking Inference Offload | Pattern: Wrap `h2o_model.predict()` in `asyncio.run_in_executor(None, predict_fn, features)`. ThreadPoolExecutor with `max_workers=cpu_count*2` | ✅ Main thread never blocks >10ms. ✅ 1000 concurrent requests handled. ✅ p99 latency <100ms |
| BA-PROC-02 | MOJO Runtime Integration | Constraint: Use `daimojo` C++ runtime, not full H2O cluster. No JVM in inference path | ✅ Cold start <2 seconds. ✅ Memory footprint <500MB per worker. ✅ Prediction latency <50ms |
| BA-PROC-03 | Event Loop Health Monitoring | Tool: Custom middleware measuring event loop lag. Alert if lag >50ms sustained for 10 seconds | ✅ Blocking code detected in staging. ✅ CI fails if latency test shows blocking. ✅ Dashboard shows event loop metrics |

#### Spike
**Spike ID**: SPK-BA-PROC-01  
**Question**: Thread pool vs. process pool for H2O inference—which provides better throughput under GIL constraints?  
**Hypothesis**: Thread pool sufficient since `daimojo` releases GIL during C++ execution; process pool adds IPC overhead  
**Timebox**: 2 Days  
**Outcome**: Benchmark comparing throughput and latency of both approaches under 500 RPS load

---

### Epic: BA-PROC-02 (Parallel Training Orchestration)

**T-Shirt Size**: L  
**Objective**: Enable scalable hyperparameter tuning via Mage Dynamic Blocks without causing cluster resource exhaustion.  
**Dependencies**: BA-LOG-01  
**Risk**: HIGH - Uncontrolled fan-out causes OOM kills, node crashes, and training job failures.

#### Job Story (SPIN Format)
> When the ML team needs to train 50 model variations across different hyperparameters and data segments in parallel [Circumstance],  
> I want to use my **Fan-Out Governor** superpower to configure safe concurrency limits [New Ability],  
> So that parallel training maximizes cluster utilization without exceeding memory bounds, completing hyperparameter sweeps in hours instead of days [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| BA-PROC-04 | Dynamic Block Configuration | Pattern: Upstream block yields `List[List[Dict]]` config matrix. Mage spawns parallel tasks per configuration | ✅ 50 hyperparameter combinations tested in parallel. ✅ Each task isolated with own memory. ✅ Results aggregated by reducer block |
| BA-PROC-05 | Resource Semaphore | Constraint: `max_parallel_blocks` = `floor(node_memory_gb / task_memory_gb)`. For 64GB node, 4GB tasks = max 16 parallel | ✅ No OOM kills during fan-out. ✅ Cluster utilization >80%. ✅ Queue drains within SLA |
| BA-PROC-06 | Champion Model Selection | Pattern: Reducer block collects metrics (AUC, LogLoss) from all parallel runs; selects best performer; registers to ModelRegistry | ✅ Best model auto-selected. ✅ All run metrics logged for comparison. ✅ Champion model deployed without manual intervention |

#### Spike
**Spike ID**: SPK-BA-PROC-02  
**Question**: How to dynamically adjust `max_parallel_blocks` based on real-time cluster capacity?  
**Hypothesis**: Kubernetes Metrics API can provide node memory availability; pre-flight check adjusts parallelism  
**Timebox**: 2 Days  
**Outcome**: Adaptive concurrency controller prototype

---

### Epic: BA-DEV-01 (GraphQL API Layer)

**T-Shirt Size**: L  
**Objective**: Implement flexible, efficient data access via GraphQL that prevents N+1 queries and complexity attacks.  
**Dependencies**: BA-LOG-01  
**Risk**: HIGH - Naive GraphQL implementation causes database overload and enables denial-of-service via complex queries.

#### Job Story (SPIN Format)
> When clients need to aggregate prediction results with feature histories and model metadata in a single request [Circumstance],  
> I want to use my **GraphQL Optimizer** superpower to implement DataLoaders and custom scalars [New Ability],  
> So that complex queries execute efficiently without N+1 database calls, while the schema remains flexible for evolving feature structures [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| BA-DEV-01 | Custom JSON Scalar | Tool: Strawberry custom scalar for `dynamic_features` JSONB. Bypasses rigid type definition for flexible nesting | ✅ Arbitrary feature structures queryable. ✅ No schema updates for new features. ✅ Type safety maintained for relational fields |
| BA-DEV-02 | DataLoader Implementation | Pattern: Buffer entity IDs; coalesce into `SELECT * FROM features WHERE id IN (...)`. One SQL per resolver batch | ✅ 50-entity query = 1 DB call, not 50. ✅ Latency scales O(1) not O(N). ✅ Connection pool not exhausted |
| BA-DEV-03 | Query Depth Limiting | Tool: Strawberry middleware enforcing `max_depth=5`. Reject queries exceeding complexity threshold | ✅ Deeply nested attacks rejected. ✅ Legitimate queries unaffected. ✅ Clear error message for rejected queries |

#### Spike
**Spike ID**: SPK-BA-DEV-01  
**Question**: How to implement query cost analysis beyond simple depth limiting?  
**Hypothesis**: Assign cost weights to field types; reject queries where total cost exceeds budget  
**Timebox**: 2 Days  
**Outcome**: Query cost analyzer middleware with configurable field weights

---

### Epic: BA-PHY-01 (Resilient Deployment)

**T-Shirt Size**: XL  
**Objective**: Deploy fault-tolerant infrastructure with proper memory allocation and graceful degradation.  
**Dependencies**: BA-PROC-01, BA-PROC-02  
**Risk**: CRITICAL - Improper memory allocation causes silent OOM kills; missing circuit breakers cause cascading failures.

#### Job Story (SPIN Format)
> When a Redis outage occurs during peak traffic and H2O training containers compete for memory with XGBoost native allocation [Circumstance],  
> I want to use my **Split-Memory Architect** and **Circuit Breaker Strategist** superpowers to maintain system stability [New Ability],  
> So that the API degrades gracefully to database fallback while training jobs complete without OOM kills, preserving user experience and job completion rates [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| BA-PHY-01 | Split Memory Configuration | Constraint: Container limit 16GB → JVM `-Xmx11g` (70%). K8s manifest enforces via env vars | ✅ No OOM kills during XGBoost training. ✅ Native memory headroom verified. ✅ Memory metrics dashboarded |
| BA-PHY-02 | Circuit Breaker Implementation | Tool: `aiobreaker` wrapping Redis and PostgreSQL. Config: `fail_max=5`, `reset_timeout=60`. Fallback: Cache→DB→Default | ✅ Redis failure triggers fallback in <1s. ✅ API returns 200 with degraded data, not 500. ✅ Circuit state visible in metrics |
| BA-PHY-03 | H2O StatefulSet Topology | Pattern: StatefulSet with Headless Service. Stable DNS: `h2o-0.h2o-headless.namespace.svc.cluster.local` | ✅ H2O cluster forms on startup. ✅ Node failure triggers clean rejoin. ✅ No split-brain scenarios |

#### Spike
**Spike ID**: SPK-BA-PHY-01  
**Question**: How to auto-tune JVM heap based on container cgroup limits without manual configuration?  
**Hypothesis**: JVM ergonomics with `-XX:+UseContainerSupport` can auto-detect limits; verify against 70% target  
**Timebox**: 1 Day  
**Outcome**: Validation that JVM auto-tuning meets split-memory requirements

---

### Epic: BA-PHY-02 (Artifact Immutability)

**T-Shirt Size**: M  
**Objective**: Eliminate Training-Serving Skew through version pinning and immutable build artifacts.  
**Dependencies**: BA-LOG-01  
**Risk**: HIGH - Version drift between training and inference causes silent model failures and incorrect predictions.

#### Job Story (SPIN Format)
> When the H2O version used in Mage training differs slightly from the FastAPI inference runtime [Circumstance],  
> I want to use my **Artifact Immutability Guardian** superpower to enforce version locking across all containers [New Ability],  
> So that MOJO artifacts load successfully in production and predictions match training validation exactly, eliminating the debugging nightmare of serialization drift [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| BA-PHY-04 | Unified Version File | Pattern: `versions.env` defines `H2O_VERSION`, `DAIMOJO_VERSION`, `GENMODEL_VERSION`. Both Dockerfiles source this file | ✅ Single source of truth for versions. ✅ Version update = one file change. ✅ CI validates version consistency |
| BA-PHY-05 | Build-Time Version Injection | Tool: Docker ARG/ENV from `versions.env`. pip install pinned versions; JAR download with exact version | ✅ Containers bit-for-bit reproducible. ✅ Version mismatch fails build. ✅ Artifact hashes logged |
| BA-PHY-06 | Runtime Version Verification | Constraint: Startup health check verifies loaded MOJO version matches expected. Fail fast on mismatch | ✅ Version drift detected at startup. ✅ Clear error message for debugging. ✅ Alert sent to on-call |

#### Spike
**Spike ID**: SPK-BA-PHY-02  
**Question**: How to verify MOJO artifact compatibility without loading the full model?  
**Hypothesis**: MOJO header contains version metadata; lightweight parser can validate before heavy load  
**Timebox**: 1 Day  
**Outcome**: Pre-load version validation utility

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 validate_event_loop.py
**Purpose**: Detect blocking code in async endpoints by measuring event loop lag  
**Superpower**: Concurrency Arbiter  
**Detection Logic**:
1. Inject middleware that schedules periodic event loop callbacks
2. Measure delta between scheduled and actual callback time
3. Alert if lag exceeds threshold (10ms sustained)
4. Trace blocking call via async stack inspection

**Usage**:
```bash
python scripts/validate_event_loop.py --app src.main:app --threshold-ms 10 --duration 60
```

### 5.2 calculate_memory_split.py
**Purpose**: Calculate optimal JVM heap and native memory allocation for hybrid containers  
**Superpower**: Split-Memory Architect  
**Detection Logic**:
1. Parse container memory limit from cgroup or K8s manifest
2. Apply 70/30 split formula: JVM = limit × 0.7
3. Validate against XGBoost memory requirements
4. Generate `-Xmx` and `-Xms` JVM arguments

**Usage**:
```bash
python scripts/calculate_memory_split.py --container-limit 16g --xgboost-estimate 4g --output jvm-args.env
```

### 5.3 benchmark_gin_index.py
**Purpose**: Compare GIN index operator classes for JSONB query performance  
**Superpower**: Hybrid Schema Engineer  
**Detection Logic**:
1. Create test table with production-like JSONB data
2. Apply both `jsonb_ops` and `jsonb_path_ops` indexes
3. Run representative query workload (existence, containment)
4. Measure latency percentiles and index sizes
5. Generate recommendation report

**Usage**:
```bash
python scripts/benchmark_gin_index.py --table feature_store --queries queries.sql --rows 10000000
```

### 5.4 validate_dataloader.py
**Purpose**: Detect N+1 query patterns in GraphQL resolvers  
**Superpower**: GraphQL Optimizer  
**Detection Logic**:
1. Instrument SQLAlchemy query logging
2. Execute representative GraphQL queries
3. Count SQL statements per GraphQL operation
4. Flag resolvers where SQL count > 1 for batched requests

**Usage**:
```bash
python scripts/validate_dataloader.py --schema src/graphql/schema.py --queries test_queries.graphql
```

### 5.5 test_circuit_breaker.py
**Purpose**: Validate circuit breaker state transitions and fallback behavior  
**Superpower**: Circuit Breaker Strategist  
**Detection Logic**:
1. Simulate dependency failures (Redis timeout, DB connection refused)
2. Verify circuit opens after `fail_max` failures
3. Verify fallback returns valid response (not 500)
4. Verify circuit half-opens after `reset_timeout`
5. Verify successful canary closes circuit

**Usage**:
```bash
python scripts/test_circuit_breaker.py --service inference-api --dependency redis --fail-count 5
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 The Asyncio Event Loop and Blocking Inference
FastAPI leverages Python's asyncio to handle thousands of concurrent connections on a single thread. The event loop yields control during I/O waits (database queries, HTTP calls), allowing other coroutines to execute. However, ML inference is CPU-bound—when `h2o_model.predict()` executes, it consumes the thread for the full duration (e.g., 50ms).

During this blocking period, the event loop cannot: accept new connections, respond to health checks, process other requests, or yield to other coroutines. Under 20 RPS with 50ms blocking, the system becomes unresponsive. Kubernetes interprets missed health checks as pod failure, triggering restarts that cascade into total unavailability.

The solution is explicit offloading via `asyncio.run_in_executor(None, predict_fn, features)`. This schedules the blocking call on a ThreadPoolExecutor, freeing the event loop immediately. The `daimojo` C++ runtime releases the GIL during execution, allowing true parallelism. Thread pool size should be `cpu_count * 2` to balance throughput with context-switching overhead.

### 6.2 Split Memory Allocation: JVM vs. Native
H2O AutoML uses a hybrid memory model. Java objects (DataFrames, model metadata) live in JVM Heap, while algorithms like XGBoost allocate native (off-heap) memory directly from the OS. This creates a dangerous scenario in containerized environments.

When a container has a 16GB limit and the JVM is configured with `-Xmx15g`, Java reserves nearly all available memory. When XGBoost starts and requests 2GB of native memory, the allocation fails. The Linux OOM Killer terminates the process, often without useful error messages. Developers see "Killed" in logs with no stack trace.

The 70/30 formula provides safety: for a 16GB container, set `-Xmx11g`, leaving 5GB for native allocation, Python interpreter overhead, and OS buffers. This split should be validated empirically for specific workloads—XGBoost with large trees may require more native headroom.

### 6.3 JSONB Indexing: jsonb_ops vs. jsonb_path_ops
PostgreSQL's GIN indexes for JSONB support two operator classes. The default `jsonb_ops` indexes both keys and values separately, supporting operators like `?` (key exists), `?|` (any key exists), `?&` (all keys exist), and `@>` (contains).

The `jsonb_path_ops` operator class takes a different approach: it indexes hashes of key-value paths. This produces significantly smaller indexes (often 50% reduction) and faster lookups for containment queries (`@>`), which is the primary access pattern for feature retrieval ("give me all features where `embedding_version` contains `v2`").

The trade-off: `jsonb_path_ops` does not support existence checks (`?` operator). For feature stores where queries are predominantly containment-based, `jsonb_path_ops` is the correct choice. Index size reduction directly impacts buffer cache efficiency—smaller indexes mean more data fits in `shared_buffers`.

### 6.4 Circuit Breaker State Machine
Circuit breakers prevent cascading failures when downstream dependencies fail. The pattern implements a state machine with three states:

**Closed** (normal): Requests pass through to the dependency. Failures increment an internal counter. If the counter exceeds `fail_max` within a time window, transition to Open.

**Open** (failing fast): All requests immediately return a fallback response without attempting the dependency call. This prevents thread exhaustion waiting for timeouts and gives the struggling service time to recover. After `reset_timeout` seconds, transition to Half-Open.

**Half-Open** (probing): Allow a single "canary" request through. If it succeeds, transition to Closed. If it fails, transition back to Open.

The critical implementation detail is the fallback strategy. An open circuit should not return 500 errors—it should execute alternative logic: cache miss falls back to database; database failure falls back to hardcoded defaults or "degraded service" responses. The API remains responsive even during total backend outages.

### 6.5 Dynamic Blocks and Resource Exhaustion
Mage's Dynamic Blocks enable parallel execution by "fanning out" a pipeline based on configuration from an upstream block. The upstream block yields a `List[List[Dict]]` where each inner list spawns a parallel task consuming the contained dictionaries.

Without constraints, this pattern can spawn hundreds of parallel tasks. Each H2O training job may allocate 4-8GB of memory. A 50-task fan-out requesting 4GB each needs 200GB—exceeding any reasonable node capacity. Kubernetes responds with OOM kills, preemption, or node crashes.

The `max_parallel_blocks` configuration acts as a semaphore, limiting concurrent executions. The safe limit is calculated as `floor(node_memory / task_memory)`. For a 64GB node with 4GB tasks, max parallelism is 16. Additional tasks queue and execute as slots become available. This ensures cluster stability while maximizing utilization.

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: backend-architect
description: Backend Architect Agent for Converged Data Warehouse & ML Prediction Platforms
superpowers:
  - concurrency-arbiter
  - split-memory-architect
  - hybrid-schema-engineer
  - fan-out-governor
  - graphql-optimizer
  - circuit-breaker-strategist
  - artifact-immutability-guardian
triggers:
  - "fastapi async"
  - "event loop blocking"
  - "h2o inference"
  - "mojo runtime"
  - "jsonb optimization"
  - "gin index"
  - "graphql dataloader"
  - "circuit breaker"
  - "mage dynamic blocks"
  - "jvm memory"
  - "training serving skew"
epics:
  - id: BA-LOG-01
    name: Feature Store & Model Registry
    size: L
    stories: 3
    spike: SPK-BA-LOG-01
  - id: BA-PROC-01
    name: Async Inference Engine
    size: XL
    stories: 3
    spike: SPK-BA-PROC-01
  - id: BA-PROC-02
    name: Parallel Training Orchestration
    size: L
    stories: 3
    spike: SPK-BA-PROC-02
  - id: BA-DEV-01
    name: GraphQL API Layer
    size: L
    stories: 3
    spike: SPK-BA-DEV-01
  - id: BA-PHY-01
    name: Resilient Deployment
    size: XL
    stories: 3
    spike: SPK-BA-PHY-01
  - id: BA-PHY-02
    name: Artifact Immutability
    size: M
    stories: 3
    spike: SPK-BA-PHY-02
scripts:
  - name: validate_event_loop.py
    superpower: concurrency-arbiter
  - name: calculate_memory_split.py
    superpower: split-memory-architect
  - name: benchmark_gin_index.py
    superpower: hybrid-schema-engineer
  - name: validate_dataloader.py
    superpower: graphql-optimizer
  - name: test_circuit_breaker.py
    superpower: circuit-breaker-strategist
checklists:
  - logical_view_backend.md
  - process_view_backend.md
  - development_view_backend.md
  - physical_view_backend.md
  - scenario_view_backend.md
references:
  - asyncio_event_loop_blocking.md
  - split_memory_jvm_native.md
  - jsonb_gin_indexing.md
  - circuit_breaker_patterns.md
  - mage_dynamic_blocks.md
```
