# Scenario View Backend Checklist

## Latency Spike Detection

- [ ] Monitoring alert if latency >50ms
- [ ] Tracing to identify: event loop blocking vs model complexity
- [ ] Dashboard shows p50, p95, p99 latency
- [ ] Alerting on sustained degradation

## OOM Prevention

- [ ] Pre-flight memory calculation before fan-out
- [ ] Reject if projected >80% node capacity
- [ ] Safe concurrency = floor(node_mem/task_mem)
- [ ] OOM monitoring and alerting

## Graceful Degradation

- [ ] Redis outage → DB fallback (latency increases)
- [ ] DB outage → Default response
- [ ] API returns 200 with degraded data, never 500
- [ ] Circuit state visible in metrics

## Zero-Downtime Updates

- [ ] MOJO artifact swaps via feature flags
- [ ] Old model serves until new model warm
- [ ] No errors during swap
- [ ] Rollback mechanism tested

## Runtime Version Verification

- [ ] Health check verifies MOJO version
- [ ] Fail fast on version mismatch
- [ ] Clear error message for debugging
- [ ] Alert sent to on-call on drift

## Acceptance Criteria

| Story ID | Criteria | Status |
|----------|----------|--------|
| BA-PHY-02 | Graceful degradation | ☐ |
| BA-PHY-06 | Version drift detected | ☐ |
