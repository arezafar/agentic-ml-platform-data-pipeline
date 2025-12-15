# Skill Specification Template

Use this template to create a new skill specification. Save as specs/{skill-name}.md.

---

## 1. Executive Summary

**Skill Name**: database-optimizer  
**Role**: The **Autonomous Database Optimizer Agent** for converged PostgreSQL Data Warehouses—an enforcer of holistic performance optimization that transcends manual tuning to become the guardian of database physics.  
**Mandate**: Continuously optimize database performance across hybrid relational/JSONB schemas, ML workloads, and high-concurrency inference through autonomous OODA loops, arbitrating between write-heavy ETL ingestion from Mage.ai and sub-50ms inference queries from FastAPI.

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: Hybrid Schema Engineer
The ability to perceive and arbitrate the physical storage conflict between rigid relational columns and flexible JSONB documents. The Agent visualizes storage overhead down to the byte level, understanding that repeating JSONB key strings across billions of rows consumes terabytes of disk bandwidth. It enforces "Key Abbreviation" protocols and orchestrates "Column Extraction" promotions based on access pattern analysis, preventing the "schema drift" that turns flexible schemas into performance cliffs.

### Superpower 2: TOAST Whisperer
The capability to detect and mitigate the hidden I/O penalty of TOAST (The Oversized-Attribute Storage Technique). The Agent monitors pg_toast tables, understands compression algorithm trade-offs between pglz and lz4, and manipulates column STORAGE strategies. It prevents the secondary lookup penalty that turns sub-millisecond queries into multi-second full table scans when large feature vectors are stored out-of-line.

### Superpower 3: GIN Index Tuner
Focuses on the Physical View. The ability to tune Generalized Inverted Indexes for high-velocity JSONB writes. The Agent understands write amplification at the posting list level, monitors gin_pending_list_limit, and selects between jsonb_ops and jsonb_path_ops operator classes. It prevents the "pending list explosion" that causes unpredictable latency spikes during bulk feature ingestion.

### Superpower 4: Vector Navigator
The power to navigate the semantic search landscape of pgvector embeddings. The Agent distinguishes between HNSW's graph-based high-performance recall and IVFFlat's cluster-based memory efficiency. It tunes m and ef_construction parameters, understanding that the choice determines whether the system supports real-time model updates or requires scheduled index rebuilds.

### Superpower 5: Plan Decoder
The ability to deconstruct EXPLAIN (ANALYZE, BUFFERS) output to reveal ground truth. The Agent identifies Seq Scans on billion-row tables, analyzes shared hit/read ratios to diagnose memory pressure, and flags Bitmap Heap Scan operations that indicate low correlation between index and heap. It creates Extended Statistics on JSONB functional expressions to correct the planner's selectivity misconceptions.

### Superpower 6: WAL Orchestrator
Controls the Write-Ahead Log lifecycle for bulk loading scenarios. The Agent tunes checkpoint_completion_target and max_wal_size to prevent the "sawtooth" I/O pattern that stalls concurrent inference queries. It enables lz4 WAL compression and mandates UNLOGGED tables for transient Mage staging data, trading durability for raw ingestion speed.

### Superpower 7: Concurrency Architect
Designs the interface between PostgreSQL's process model and FastAPI's async event loop. The Agent calculates optimal connection pool sizes using core-based formulas, enforces asyncpg over psycopg2, and implements cache busting version keys. It prevents the "event loop blockage" that occurs when synchronous database calls freeze the entire application.

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- **Hybrid Schema Mandate**: Core business keys (user_id, event_time) must be relational columns with primary keys; experimental ML features must reside in JSONB columns
- **Key Abbreviation Protocol**: JSONB keys must be <= 3 characters (e.g., "v" not "value") to mitigate storage overhead
- **Column Extraction**: Keys accessed in >80% of queries must be promoted to relational columns based on pg_stats analysis
- **Schema-on-Read Validation**: Pydantic models must enforce JSONB structure at ingestion; deviations trigger alerts

### 3.2 Process View
- **Async Driver Constraint**: All FastAPI connections must use asyncpg; psycopg2 is forbidden in async contexts
- **WAL Throttling**: max_wal_size must be >= 50GB for bulk ingestion; checkpoint_completion_target = 0.9
- **Partition Pruning**: All time-series queries must include partition key in WHERE clause; pg_partman automates lifecycle
- **Vacuum Aggressiveness**: autovacuum_vacuum_scale_factor = 0.02 for tables with high update rates (n_tup_upd > 1M/day)

### 3.3 Development View
- **Mage Block Atomicity**: Transform blocks must return DataFrames; I/O side effects belong in Exporters only
- **Query Rewriting**: CTEs must be verified for MATERIALIZED behavior; LATERAL joins preferred for JSONB array unnesting
- **Pydantic Contracts**: All JSONB insertion paths must validate against schema registry models
- **Versioned Cache Keys**: Cache keys must include model_version prefix for instant invalidation

### 3.4 Physical View
- **TOAST Strategy**: Columns >2KB must use lz4 compression; frequently accessed columns use STORAGE MAIN
- **Column Tetris**: DDL must order columns as: wide fixed-length (bigint, timestamp) → narrow fixed-length → variable-length (jsonb, text)
- **GIN Pending List**: gin_pending_list_limit tuned per table based on write velocity (default 4MB, high-write tables: 16MB)
- **Memory Allocation**: Container memory limit must be >= JVM_Heap + Native_Overhead; JVM_Heap <= 70% of limit

### 3.5 Scenario View
- **Drift Handling**: System must support automated retraining triggered by data drift detection in pg_stat_statements query patterns
- **Zero-Downtime Updates**: MOJO artifact swaps must be decoupled from database migrations; cache version keys enable instant cutover
- **Cache Warmup**: New model deployments must trigger background cache population before serving production traffic

---

## 4. JTBD Task List

### Epic: DB-OPT-LOG-01 (Hybrid Schema Integrity Enforcement)

**T-Shirt Size**: L  
**Objective**: Enforce hybrid relational/JSONB schema design to balance analytical flexibility with storage/query performance.  
**Dependencies**: None  
**Risk**: HIGH - Poor JSONB design causes 10-100x storage bloat and full table scans.

#### Job Story (SPIN Format)
> When a data scientist adds experimental features to the JSONB column without key abbreviation [Circumstance],  
> I want to apply my **Hybrid Schema Engineer** superpower to detect storage overhead and enforce column extraction rules [New Ability],  
> So that I can prevent TOAST table explosion and ensure GIN indexes remain cache-efficient, feeling confident that the system scales to billions of rows [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DB-OPT-01 | Key Abbreviation Enforcement | Constraint: JSONB keys <= 3 chars. Tool: Custom SQL function analyzing pg_stats | ✅ Migration flagged if avg key length > 3. ✅ Alert triggers when key repetition exceeds 1M instances. ✅ Compression ratio improves >20% |
| DB-OPT-02 | Column Extraction Decision | Pattern: Analyze pg_stat_user_tables.idx_scan vs seq_scan. Tool: Python script monitoring access patterns | ✅ Script identifies keys queried in >80% of operations. ✅ Promotion DDL generated automatically. ✅ Query latency drops >50% post-promotion |
| DB-OPT-03 | TOAST Threshold Monitoring | Constraint: Monitor pg_class.reltoastrelid size. Tool: daily cron job | ✅ Alert fires when toast table >10% of main table. ✅ STORAGE MAIN strategy applied to hot columns. ✅ lz4 compression enabled on large columns |

#### Spike
**Spike ID**: SPK-DB-OPT-01  
**Question**: How to automatically detect "deeply nested JSON" anti-patterns that defeat GIN indexing?  
**Hypothesis**: Recursive CTE on jsonb_object_keys can calculate max depth; depth >3 triggers manual review  
**Timebox**: 2 Days  
**Outcome**: Python script that flags migrations with nested JSONB structures

---

### Epic: DB-OPT-IDX-01 (Advanced Indexing Strategy)

**T-Shirt Size**: XL  
**Objective**: Deploy specialized indexes (GIN, HNSW, Partial) for JSONB, vectors, and high-concurrency lookups.  
**Dependencies**: DB-OPT-LOG-01  
**Risk**: CRITICAL - Wrong index type causes 100x slower queries or write stalls.

#### Job Story (SPIN Format)
> When the inference API experiences p95 latency spikes during feature ingestion [Circumstance],  
> I want to use my **GIN Index Tuner** superpower to analyze pending list merges [New Ability],  
> So that I can tune fastupdate thresholds and prevent the event loop from blocking on index maintenance, ensuring stable sub-50ms latency [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DB-OPT-04 | GIN Operator Class Selection | Constraint: Use jsonb_path_ops if @> is primary operator. Tool: log analysis of query patterns | ✅ Query log shows >90% containment queries. ✅ Index size reduced 30-50% vs jsonb_ops. ✅ Build time improved >2x |
| DB-OPT-05 | HNSW Parameter Tuning | Pattern: m=16, ef_construction=64 for hot vectors. Tool: pgvector CREATE INDEX with hnsw | ✅ Recall@10 >0.95 on benchmark queries. ✅ QPS sustains 1000+ under load. ✅ Index updates don't degrade performance |
| DB-OPT-06 | Covering Index for Lookups | Constraint: INCLUDE payload columns for index-only scans. Tool: EXPLAIN (BUFFERS) verification | ✅ Buffers number shows zero heap hits. ✅ Latency <5ms for point lookups. ✅ Visibility map is 100% all-visible |

#### Spike
**Spike ID**: SPK-DB-OPT-02  
**Question**: Can we predict GIN index bloat from write velocity without waiting for pg_bloat_check?  
**Hypothesis**: Monitoring pg_stat_user_indexes.idx_tup_fetch vs idx_scan reveals write amplification patterns  
**Timebox**: 3 Days  
**Outcome**: Grafana dashboard showing real-time GIN health metrics

---

### Epic: DB-OPT-QUERY-01 (Query Plan Optimization)

**T-Shirt Size**: L  
**Objective**: Correct query planner misconceptions using Extended Statistics and execution plan analysis.  
**Dependencies**: DB-OPT-IDX-01  
**Risk**: HIGH - Poor selectivity estimates cause catastrophic join strategies.

#### Job Story (SPIN Format)
> When an AutoML query joins the features table with predictions [Circumstance],  
> I want to apply my **Plan Decoder** superpower to verify Nested Loop vs Hash Join selection [New Ability],  
> So that I can create Extended Statistics on JSONB expressions, preventing 10-minute queries and ensuring training jobs complete on schedule [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DB-OPT-07 | Extended Statistics on JSONB | Constraint: CREATE STATISTICS on (data ->> 'serviceId'). Tool: analyze on functional expression | ✅ Planner estimates match actual row counts within 10%. ✅ No more Nested Loop on million-row tables. ✅ Training query runtime <5 min |
| DB-OPT-08 | Buffer Hit Ratio Analysis | Pattern: shared_blks_hit / (hit+read) > 99%. Tool: pg_stat_statements | ✅ Queries with <99% hit ratio flagged. ✅ shared_buffers sized to capture working set. ✅ Cache warming script preloads hot data |
| DB-OPT-09 | CTE Inlining Verification | Constraint: Remove MATERIALIZED if blocking predicate pushdown. Tool: EXPLAIN output analysis | ✅ Predicate appears in scan node below CTE. ✅ Query runtime reduced >50%. ✅ No semantic change in results |

#### Spike
**Spike ID**: SPK-DB-OPT-03  
**Question**: Can AST parsing of SQLAlchemy queries detect anti-patterns before execution?  
**Hypothesis**: regex for ->> in WHERE without functional index flag can catch 80% of issues in CI  
**Timebox**: 1 Day  
**Outcome**: flake8 plugin for SQL anti-patterns

---

### Epic: DB-OPT-WRITE-01 (Write-Heavy Orchestration)

**T-Shirt Size**: XL  
**Objective**: Tune WAL, partitioning, and vacuum to support 100K+ row/sec ingestion without degrading reads.  
**Dependencies**: None  
**Risk**: CRITICAL - Checkpoint spikes cause cascading timeouts in inference layer.

#### Job Story (SPIN Format)
> When the Mage pipeline bulk loads 10M rows for model retraining [Circumstance],  
> I want to use my **WAL Orchestrator** superpower to spread checkpoint I/O over time [New Ability],  
> So that I can prevent the "sawtooth" latency pattern, ensuring the inference API maintains p99 <100ms during ETL [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DB-OPT-10 | Checkpoint Smoothing | Constraint: max_wal_size=50GB, checkpoint_completion_target=0.9. Tool: pg_stat_bgwriter | ✅ Checkpoint write duration <1% of interval. ✅ No backend_write spikes >100ms. ✅ Inference latency stable during bulk load |
| DB-OPT-11 | Partition Lifecycle Automation | Pattern: pg_partman creates 30-day future partitions. Tool: scheduled maintenance | ✅ No manual partition creation. ✅ Pruning confirmed in EXPLAIN. ✅ Detached partitions archived to S3 |
| DB-OPT-12 | Autovacuum Aggressiveness | Constraint: autovacuum_vacuum_scale_factor=0.02 for hot tables. Tool: pg_stat_user_tables | ✅ Dead tuples <1% of live tuples. ✅ No table bloat >20%. ✅ VACUUM never runs during peak hours |

#### Spike
**Spike ID**: SPK-DB-OPT-04  
**Question**: Can UNLOGGED tables for Mage staging survive pod restarts without data loss?  
**Hypothesis**: Since Mage blocks are idempotent, transient data can be rebuilt; we just need to detect when rebuild is required  
**Timebox**: 2 Days  
**Outcome**: Decision matrix for when UNLOGGED is safe vs when WAL-logged is required

---

### Epic: DB-OPT-CONN-01 (Concurrency and Application Interface)

**T-Shirt Size**: M  
**Objective**: Design async connection pooling and caching patterns that respect both database limits and FastAPI event loop.  
**Dependencies**: DB-OPT-WRITE-01  
**Risk**: MEDIUM - Pool exhaustion causes connection refused errors.

#### Job Story (SPIN Format)
> When the inference API scales to 1000 concurrent requests [Circumstance],  
> I want to apply my **Concurrency Architect** superpower to calculate optimal pool size [New Ability],  
> So that I can prevent connection churn and OOM kills, ensuring the system remains stable under load and avoiding 3am pages [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DB-OPT-13 | Pool Sizing Formula | Constraint: pool_size = (core_count * 2) + effective_spindle_count. Tool: asyncpg connection pool | ✅ Pool never exceeds 50 connections total. ✅ Queue timeouts <5s. ✅ No connection refused errors |
| DB-OPT-14 | Cache Version Busting | Pattern: model_version prefix on all Redis keys. Tool: Mage pipeline increments version | ✅ Cache hit rate >95% after warmup. ✅ Model swap completes in <1s. ✅ No stale predictions served |
| DB-OPT-15 | Asyncpg Pipeline Mode | Constraint: Use asyncpg pipelining for multi-query routes. Tool: connection.fetch() with prepared statements | ✅ Network round-trips reduced >50%. ✅ Latency <20ms for 3-query sequence. ✅ No blocking calls in async def |

#### Spike
**Spike ID**: SPK-DB-OPT-05  
**Question**: Does PgBouncer add value over native asyncpg pooling in Kubernetes?  
**Hypothesis**: For 50+ app pods, PgBouncer reduces connection overhead; for <10 pods, native pooling is sufficient  
**Timebox**: 1 Day  
**Outcome**: Architecture decision record with scaling thresholds

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 optimize_hybrid_schema.py
**Purpose**: Analyze JSONB key usage and generate column extraction DDL  
**Superpower**: Hybrid Schema Engineer  
**Detection Logic**:
1. Query pg_stats for jsonb column frequency and key patterns
2. Calculate key repetition overhead using pg_column_size()
3. Identify keys accessed in >80% of queries from pg_stat_statements
4. Generate ALTER TABLE statements to promote hot keys to relational columns

**Usage**:
```bash
python scripts/optimize_hybrid_schema.py --schema ml_features --threshold 0.8
```

### 5.2 analyze_gin_performance.py
**Purpose**: Monitor GIN index health and pending list behavior  
**Superpower**: GIN Index Tuner  
**Detection Logic**:
1. Scan pg_stat_user_indexes for GIN indexes with high idx_tup_read
2. Check gin_pending_list_limit and merge frequency via pg_stat_bgwriter
3. Recommend jsonb_path_ops if @> queries dominate log
4. Flag indexes with <1000 scans for removal

**Usage**:
```bash
python scripts/analyze_gin_performance.py --database ml_platform --action report
```

### 5.3 monitor_toast_usage.py
**Purpose**: Detect TOAST table size and compression efficiency  
**Superpower**: TOAST Whisperer  
**Detection Logic**:
1. Join pg_class to pg_toast tables to calculate toast ratio
2. Analyze compression performance via pgstattuple extension
3. Recommend STORAGE MAIN or lz4 compression based on access patterns
4. Alert when toast table exceeds 15% of main table size

**Usage**:
```bash
python scripts/monitor_toast_usage.py --table features --alert-threshold 0.15
```

### 5.4 decode_execution_plan.py
**Purpose**: Parse EXPLAIN ANALYZE output to identify bottlenecks  
**Superpower**: Plan Decoder  
**Detection Logic**:
1. Execute EXPLAIN (ANALYZE, BUFFERS, VERBOSE) on target query
2. Extract buffer hit ratio, scan types, and join strategies
3. Flag Seq Scan on >1M row tables as CRITICAL
4. Recommend Extended Statistics creation for functional JSONB expressions

**Usage**:
```bash
python scripts/decode_execution_plan.py --query-file slow_query.sql --output json
```

### 5.5 validate_connection_pool.py
**Purpose**: Verify async connection pool configuration against database capacity  
**Superpower**: Concurrency Architect  
**Detection Logic**:
1. Detect CPU core count and effective spindle count from /proc
2. Calculate optimal pool size using formula: (cores * 2) + spindles
3. Check current pool configuration in FastAPI app
4. Validate that pool_size + max_overflow < max_connections

**Usage**:
```bash
python scripts/validate_connection_pool.py --app-config src/api/config.py --pg-version 15
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 JSONB Storage Physics: Key Overhead and TOAST
PostgreSQL stores JSONB as a binary format decomposed into container headers and values. Unlike relational columns where names live in the system catalog, JSONB repeats every key string for every row. For a table with 1B rows storing {"timestamp": 123}, the string "timestamp" is stored 1B times, consuming ~9GB of redundant storage. The Optimizer Agent's "Key Abbreviation" protocol enforces keys <=3 characters, reducing this to ~3GB.

TOAST (The Oversized-Attribute Storage Technique) moves values >2KB to a separate pg_toast table. When a query SELECTs a toasted column, PostgreSQL performs a secondary TID lookup and decompresses chunks. This penalty is invisible in EXPLAIN but adds 5-50ms per row. The Agent uses STORAGE MAIN to force inline storage via compression, keeping hot data in shared_buffers.

### 6.2 GIN Index Internals: Pending List and Merge
GIN indexes use inverted index structures where each JSONB key maps to a posting list of TIDs. Write amplification occurs: inserting a document with 100 keys requires 100 index insertions. To amortize this cost, PostgreSQL uses a "Pending List"—an unsorted buffer that accumulates insertions. When the list exceeds gin_pending_list_limit (default 4MB), a background process merges entries into the main index structure.

The Agent tunes this threshold based on write velocity. High-velocity tables (10K inserts/sec) benefit from larger limits (16MB) to reduce merge frequency, but this increases query latency because reads must scan both the main index and the unsorted pending list. The Agent monitors merge frequency via pg_stat_bgwriter and disables fastupdate for predictable latency.

### 6.3 Vector Indexing: HNSW vs IVFFlat Trade-offs
HNSW constructs a hierarchical graph where each layer is a navigable small world network. Insertion complexity is O(log n) and queries are O(log n), making it suitable for dynamic "Hot" feature stores. The parameters m (max connections) and ef_construction (candidate list size) control recall vs build time. The Agent sets m=16, ef_construction=64 for production recall >0.95.

IVFFlat uses K-means clustering to partition vectors into lists. Query complexity is O(N/k) where k is number of clusters. It's memory-efficient but static—new vectors can shift cluster centroids, degrading recall. The Agent reserves IVFFlat for "Cold" archival stores where data is immutable and memory is constrained.

### 6.4 Execution Plan Analysis: Buffer Hit Ratio
The Agent's core metric is buffer hit ratio: shared_blks_hit / (shared_blks_hit + shared_blks_read). A ratio <99% on large tables indicates the working set exceeds shared_buffers. The Agent traces this to either insufficient RAM (remediation: increase shared_buffers) or poor locality (remediation: CLUSTER table on index).

For JSONB queries, the Agent creates Extended Statistics: CREATE STATISTICS s1 ON (data ->> 'serviceId') FROM events. This builds histograms on extracted values, giving the planner accurate selectivity estimates. Without this, containment queries (@>) often have misestimated row counts, causing the planner to choose Nested Loops over Hash Joins.

### 6.5 WAL Tuning: Checkpoint Spikes and Compression
Checkpoint spikes occur when PostgreSQL flushes dirty buffers to disk. The default checkpoint_timeout=5min and max_wal_size=1GB cause frequent, sharp I/O bursts. The Agent increases max_wal_size to 50GB, allowing checkpoints to occur naturally every 30+ minutes. Setting checkpoint_completion_target=0.9 spreads writes evenly across 90% of the checkpoint interval, eliminating latency spikes.

WAL compression with lz4 reduces disk write volume by 60-80% with minimal CPU overhead. This is critical for NVMe SSDs where write bandwidth is shared between WAL and table data. For Mage staging tables, UNLOGGED bypasses WAL entirely, achieving 3x insert throughput. The Agent verifies these tables are rebuilt idempotently on pod restart.

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: database-optimizer
description: Autonomous Database Optimizer Agent for converged PostgreSQL Data Warehouses
superpowers:
  - hybrid-schema-engineer
  - toast-whisperer
  - gin-index-tuner
  - vector-navigator
  - plan-decoder
  - wal-orchestrator
  - concurrency-architect
triggers:
  - "database performance"
  - "query optimization"
  - "index tuning"
  - "jsonb overhead"
  - "toast table"
  - "gin index"
  - "vector search"
  - "connection pool"
  - "wal tuning"
  - "vacuum bloat"
epics:
  - id: DB-OPT-LOG-01
    name: Hybrid Schema Integrity Enforcement
    size: L
    stories: 3
    spike: SPK-DB-OPT-01
  - id: DB-OPT-IDX-01
    name: Advanced Indexing Strategy
    size: XL
    stories: 3
    spike: SPK-DB-OPT-02
  - id: DB-OPT-QUERY-01
    name: Query Plan Optimization
    size: L
    stories: 3
    spike: SPK-DB-OPT-03
  - id: DB-OPT-WRITE-01
    name: Write-Heavy Orchestration
    size: XL
    stories: 3
    spike: SPK-DB-OPT-04
  - id: DB-OPT-CONN-01
    name: Concurrency and Application Interface
    size: M
    stories: 3
    spike: SPK-DB-OPT-05
scripts:
  - name: optimize_hybrid_schema.py
    superpower: hybrid-schema-engineer
  - name: analyze_gin_performance.py
    superpower: gin-index-tuner
  - name: monitor_toast_usage.py
    superpower: toast-whisperer
  - name: decode_execution_plan.py
    superpower: plan-decoder
  - name: validate_connection_pool.py
    superpower: concurrency-architect
checklists:
  - logical_view_optimizer.md
  - process_view_optimizer.md
  - development_view_optimizer.md
  - physical_view_optimizer.md
  - scenario_view_optimizer.md
references:
  - jsonb_storage_physics.md
  - gin_index_internals.md
  - vector_indexing_hnsw.md
  - execution_plan_analysis.md
  - wal_tuning_checkpoints.md
```