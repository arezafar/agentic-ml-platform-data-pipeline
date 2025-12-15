# Physical View Backend Checklist

## Split Memory Allocation

- [ ] Container limit defined in K8s manifest
- [ ] JVM `-Xmx` = 70% of container limit
- [ ] Calculation: 16GB → Xmx=11g
- [ ] Native headroom = 30% for XGBoost
- [ ] Memory metrics dashboarded

## H2O Cluster Topology

- [ ] Deployed as StatefulSet
- [ ] Headless Service configured
- [ ] Stable DNS: h2o-0.h2o-headless.ns.svc
- [ ] Cluster forms correctly on startup
- [ ] Node failure triggers clean rejoin
- [ ] No split-brain scenarios

## Inference Deployment

- [ ] FastAPI as stateless Deployment
- [ ] HPA configured for auto-scaling
- [ ] No local state in pods
- [ ] Horizontal scaling enabled

## Container Sizing

- [ ] Training containers: 16GB+ (burst)
- [ ] Inference containers: 4-8GB (steady-state)
- [ ] Resource requests/limits defined

## Acceptance Criteria

| Story ID | Criteria | Status |
|----------|----------|--------|
| BA-PHY-01 | No OOM (70/30 split) | ☐ |
| BA-PHY-02 | Fallback returns 200 | ☐ |
| BA-PHY-03 | H2O cluster forms | ☐ |
