# Process View Security Audit Checklist

## Async Safety

- [ ] **CPU-Bound Offloading**: Are CPU-bound operations (token validation, ML scoring) offloaded to thread pools?
  - Pattern: `await loop.run_in_executor(None, blocking_func)`
  - Verification: Use blockbuster to detect event loop blocking
  - Risk: Event loop starvation, throughput collapse

- [ ] **Cryptographic Operations**: Are JWT signature verifications non-blocking?
  - Verification: Profile token validation latency
  - Threshold: <5ms p99 for validation

- [ ] **JWKS Fetching**: Are network calls to fetch JWKS handled asynchronously?
  - Verification: Check for async HTTP client usage (httpx, aiohttp)
  - Risk: Blocking main loop during key refresh

---

## Rate Limiting

- [ ] **Redis Backend**: Is rate limiting backed by Redis for distributed coordination?
  - Verification: Check `fastapi-limiter` configuration
  - Risk: Per-instance limits bypass in replicated deployments

- [ ] **Non-Blocking Calls**: Are Redis rate limit checks executed asynchronously?
  - Required: `await redis.incr()`
  - Verification: Profile rate limit overhead
  - Risk: Rate limiting becomes bottleneck

- [ ] **Tiered Limits**: Are rate limits differentiated by identity tier?
  - Minimum Tiers:
    - Anonymous: 10 req/min
    - Free Tier: 100 req/min
    - Enterprise: 1000 req/min
  - Verification: Locust test at threshold; expect 429

- [ ] **Identity-Based Limiting**: Is rate limiting keyed by OIDC identity, not just IP?
  - Verification: Test from same IP with different tokens
  - Risk: Legitimate users behind NAT blocked together

---

## Session Management

- [ ] **JWT Blocklist**: Is there a Redis-backed blocklist for revoked JWT JTI claims?
  - Verification: Revoke token manually; verify immediate rejection
  - Risk: Compromised tokens valid until expiry

- [ ] **Short-Lived Access Tokens**: Are access tokens short-lived (<15 min)?
  - Verification: Check token `exp` claim
  - Risk: Long window for compromised token abuse

- [ ] **Sliding Window Refresh**: Are refresh tokens managed with sliding expiration?
  - Verification: Refresh token extends session; idle sessions expire
  - Risk: Zombie sessions

- [ ] **Blocklist TTL Alignment**: Does blocklist entry TTL match access token lifetime?
  - Verification: Check Redis TTL on revoked JTI
  - Risk: Memory bloat from indefinite blocklist entries

---

## Request Coalescing

- [ ] **Cache Stampede Prevention**: Is request coalescing implemented for cache misses?
  - Pattern: Single request fetches, others wait
  - Verification: Expire popular key; verify single backend hit
  - Risk: Thundering herd on cache expiration

- [ ] **Probabilistic Early Expiration**: Is PER (probabilistic early recomputation) implemented?
  - Verification: Monitor cache refresh patterns
  - Risk: Synchronized expiration across keys

---

## Task Coverage

| Task ID | Description | Status |
|---------|-------------|--------|
| IAM-03 | Redis-Backed Session Revocation | [ ] |
| API-01 | Adaptive Rate Limiting Implementation | [ ] |
| MLSEC-01 | Model Artifact Signing | [ ] |
