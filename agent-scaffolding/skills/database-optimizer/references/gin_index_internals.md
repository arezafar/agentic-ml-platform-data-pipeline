# GIN Index Internals: Pending List and Merge

## Inverted Index Structure

GIN (Generalized Inverted Index) creates an inverted index where each JSONB key maps to a posting list of TIDs (tuple identifiers).

```
Document: {"color": "red", "size": "large", "active": true}

GIN Entry:
├── "color=red" → [TID_1, TID_47, TID_892, ...]
├── "size=large" → [TID_1, TID_23, TID_156, ...]
└── "active=true" → [TID_1, TID_5, TID_8, ...]
```

## Write Amplification

Inserting one document with 100 keys requires **100 separate index insertions**.

```
INSERT 1 row with 100 JSONB keys
├── 1 heap insert
└── 100 GIN posting list updates
    └── 100x I/O amplification
```

## Pending List (fastupdate)

To reduce write amplification, GIN uses an unsorted buffer called the **Pending List**.

### Mechanism

1. Insertions go to unsorted pending list
2. When list exceeds `gin_pending_list_limit` (default 4MB), merge occurs
3. Background process sorts and merges into main index

### Configuration

```sql
-- Per-table pending list limit
ALTER INDEX idx_features_gin 
  SET (gin_pending_list_limit = 16384);  -- 16MB for high-write

-- Disable fastupdate for predictable reads
ALTER INDEX idx_features_gin 
  SET (fastupdate = off);
```

### Trade-offs

| Setting | Write Speed | Read Consistency | Use Case |
|---------|-------------|------------------|----------|
| Large pending (16MB) | Fast | Variable latency | High-write ingestion |
| Small pending (1MB) | Slower | Consistent | Read-heavy workloads |
| fastupdate=off | Slowest | Instant | Real-time analytics |

## Operator Class Selection

### jsonb_ops (default)
- Supports all operators: @>, ?, ?&, ?|, @@
- Creates entries for keys AND values
- Larger index size

### jsonb_path_ops
- Supports only @> (containment)
- Creates hash of entire path
- **30-50% smaller index**

```sql
-- Use jsonb_path_ops for containment-only queries
CREATE INDEX idx_features_path 
  ON features USING GIN (data jsonb_path_ops);
```

## Monitoring GIN Health

```sql
-- Check pending list status
SELECT 
  indexrelid::regclass AS index_name,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexrelid::regclass::text LIKE '%gin%';

-- Check index bloat
SELECT 
  indexrelid::regclass AS index_name,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size,
  idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan < 1000  -- Unused indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

## REINDEX Strategy

```sql
-- Rebuild without blocking
REINDEX INDEX CONCURRENTLY idx_features_gin;
```
