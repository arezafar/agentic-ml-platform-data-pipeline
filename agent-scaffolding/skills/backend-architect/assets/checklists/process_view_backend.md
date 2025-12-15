# Process View Backend Checklist

## Event Loop Protection

- [ ] All `h2o.predict()` wrapped in `run_in_executor`
- [ ] ThreadPoolExecutor(max_workers=cpu*2) created at startup
- [ ] Main thread never blocks >10ms
- [ ] Event loop lag monitoring middleware active
- [ ] CI fails on blocking detection

## MOJO Runtime

- [ ] Using `daimojo` C++ runtime
- [ ] No JVM in inference path
- [ ] Cold start <2 seconds
- [ ] Memory footprint <500MB per worker

## Fan-Out Control

- [ ] Dynamic Blocks configured
- [ ] `max_parallel_blocks` calculated: floor(node_memory/task_memory)
- [ ] No OOM kills during hyperparameter tuning
- [ ] Cluster utilization >80%

## Circuit Breakers

- [ ] Redis wrapped with circuit breaker (fail_max=5)
- [ ] PostgreSQL wrapped with circuit breaker
- [ ] `reset_timeout=60s` configured
- [ ] Fallback cascade: Cache→DB→Default
- [ ] Circuit state visible in metrics

## Acceptance Criteria

| Story ID | Criteria | Status |
|----------|----------|--------|
| BA-PROC-01 | No blocking >10ms | ☐ |
| BA-PROC-02 | Cold start <2s | ☐ |
| BA-PROC-05 | No OOM kills | ☐ |
