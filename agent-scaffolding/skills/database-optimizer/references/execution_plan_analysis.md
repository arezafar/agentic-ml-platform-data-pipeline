# Execution Plan Analysis: EXPLAIN ANALYZE

## Overview

`EXPLAIN (ANALYZE, BUFFERS)` reveals the **actual** execution path, not just the plan.

## Key Metrics

### Buffer Hit Ratio

```
shared_blks_hit / (shared_blks_hit + shared_blks_read)
```

| Ratio | Interpretation | Action |
|-------|---------------|--------|
| >99% | Excellent | Maintain |
| 95-99% | Good | Monitor |
| <95% | Poor | Increase shared_buffers or optimize |

### Row Estimation Accuracy

```
actual rows / estimated rows
```

| Ratio | Interpretation | Action |
|-------|---------------|--------|
| 0.5-2x | Accurate | None |
| 2-10x | Inaccurate | Review statistics |
| >10x | Catastrophic | Create Extended Statistics |

## Common Issues

### Seq Scan on Large Table

```sql
Seq Scan on features  (cost=0.00..500000.00 rows=10000000 actual time=0.01..5000.00)
```

**Problem**: Full table scan on 10M rows
**Solution**: Add appropriate index

### Nested Loop with Large Outer

```sql
Nested Loop  (cost=... actual rows=50000)
  ->  Seq Scan on users (actual rows=50000)
  ->  Index Scan on features
```

**Problem**: 50K iterations × index lookup
**Solution**: Use Hash Join (often planner misestimate)

### Low Buffer Hit Ratio

```sql
Buffers: shared hit=1000 read=50000
```

**Problem**: 98% disk reads
**Solution**: Increase shared_buffers or reduce working set

## Extended Statistics for JSONB

The standard planner cannot estimate JSONB expression selectivity.

```sql
-- Create statistics on extracted value
CREATE STATISTICS s1 ON (data ->> 'serviceId') 
FROM events;

-- Analyze to collect statistics
ANALYZE events;
```

### Before

```sql
Seq Scan on events  (rows=100 actual rows=50000)
  Filter: ((data ->> 'serviceId') = 'svc-123')
```

### After

```sql
Index Scan using idx_serviceid on events  (rows=48000 actual rows=50000)
  Index Cond: ((data ->> 'serviceId') = 'svc-123')
```

## CTE Materialization

PostgreSQL 12+ can inline CTEs, but sometimes forces materialization.

### Problem

```sql
WITH filtered AS (
  SELECT * FROM events WHERE created_at > '2024-01-01'
)
SELECT * FROM filtered WHERE data @> '{"type": "click"}';
```

If CTE is MATERIALIZED, the JSONB filter runs after fetching all dates.

### Solution

```sql
WITH filtered AS NOT MATERIALIZED (
  SELECT * FROM events WHERE created_at > '2024-01-01'
)
SELECT * FROM filtered WHERE data @> '{"type": "click"}';
```

## Diagnostic Queries

```sql
-- Find slow queries with poor estimates
SELECT 
  query,
  calls,
  mean_exec_time,
  rows / calls AS avg_rows
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- >100ms
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Find missing indexes
SELECT 
  relname,
  seq_scan,
  idx_scan,
  seq_scan - idx_scan AS too_many_seqs
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY too_many_seqs DESC;
```
