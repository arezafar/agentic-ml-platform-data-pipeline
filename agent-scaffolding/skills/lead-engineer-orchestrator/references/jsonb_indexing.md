# JSONB Indexing: GIN and TOAST Strategy

## Overview

PostgreSQL stores large field values in TOAST (The Oversized-Attribute Storage Technique). Proper indexing is critical for JSONB query performance.

## The Problem: The IO Cliff

When querying JSONB columns without proper indexes:

1. PostgreSQL fetches data from main table heap
2. Retrieves TOAST chunks for large JSON blobs
3. Decompresses and deserializes entire JSON
4. Scans all rows for matching values

**Result**: Query time scales linearly with data volume. At 100M rows, queries become unusable.

## The Solution: GIN Indexes

GIN (Generalized Inverted Index) indexes the keys and values inside JSONB documents.

### Creating GIN Index

```sql
-- Create GIN index on JSONB column
CREATE INDEX idx_features_gin ON features USING GIN (attributes);

-- For specific path optimization
CREATE INDEX idx_features_path ON features USING GIN ((attributes -> 'category'));
```

### Containment Queries

```sql
-- ✅ GOOD: Uses GIN index
SELECT * FROM features WHERE attributes @> '{"color": "red"}';

-- ❌ BAD: Full table scan
SELECT * FROM features WHERE attributes->>'color' = 'red';
```

## JSON vs JSONB

| Aspect | JSON | JSONB |
|--------|------|-------|
| Storage | Text | Binary |
| Write Speed | Faster | Slower (parsing) |
| Read Speed | Slower | Faster |
| GIN Index | **Not supported** | Supported |
| Duplicate Keys | Preserved | Last wins |

**Always use JSONB for queryable JSON data.**

## Key Extraction with B-Tree

If you must use `->>`extraction, add a B-Tree index:

```sql
-- B-Tree index on extracted value
CREATE INDEX idx_category ON features ((attributes->>'category'));

-- Now this uses the index
SELECT * FROM features WHERE attributes->>'category' = 'electronics';
```

## Time-Travel with event_time

For Feature Store requirements:

```sql
CREATE TABLE features (
    entity_id UUID NOT NULL,
    attributes JSONB NOT NULL,
    event_time TIMESTAMP NOT NULL,  -- Required for time-travel
    PRIMARY KEY (entity_id, event_time)
);

-- Query features as of a specific point in time
SELECT * FROM features
WHERE entity_id = $1
  AND event_time <= $2
ORDER BY event_time DESC
LIMIT 1;
```

## Migration Validation

```sql
-- ❌ WRONG: Using JSON type
ALTER TABLE features ADD COLUMN data JSON;

-- ✅ CORRECT: Using JSONB with GIN
ALTER TABLE features ADD COLUMN data JSONB;
CREATE INDEX idx_data_gin ON features USING GIN (data);
```

## Detection Script

```bash
python scripts/validate_schema_migration.py --migration-dir ./alembic/versions
```

## References

- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [GIN Index Internals](https://www.postgresql.org/docs/current/gin-intro.html)
- [TOAST Explanation](https://www.postgresql.org/docs/current/storage-toast.html)
