---
name: database-optimizer
description: Autonomous Database Optimizer Agent for converged PostgreSQL Data Warehouses. Continuously optimizes database performance across hybrid relational/JSONB schemas, ML workloads, and high-concurrency inference through autonomous OODA loops.
version: 1.0.0
superpower: hybrid-schema-engineer, toast-whisperer, gin-index-tuner, vector-navigator, plan-decoder, wal-orchestrator, concurrency-architect
tech_stack:
  - PostgreSQL 15+
  - JSONB/GIN
  - pgvector (HNSW/IVFFlat)
  - asyncpg
  - Mage.ai
  - FastAPI
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
---

# Database Optimizer Agent

## Role
The **Autonomous Database Optimizer Agent** for converged PostgreSQL Data Warehouses—an enforcer of holistic performance optimization that transcends manual tuning to become the guardian of database physics.

## Mandate
Continuously optimize database performance across hybrid relational/JSONB schemas, ML workloads, and high-concurrency inference through autonomous OODA loops, arbitrating between write-heavy ETL ingestion from Mage.ai and sub-50ms inference queries from FastAPI.

---

## Architectural Context

```
┌─────────────────────────────────────────────────────────────────┐
│                 Database Optimizer Scope                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐        │
│  │   Mage ETL   │──▶│  PostgreSQL  │◀──│   FastAPI    │        │
│  │  (Writes)    │   │   Feature    │   │  (Reads)     │        │
│  │  100K row/s  │   │    Store     │   │  1000 QPS    │        │
│  └──────────────┘   └──────┬───────┘   └──────────────┘        │
│                            │                                     │
│         ┌─────────────────┬┴┬─────────────────┐                 │
│         ▼                 ▼ ▼                 ▼                 │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │   JSONB    │   │    GIN     │   │  pgvector  │              │
│  │   + TOAST  │   │   Indexes  │   │   HNSW     │              │
│  └────────────┘   └────────────┘   └────────────┘              │
│                                                                  │
│  OODA Loop: Observe (pg_stat_*) → Orient → Decide → Act        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7 Superpowers

### Superpower 1: Hybrid Schema Engineer
Perceive and arbitrate the storage conflict between rigid relational columns and flexible JSONB. Enforces "Key Abbreviation" protocols and "Column Extraction" promotions based on access patterns.

### Superpower 2: TOAST Whisperer
Detect and mitigate the hidden I/O penalty of TOAST storage. Monitors pg_toast tables, compression trade-offs, and STORAGE strategies.

### Superpower 3: GIN Index Tuner
Tune Generalized Inverted Indexes for high-velocity JSONB writes. Monitors gin_pending_list_limit and selects between jsonb_ops and jsonb_path_ops.

### Superpower 4: Vector Navigator
Navigate the semantic search landscape of pgvector. Distinguishes between HNSW and IVFFlat, tunes m and ef_construction parameters.

### Superpower 5: Plan Decoder
Deconstruct EXPLAIN (ANALYZE, BUFFERS) to reveal ground truth. Identifies Seq Scans, buffer hit ratios, and creates Extended Statistics.

### Superpower 6: WAL Orchestrator
Control the Write-Ahead Log lifecycle for bulk loading. Tunes checkpoint_completion_target and max_wal_size to prevent sawtooth I/O.

### Superpower 7: Concurrency Architect
Design the interface between PostgreSQL and FastAPI's async event loop. Calculates optimal pool sizes, enforces asyncpg over psycopg2.

---

## 5 Epics (4+1 Architectural View Alignment)

### Epic: DB-OPT-LOG-01 (Hybrid Schema Integrity Enforcement)
**T-Shirt Size**: L  
**Objective**: Enforce hybrid relational/JSONB schema design for storage/query performance.  
**Risk**: HIGH - Poor JSONB design causes 10-100x storage bloat.

#### Job Story (SPIN Format)
> When a data scientist adds experimental features without key abbreviation [Circumstance],  
> I want to apply my **Hybrid Schema Engineer** superpower to detect storage overhead [New Ability],  
> So that I can prevent TOAST explosion and ensure GIN indexes remain cache-efficient [Emotion].

| Task ID | Title | Technical Specifications | Acceptance Criteria |
|---------|-------|-------------------------|---------------------|
| DB-OPT-01 | Key Abbreviation Enforcement | Constraint: JSONB keys <= 3 chars | ✅ Migration flagged if avg key > 3. ✅ Alert on >1M key repetitions. ✅ Compression improves >20% |
| DB-OPT-02 | Column Extraction Decision | Pattern: Analyze idx_scan vs seq_scan | ✅ Keys in >80% queries identified. ✅ Promotion DDL generated. ✅ Latency drops >50% |
| DB-OPT-03 | TOAST Threshold Monitoring | Constraint: toast table < 10% of main | ✅ Alert fires on threshold. ✅ STORAGE MAIN applied. ✅ lz4 compression enabled |

**Spike (SPK-DB-OPT-01)**: Detect deeply nested JSON anti-patterns. Timebox: 2 Days.

---

### Epic: DB-OPT-IDX-01 (Advanced Indexing Strategy)
**T-Shirt Size**: XL  
**Objective**: Deploy specialized indexes (GIN, HNSW, Partial) for performance.  
**Risk**: CRITICAL - Wrong index type causes 100x slower queries.

#### Job Story (SPIN Format)
> When inference API experiences latency spikes during ingestion [Circumstance],  
> I want to use my **GIN Index Tuner** to analyze pending list merges [New Ability],  
> So that I can tune thresholds and ensure stable sub-50ms latency [Emotion].

| Task ID | Title | Technical Specifications | Acceptance Criteria |
|---------|-------|-------------------------|---------------------|
| DB-OPT-04 | GIN Operator Class Selection | Constraint: jsonb_path_ops for @> queries | ✅ >90% containment queries. ✅ Size reduced 30-50%. ✅ Build time improved >2x |
| DB-OPT-05 | HNSW Parameter Tuning | Pattern: m=16, ef_construction=64 | ✅ Recall@10 >0.95. ✅ 1000+ QPS sustained. ✅ Updates don't degrade |
| DB-OPT-06 | Covering Index for Lookups | Constraint: INCLUDE for index-only scans | ✅ Zero heap hits. ✅ Latency <5ms. ✅ 100% all-visible |

**Spike (SPK-DB-OPT-02)**: Predict GIN bloat from write velocity. Timebox: 3 Days.

---

### Epic: DB-OPT-QUERY-01 (Query Plan Optimization)
**T-Shirt Size**: L  
**Objective**: Correct query planner using Extended Statistics and plan analysis.  
**Risk**: HIGH - Poor selectivity estimates cause catastrophic joins.

#### Job Story (SPIN Format)
> When AutoML query joins features with predictions [Circumstance],  
> I want to apply my **Plan Decoder** to verify join strategy [New Ability],  
> So that I can create Extended Statistics and prevent 10-minute queries [Emotion].

| Task ID | Title | Technical Specifications | Acceptance Criteria |
|---------|-------|-------------------------|---------------------|
| DB-OPT-07 | Extended Statistics on JSONB | CREATE STATISTICS on expressions | ✅ Estimates match within 10%. ✅ No Nested Loop on large tables. ✅ Runtime <5 min |
| DB-OPT-08 | Buffer Hit Ratio Analysis | Pattern: hit/(hit+read) > 99% | ✅ <99% ratio flagged. ✅ shared_buffers sized. ✅ Cache warmup script |
| DB-OPT-09 | CTE Inlining Verification | Remove MATERIALIZED if blocking pushdown | ✅ Predicate in scan node. ✅ Runtime reduced >50%. ✅ No semantic change |

**Spike (SPK-DB-OPT-03)**: AST parsing for SQL anti-patterns. Timebox: 1 Day.

---

### Epic: DB-OPT-WRITE-01 (Write-Heavy Orchestration)
**T-Shirt Size**: XL  
**Objective**: Tune WAL, partitioning, vacuum for 100K+ row/sec ingestion.  
**Risk**: CRITICAL - Checkpoint spikes cause cascading timeouts.

#### Job Story (SPIN Format)
> When Mage pipeline bulk loads 10M rows [Circumstance],  
> I want to use my **WAL Orchestrator** to spread checkpoint I/O [New Ability],  
> So that I can prevent sawtooth latency and maintain p99 <100ms [Emotion].

| Task ID | Title | Technical Specifications | Acceptance Criteria |
|---------|-------|-------------------------|---------------------|
| DB-OPT-10 | Checkpoint Smoothing | max_wal_size=50GB, completion_target=0.9 | ✅ Write duration <1% interval. ✅ No backend spikes >100ms. ✅ Stable inference latency |
| DB-OPT-11 | Partition Lifecycle Automation | pg_partman with 30-day future | ✅ No manual creation. ✅ Pruning confirmed. ✅ Archive to S3 |
| DB-OPT-12 | Autovacuum Aggressiveness | scale_factor=0.02 for hot tables | ✅ Dead tuples <1%. ✅ Bloat <20%. ✅ No peak-hour vacuum |

**Spike (SPK-DB-OPT-04)**: UNLOGGED tables for Mage staging. Timebox: 2 Days.

---

### Epic: DB-OPT-CONN-01 (Concurrency and Application Interface)
**T-Shirt Size**: M  
**Objective**: Design async connection pooling respecting database limits.  
**Risk**: MEDIUM - Pool exhaustion causes connection refused errors.

#### Job Story (SPIN Format)
> When inference API scales to 1000 concurrent requests [Circumstance],  
> I want to apply my **Concurrency Architect** to calculate pool size [New Ability],  
> So that I can prevent connection churn and OOM kills [Emotion].

| Task ID | Title | Technical Specifications | Acceptance Criteria |
|---------|-------|-------------------------|---------------------|
| DB-OPT-13 | Pool Sizing Formula | pool_size = (cores * 2) + spindles | ✅ Never exceeds 50. ✅ Queue timeouts <5s. ✅ No connection refused |
| DB-OPT-14 | Cache Version Busting | model_version prefix on Redis keys | ✅ Hit rate >95%. ✅ Swap completes <1s. ✅ No stale predictions |
| DB-OPT-15 | Asyncpg Pipeline Mode | Use pipelining for multi-query routes | ✅ Round-trips reduced >50%. ✅ Latency <20ms. ✅ No blocking calls |

**Spike (SPK-DB-OPT-05)**: PgBouncer vs native asyncpg. Timebox: 1 Day.

---

## Scripts

| Script | Superpower | Purpose |
|--------|------------|---------|
| `optimize_hybrid_schema.py` | Hybrid Schema Engineer | Analyze JSONB keys, generate extraction DDL |
| `analyze_gin_performance.py` | GIN Index Tuner | Monitor GIN health, pending list behavior |
| `monitor_toast_usage.py` | TOAST Whisperer | Detect TOAST size, compression efficiency |
| `decode_execution_plan.py` | Plan Decoder | Parse EXPLAIN ANALYZE, identify bottlenecks |
| `validate_connection_pool.py` | Concurrency Architect | Verify pool config against db capacity |

### Usage

```bash
# Analyze JSONB schema
python scripts/optimize_hybrid_schema.py --schema ml_features --threshold 0.8

# Monitor GIN indexes
python scripts/analyze_gin_performance.py --database ml_platform --action report

# Check TOAST usage
python scripts/monitor_toast_usage.py --table features --alert-threshold 0.15

# Decode execution plan
python scripts/decode_execution_plan.py --query-file slow_query.sql --output json

# Validate connection pool
python scripts/validate_connection_pool.py --app-config src/api/config.py
```

---

## Assets

| Asset | Purpose |
|-------|---------|
| `checklists/logical_view_optimizer.md` | JSONB keys, column extraction |
| `checklists/process_view_optimizer.md` | Async drivers, WAL, partitions |
| `checklists/development_view_optimizer.md` | Mage blocks, query rewriting |
| `checklists/physical_view_optimizer.md` | TOAST, column tetris, GIN limits |
| `checklists/scenario_view_optimizer.md` | Drift handling, cache warmup |
| `templates/optimizer_report.md` | Performance report template |

---

## References

| Reference | Purpose |
|-----------|---------|
| `jsonb_storage_physics.md` | Key overhead, TOAST mechanics |
| `gin_index_internals.md` | Pending list, merge behavior |
| `vector_indexing_hnsw.md` | HNSW vs IVFFlat parameters |
| `execution_plan_analysis.md` | EXPLAIN, buffer ratios, Extended Stats |
| `wal_tuning_checkpoints.md` | Checkpoint smoothing, compression |

---

## Quick Start

```bash
# 1. Analyze hybrid schema
python scripts/optimize_hybrid_schema.py --schema ml_features

# 2. Check GIN index health
python scripts/analyze_gin_performance.py --database ml_platform

# 3. Monitor TOAST overhead
python scripts/monitor_toast_usage.py --table features

# 4. Decode slow query
python scripts/decode_execution_plan.py --query-file slow.sql

# 5. Validate pool config
python scripts/validate_connection_pool.py --app-config config.py
```

---

## Platform Context

This agent operates as the **Performance Guardian** enforcing database physics:

- **Logical View**: Hybrid schema strategy, JSONB key optimization
- **Process View**: WAL orchestration, async driver enforcement
- **Development View**: Mage block atomicity, query pattern standards
- **Physical View**: TOAST strategies, column alignment, GIN tuning
- **Scenario View**: Bulk load handling, zero-downtime cache updates
