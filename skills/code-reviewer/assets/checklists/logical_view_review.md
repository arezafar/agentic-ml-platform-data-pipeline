# Logical View Review Checklist

Code review checklist for **Logical View** alignment—data modeling, schema integrity, and component atomicity.

---

## Epic: REV-LOG-01 (Hybrid Schema Integrity)

### ✅ JSONB Indexing Verification (LOG-REV-01-01)

**Migration File Checks:**
- [ ] Uses `sa.Column(..., JSONB)` NOT `JSON`
- [ ] `CREATE INDEX ... USING GIN` exists for JSONB columns
- [ ] GIN index covers frequently queried JSON paths
- [ ] No `->>` operators in WHERE clauses without B-Tree index on extracted field

**Anti-Patterns to Reject:**
```python
# ❌ WRONG: JSON type (not JSONB)
sa.Column('features', sa.JSON)

# ❌ WRONG: Missing GIN index
op.add_column('features', sa.Column('data', JSONB))
# No index created

# ❌ WRONG: Unindexed extraction in queries
WHERE features->>'color' = 'red'  # Full table scan!
```

**Correct Patterns:**
```python
# ✅ CORRECT: JSONB with GIN index
op.add_column('features', sa.Column('data', JSONB))
op.create_index('ix_features_data_gin', 'features', ['data'], 
                postgresql_using='gin')

# ✅ CORRECT: Containment query (uses GIN)
WHERE features @> '{"color": "red"}'::jsonb
```

---

### ✅ Feature Time-Travel Compliance (LOG-REV-01-02)

**Schema Requirements:**
- [ ] Feature tables include `event_time` or `valid_from` timestamp column
- [ ] Updates implemented as INSERTs (append-only) OR versioned rows (SCD Type 2)
- [ ] No destructive UPDATEs on historical feature data

**SCD Type 2 Pattern:**
```sql
-- Required columns for time-travel
event_time TIMESTAMP NOT NULL,
valid_from TIMESTAMP DEFAULT NOW(),
valid_to TIMESTAMP DEFAULT '9999-12-31'

-- Index for point-in-time queries
CREATE INDEX ix_features_event_time ON features(event_time);
```

---

### ✅ Mage Block Atomicity Check (LOG-REV-01-03)

**Transform Block Rules:**
- [ ] Transform blocks return DataFrames only
- [ ] No I/O operations in Transform blocks (must be in Loaders/Exporters)
- [ ] No side effects (file writes, API calls, logging to external services)
- [ ] Single transformation responsibility per block

**Anti-Patterns:**
```python
# ❌ WRONG: I/O in Transform block
@transformer
def transform(data, *args, **kwargs):
    df = data.copy()
    df.to_csv('output.csv')  # Side effect!
    return df

# ❌ WRONG: External API call in Transform
@transformer  
def transform(data, *args, **kwargs):
    response = requests.get('http://api/enrich')  # Side effect!
    return data
```

**Correct Pattern:**
```python
# ✅ CORRECT: Pure transformation
@transformer
def transform(data, *args, **kwargs):
    df = data.copy()
    df['new_col'] = df['existing'].apply(some_calculation)
    return df
```

---

## Review Decision Matrix

| Finding | Severity | Action |
|---------|----------|--------|
| `JSON` type instead of `JSONB` | 🔴 HIGH | Block PR |
| Missing GIN index on JSONB | 🔴 HIGH | Block PR |
| No temporal column on Feature table | 🟠 MEDIUM | Request change |
| Destructive UPDATE on features | 🟠 MEDIUM | Request change |
| I/O in Transform block | 🔴 HIGH | Block PR |
| Side effects in Transform | 🟠 MEDIUM | Request change |

---

## Related Task IDs
- `LOG-REV-01-01`: JSONB Indexing Verification
- `LOG-REV-01-02`: Feature Time-Travel Compliance  
- `LOG-REV-01-03`: Mage Block Atomicity Check
