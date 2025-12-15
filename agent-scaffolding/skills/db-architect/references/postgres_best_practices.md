# PostgreSQL 15+ Best Practices

Reference guide for database design patterns in the Agentic ML Platform.

## Core Design Principles

### 1. JSONB for Schema Flexibility

Use JSONB columns for data with:
- Variable structure (API responses)
- Evolving schemas (schema drift tolerance)
- Nested/hierarchical data

```sql
-- Create table with JSONB
CREATE TABLE raw_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_payload JSONB NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- GIN index for JSONB queries
CREATE INDEX idx_raw_events_payload ON raw_events USING GIN (raw_payload);

-- Query nested data
SELECT raw_payload->>'event_type' as event_type,
       raw_payload->'metadata'->>'source' as source
FROM raw_events
WHERE raw_payload @> '{"status": "active"}'::jsonb;
```

### 2. Declarative Partitioning

Use partitioning for:
- Time-series data (events, predictions, features)
- Tables expected to grow > 10M rows
- Query patterns that filter by partition key

```sql
-- Create partitioned table
CREATE TABLE predictions (
    id UUID PRIMARY KEY,
    predicted_at TIMESTAMPTZ NOT NULL,
    prediction JSONB NOT NULL
) PARTITION BY RANGE (predicted_at);

-- Create monthly partitions
CREATE TABLE predictions_2024_01 
    PARTITION OF predictions 
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Default partition for unexpected data
CREATE TABLE predictions_default 
    PARTITION OF predictions DEFAULT;
```

### 3. Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Tables | lowercase_snake_case | `raw_events`, `model_metrics` |
| Columns | lowercase_snake_case | `created_at`, `entity_id` |
| Primary Keys | `{table}_pkey` | `users_pkey` |
| Foreign Keys | `fk_{table}_{column}` | `fk_features_entity_id` |
| Indexes | `idx_{table}_{columns}` | `idx_predictions_model_id` |
| Unique | `uq_{table}_{columns}` | `uq_models_name_version` |
| Check | `ck_{table}_{description}` | `ck_models_status` |

### 4. Index Strategies

#### Standard B-Tree (default)
```sql
CREATE INDEX idx_models_name ON models(name);
```

#### Partial Indexes (filter common queries)
```sql
CREATE INDEX idx_events_unprocessed 
    ON raw_events(ingested_at) 
    WHERE processed = false;
```

#### GIN for JSONB
```sql
CREATE INDEX idx_features_gin ON features USING GIN (features);
```

#### Covering Indexes (PostgreSQL 11+)
```sql
CREATE INDEX idx_models_lookup 
    ON models(name, version) 
    INCLUDE (artifact_path, status);
```

### 5. UUID Primary Keys

Prefer UUIDs over serial integers:
- Globally unique (no collisions in distributed systems)
- No enumeration attacks
- Works with partitioning

```sql
-- Requires uuid-ossp or pgcrypto extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Use gen_random_uuid() (PostgreSQL 13+)
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);
```

---

## Schema Patterns

### Feature Store Pattern

```sql
-- Entity as primary dimension
CREATE TABLE feature_store.entities (
    id UUID PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    UNIQUE(entity_type, external_id)
);

-- Point-in-time features with versioning
CREATE TABLE feature_store.features (
    id UUID PRIMARY KEY,
    entity_id UUID REFERENCES entities(id),
    feature_set VARCHAR(100) NOT NULL,
    feature_version VARCHAR(50) NOT NULL,
    features JSONB NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ  -- NULL = current
) PARTITION BY RANGE (computed_at);
```

### Model Registry Pattern

```sql
-- Model versions with metadata
CREATE TABLE model_registry.models (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    artifact_path TEXT NOT NULL,
    hyperparameters JSONB,
    status VARCHAR(50) DEFAULT 'registered',
    UNIQUE(name, version),
    CHECK (status IN ('registered', 'staging', 'production', 'archived'))
);

-- Separate metrics table (normalized)
CREATE TABLE model_registry.model_metrics (
    id UUID PRIMARY KEY,
    model_id UUID REFERENCES models(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL
);
```

---

## Performance Guidelines

### 1. Connection Pooling
- Use PgBouncer or built-in connection limits
- Async connections with asyncpg for Python

### 2. Query Optimization
- Always use EXPLAIN ANALYZE for slow queries
- Avoid SELECT * in production code
- Use prepared statements

### 3. Vacuum Strategy
- Configure autovacuum aggressively for high-write tables
- Manual VACUUM ANALYZE after bulk loads

### 4. PostgreSQL 15+ Features to Use
- `MERGE` command for upserts
- JSON path improvements
- Enhanced compression for TOAST
- Improved sorting performance (up to 25% faster)
