# Process View Orchestrator Checklist

## Event Loop Protection

### Pre-Review
- [ ] Identify all `async def` functions in PR
- [ ] Map external calls (DB, cache, ML inference)
- [ ] Understand latency requirements

### Blocking Call Isolation
- [ ] No `time.sleep()` in async functions
- [ ] `h2o.predict()` wrapped in `run_in_executor()`
- [ ] `requests` library replaced with `httpx`
- [ ] No synchronous file I/O (use `aiofiles`)
- [ ] subprocess calls offloaded to thread pool

### Database Connection Pooling
- [ ] Using `asyncpg` (not `psycopg2`) for async
- [ ] Pool created in FastAPI `startup` event
- [ ] `max_size` enforced to prevent exhaustion
- [ ] No per-request connection creation

### Redis Caching Pattern
- [ ] Cache keys include `model_version`
- [ ] All `SET` operations include `ex` (expiration)
- [ ] Fallback logic for Redis connection failure
- [ ] Look-Aside pattern implemented (Get → Miss → Compute → Set)

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| LEAD-PROC-01-01 | No blocking in async | ☐ |
| LEAD-PROC-01-02 | Pool in startup event | ☐ |
| LEAD-PROC-01-03 | TTL on cache keys | ☐ |
