# Process View Optimizer Checklist

## Async Driver Enforcement

### Pre-Review
- [ ] Identify all database connection code
- [ ] Map sync vs async driver usage
- [ ] Review connection initialization patterns

### Driver Requirements
- [ ] All FastAPI routes use asyncpg (not psycopg2)
- [ ] SQLAlchemy async mode enabled if used
- [ ] No sync database calls in async contexts
- [ ] Connection pool created in startup event

### WAL Configuration
- [ ] `max_wal_size` ≥50GB for bulk ingestion
- [ ] `checkpoint_completion_target` = 0.9
- [ ] WAL compression enabled (lz4)
- [ ] No checkpoint warnings in logs

### Partition Management
- [ ] Time-series tables use declarative RANGE partitioning
- [ ] pg_partman configured for auto-creation
- [ ] Partition pruning confirmed in EXPLAIN
- [ ] Archive policy defined for old partitions

### Vacuum Configuration
- [ ] `autovacuum_vacuum_scale_factor` = 0.02 for hot tables
- [ ] Dead tuples <1% of live tuples
- [ ] Table bloat <20%
- [ ] Vacuum scheduling avoids peak hours

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| DB-OPT-10 | Checkpoint smooth | ☐ |
| DB-OPT-11 | Auto-partition | ☐ |
| DB-OPT-12 | Bloat <20% | ☐ |
