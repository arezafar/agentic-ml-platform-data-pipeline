# JSONB Indexing Deep Dive

Technical reference for the **Schema Drift Detector** superpower. Understanding why GIN indexes matter and how to avoid "The IO Cliff."

---

## PostgreSQL JSON Types

### JSON vs JSONB

| Aspect | JSON | JSONB |
|--------|------|-------|
| Storage | Text (preserves formatting) | Binary (parsed) |
| Parsing | Every access | Once at write |
| Indexing | None | GIN, GiST, B-Tree |
| Operators | Limited | Full set |
| Size | Smaller | Slightly larger |
| Use Case | Rarely, logs only | Always for queries |

**Rule:** Always use `JSONB` for feature data. Never `JSON`.

---

## The IO Cliff Problem

### Without Index

```sql
-- Query without index
SELECT * FROM features 
WHERE data->>'color' = 'red';

-- Execution Plan:
-- Seq Scan on features  (cost=0.00..50000.00)
--   Filter: ((data ->> 'color') = 'red')
--   Rows Removed by Filter: 999000
--   Actual Time: 2500ms  ← Full table scan!
```

```
┌────────────────────────────────────────────────────────────┐
│              Without GIN Index: The IO Cliff                │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Query: Find records where color = 'red'                   │
│                                                             │
│  1M rows → Read ALL 1M rows from disk                      │
│         → Decompress JSONB for each                        │
│         → Extract 'color' key                              │
│         → Compare to 'red'                                 │
│         → Return 1000 matches                              │
│                                                             │
│  Time: O(n) where n = total rows                           │
│  Result: Query time grows linearly with data               │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### With GIN Index

```sql
-- Create GIN index
CREATE INDEX ix_features_data_gin ON features USING GIN (data);

-- Same query, now indexed
SELECT * FROM features 
WHERE data @> '{"color": "red"}';

-- Execution Plan:
-- Bitmap Index Scan on ix_features_data_gin  (cost=0.00..50.00)
--   Index Cond: (data @> '{"color": "red"}'::jsonb)
--   Actual Time: 5ms  ← Index lookup!
```

```
┌────────────────────────────────────────────────────────────┐
│              With GIN Index: Fast Lookup                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Query: Find records where color = 'red'                   │
│                                                             │
│  GIN Index: {"color": "red"} → [row_id_1, row_id_2, ...]   │
│                                                             │
│  1M rows → Index scan finds 1000 matching row IDs          │
│         → Fetch only 1000 rows from disk                   │
│         → Return 1000 matches                              │
│                                                             │
│  Time: O(log n + k) where k = matching rows                │
│  Result: Query time independent of total data              │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

---

## GIN Index Mechanics

### What GIN Indexes

GIN (Generalized Inverted Index) creates an index entry for every key and value in the JSONB:

```json
{"color": "red", "size": "large", "tags": ["new", "sale"]}
```

**Index entries created:**
```
"color"  → row_ids
"red"    → row_ids  
"size"   → row_ids
"large"  → row_ids
"tags"   → row_ids
"new"    → row_ids
"sale"   → row_ids
```

### Operator Support

| Operator | Meaning | Uses GIN? |
|----------|---------|-----------|
| `@>` | Contains | ✅ Yes |
| `<@` | Contained by | ✅ Yes |
| `?` | Key exists | ✅ Yes |
| `?&` | All keys exist | ✅ Yes |
| `?\|` | Any key exists | ✅ Yes |
| `->>` | Extract as text | ❌ No* |
| `->` | Extract as JSONB | ❌ No* |

\* Extraction operators require separate B-Tree index on the extracted expression.

---

## Query Patterns

### ✅ Correct: Containment Queries

```sql
-- Uses GIN index
SELECT * FROM features 
WHERE data @> '{"color": "red"}';

-- Multiple conditions (still uses GIN)
SELECT * FROM features 
WHERE data @> '{"color": "red", "size": "large"}';

-- Nested containment
SELECT * FROM features 
WHERE data @> '{"metadata": {"source": "api"}}';
```

### ❌ Incorrect: Extraction Queries Without Index

```sql
-- Does NOT use GIN index → Full table scan
SELECT * FROM features 
WHERE data->>'color' = 'red';

-- Also no index usage
SELECT * FROM features 
WHERE data->'metadata'->>'source' = 'api';
```

### 🔧 Fix: Expression Index for Extraction

If you must use extraction operators:

```sql
-- Create B-Tree index on extracted expression
CREATE INDEX ix_features_color ON features ((data->>'color'));

-- Now this uses the index
SELECT * FROM features 
WHERE data->>'color' = 'red';
```

---

## TOAST and Performance

### What is TOAST?

TOAST (The Oversized-Attribute Storage Technique) stores large values separately:

```
┌────────────────────────────────────────────────────────────┐
│                    TOAST Storage                            │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Main Table Heap:                                           │
│  ┌──────┬──────┬────────────────────┐                      │
│  │ id   │ name │ data (JSONB)       │                      │
│  ├──────┼──────┼────────────────────┤                      │
│  │ 1    │ foo  │ [TOAST pointer]    │ ← If data > 2KB      │
│  │ 2    │ bar  │ {"small": "json"}  │ ← Inline if small    │
│  └──────┴──────┴────────────────────┘                      │
│                                                             │
│  TOAST Table:                                               │
│  ┌──────────────────────────────────┐                      │
│  │ chunk_1: compressed JSONB data   │                      │
│  │ chunk_2: compressed JSONB data   │                      │
│  └──────────────────────────────────┘                      │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Performance Impact

```sql
-- Without GIN: Must read TOAST for every row
SELECT * FROM features WHERE data->>'color' = 'red';
-- For 1M rows with 4KB JSONB each:
-- 1M × 4KB = 4GB of TOAST reads! (compressed, but still huge)

-- With GIN containment: Only reads matching TOAST rows
SELECT * FROM features WHERE data @> '{"color": "red"}';
-- 1000 matches × 4KB = 4MB of TOAST reads
```

---

## Migration Patterns

### ✅ Correct Migration

```python
# Alembic migration
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

def upgrade():
    # 1. Add JSONB column (not JSON!)
    op.add_column('features', sa.Column('data', JSONB))
    
    # 2. Create GIN index
    op.create_index(
        'ix_features_data_gin',
        'features',
        ['data'],
        postgresql_using='gin'
    )

def downgrade():
    op.drop_index('ix_features_data_gin')
    op.drop_column('features', 'data')
```

### ❌ Incorrect Migration

```python
# WRONG: JSON type
op.add_column('features', sa.Column('data', sa.JSON))  # ❌

# WRONG: No index
op.add_column('features', sa.Column('data', JSONB))
# Missing: op.create_index(..., postgresql_using='gin')  # ❌

# WRONG: B-Tree index on JSONB (doesn't work for containment)
op.create_index('ix_features_data', 'features', ['data'])  # ❌
```

---

## Detection Script Logic

```python
import ast
import re

class SchemaValidator:
    def __init__(self, migration_content: str):
        self.content = migration_content
        self.violations = []
    
    def check(self):
        self._check_json_type()
        self._check_gin_index()
        self._check_extraction_in_queries()
        return self.violations
    
    def _check_json_type(self):
        """Detect JSON instead of JSONB."""
        # Pattern: sa.JSON or sa.Column(..., JSON)
        if re.search(r'sa\.JSON(?!\s*B)', self.content):
            self.violations.append({
                'type': 'WRONG_JSON_TYPE',
                'severity': 'HIGH',
                'message': 'Use JSONB instead of JSON'
            })
    
    def _check_gin_index(self):
        """Verify GIN index exists for JSONB columns."""
        has_jsonb = 'JSONB' in self.content
        has_gin = "postgresql_using='gin'" in self.content
        
        if has_jsonb and not has_gin:
            self.violations.append({
                'type': 'MISSING_GIN_INDEX',
                'severity': 'HIGH',
                'message': 'JSONB column requires GIN index'
            })
    
    def _check_extraction_in_queries(self):
        """Flag unindexed extraction operators."""
        # Pattern: ->> in WHERE without expression index
        if re.search(r"->>'[^']+'\s*=", self.content):
            self.violations.append({
                'type': 'UNINDEXED_EXTRACTION',
                'severity': 'MEDIUM',
                'message': 'Use @> containment or create expression index'
            })
```

---

## Best Practices Summary

1. **Always JSONB, never JSON** for queryable data
2. **Always create GIN index** on JSONB columns
3. **Use containment operators** (`@>`) for filtering
4. **Create expression indexes** if extraction (`->>`) is unavoidable
5. **Monitor query plans** with `EXPLAIN ANALYZE`
6. **Keep JSONB documents reasonably sized** (<1MB ideally)

---

## References

- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL GIN Indexes](https://www.postgresql.org/docs/current/gin.html)
- [TOAST Internals](https://www.postgresql.org/docs/current/storage-toast.html)
