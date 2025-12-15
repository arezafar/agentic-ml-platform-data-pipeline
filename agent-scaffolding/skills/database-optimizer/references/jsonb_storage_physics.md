# JSONB Storage Physics: Key Overhead and TOAST

## Key Repetition Tax

PostgreSQL stores JSONB as a binary format with container headers and values. Unlike relational columns where names live in the system catalog, **JSONB repeats every key string for every row**.

### Storage Impact

```
Table: features (1 billion rows)
Key: "timestamp" (9 bytes)

Storage overhead = 9 bytes × 1B rows = 9 GB
With abbreviation "ts" = 2 bytes × 1B rows = 2 GB

Savings: 7 GB (78% reduction)
```

### Key Abbreviation Protocol

| Original Key | Abbreviated | Savings per 1M rows |
|-------------|-------------|---------------------|
| "timestamp" | "ts" | 7 MB |
| "user_id" | "uid" | 4 MB |
| "feature_value" | "fv" | 11 MB |

## TOAST: The Oversized-Attribute Storage Technique

When a value exceeds ~2KB, PostgreSQL moves it to a secondary `pg_toast` table.

### The Lookup Penalty

```
Main Query → TID lookup → TOAST fetch → Decompress → Return

Timeline:
├── Main heap access: 0.1ms
├── TOAST TID lookup: 0.5ms
├── TOAST data fetch: 2-5ms
└── Decompression: 1-3ms
    ─────────────────────
    Total: 3.6-8.6ms per row
```

This penalty is **invisible in EXPLAIN** but adds 5-50ms per row for large documents.

### STORAGE Strategies

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| PLAIN | No TOAST, no compression | Small values only |
| MAIN | Compress first, TOAST only if needed | **Hot columns** |
| EXTERNAL | TOAST without compression | Pre-compressed data |
| EXTENDED | Compress + TOAST (default) | Archive columns |

### Configuration

```sql
-- Force inline storage for hot column
ALTER TABLE features 
  ALTER COLUMN embedding SET STORAGE MAIN;

-- Enable lz4 compression (PostgreSQL 14+)
ALTER TABLE features 
  ALTER COLUMN payload SET COMPRESSION lz4;
```

## Monitoring TOAST

```sql
-- Check TOAST ratio
SELECT 
  relname,
  pg_size_pretty(pg_relation_size(relid)) AS main_size,
  pg_size_pretty(pg_relation_size(reltoastrelid)) AS toast_size,
  round(pg_relation_size(reltoastrelid)::numeric / 
        pg_relation_size(relid) * 100, 1) AS toast_ratio
FROM pg_stat_user_tables
WHERE reltoastrelid != 0
ORDER BY toast_ratio DESC;
```

## Remediation Strategies

1. **Key Abbreviation**: Reduce key names to ≤3 characters
2. **Column Extraction**: Promote hot keys to relational columns
3. **STORAGE MAIN**: Force inline storage for frequently accessed data
4. **lz4 Compression**: Faster decompression than default pglz
