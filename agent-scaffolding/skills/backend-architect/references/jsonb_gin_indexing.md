# JSONB GIN Indexing: Operator Classes

## Two Options

### jsonb_ops (default)
- Indexes keys AND values separately
- Supports: `@>`, `?`, `?|`, `?&`
- Larger index size

### jsonb_path_ops
- Indexes hashes of key-value paths
- Supports: only `@>` (containment)
- **30-50% smaller index**

## When to Use Each

| Query Pattern | Operator Class | Example |
|---------------|----------------|---------|
| Containment only | jsonb_path_ops | `data @> '{"type":"click"}'` |
| Key existence | jsonb_ops | `data ? 'user_id'` |
| Mixed | jsonb_ops | Both patterns |

## Implementation

```sql
-- Containment-heavy (feature store)
CREATE INDEX idx_features_path 
  ON features USING GIN (data jsonb_path_ops);

-- Mixed queries
CREATE INDEX idx_events_ops 
  ON events USING GIN (data);
```

## Why Size Matters

Smaller indexes = more fits in `shared_buffers` = fewer disk reads.

A 50% reduction in index size can double buffer cache efficiency.

## Benchmark

```bash
python scripts/benchmark_gin_index.py --table features --simulate
```
