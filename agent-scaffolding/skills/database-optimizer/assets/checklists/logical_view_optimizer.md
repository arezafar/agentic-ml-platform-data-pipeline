# Logical View Optimizer Checklist

## JSONB Key Optimization

### Pre-Review
- [ ] Identify all JSONB columns in schema
- [ ] Map key usage patterns from application code
- [ ] Analyze pg_stats for key frequencies

### Key Abbreviation Protocol
- [ ] All JSONB keys are ≤3 characters
- [ ] Key mapping documentation exists
- [ ] Compression ratio verified >20% improvement

### Column Extraction
- [ ] Keys accessed in >80% of queries identified
- [ ] Promotion DDL generated for hot keys
- [ ] B-Tree index replaces GIN for extracted columns
- [ ] Query latency measured before/after

### TOAST Configuration
- [ ] Frequently accessed columns use STORAGE MAIN
- [ ] Large archive columns use STORAGE EXTERNAL
- [ ] lz4 compression enabled for large columns
- [ ] TOAST ratio monitored (<15% of main table)

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| DB-OPT-01 | Keys ≤3 chars | ☐ |
| DB-OPT-02 | Hot keys promoted | ☐ |
| DB-OPT-03 | TOAST <15% | ☐ |
