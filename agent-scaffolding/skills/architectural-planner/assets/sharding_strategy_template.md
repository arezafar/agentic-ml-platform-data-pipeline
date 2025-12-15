# Sharding Strategy Template

Sequential-thinking decomposition for database sharding.

---

## Project: {{ project_name }}

### Objective
Implement horizontal partitioning to handle {{ data_volume }} with {{ throughput }} IOPS.

---

## Step 1: Profile Data

### Cardinality Analysis

| Column | Cardinality | Distribution | Access Pattern |
|--------|-------------|--------------|----------------|
| `entity_id` | {{ count }} | Uniform | Point lookups |
| `segment` | {{ count }} | Skewed | Range scans |
| `event_time` | {{ count }} | Time-ordered | Recent bias |

### Access Patterns

- **Read/Write Ratio**: {{ ratio }} (e.g., 80/20)
- **Hot Partitions**: {{ describe_hotspots }}
- **Query Types**: Point lookup / Range scan / Aggregation

### Decision Gate
- [ ] Cardinality sufficient for uniform distribution?
- [ ] Write patterns avoid temporal hotspots?

---

## Step 2: Select Shard Key

### Candidate Analysis

| Candidate | Cardinality | Stability | Hotspot Risk |
|-----------|-------------|-----------|--------------|
| `entity_id` (UUID) | High ✓ | Immutable ✓ | Low ✓ |
| `created_at` (Date) | Medium | Immutable | High ✗ |
| `segment` | Low | Mutable ✗ | High ✗ |

### Recommendation

**Selected Key**: `entity_id`

**Rationale**:
- High cardinality ensures even distribution
- UUIDs are immutable (no row migration)
- Natural tenant isolation for multi-tenant workloads

### Composite Key Option

If single-key distribution is insufficient:
```sql
shard_key = hash(entity_id || region_id)
```

---

## Step 3: Design Routing

### Routing Architecture

**Pattern**: Application-Side Routing

```python
def get_shard_index(entity_id: str, total_shards: int) -> int:
    """Consistent hash routing."""
    return hash(entity_id) % total_shards

def get_connection(entity_id: str) -> Connection:
    """Return connection pool for target shard."""
    shard_idx = get_shard_index(entity_id, TOTAL_SHARDS)
    return connection_pools[shard_idx]
```

### Implementation Patterns

| Layer | Pattern | Tooling |
|-------|---------|---------|
| Mage Blocks | Connection Map | Batch by shard, write to correct pool |
| FastAPI | Dependency Injection | `get_db_shard(entity_id)` provider |
| Direct SQL | Middleware | Pgpool-II or custom router |

### Cross-Shard Queries

Handle with:
1. **Scatter-Gather**: Query all shards, merge results
2. **Global Table**: Replicate small reference tables to all shards
3. **Avoid**: Redesign queries to be shard-local

---

## Step 4: Plan Migration

### Migration Strategy

**Pattern**: Online Migration (Zero Downtime)

### Phase 1: Dual-Write Setup
```
┌─────────────┐    ┌─────────────┐
│ Old Single  │───→│ New Sharded │
│ Database    │    │ Cluster     │
└─────────────┘    └─────────────┘
       │                  │
       └──── Writes ──────┘
```

### Phase 2: Backfill Historical Data
```bash
# Batch copy with shard-aware routing
python scripts/migrate_shard.py \
    --source postgres://old-db \
    --target shard-config.yaml \
    --batch-size 10000
```

### Phase 3: Cutover
1. Enable read from new cluster
2. Disable write to old cluster
3. Verify data consistency
4. Decommission old cluster

### Rollback Plan
- [ ] Keep old cluster running for 7 days post-cutover
- [ ] Maintain ability to re-route traffic
- [ ] Monitor consistency metrics

---

## Verification Checklist

### Pre-Implementation
- [ ] Cardinality analysis complete
- [ ] Shard key selected and documented
- [ ] Routing logic designed
- [ ] Migration plan reviewed

### Post-Implementation
- [ ] Data distributed evenly across shards
- [ ] No cross-shard queries in critical paths
- [ ] Failover tested per shard
- [ ] Performance meets SLA

---

## Topology Summary

```
Total Shards: {{ N }}
Shard Key: {{ key }}
Routing: Application-Side / Middleware

Shard 0: postgres://shard-0:5432/features
Shard 1: postgres://shard-1:5432/features
...
Shard N: postgres://shard-N:5432/features
```
