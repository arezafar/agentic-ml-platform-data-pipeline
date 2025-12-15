# Physical View Orchestrator Checklist

## Resource Isolation

### Pre-Review
- [ ] Identify all containers with Java/H2O workloads
- [ ] Collect memory limits from manifests
- [ ] Document JAVA_OPTS settings

### Memory Split Verification
- [ ] `JAVA_OPTS` contains `-Xmx` setting
- [ ] Container `memory` limit defined
- [ ] **Xmx ≤ 70% of container limit** (for Native memory)
- [ ] XGBoost workloads have 30-40% Native headroom

### Memory Calculation

```
Container Limit: 10Gi
├── JVM Heap (-Xmx): 7Gi (70%)    ✅ Safe
└── Native Memory: 3Gi (30%)      ✅ XGBoost buffer space
```

### Network Security
- [ ] Postgres port (5432) not exposed to host
- [ ] Redis port (6379) not exposed to host
- [ ] Services use internal Docker DNS
- [ ] Private bridge network configured

### Volume Persistence
- [ ] Postgres data on named volume/PVC
- [ ] Mage project data on named volume/PVC
- [ ] Volume reclaim policy set to `Retain`
- [ ] Stateless services have no volumes

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| LEAD-PHY-01-01 | Xmx ≤ 70% of limit | ☐ |
| LEAD-PHY-01-02 | Internal networking | ☐ |
| LEAD-PHY-01-03 | Named volumes | ☐ |
