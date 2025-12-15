# Development View Optimizer Checklist

## Mage Block Atomicity

### Pre-Review
- [ ] Review all Mage Transform blocks
- [ ] Map I/O operations in pipeline
- [ ] Identify side-effect patterns

### Block Requirements
- [ ] Transform blocks return DataFrames only
- [ ] No side-effect I/O in Transform blocks
- [ ] All database writes in Exporter blocks
- [ ] Pipeline failure leaves no partial state

### Query Pattern Standards
- [ ] CTEs verified for predicate pushdown (not MATERIALIZED)
- [ ] LATERAL joins used for JSONB array unnesting
- [ ] No correlated subqueries in hot paths
- [ ] Partition keys included in all time-series queries

### Pydantic Contracts
- [ ] All JSONB insertion paths validate against schema
- [ ] Schema registry models defined for all JSON types
- [ ] Validation errors logged with context
- [ ] Deviations trigger alerts

### Cache Version Management
- [ ] Cache keys include model_version prefix
- [ ] Version incremented on model update
- [ ] Cache warmup script exists
- [ ] Stale cache detection implemented

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| DB-OPT-09 | CTE inlining | ☐ |
| DB-OPT-14 | Version keys | ☐ |
