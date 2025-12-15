# Logical View Orchestrator Checklist

## JSONB Indexing Verification

### Pre-Review
- [ ] Migration file identified
- [ ] Target table/columns identified
- [ ] Understanding of query patterns

### Technical Checks
- [ ] Migration uses `JSONB` type (not `JSON`)
- [ ] `CREATE INDEX ... USING GIN` exists for JSONB columns
- [ ] No `->>` operators in WHERE without B-Tree index
- [ ] Containment queries (`@>`) preferred over extraction (`->>`)

### Time-Travel Compliance
- [ ] Feature tables include `event_time` or `valid_from` column
- [ ] Updates implemented as INSERT (append-only)
- [ ] No in-place UPDATE on feature tables
- [ ] Snapshot isolation supported for ML training

### Mage Block Atomicity
- [ ] Transform blocks return DataFrames only
- [ ] No side-effect I/O in Transform blocks
- [ ] All database writes in Exporter blocks
- [ ] Pipeline failure leaves no partial state

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| LEAD-LOG-01-01 | JSONB + GIN indexes | ☐ |
| LEAD-LOG-01-02 | event_time present | ☐ |
| LEAD-LOG-01-03 | Atomic Mage blocks | ☐ |
