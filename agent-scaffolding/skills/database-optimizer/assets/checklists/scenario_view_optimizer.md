# Scenario View Optimizer Checklist

## Drift Handling

### Pre-Review
- [ ] Drift detection metrics defined
- [ ] Threshold triggers documented
- [ ] Retrain pipeline exists

### Automation
- [ ] Query pattern drift detected via pg_stat_statements
- [ ] PSI/KL divergence monitored
- [ ] Automated retraining triggers on threshold
- [ ] New model validated before deployment

## Zero-Downtime Updates

### Cache Strategy
- [ ] Cache keys include model_version prefix
- [ ] Version swap completes in <1s
- [ ] No stale predictions served
- [ ] Rollback mechanism exists

### Model Swap
- [ ] MOJO artifact swap decoupled from DB migration
- [ ] Hot-swap tested under load
- [ ] No 500 errors during transition
- [ ] Latency remains stable

## Cache Warmup

### Deployment Process
- [ ] Background cache population on deploy
- [ ] Warmup script preloads hot data
- [ ] Buffer hit ratio >99% before serving
- [ ] Monitoring confirms warmup complete

## Connection Resilience

### Failover Handling
- [ ] Connection pools gracefully handle restarts
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker for cascade prevention
- [ ] No application-level errors on failover

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| DB-OPT-08 | Buffer >99% | ☐ |
| DB-OPT-14 | Swap <1s | ☐ |
| DB-OPT-13 | No refused | ☐ |
