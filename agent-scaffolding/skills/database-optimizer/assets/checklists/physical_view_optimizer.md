# Physical View Optimizer Checklist

## TOAST Strategy

### Pre-Review
- [ ] Identify columns >2KB average size
- [ ] Map access patterns (hot vs cold)
- [ ] Review current STORAGE settings

### Storage Configuration
- [ ] Hot columns use STORAGE MAIN
- [ ] Cold/archive columns use STORAGE EXTERNAL
- [ ] lz4 compression for write-heavy workloads
- [ ] TOAST ratio <15% of main table

## Column Tetris (Alignment)

### DDL Order
- [ ] Wide fixed-length first (bigint, timestamp)
- [ ] Narrow fixed-length middle (int, smallint)
- [ ] Variable-length last (jsonb, text)
- [ ] Padding bytes <5% of row size

## GIN Index Configuration

### Per-Table Settings
- [ ] `gin_pending_list_limit` tuned per write velocity
  - Default tables: 4MB
  - High-write tables (>10K/s): 16MB
- [ ] Operator class appropriate for query patterns
  - Containment only (@>): jsonb_path_ops
  - Key existence (?): jsonb_ops
- [ ] Index bloat monitored and REINDEX scheduled

## Memory Allocation

### Container Settings
- [ ] Container memory limit defined
- [ ] shared_buffers = 25% of container RAM
- [ ] effective_cache_size = 75% of container RAM
- [ ] work_mem sized for complex queries

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| DB-OPT-03 | TOAST <15% | ☐ |
| DB-OPT-04 | Operator class | ☐ |
| DB-OPT-05 | HNSW tuned | ☐ |
