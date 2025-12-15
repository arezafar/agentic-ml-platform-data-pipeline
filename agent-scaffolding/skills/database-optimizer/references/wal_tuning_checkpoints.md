# WAL Tuning: Checkpoint Smoothing

## Overview

Write-Ahead Logging (WAL) ensures durability but can cause performance spikes.

## The Checkpoint Problem

### Default Behavior

```
checkpoint_timeout = 5min
max_wal_size = 1GB

Timeline:
0:00 ──────────── 5:00 ──────────── 10:00
     [WAL accumulates]  [CHECKPOINT]   [WAL]
     (smooth writes)    (I/O SPIKE)    (smooth)
```

### The Sawtooth Pattern

During checkpoint:
1. All dirty buffers flushed to disk
2. Disk I/O saturates
3. All queries slow down
4. Inference API latency spikes

## Checkpoint Smoothing

### Configuration

```
max_wal_size = 50GB
checkpoint_completion_target = 0.9
```

This spreads checkpoint I/O over 90% of the interval:

```
0:00 ──────────────────── 5:00
     [WAL + gradual flush] [Complete]
     (smooth throughout)
```

### Parameters

| Parameter | Default | Optimized | Effect |
|-----------|---------|-----------|--------|
| `max_wal_size` | 1GB | 50GB | Fewer checkpoints |
| `checkpoint_timeout` | 5min | 30min | Less frequent |
| `checkpoint_completion_target` | 0.5 | 0.9 | Spread I/O |

## WAL Compression

```
wal_compression = lz4  # PostgreSQL 15+
```

### Benefits
- 60-80% reduction in WAL volume
- Less disk I/O during bulk loads
- Minimal CPU overhead

## UNLOGGED Tables for Staging

For Mage.ai staging data that can be rebuilt:

```sql
CREATE UNLOGGED TABLE staging_features (
  id serial,
  data jsonb
);
```

### Trade-offs

| Aspect | LOGGED | UNLOGGED |
|--------|--------|----------|
| Durability | Yes | No (data lost on crash) |
| Insert Speed | 1x | 3x |
| Recovery | Automatic | Must rebuild |
| WAL | Generated | None |

### Safe Usage

```python
# In Mage pipeline
@data_loader
def load_to_staging():
    # UNLOGGED staging table - fast insert
    return df.to_sql('staging_features', engine, if_exists='replace')

@data_exporter  
def export_to_production():
    # Move to LOGGED production table
    engine.execute("""
        INSERT INTO features 
        SELECT * FROM staging_features;
        TRUNCATE staging_features;
    """)
```

## Monitoring

```sql
-- Check checkpoint frequency
SELECT 
  checkpoints_timed,
  checkpoints_req,
  checkpoint_write_time,
  checkpoint_sync_time,
  buffers_checkpoint
FROM pg_stat_bgwriter;

-- Monitor WAL generation rate
SELECT 
  pg_current_wal_lsn(),
  pg_walfile_name(pg_current_wal_lsn());
```

## Bulk Load Optimization

### Index Strategy

```sql
-- Drop indexes before load
DROP INDEX idx_features_gin;

-- Bulk insert (3x faster)
COPY features FROM '/data/features.csv';

-- Recreate indexes (parallel on PG 11+)
CREATE INDEX CONCURRENTLY idx_features_gin 
  ON features USING GIN (data);
```

### Session-Level Tuning

```sql
-- Temporary settings for bulk load session
SET maintenance_work_mem = '2GB';
SET synchronous_commit = off;
SET wal_compression = lz4;
```
