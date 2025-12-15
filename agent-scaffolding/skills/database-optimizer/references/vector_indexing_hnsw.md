# Vector Indexing: HNSW vs IVFFlat

## Overview

pgvector provides two index types for approximate nearest neighbor (ANN) search.

## HNSW (Hierarchical Navigable Small World)

### Structure
A hierarchical graph where each layer is a navigable small world network.

```
Layer 3:  [1] ─────────────────────── [67]
Layer 2:  [1] ────── [23] ─────────── [67]
Layer 1:  [1] ── [12] ── [23] ── [45] ── [67]
Layer 0:  [1] [5] [12] [18] [23] [31] [45] [52] [67]
```

### Complexity
- **Insert**: O(log n) - walks down through layers
- **Query**: O(log n) - same walk, then local search
- **Memory**: High (stores graph connections)

### Parameters

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `m` | Max connections per layer | 16 (default) |
| `ef_construction` | Candidate list size during build | 64 |

```sql
CREATE INDEX idx_embeddings_hnsw 
  ON features USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

### Use Cases
- **Hot Feature Store**: Frequent updates, real-time search
- **High Recall Required**: >0.95 recall@10
- **Dynamic Data**: Supports incremental updates

## IVFFlat (Inverted File with Flat Storage)

### Structure
Partitions vectors into k clusters using K-means.

```
Cluster 1: [vec_1, vec_5, vec_12, ...]
Cluster 2: [vec_2, vec_8, vec_23, ...]
Cluster 3: [vec_3, vec_7, vec_15, ...]
...
Cluster k: [vec_n, ...]
```

### Complexity
- **Insert**: O(k) - find nearest cluster
- **Query**: O(N/k) - search nearest clusters
- **Memory**: Low (just cluster centroids)

### Parameters

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| `lists` | Number of clusters | rows / 1000 to sqrt(rows) |

```sql
CREATE INDEX idx_embeddings_ivf 
  ON features USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 1000);

-- Must train centroids first
SET ivfflat.probes = 10;  -- Search 10 nearest clusters
```

### Use Cases
- **Cold Archive**: Immutable historical embeddings
- **Memory Constrained**: Smaller index footprint
- **Batch Updates**: Requires periodic reindex

## Comparison

| Aspect | HNSW | IVFFlat |
|--------|------|---------|
| Build Time | Slow | Fast |
| Query Speed | Fast | Medium |
| Memory | High | Low |
| Update Cost | Low | High (degrades recall) |
| Recall | Higher | Lower (tunable) |
| Dynamic Data | Yes | No (needs reindex) |

## Monitoring

```sql
-- Check index usage
SELECT 
  indexrelid::regclass AS index_name,
  idx_scan,
  pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE indexrelid::regclass::text LIKE '%hnsw%'
   OR indexrelid::regclass::text LIKE '%ivf%';
```

## Decision Matrix

```
Is data frequently updated?
├── Yes → Use HNSW
└── No
    └── Is memory constrained?
        ├── Yes → Use IVFFlat
        └── No → Use HNSW
```
