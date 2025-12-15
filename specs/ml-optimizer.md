# Skill Specification Template

Use this template to create a new skill specification. Save as specs/{skill-name}.md.

---

## 1. Executive Summary

**Skill Name**: ml-optimizer  
**Role**: The **ML Optimizer Agent** for High-Performance Inference and Training Platforms—an architectural linchpin that transcends hyperparameter tuning to become the guardian of end-to-end latency budgets, resource efficiency, and predictive throughput across the entire data-to-inference lifecycle.  
**Mandate**: Achieve 1,000 req/s throughput with sub-50ms p99 latency through systematic optimization across database indices, concurrency models, model artifact quantization, and container topology, operating as an autonomous agent responsible for the performance physics of converged Data & ML platforms.

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: Event Loop Guardian
The ability to perceive and protect the sacred AsyncIO event loop from CPU-bound contamination. The Agent visualizes thread contention at the millisecond level, understanding that a 10ms blocking call on the main thread caps throughput at 100 req/s regardless of hardware. It enforces strict async/sync separation via `run_in_executor`, preventing the "blocking loop" failures that cascade into connection timeouts.

### Superpower 2: TOAST Preventer
The capability to detect and prevent PostgreSQL TOAST (The Oversized-Attribute Storage Technique) penalties in JSONB columns. The Agent monitors column sizes and access patterns, understanding that documents exceeding 8KB page boundaries force secondary I/O lookups with unpredictable latency. It partitions "Hot" features from "Cold" to prevent TOASTing on the inference path.

### Superpower 3: GIN Index Optimizer
The power to tune Generalized Inverted Index configurations for JSONB columns under high write velocity. The Agent understands the write amplification trade-off—updating a single key re-indexes the entire document—and selects between `jsonb_ops` (full indexing) and `jsonb_path_ops` (path-only, smaller, faster) based on downstream query patterns.

### Superpower 4: Model Quantizer
The ability to enforce lightweight, optimized model representations through MOJO (Model Object, Optimized) artifacts. The Agent rejects POJOs (Plain Old Java Objects) that require runtime compilation and exceed JVM limits, instead mandating binary serialization compatible with C++ runtimes that bypass the heavy JVM entirely—achieving "Operational Quantization."

### Superpower 5: Cache Coherence Architect
The capability to design Redis look-aside caching strategies that survive model updates without serving stale predictions. The Agent implements versioned cache keys (`v{model_version}:pred:{feature_hash}`) enabling instant cache busting on model deployment without expensive FLUSHDB operations.

### Superpower 6: Memory Split Calculator
The power to prevent OOM kills in hybrid JVM/Native workloads by calculating optimal memory allocation. The Agent understands that XGBoost runs in C++ native memory outside JVM heap control—setting `-Xmx` to 100% of container memory guarantees OOM death when XGBoost allocates. It enforces the 60-70% JVM / 30-40% Native split formula.

### Superpower 7: AutoML Pruner
The ability to constrain H2O AutoML search spaces for production viability. The Agent prunes model architecture space (rejecting complex Ensembles and Deep Learning for latency-sensitive paths), sets aggressive stopping metrics, and enforces runtime budgets—ensuring trained models are deployment-compatible, not just accuracy-optimal.

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- **Hybrid Schema Mandate**: Immutable entities in relational columns; dynamic features in JSONB with strict size monitoring to prevent TOAST
- **Feature Temperature Partitioning**: "Hot" features (real-time inference) separated from "Cold" features (offline training); Hot features never TOASTed
- **GIN Index Strategy**: `jsonb_path_ops` for containment queries; benchmark write penalty before deploying `jsonb_ops`
- **Feature Pruning**: PCA/GLRM dimensionality reduction executed in H2O distributed engine before training loop

### 3.2 Process View
- **Event Loop Protection**: All CPU-bound operations (model scoring, large JSON parsing) wrapped in `run_in_executor` with dedicated ThreadPoolExecutor
- **Thread Pool Sizing**: Initial heuristic `CPU_CORES * 1.5`; empirically tuned to avoid context-switching thrash
- **Look-Aside Caching**: Redis L2 cache (~1-2ms) shields compute path (~20-50ms); versioned keys enable atomic cache busting
- **Transaction Isolation**: `REPEATABLE READ` isolation during training data extraction; ensures point-in-time snapshot consistency

### 3.3 Development View
- **MOJO-Only Policy**: CI/CD gate rejects POJO exports; only `mojo.zip` artifacts accepted for deployment
- **C++ Runtime Integration**: `daimojo` wrapper bypasses JVM in inference containers; cold start <2 seconds
- **Strict Version Pinning**: Single `versions.env` file dictates H2O version across all Dockerfiles; prevents serialization drift
- **Monorepo Structure**: Training (Mage) and Inference (FastAPI) share version dependencies to ensure bit-for-bit MOJO compatibility

### 3.4 Physical View
- **Split Memory Formula**: JVM `-Xmx` = 60-70% of container limit; 30-40% reserved for XGBoost native + OS overhead
- **StatefulSet for H2O**: Headless Service enables stable network identity; Flatfile discovery prevents split-brain in cloud environments
- **Stateless Inference**: FastAPI as Deployment with HPA triggered by CPU/latency metrics; no local state
- **Atomic Artifact Transfer**: RWX volumes or S3 for MOJO transfer; prevents API loading partial files

### 3.5 Scenario View
- **Zero-Downtime Hot-Swap**: New model loaded alongside old; atomic pointer swap; no dropped requests during reload
- **Model Drift Detection**: Reservoir Sampling maintains statistically significant stream sample; PSI calculated without full table scan
- **Latency Budget Validation**: Load test during model reload verifies zero 500 errors and maintained p99 <50ms
- **Cache Invalidation**: Model version increment instantly invalidates old cache entries via key prefix change

---

## 4. JTBD Task List

### Epic: MLO-LOG-01 (Feature Store Schema & Index Optimization)

**T-Shirt Size**: L  
**Objective**: Optimize PostgreSQL schema for sub-10ms feature retrieval while maintaining data science experimentation flexibility.  
**Dependencies**: None  
**Risk**: HIGH - Write amplification from GIN indexes slows ingestion below 500 rows/sec threshold.

#### Job Story (SPIN Format)
> When the feature store experiences unpredictable latency spikes due to TOAST lookups and unoptimized GIN indexes [Circumstance],  
> I want to apply my **TOAST Preventer** and **GIN Index Optimizer** superpowers to partition features and tune index strategy [New Ability],  
> So that feature retrieval consistently meets the 10ms SLA while maintaining ingestion throughput, feeling confident the schema scales to production load [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-LOG-01 | Hybrid JSONB/Relational Partitioning | Pattern: Hot features in lightweight columns; Cold features in JSONB. Constraint: No hot-path column exceeds 2KB | ✅ EXPLAIN ANALYZE confirms no TOAST access on hot path. ✅ Feature fetch <10ms at p99. ✅ Schema supports feature addition without migration |
| MLO-LOG-02 | GIN Index Strategy Selection | Constraint: `jsonb_path_ops` for containment queries. Benchmark: Write penalty <20% overhead at 500 rows/sec | ✅ Index size reduced >30% vs `jsonb_ops`. ✅ Ingestion throughput >500 rows/sec. ✅ Query performance maintained |
| MLO-LOG-03 | Feature Pruning via PCA | Library: `h2o.transforms.decomposition`. Target: 50% dimensionality reduction with <1% variance loss | ✅ Input feature count halved. ✅ Training time reduced >20%. ✅ Model accuracy within 0.5% of full feature set |

#### Spike
**Spike ID**: SPK-MLO-LOG-01  
**Question**: What is the optimal GIN configuration for mixed read/write workloads at 1000 req/s?  
**Hypothesis**: `jsonb_path_ops` with partial indexes on hot keys outperforms full `jsonb_ops` by 40%+ on writes  
**Timebox**: 2 Days  
**Outcome**: Benchmark report with index size, write latency, and query performance across configurations

---

### Epic: MLO-PROC-01 (Inference Latency Reduction)

**T-Shirt Size**: XL  
**Objective**: Achieve sub-50ms p99 latency for prediction API while maintaining 1000 req/s throughput.  
**Dependencies**: MLO-LOG-01, MLO-DEV-01  
**Risk**: CRITICAL - Event loop blocking causes cascading timeouts and complete service unavailability.

#### Job Story (SPIN Format)
> When CPU-bound model inference threatens to block the AsyncIO event loop and collapse throughput [Circumstance],  
> I want to use my **Event Loop Guardian** superpower to enforce strict async/sync separation [New Ability],  
> So that the API handles 1000 req/s with sub-50ms p99 latency, and heartbeat checks never timeout during heavy inference load [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-PROC-01 | Thread Pool Offloading | Pattern: `loop.run_in_executor(pool, predict)`. ThreadPoolExecutor size: `CPU_CORES * 1.5` initial, empirically tuned | ✅ API heartbeat <100ms during heavy inference. ✅ No "blocking loop" warnings. ✅ 1000 req/s sustained |
| MLO-PROC-02 | Redis Look-Aside Caching | Pattern: Check Redis → Cache hit returns immediately → Cache miss triggers inference → Write-back with TTL | ✅ Cache hit rate >80% at steady state. ✅ Cache lookup <2ms. ✅ Inference path only on cache miss |
| MLO-PROC-03 | Versioned Cache Busting | Key format: `v{model_version}:pred:{sha256(features)}`. Atomic version increment on model deploy | ✅ Zero stale predictions after model update. ✅ No FLUSHDB required. ✅ Old keys expire naturally via TTL |

#### Spike
**Spike ID**: SPK-MLO-PROC-01  
**Question**: What is the optimal thread pool size to maximize throughput without context-switching thrash?  
**Hypothesis**: `CPU_CORES * 1.5` is starting point; actual optimum is workload-dependent and requires load testing  
**Timebox**: 2 Days  
**Outcome**: Thread pool sizing guide with benchmarks across different inference latencies

---

### Epic: MLO-PROC-02 (Concurrency & Connection Management)

**T-Shirt Size**: M  
**Objective**: Ensure database and cache connections scale to 1000 req/s without exhaustion or contention.  
**Dependencies**: MLO-PROC-01  
**Risk**: HIGH - Connection pool exhaustion causes "connection refused" errors under load.

#### Job Story (SPIN Format)
> When concurrent requests exhaust database connection pools faster than connections can be recycled [Circumstance],  
> I want to configure global connection pooling with appropriate sizing and lifecycle management [New Ability],  
> So that no request fails due to connection unavailability, and pool resources are efficiently utilized [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-PROC-04 | Async Connection Pooling | Library: `asyncpg`. Config: `max_size=50`, `min_size=10`. Lifecycle: Pool initialized on startup | ✅ No "connection refused" under 1000 req/s. ✅ Pool metrics dashboarded. ✅ Graceful degradation on pool exhaustion |
| MLO-PROC-05 | Redis Connection Pool | Library: `redis-py` async. Config: `max_connections=100`. Health check: Periodic ping | ✅ Cache operations never timeout due to connection wait. ✅ Connection reuse >95%. ✅ Automatic reconnection on failure |
| MLO-PROC-06 | Transaction Isolation | Pattern: `REPEATABLE READ` for training extraction. Constraint: Point-in-time snapshot consistency | ✅ Training data deterministic across retries. ✅ No dirty reads during extraction. ✅ Isolation level logged |

#### Spike
**Spike ID**: SPK-MLO-PROC-02  
**Question**: How to implement connection pool warmup to eliminate cold-start latency spikes?  
**Hypothesis**: Pre-establishing minimum connections on startup eliminates first-request latency penalty  
**Timebox**: 1 Day  
**Outcome**: Connection warmup implementation with latency comparison

---

### Epic: MLO-DEV-01 (Model Quantization & Artifact Optimization)

**T-Shirt Size**: L  
**Objective**: Ensure deployed models are lightweight, quantized (MOJO), and compatible with C++ runtime.  
**Dependencies**: None  
**Risk**: CRITICAL - POJO artifacts fail JVM method size limits; version drift causes silent scoring errors.

#### Job Story (SPIN Format)
> When model artifacts are too large for JVM compilation or incompatible between training and inference environments [Circumstance],  
> I want to use my **Model Quantizer** superpower to enforce MOJO-only exports with strict version pinning [New Ability],  
> So that models load instantly via C++ runtime with minimal memory footprint, and training/inference environments are bit-for-bit compatible [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-DEV-01 | MOJO-Only Export Policy | Artifact: `mojo.zip`. CI/CD gate: Reject POJO requests. Validation: Artifact size <500MB | ✅ Pipeline fails if POJO requested. ✅ Artifact size validated. ✅ MOJO loads successfully in inference |
| MLO-DEV-02 | C++ Runtime Integration | Library: `daimojo` / H2O C++ wrapper. Constraint: No JVM in inference container | ✅ Cold start <2 seconds. ✅ Memory footprint reduced >40% vs JVM. ✅ Prediction accuracy identical to JVM |
| MLO-DEV-03 | Version Pinning Strategy | Config: Single `versions.env` sourced by all Dockerfiles. Validation: Build fails on version mismatch | ✅ H2O version identical across training/inference. ✅ MOJO serialization compatible. ✅ No silent numerical errors |

#### Spike
**Spike ID**: SPK-MLO-DEV-01  
**Question**: What is the maximum model complexity (trees, depth) supported by C++ runtime within latency budget?  
**Hypothesis**: 1000 trees × depth 10 GBM scores in <20ms on C++ runtime  
**Timebox**: 2 Days  
**Outcome**: Model complexity vs. latency benchmark for C++ runtime

---

### Epic: MLO-DEV-02 (AutoML Search Space Pruning)

**T-Shirt Size**: M  
**Objective**: Constrain H2O AutoML to produce models compatible with latency requirements and deployment constraints.  
**Dependencies**: MLO-DEV-01  
**Risk**: MEDIUM - Unconstrained AutoML produces accurate but undeployable models.

#### Job Story (SPIN Format)
> When H2O AutoML produces complex Stacked Ensembles that exceed inference latency budgets [Circumstance],  
> I want to use my **AutoML Pruner** superpower to constrain the model architecture search space [New Ability],  
> So that trained models are deployment-compatible from the start, avoiding the waste of training models that can never serve production traffic [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-DEV-04 | Runtime Budget Enforcement | Config: `max_runtime_secs=3600`. Stopping: `stopping_metric='logloss'`, `stopping_tolerance=0.001` | ✅ Training completes within budget. ✅ Early stopping triggers on plateau. ✅ Resources released after timeout |
| MLO-DEV-05 | Model Architecture Restriction | Config: `exclude_algos=['DeepLearning', 'StackedEnsemble']` for latency-sensitive paths | ✅ Only GBM/GLM/XGBoost models produced. ✅ Inference latency <50ms for all models. ✅ Model type logged |
| MLO-DEV-06 | Hyperparameter Space Pruning | Constraint: `max_depth<=10`, `ntrees<=1000` for tree models. Validation: Complexity within C++ runtime budget | ✅ Model complexity within benchmark limits. ✅ No models exceed latency threshold. ✅ Pruning rules documented |

#### Spike
**Spike ID**: SPK-MLO-DEV-02  
**Question**: What is the optimal balance between AutoML exploration and production constraints?  
**Hypothesis**: Restricting to top 3 algorithm families loses <2% accuracy while guaranteeing deployability  
**Timebox**: 2 Days  
**Outcome**: Accuracy vs. deployability trade-off analysis

---

### Epic: MLO-PHY-01 (Resource Allocation & Topology)

**T-Shirt Size**: L  
**Objective**: Prevent OOM kills and ensure stable cluster formation through proper memory and network configuration.  
**Dependencies**: None  
**Risk**: CRITICAL - 100% JVM heap allocation guarantees OOM death when XGBoost allocates native memory.

#### Job Story (SPIN Format)
> When H2O training containers die with cryptic "Killed" messages and no stack trace due to OOM [Circumstance],  
> I want to use my **Memory Split Calculator** superpower to configure proper JVM/Native allocation [New Ability],  
> So that XGBoost training completes reliably and I can diagnose memory issues from dashboards rather than post-mortems [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-PHY-01 | Split Memory Configuration | Formula: `-Xmx` = 65% of container limit. Example: 64GB container → `-Xmx42g`. Reserve 35% for Native + OS | ✅ No OOM kills during XGBoost training. ✅ JVM heap usage stable and monitored. ✅ Native memory tracked |
| MLO-PHY-02 | Flatfile Cluster Discovery | Config: K8s StatefulSet with Headless Service. Discovery: Pod IPs written to flatfile, passed to H2O startup | ✅ H2O cluster forms successfully in K8s. ✅ No split-brain scenarios. ✅ Nodes auto-rejoin on restart |
| MLO-PHY-03 | Atomic Artifact Transfer | Storage: RWX volume or S3 with atomic rename. Validation: Checksum verification before API load | ✅ No partial MOJO loads. ✅ Transfer completes atomically. ✅ Rollback possible on checksum failure |

#### Spike
**Spike ID**: SPK-MLO-PHY-01  
**Question**: What is the optimal JVM/Native split ratio for different XGBoost configurations?  
**Hypothesis**: Deeper trees (depth >8) require more native memory; 60/40 split safer than 70/30 for complex models  
**Timebox**: 2 Days  
**Outcome**: Memory split guide indexed by model complexity

---

### Epic: MLO-SCN-01 (Production Validation Scenarios)

**T-Shirt Size**: L  
**Objective**: Validate optimization claims under realistic production conditions including model updates and drift.  
**Dependencies**: MLO-PROC-01, MLO-DEV-01, MLO-PHY-01  
**Risk**: MEDIUM - Integration failures not caught by unit tests; drift detection too slow.

#### Job Story (SPIN Format)
> When production requires zero-downtime model updates and early drift detection without performance regression [Circumstance],  
> I want to implement hot-swap patterns and efficient drift monitoring [New Ability],  
> So that model updates are invisible to users and degradation is detected weeks before business impact [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| MLO-SCN-01 | Zero-Downtime Hot-Swap | Pattern: Load new model alongside old → atomic pointer swap → garbage collect old. Trigger: Webhook from Mage | ✅ Zero 500 errors during reload. ✅ p99 latency maintained <50ms. ✅ Rollback possible within 30 seconds |
| MLO-SCN-02 | Drift Detection via Reservoir Sampling | Pattern: Maintain fixed-size sample in Redis; calculate PSI without full scan. Threshold: PSI >0.25 triggers alert | ✅ Sample statistically significant. ✅ PSI calculation <1 second. ✅ Alert within 24h of drift onset |
| MLO-SCN-03 | Load Test Validation | Tool: Locust/k6. Scenario: 1000 req/s sustained while triggering model reload | ✅ Throughput maintained during reload. ✅ No connection timeouts. ✅ Memory stable post-reload |

#### Spike
**Spike ID**: SPK-MLO-SCN-01  
**Question**: How to implement A/B testing between model versions without separate deployments?  
**Hypothesis**: Traffic splitting at application layer using model version routing enables in-place A/B testing  
**Timebox**: 2 Days  
**Outcome**: In-place A/B testing pattern with metrics collection

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 benchmark_gin_index.py
**Purpose**: Compare GIN index configurations for JSONB columns under production workload patterns  
**Superpower**: GIN Index Optimizer  
**Detection Logic**:
1. Create test table with production-like JSONB data (1M+ rows)
2. Apply `jsonb_ops` index, measure size and write latency
3. Apply `jsonb_path_ops` index, measure size and write latency
4. Run representative query workload on both configurations
5. Generate comparison report with recommendations

**Usage**:
```bash
python scripts/benchmark_gin_index.py --table feature_store --rows 1000000 --write-rate 500 --output gin_benchmark.json
```

### 5.2 validate_event_loop.py
**Purpose**: Detect blocking code in async endpoints by measuring event loop responsiveness  
**Superpower**: Event Loop Guardian  
**Detection Logic**:
1. Inject middleware measuring time between scheduled and actual callback execution
2. Run inference requests under load
3. Alert if event loop lag exceeds threshold (10ms)
4. Trace blocking calls via async stack inspection
5. Generate blocking code report with line numbers

**Usage**:
```bash
python scripts/validate_event_loop.py --app src.main:app --threshold-ms 10 --requests 1000 --concurrency 100
```

### 5.3 calculate_memory_split.py
**Purpose**: Calculate optimal JVM heap and native memory allocation for H2O containers  
**Superpower**: Memory Split Calculator  
**Detection Logic**:
1. Parse container memory limit from cgroup or K8s manifest
2. Estimate XGBoost native memory requirements based on model complexity
3. Apply split formula: JVM = (limit - native_estimate - os_buffer)
4. Generate `-Xmx` and `-Xms` JVM arguments
5. Validate against minimum requirements

**Usage**:
```bash
python scripts/calculate_memory_split.py --container-limit 64g --model-complexity high --output jvm-args.env
```

### 5.4 validate_mojo_artifact.py
**Purpose**: Verify MOJO artifact integrity and compatibility before deployment  
**Superpower**: Model Quantizer  
**Detection Logic**:
1. Validate MOJO zip structure and required files
2. Check H2O version compatibility with inference runtime
3. Verify artifact size within limits
4. Test load in C++ runtime
5. Compare prediction output against reference inputs

**Usage**:
```bash
python scripts/validate_mojo_artifact.py --mojo model.zip --runtime daimojo --reference-data test_inputs.csv
```

### 5.5 test_cache_coherence.py
**Purpose**: Validate cache busting behavior during model updates  
**Superpower**: Cache Coherence Architect  
**Detection Logic**:
1. Populate cache with predictions from model v1
2. Trigger model update to v2
3. Verify new requests use v2 key prefix
4. Confirm no stale v1 predictions returned
5. Measure cache invalidation latency

**Usage**:
```bash
python scripts/test_cache_coherence.py --redis-url redis://localhost:6379 --model-v1 v1.zip --model-v2 v2.zip
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 AsyncIO Event Loop Physics
FastAPI utilizes Python's asyncio with a single-threaded event loop that handles thousands of concurrent connections. The loop functions as a high-speed distributor: accepting requests, dispatching I/O operations, and resuming coroutines when I/O completes. This model excels at I/O-bound workloads where most time is spent waiting for network or disk.

The critical constraint: the event loop must never be blocked. When a CPU-bound operation (model scoring, large JSON parsing) executes on the main thread, the loop cannot accept connections, process bytes, or send heartbeats. A 10ms blocking call at 1000 req/s means 10 requests queue during each block, cascading into timeouts.

The solution is `run_in_executor`, which dispatches CPU-bound work to a ThreadPoolExecutor. The GIL (Global Interpreter Lock) normally prevents Python thread parallelism, but native C++ code (like H2O's MOJO runtime) releases the GIL during execution, enabling true parallelism. Thread pool sizing requires empirical tuning—too few threads queue requests, too many cause context-switching overhead.

### 6.2 PostgreSQL JSONB and TOAST Mechanics
PostgreSQL stores JSONB in a decomposed binary format optimized for key access. However, when a JSONB column exceeds the page size (~8KB), PostgreSQL moves the data to TOAST (The Oversized-Attribute Storage Technique) tables. Accessing TOASTed data requires secondary I/O: locating the TOAST pointer, fetching chunks from the TOAST table, and decompressing.

This penalty is invisible in simple EXPLAIN output but adds 5-50ms per row depending on compression and I/O latency. For real-time inference requiring <10ms feature retrieval, TOAST access is unacceptable.

Prevention strategies: partition features by temperature (Hot features in small columns, Cold in JSONB), enforce column size limits, and monitor `pg_stat_user_tables` for TOAST access patterns. The goal is ensuring the inference hot path never touches TOAST tables.

### 6.3 MOJO vs. POJO: Operational Quantization
H2O models can be exported as POJOs (Plain Old Java Objects) or MOJOs (Model Objects, Optimized). POJOs are generated Java source code containing the model logic—if-then-else trees or coefficient matrices. This approach has fatal flaws for production:

POJOs require runtime compilation, adding cold-start latency. Large models (3000 trees, depth 10) generate millions of lines of Java that exceed JVM method size limits (64KB bytecode). The verbose representation wastes memory on Java object headers.

MOJOs are serialized binary representations designed for rapid traversal. They load instantly without compilation, support arbitrarily large models, and enable C++ runtime execution via `daimojo`. This "Operational Quantization" replaces the heavy JVM (gigabytes of memory, seconds of startup) with a lightweight native runtime (megabytes of memory, milliseconds of startup).

### 6.4 Cache Busting and Model Version Coherence
Redis look-aside caching dramatically reduces inference latency by serving cached predictions (~2ms) instead of computing them (~30ms). However, cached predictions become stale when the underlying model changes.

The naive solution—FLUSHDB on model update—is expensive and causes a cache stampede where all requests simultaneously miss and hit the compute path. The elegant solution is versioned keys: `v{model_version}:pred:{feature_hash}`.

When model v2 deploys, the application starts using the v2 key prefix. All v1 keys become unreachable (logically invalidated) but remain in Redis until TTL expiration. No expensive flush, no stampede, instant coherence. The model version can be stored in Redis itself, fetched on startup, and watched for changes.

### 6.5 JVM vs. Native Memory: The OOM Trap
H2O runs on the JVM for cluster coordination and data management, but XGBoost executes in native C++ memory outside JVM heap control. This creates a dangerous interaction in containerized environments.

When a 64GB container is configured with `-Xmx64g`, the JVM reserves all available memory. When XGBoost starts and requests native memory from the OS, the allocation fails. The Linux OOM Killer terminates the process—often with no useful error message, just "Killed" in logs.

The split memory formula reserves headroom: JVM heap at 60-70% of container limit, leaving 30-40% for native allocation, Python interpreter, and OS buffers. The exact ratio depends on XGBoost configuration—deeper trees and more trees require more native memory. Empirical tuning via the defined spikes is essential.

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: ml-optimizer
description: ML Optimizer Agent for High-Performance Inference and Training Platforms
superpowers:
  - event-loop-guardian
  - toast-preventer
  - gin-index-optimizer
  - model-quantizer
  - cache-coherence-architect
  - memory-split-calculator
  - automl-pruner
triggers:
  - "inference latency"
  - "model optimization"
  - "mojo artifact"
  - "event loop blocking"
  - "cache busting"
  - "gin index"
  - "toast prevention"
  - "memory allocation"
  - "automl pruning"
  - "thread pool"
  - "connection pooling"
epics:
  - id: MLO-LOG-01
    name: Feature Store Schema & Index Optimization
    size: L
    stories: 3
    spike: SPK-MLO-LOG-01
  - id: MLO-PROC-01
    name: Inference Latency Reduction
    size: XL
    stories: 3
    spike: SPK-MLO-PROC-01
  - id: MLO-PROC-02
    name: Concurrency & Connection Management
    size: M
    stories: 3
    spike: SPK-MLO-PROC-02
  - id: MLO-DEV-01
    name: Model Quantization & Artifact Optimization
    size: L
    stories: 3
    spike: SPK-MLO-DEV-01
  - id: MLO-DEV-02
    name: AutoML Search Space Pruning
    size: M
    stories: 3
    spike: SPK-MLO-DEV-02
  - id: MLO-PHY-01
    name: Resource Allocation & Topology
    size: L
    stories: 3
    spike: SPK-MLO-PHY-01
  - id: MLO-SCN-01
    name: Production Validation Scenarios
    size: L
    stories: 3
    spike: SPK-MLO-SCN-01
scripts:
  - name: benchmark_gin_index.py
    superpower: gin-index-optimizer
  - name: validate_event_loop.py
    superpower: event-loop-guardian
  - name: calculate_memory_split.py
    superpower: memory-split-calculator
  - name: validate_mojo_artifact.py
    superpower: model-quantizer
  - name: test_cache_coherence.py
    superpower: cache-coherence-architect
checklists:
  - logical_view_ml_optimizer.md
  - process_view_ml_optimizer.md
  - development_view_ml_optimizer.md
  - physical_view_ml_optimizer.md
  - scenario_view_ml_optimizer.md
references:
  - asyncio_event_loop_physics.md
  - postgresql_jsonb_toast.md
  - mojo_vs_pojo_quantization.md
  - cache_busting_patterns.md
  - jvm_native_memory_split.md
```
