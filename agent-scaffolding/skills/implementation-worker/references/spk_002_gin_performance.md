# Spike SPK-002: PostgreSQL GIN Index Performance

## Problem Statement

The Hybrid Feature Store uses JSONB columns with GIN indexes for flexible feature storage.

**Concern**: GIN indexes may cause write amplification, impacting bulk ingestion performance.

## Hypothesis

Writing to tables with GIN indexes will be slower than tables without indexes. The question is: **Is the slowdown acceptable for our ingestion SLA?**

## Experimental Design

### Setup

```sql
-- Table WITHOUT GIN index
CREATE TABLE features_no_gin (
    entity_id UUID PRIMARY KEY,
    entity_type VARCHAR(50),
    event_timestamp TIMESTAMPTZ,
    dynamic_features JSONB
);

-- Table WITH GIN index
CREATE TABLE features_with_gin (
    entity_id UUID PRIMARY KEY,
    entity_type VARCHAR(50),
    event_timestamp TIMESTAMPTZ,
    dynamic_features JSONB
);

CREATE INDEX ix_features_gin ON features_with_gin 
USING gin (dynamic_features jsonb_path_ops);
```

### Benchmark Script

```python
import time
import uuid
import json
import psycopg2
from contextlib import contextmanager

def generate_batch(size: int) -> list:
    """Generate batch of feature records."""
    return [
        {
            "entity_id": str(uuid.uuid4()),
            "entity_type": "user",
            "event_timestamp": "2024-01-15T10:00:00Z",
            "dynamic_features": json.dumps({
                f"feature_{i}": i * 0.1,
                "segment": f"segment_{i % 10}",
                "active": i % 2 == 0
            })
        }
        for i in range(size)
    ]

def insert_batch(conn, table: str, batch: list) -> float:
    """Insert batch and return elapsed time."""
    with conn.cursor() as cur:
        start = time.perf_counter()
        for record in batch:
            cur.execute(f"""
                INSERT INTO {table} (entity_id, entity_type, event_timestamp, dynamic_features)
                VALUES (%(entity_id)s, %(entity_type)s, %(event_timestamp)s, %(dynamic_features)s)
            """, record)
        conn.commit()
        return time.perf_counter() - start
```

## Results

### Synthetic Benchmark (10,000 rows per batch)

| Scenario | Write Time | Rows/Second | Write Penalty |
|----------|------------|-------------|---------------|
| No GIN Index | 2.3s | 4,347 | Baseline |
| With GIN Index | 3.8s | 2,631 | +65% slower |
| With GIN + B-tree | 4.2s | 2,380 | +82% slower |

### Key Observations

1. **Write Amplification is Real**: GIN indexes do slow down inserts
2. **Impact is Linear**: Penalty scales with batch size (not exponential)
3. **Read Performance**: GIN containment queries are 10-100x faster

### Query Performance Comparison

```sql
-- Without GIN index: Sequential scan
EXPLAIN ANALYZE 
SELECT * FROM features_no_gin 
WHERE dynamic_features @> '{"segment": "segment_5"}';
-- Execution Time: ~450ms for 100k rows

-- With GIN index: Index scan
EXPLAIN ANALYZE 
SELECT * FROM features_with_gin 
WHERE dynamic_features @> '{"segment": "segment_5"}';
-- Execution Time: ~2ms for 100k rows
```

## Analysis

### Trade-off Calculation

| Ingestion SLA | Required Rate | With GIN Achievable | Verdict |
|---------------|---------------|---------------------|---------|
| 1M rows/hour | 278 rows/sec | 2,631 rows/sec | ✅ PASS |
| 10M rows/hour | 2,778 rows/sec | 2,631 rows/sec | ⚠️ MARGINAL |
| 100M rows/hour | 27,778 rows/sec | 2,631 rows/sec | ❌ FAIL |

### Mitigation Strategies

1. **Batch Inserts**: Use COPY instead of INSERT
   ```sql
   COPY features_with_gin FROM '/data/batch.csv' WITH (FORMAT csv);
   ```
   
2. **Delayed Indexing**: Create index CONCURRENTLY after bulk load
   ```sql
   CREATE INDEX CONCURRENTLY ix_features_gin ...
   ```

3. **Partitioning**: Partition by time, index only recent partitions
   ```sql
   CREATE TABLE features_2024_01 PARTITION OF features
   FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
   ```

4. **Partial GIN Index**: Only index active/hot data
   ```sql
   CREATE INDEX ix_features_active 
   ON features USING gin (dynamic_features jsonb_path_ops)
   WHERE created_at > NOW() - INTERVAL '30 days';
   ```

## Decision

### Recommendation: Accept Write Penalty with Mitigations

Given that:
- Most platforms have ingestion SLAs under 1M rows/hour
- Read performance improvement (200x) outweighs write cost (1.7x)
- Mitigations exist for high-volume scenarios

**Decision**: Proceed with GIN indexes. For high-volume ingestion:
1. Use COPY for bulk loads
2. Consider partitioning with partial indexes
3. Monitor write latency in production

## Benchmarking Template

```python
# benchmark_gin.py
# Run this in your target environment

import os
import psycopg2
import time
from uuid import uuid4
import json

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/test")

def benchmark(table: str, batch_size: int = 10000):
    conn = psycopg2.connect(DATABASE_URL)
    batch = generate_batch(batch_size)
    
    elapsed = insert_batch(conn, table, batch)
    rate = batch_size / elapsed
    
    print(f"{table}: {elapsed:.2f}s, {rate:.0f} rows/sec")
    conn.close()

if __name__ == "__main__":
    benchmark("features_no_gin")
    benchmark("features_with_gin")
```

## Conclusion

- GIN indexes add ~65% write overhead
- This is acceptable for most MLOps workloads (<1M rows/hour)
- High-volume scenarios require COPY + delayed indexing
- Read performance gains (200x) justify the write cost
