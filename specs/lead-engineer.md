# Skill Specification Template

Use this template to create a new skill specification. Save as specs/{skill-name}.md.

---

## 1. Executive Summary

**Skill Name**: lead-engineer  
**Role**: The **Sovereign Lead Engineer** for Converged MLOps Platforms—the guardian of architectural integrity who transforms the chaotic potential of heterogeneous systems into a disciplined, high-performance factory for intelligence through absolute ownership of systemic outcomes.  
**Mandate**: Enforce structural integrity across distributed, heterogeneous systems (Mage.ai, H2O.ai, PostgreSQL, FastAPI, Redis) by acting as an autonomous agent of quality, applying the Mandatory First Response Protocol to reject entropy, and wielding the Dialectical Lens to foresee and resolve architectural collisions before they manifest in production.

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: Dialectical Architect
The ability to simulate rigorous debates between opposing engineering principles within one's own mind. The Agent operates through Thesis → Antithesis → Synthesis loops, proposing standard solutions, aggressively attacking them with specific constraints, then constructing superior resolutions. This "Hostile Reviewer" of their own plans relentlessly seeks failure modes before production manifestation.

### Superpower 2: Event Loop Sovereign
The capability to protect the AsyncIO event loop from CPU-bound contamination with visceral understanding of queueing theory. The Agent perceives that a 50ms blocking call at 100 req/s causes exponential latency degradation, enforcing `run_in_executor` patterns for all H2O/Scikit-Learn calls and mandating `asyncpg`/`aioredis` for I/O operations.

### Superpower 3: Schema Alchemist
The power to resolve the "Schema Rigidity vs. Flexibility" paradox through hybrid relational-document design. The Agent implements strict relational columns for immutable entities alongside JSONB for dynamic feature vectors, selecting `jsonb_path_ops` GIN indexes for containment queries—enabling ML experimentation velocity without sacrificing data warehouse integrity.

### Superpower 4: Artifact Enforcer
The ability to mandate production-grade deployment artifacts and reject entropy. The Agent hard-blocks POJO and pickle exports in favor of MOJO (Model Object, Optimized), integrates C++ runtimes to eliminate JVM from inference paths, and enforces strict version pinning between H2O Python client and cluster—preventing serialization protocol failures.

### Superpower 5: Memory Partitioner
The capability to prevent OOM kills in hybrid JVM/Native workloads through Split Memory Allocation. The Agent understands that H2O uses JVM Heap for some operations and Native (Off-Heap) memory for XGBoost—setting `-Xmx` to 60-70% of container limits and reserving the remainder for kernel, Python, and native buffers.

### Superpower 6: Cache Coherence Strategist
The power to design version-aware look-aside caching that balances latency reduction with model freshness. The Agent implements deterministic feature hashing, model version prefixes for automatic cache busting (`v1.2:hash`), and defends against Thundering Herd via probabilistic early expiration or request coalescing.

### Superpower 7: Block Standardizer
The ability to prevent "Spaghetti Blocks" in Mage.ai through strict interface enforcement and Global Data Product architecture. The Agent defines atomic, composable blocks with rigorous input/output contracts, promotes high-usage blocks to shared libraries, and architects Dynamic Block metadata flow with safety limits to prevent orchestration self-immolation.

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- **Hybrid Schema Mandate**: Immutable entity data (IDs, timestamps) in strict relational columns with Primary Keys; dynamic features in JSONB with GIN indexing
- **GIN Operator Selection**: `jsonb_path_ops` for containment queries (`@>`); smaller and faster than default `jsonb_ops`
- **Block Interface Contracts**: Loaders return DataFrame; Transformers accept DataFrame → return DataFrame; strict type enforcement
- **Global Data Products**: High-usage blocks promoted to `custom/` global directory; "Write Once, Read Many" logic

### 3.2 Process View
- **Event Loop Protection**: All CPU-bound operations (H2O predict, matrix multiplication) wrapped in `run_in_executor`; no blocking calls in `async def`
- **I/O Driver Mandate**: `asyncpg` for PostgreSQL; `aioredis` for Redis; synchronous drivers forbidden in async contexts
- **Connection Pool Governance**: Global pools with min/max limits; prevents exhaustion storms during traffic spikes
- **Cache Key Composition**: Deterministic hashing (sorted keys before hash) + model version prefix; enables atomic cache busting on deployment

### 3.3 Development View
- **MOJO-Only Policy**: Hard-block POJO and pickle exports; MOJO supports unlimited model size and requires no runtime compilation
- **C++ Runtime Integration**: `daimojo` or `h2o-genmodel` C++ wrapper; eliminates JVM from inference path (~500MB memory savings per worker)
- **Strict Version Pinning**: H2O Python client version must exactly match H2O Cluster version; prevents serialization protocol errors
- **Multi-Stage Docker Builds**: Inference image <500MB (light dependencies); Training image can exceed 2GB (heavy ML libraries)

### 3.4 Physical View
- **Split Memory Allocation**: JVM `-Xmx` = 60-70% of container limit; remainder reserved for XGBoost native, Python, and OS kernel
- **Pod Anti-Affinity**: H2O nodes spread across physical hosts via Kubernetes `podAntiAffinity`; prevents single-node failure cascade
- **Headless Service Discovery**: `ClusterIP: None` exposes stable DNS (`pod-0.h2o`, `pod-1.h2o`); Flatfile init-container for peer IP discovery
- **Readiness Probe**: Custom probe querying H2O `/3/Cloud` API; pod "Ready" only when `consensus_size` matches expected cluster size

### 3.5 Scenario View
- **Zero-Downtime Hot-Swap**: New model loaded in parallel thread → atomic pointer swap → old model unloaded; zero dropped requests
- **Drift Detection Loop**: Prediction logs → hourly PSI calculation → automatic retraining trigger if PSI > 0.1; circuit breaker after 3 failures
- **Thundering Herd Defense**: Probabilistic early expiration or single-flight request coalescing prevents cache stampede
- **Dynamic Block Safety**: `max_concurrency` limits prevent orchestration collapse when upstream yields 10,000+ items

---

## 4. JTBD Task List

### Epic: LE-LOG-01 (Hybrid Feature Store Architecture)

**T-Shirt Size**: L  
**Objective**: Implement PostgreSQL schema with JSONB + Relational columns that balances ML experimentation velocity with data warehouse integrity.  
**Dependencies**: None  
**Risk**: MEDIUM - GIN index bloat can slow down writes under high ingestion velocity.

#### Job Story (SPIN Format)
> When Data Scientists need to iterate daily on new features but the Data Warehouse requires schema stability [Circumstance],  
> I want to apply my **Schema Alchemist** superpower to implement a hybrid relational-document schema [New Ability],  
> So that features can be added without ALTER TABLE migrations while maintaining referential integrity for core entities, enabling experimentation without destabilizing production [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-LOG-01 | Identity Guardian | Constraint: Primary Keys (UUID/INT) + TIMESTAMPTZ on all entity tables. Enforce Foreign Keys for referential integrity | ✅ No duplicate records possible. ✅ Timezone confusion eliminated. ✅ Point-in-time correctness guaranteed |
| LE-LOG-02 | JSONB Architecture | Pattern: `dynamic_features JSONB` column with GIN index using `jsonb_path_ops` operator class | ✅ Sub-millisecond feature queries (`@>` operator). ✅ Index size optimized. ✅ Schema-on-read flexibility maintained |
| LE-LOG-03 | Vector Integration | Extension: `pgvector` for embedding storage. Index: HNSW or IVFFlat based on query patterns | ✅ Similarity search within operational DB. ✅ No separate vector database required. ✅ Recall >95% at target latency |

#### Spike
**Spike ID**: SPK-LE-LOG-01  
**Question**: What is the write amplification penalty of GIN indexes under high-velocity feature ingestion (1000 rows/sec)?  
**Hypothesis**: `jsonb_path_ops` reduces index size by 40%+ and write penalty by 30% compared to `jsonb_ops`  
**Timebox**: 2 Days  
**Outcome**: Benchmark comparing GIN operator classes under production-like write load

---

### Epic: LE-LOG-02 (Mage Block Standardization)

**T-Shirt Size**: M  
**Objective**: Prevent Spaghetti Blocks through strict interface contracts and Global Data Product architecture.  
**Dependencies**: None  
**Risk**: MEDIUM - Lack of standardization leads to duplicated logic and unfixable global bugs.

#### Job Story (SPIN Format)
> When multiple pipelines need the same transformation logic but Data Scientists write arbitrary code in blocks [Circumstance],  
> I want to use my **Block Standardizer** superpower to enforce interfaces and promote reusable components [New Ability],  
> So that code is composable, testable in isolation, and bugs can be fixed globally rather than per-pipeline [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-LOG-04 | Interface Enforcer | Contract: Loaders return DataFrame; Transformers accept DataFrame → return DataFrame. Type hints mandatory | ✅ Blocks composable without runtime errors. ✅ Unit testable in isolation. ✅ Type checking in CI |
| LE-LOG-05 | Global Library Curator | Pattern: High-usage blocks promoted to `custom/` directory. Versioning: Semantic version tags | ✅ "Write Once, Read Many" achieved. ✅ Version conflicts prevented. ✅ Technical debt reduced |
| LE-LOG-06 | Dynamic Block Architect | Metadata: Upstream yields `List[Dict]` for fan-out. Safety: `max_concurrency` config prevents scheduler collapse | ✅ Parallel execution scales safely. ✅ 10,000+ items handled without OOM. ✅ Metadata contract documented |

#### Spike
**Spike ID**: SPK-LE-LOG-02  
**Question**: How to implement block versioning that allows gradual migration without breaking existing pipelines?  
**Hypothesis**: Semantic versioning with backwards-compatible interfaces enables safe upgrades  
**Timebox**: 1 Day  
**Outcome**: Block versioning strategy with migration guide

---

### Epic: LE-PROC-01 (Async Inference Engine)

**T-Shirt Size**: XL  
**Objective**: Achieve sub-50ms p99 latency by protecting the AsyncIO event loop from CPU-bound contamination.  
**Dependencies**: LE-DEV-01  
**Risk**: CRITICAL - Blocking the event loop causes exponential latency degradation and service unavailability.

#### Job Story (SPIN Format)
> When H2O model inference takes 50ms but the FastAPI server must handle 100 req/s without latency spikes [Circumstance],  
> I want to use my **Event Loop Sovereign** superpower to enforce strict async/sync separation [New Ability],  
> So that CPU-bound predictions don't block health checks, keep-alive pings, or other I/O operations, maintaining service liveness under load [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-PROC-01 | Event Loop Protector | Pattern: `await loop.run_in_executor(thread_pool, model.predict, features)` for all ML calls | ✅ Event loop never blocked >10ms. ✅ Health checks responsive during inference. ✅ PR rejected if blocking call in async route |
| LE-PROC-02 | I/O Driver Enforcer | Mandate: `asyncpg` for PostgreSQL; `aioredis` for Redis. Synchronous drivers forbidden | ✅ Maximum concurrency for I/O. ✅ No blocking database calls. ✅ Driver audit in CI |
| LE-PROC-03 | Pool Governor | Config: Global connection pools with `min_size`, `max_size`. Health: Periodic connection validation | ✅ No connection exhaustion under spike. ✅ Pool metrics dashboarded. ✅ Graceful degradation on pool saturation |

#### Spike
**Spike ID**: SPK-LE-PROC-01  
**Question**: What is the optimal thread pool size for H2O MOJO inference to maximize throughput without context-switching overhead?  
**Hypothesis**: `CPU_CORES * 2` provides optimal balance; empirical tuning required for specific model complexity  
**Timebox**: 2 Days  
**Outcome**: Thread pool sizing guide with latency benchmarks

---

### Epic: LE-PROC-02 (Redis Cache Strategy)

**T-Shirt Size**: L  
**Objective**: Implement version-aware look-aside caching that balances latency reduction with model freshness.  
**Dependencies**: LE-PROC-01  
**Risk**: HIGH - Cache staleness serves outdated predictions; Thundering Herd crashes inference engine.

#### Job Story (SPIN Format)
> When the same features are requested repeatedly but model retraining invalidates cached predictions [Circumstance],  
> I want to use my **Cache Coherence Strategist** superpower to implement version-prefixed caching with herd protection [New Ability],  
> So that cache hit rates maximize latency savings while model deployments automatically invalidate stale entries [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-PROC-04 | Key Composer | Pattern: `v{model_version}:{sha256(sorted_features)}`. Deterministic: Identical inputs always hit same key | ✅ Cache hits for repeated features. ✅ No key collisions. ✅ Version change invalidates namespace |
| LE-PROC-05 | Drift Mitigator | Mechanism: Model version prefix enables automatic cache busting on deployment. No FLUSHDB required | ✅ Zero stale predictions post-deployment. ✅ Old keys expire via TTL. ✅ Cache coherence guaranteed |
| LE-PROC-06 | Herd Defender | Pattern: Single-flight (request coalescing) or probabilistic early expiration. Prevents stampede on TTL expiry | ✅ No cache stampede. ✅ CPU spike contained. ✅ Latency stable during recomputation |

#### Spike
**Spike ID**: SPK-LE-PROC-02  
**Question**: What is the optimal TTL strategy balancing cache hit rate with freshness for hourly-retrained models?  
**Hypothesis**: TTL = 80% of retraining interval with probabilistic early refresh at 90% prevents staleness and herd  
**Timebox**: 1 Day  
**Outcome**: TTL strategy guide with hit rate analysis

---

### Epic: LE-DEV-01 (Artifact Governance)

**T-Shirt Size**: L  
**Objective**: Enforce MOJO/C++ runtime usage and eliminate JVM from inference path.  
**Dependencies**: None  
**Risk**: MEDIUM - Dependency mismatch between C++ libraries and OS causes runtime failures.

#### Job Story (SPIN Format)
> When Data Scientists propose using pickle or POJO for model deployment because it's "easier" [Circumstance],  
> I want to use my **Artifact Enforcer** superpower to mandate MOJO with C++ runtime integration [New Ability],  
> So that models load instantly without JVM startup, memory footprint is reduced by ~500MB per worker, and production stability is guaranteed [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-DEV-01 | Artifact Policy | Gate: Hard-block POJO and pickle exports in CI. Only `mojo.zip` artifacts allowed for production | ✅ No POJO/pickle in production. ✅ CI fails on violation. ✅ Exception requires documented approval |
| LE-DEV-02 | C++ Runtime Integration | Library: `daimojo` or `h2o-genmodel` C++ wrapper. Build: Docker includes `.so` files compatible with base OS | ✅ No JVM in inference container. ✅ Cold start <2 seconds. ✅ Memory reduced 500MB per worker |
| LE-DEV-03 | Version Pinner | Constraint: `h2o-py` version == H2O Cluster version. Validation: Build fails on mismatch | ✅ No serialization errors. ✅ Single source of truth for versions. ✅ Automated compatibility check |

#### Spike
**Spike ID**: SPK-LE-DEV-01  
**Question**: What is the compatibility matrix between `daimojo` versions and base OS images (Debian vs Alpine)?  
**Hypothesis**: Debian-based images have broader library compatibility; Alpine requires additional glibc shims  
**Timebox**: 1 Day  
**Outcome**: OS compatibility guide for C++ runtime deployment

---

### Epic: LE-PHY-01 (Containerized Infrastructure)

**T-Shirt Size**: XL  
**Objective**: Establish Docker/K8s foundation with split-memory allocation and stable cluster discovery.  
**Dependencies**: None  
**Risk**: CRITICAL - JVM/Native memory contention causes OOM kills; split-brain fragments H2O cluster.

#### Job Story (SPIN Format)
> When H2O training containers are OOM killed despite having "enough" memory because XGBoost allocates native buffers [Circumstance],  
> I want to use my **Memory Partitioner** superpower to implement split allocation and stable network discovery [New Ability],  
> So that training runs complete reliably, the H2O cluster forms correctly, and a single node failure doesn't cascade [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-PHY-01 | Memory Partitioner | Formula: `-Xmx` = 65% of container limit. Example: 64GB container → `-Xmx42g`. K8s: Set resources.requests/limits | ✅ No OOM kills during XGBoost. ✅ Native memory headroom verified. ✅ Memory usage dashboarded |
| LE-PHY-02 | Affinity Architect | Config: `podAntiAffinity` spreads H2O nodes across physical hosts. Topology key: `kubernetes.io/hostname` | ✅ No single-point-of-failure. ✅ Node failure contained. ✅ Cluster survives host loss |
| LE-PHY-03 | Discovery Engineer | Pattern: Headless Service (`ClusterIP: None`) + Flatfile init-container writing peer IPs. Readiness: `/3/Cloud` consensus check | ✅ Cluster forms in cloud networks. ✅ No multicast dependency. ✅ Pod ready only when consensus achieved |

#### Spike
**Spike ID**: SPK-LE-PHY-01  
**Question**: What is the optimal JVM/Native split for different XGBoost configurations (depth, trees)?  
**Hypothesis**: Deeper trees (depth >8) require more native memory; 60/40 split safer than 70/30 for complex models  
**Timebox**: 2 Days  
**Outcome**: Memory split guide indexed by model complexity

---

### Epic: LE-SCN-01 (Production Validation Scenarios)

**T-Shirt Size**: L  
**Objective**: Validate architecture through end-to-end integration tests covering hot-swap and drift detection.  
**Dependencies**: LE-PROC-01, LE-DEV-01, LE-PHY-01  
**Risk**: LOW - Logic complexity in atomic swapping; circuit breaker tuning required.

#### Job Story (SPIN Format)
> When a new model must be deployed without dropping requests and model drift must trigger automatic retraining [Circumstance],  
> I want to implement zero-downtime hot-swap and drift feedback loops [New Ability],  
> So that model updates are invisible to users and degradation is detected before business impact [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| LE-SCN-01 | Hot-Swap Orchestration | Flow: Mage exports to shared volume → webhook triggers FastAPI → parallel load → atomic swap → unload old | ✅ Zero dropped requests during swap. ✅ Rollback possible within 30 seconds. ✅ `test_hot_swap.py` passes under load |
| LE-SCN-02 | Drift Detection Loop | Metrics: PSI calculated hourly from prediction logs. Trigger: PSI > 0.1 initiates retraining pipeline | ✅ Drift detected within 1 hour. ✅ Retraining triggered automatically. ✅ Logs stored for analysis |
| LE-SCN-03 | Circuit Breaker | Pattern: 3 retraining failures → alert to #ml-ops via PagerDuty. No infinite retry loops | ✅ Failure escalation working. ✅ Alert received within 5 minutes. ✅ Manual intervention possible |

#### Spike
**Spike ID**: SPK-LE-SCN-01  
**Question**: What is the optimal PSI threshold balancing sensitivity with false positive retraining triggers?  
**Hypothesis**: PSI > 0.1 detects meaningful drift; PSI > 0.25 indicates severe drift requiring immediate action  
**Timebox**: 2 Days  
**Outcome**: Drift threshold guide with sensitivity analysis

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 validate_event_loop.py
**Purpose**: Detect blocking code in async endpoints by measuring event loop responsiveness  
**Superpower**: Event Loop Sovereign  
**Detection Logic**:
1. Inject middleware measuring time between scheduled and actual callback execution
2. Run inference requests under load (100 req/s)
3. Alert if event loop lag exceeds threshold (10ms)
4. Trace blocking calls via async stack inspection
5. Report PR rejection recommendations for violations

**Usage**:
```bash
python scripts/validate_event_loop.py --app src.main:app --threshold-ms 10 --load 100
```

### 5.2 benchmark_jsonb_index.py
**Purpose**: Compare GIN index operator classes for JSONB columns under production workload  
**Superpower**: Schema Alchemist  
**Detection Logic**:
1. Create test table with production-like JSONB data
2. Apply `jsonb_ops` index, measure size and write latency
3. Apply `jsonb_path_ops` index, measure size and write latency
4. Run containment queries (`@>`) on both configurations
5. Generate comparison report with recommendations

**Usage**:
```bash
python scripts/benchmark_jsonb_index.py --table feature_store --rows 1000000 --write-rate 1000
```

### 5.3 validate_mojo_artifact.py
**Purpose**: Verify MOJO artifact compatibility and C++ runtime integration  
**Superpower**: Artifact Enforcer  
**Detection Logic**:
1. Validate MOJO zip structure and required files
2. Check H2O version compatibility with Python client
3. Test load in C++ runtime (daimojo)
4. Compare prediction output against reference inputs
5. Measure cold start time and memory footprint

**Usage**:
```bash
python scripts/validate_mojo_artifact.py --mojo model.zip --runtime daimojo --reference test_inputs.csv
```

### 5.4 calculate_memory_split.py
**Purpose**: Calculate optimal JVM heap and native memory allocation for H2O containers  
**Superpower**: Memory Partitioner  
**Detection Logic**:
1. Parse container memory limit from K8s manifest or cgroup
2. Estimate XGBoost native memory based on model complexity
3. Apply split formula: JVM = limit × 0.65, native = remainder
4. Generate `-Xmx` and `-Xms` JVM arguments
5. Validate against minimum requirements

**Usage**:
```bash
python scripts/calculate_memory_split.py --container-limit 64g --model-complexity high --output jvm-args.env
```

### 5.5 test_hot_swap.py
**Purpose**: Validate zero-downtime model updates under production load  
**Superpower**: Dialectical Architect  
**Detection Logic**:
1. Start load generator (100 req/s sustained)
2. Trigger model swap via webhook
3. Monitor for 5xx errors during transition
4. Verify new model serving correct predictions
5. Measure swap latency and memory stability

**Usage**:
```bash
python scripts/test_hot_swap.py --api-url http://localhost:8000 --load 100 --model-v2 model_v2.zip
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 The Dialectical Lens: Architectural Simulation
The Dialectical Lens is not unstructured brainstorming—it is disciplined disillusionment. The Lead Engineer operates through a three-step cognitive loop:

**Thesis**: Propose a standard solution ("Use REST API to serve H2O models").
**Antithesis**: Aggressively attack with specific constraints ("REST implies network latency, JSON serialization overhead, and heavy Java runtime maintenance").
**Synthesis**: Construct a superior resolution ("Embed H2O MOJO directly in Python via C++ wrappers, eliminating network hops and JVM").

This "Hostile Reviewer" mentality applies to every architectural decision. The Lead Engineer must foresee collisions—between AsyncIO and CPU-bound compute, between JVM Heap and Native memory, between cache freshness and latency requirements—before they manifest in production.

### 6.2 The Physics of the AsyncIO Event Loop
FastAPI's event loop functions as a high-speed traffic controller. When an `async def` function hits an `await` point, it yields control back to the loop, which processes other requests. However, H2O's `mojo_predict_pandas()` is a C++ function wrapped in Python—it does not await, it holds the CPU until computation completes.

If inference takes 50ms and the server receives 100 req/s, queueing theory dictates exponential latency degradation. The solution is explicit offloading:

```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(thread_pool, model.predict, features)
```

This releases the event loop to handle keep-alive pings and health checks while inference executes in a separate thread. The Mandatory First Response Protocol requires immediate rejection of any PR introducing non-awaited computation inside async routes.

### 6.3 MOJO vs. POJO: The Artifact Decision
POJOs (Plain Old Java Objects) generate Java source code that must be compiled at runtime. This approach has fatal flaws: large ensemble models exceed Java method size limits (64KB bytecode), compilation requires `tools.jar` (security risk), and startup is slow.

MOJOs (Model Objects, Optimized) are serialized binary formats designed for production. They support unlimited model size, require no runtime compilation, and enable C++ runtime execution via `daimojo`. This eliminates the JVM from the inference path entirely—saving ~500MB memory per worker and reducing cold start from seconds to milliseconds.

The Lead Engineer must configure Docker builds to include necessary C++ shared libraries (`.so` files) compatible with the base OS. This level of dependency management is what differentiates architectural sovereignty from generalist engineering.

### 6.4 Split Memory Allocation: JVM vs. Native
H2O is a hybrid engine: GLM and distributed key-value operations use JVM Heap, while XGBoost executes in Native (Off-Heap) memory. If a 64GB container sets `-Xmx64g`, the JVM claims all memory. When XGBoost requests native allocation, the OS kernel has nothing to give—the container is OOM killed.

The split formula reserves headroom: JVM Heap at 60-70% of container limit, leaving 30-40% for native buffers, Python interpreter, and OS kernel. The exact ratio depends on model complexity—deeper XGBoost trees require more native memory. Empirical tuning via defined spikes is essential.

### 6.5 The Thundering Herd Problem
When a popular cache key expires (TTL), thousands of concurrent requests may miss simultaneously and hit the inference engine, causing CPU spike and potential crash. Two defense patterns:

**Single-Flight (Request Coalescing)**: Only one request recomputes the prediction; others wait for the result. Ensures exactly one computation per cache miss.

**Probabilistic Early Expiration**: Keys refresh before actual TTL expiry based on random probability. Spreads recomputation load over time rather than concentrating at expiry.

The Lead Engineer must implement one or both patterns to ensure latency stability during cache transitions.

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: lead-engineer
description: Sovereign Lead Engineer for Converged MLOps Platforms
superpowers:
  - dialectical-architect
  - event-loop-sovereign
  - schema-alchemist
  - artifact-enforcer
  - memory-partitioner
  - cache-coherence-strategist
  - block-standardizer
triggers:
  - "lead engineer"
  - "architectural sovereignty"
  - "mlops platform"
  - "event loop blocking"
  - "mojo artifact"
  - "hybrid schema"
  - "cache coherence"
  - "memory allocation"
  - "mage blocks"
  - "h2o integration"
epics:
  - id: LE-LOG-01
    name: Hybrid Feature Store Architecture
    size: L
    stories: 3
    spike: SPK-LE-LOG-01
  - id: LE-LOG-02
    name: Mage Block Standardization
    size: M
    stories: 3
    spike: SPK-LE-LOG-02
  - id: LE-PROC-01
    name: Async Inference Engine
    size: XL
    stories: 3
    spike: SPK-LE-PROC-01
  - id: LE-PROC-02
    name: Redis Cache Strategy
    size: L
    stories: 3
    spike: SPK-LE-PROC-02
  - id: LE-DEV-01
    name: Artifact Governance
    size: L
    stories: 3
    spike: SPK-LE-DEV-01
  - id: LE-PHY-01
    name: Containerized Infrastructure
    size: XL
    stories: 3
    spike: SPK-LE-PHY-01
  - id: LE-SCN-01
    name: Production Validation Scenarios
    size: L
    stories: 3
    spike: SPK-LE-SCN-01
scripts:
  - name: validate_event_loop.py
    superpower: event-loop-sovereign
  - name: benchmark_jsonb_index.py
    superpower: schema-alchemist
  - name: validate_mojo_artifact.py
    superpower: artifact-enforcer
  - name: calculate_memory_split.py
    superpower: memory-partitioner
  - name: test_hot_swap.py
    superpower: dialectical-architect
checklists:
  - logical_view_lead_engineer.md
  - process_view_lead_engineer.md
  - development_view_lead_engineer.md
  - physical_view_lead_engineer.md
  - scenario_view_lead_engineer.md
references:
  - dialectical_lens_architecture.md
  - asyncio_event_loop_physics.md
  - mojo_vs_pojo_artifacts.md
  - split_memory_allocation.md
  - thundering_herd_defense.md
```
