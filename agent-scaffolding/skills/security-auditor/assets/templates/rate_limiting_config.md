# Rate Limiting Configuration

## Redis-Backed Rate Limiting for FastAPI

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI   │────▶│    Redis    │
│             │     │ (Limiter)   │     │  (Counters) │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Tiered Rate Limits

| Tier | Limit | Window | Key |
|------|-------|--------|-----|
| Anonymous | 10 req | 1 min | IP address |
| Free | 100 req | 1 min | User ID |
| Enterprise | 1000 req | 1 min | User ID |

---

## Implementation

### 1. Dependencies

```python
# requirements.txt
fastapi-limiter>=0.1.5
redis>=4.5.0
```

### 2. Limiter Setup

```python
# config/rate_limit.py
from fastapi import FastAPI, Request
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from redis.asyncio import Redis

async def init_rate_limiter(app: FastAPI):
    """Initialize rate limiter with Redis backend."""
    redis = await Redis.from_url(
        "redis://redis:6379",
        encoding="utf-8",
        decode_responses=True
    )
    await FastAPILimiter.init(redis)

async def close_rate_limiter():
    """Cleanup on shutdown."""
    await FastAPILimiter.close()

# Startup/shutdown hooks
app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_rate_limiter(app)

@app.on_event("shutdown")
async def shutdown():
    await close_rate_limiter()
```

### 3. Custom Identifier (Identity-Based)

```python
# auth/rate_limit.py
from fastapi import Request
from typing import Optional

async def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on identity.
    Falls back to IP for anonymous requests.
    """
    # Check for authenticated user
    user = getattr(request.state, "user", None)
    
    if user:
        user_id = user.get("sub", "unknown")
        tier = user.get("tier", "free")
        return f"user:{user_id}:{tier}"
    
    # Anonymous: use IP
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Trust only first IP (set by reverse proxy)
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host
    
    return f"anon:{client_ip}"
```

### 4. Tiered Limit Middleware

```python
# middleware/rate_limit.py
from fastapi import Request, HTTPException, status
from redis.asyncio import Redis

TIER_LIMITS = {
    "anon": {"requests": 10, "window": 60},
    "free": {"requests": 100, "window": 60},
    "enterprise": {"requests": 1000, "window": 60},
}

async def rate_limit_middleware(
    request: Request,
    redis: Redis
):
    """Non-blocking rate limit check."""
    key = await get_rate_limit_key(request)
    tier = key.split(":")[0] if ":" in key else "anon"
    
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["anon"])
    redis_key = f"ratelimit:{key}"
    
    # Atomic increment with expiry
    pipe = redis.pipeline()
    pipe.incr(redis_key)
    pipe.expire(redis_key, limits["window"])
    results = await pipe.execute()
    
    current_count = results[0]
    
    if current_count > limits["requests"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limits['requests']}/{limits['window']}s",
            headers={"Retry-After": str(limits["window"])}
        )
    
    # Add rate limit headers
    request.state.rate_limit_remaining = limits["requests"] - current_count
    request.state.rate_limit_limit = limits["requests"]
```

### 5. Response Headers

```python
# middleware/headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Add rate limit headers
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Remaining"] = str(
                request.state.rate_limit_remaining
            )
            response.headers["X-RateLimit-Limit"] = str(
                request.state.rate_limit_limit
            )
        
        return response
```

### 6. Route-Level Limits

```python
# routes/inference.py
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter

router = APIRouter()

@router.post(
    "/predict",
    dependencies=[Depends(RateLimiter(times=100, seconds=60))]
)
async def predict(request: PredictionRequest):
    """Inference endpoint with rate limiting."""
    ...

# Stricter limit for expensive operations
@router.post(
    "/batch-predict",
    dependencies=[Depends(RateLimiter(times=10, seconds=60))]
)
async def batch_predict(request: BatchPredictionRequest):
    """Batch inference with stricter limits."""
    ...
```

---

## Verification

```bash
# Test rate limit enforcement with locust
locust -f load_tests/rate_limit_test.py --users 50 --spawn-rate 10

# Verify 429 responses appear at threshold
grep "429" locust_stats.csv

# Check Redis keys
redis-cli KEYS "ratelimit:*"
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Risk | Solution |
|--------------|------|----------|
| IP-only limiting | NAT bypass, VPN evasion | Identity-based keys |
| Synchronous Redis | Event loop blocking | Use `await redis.incr()` |
| Fixed window only | Burst at window boundary | Sliding window or token bucket |
| No headers | Poor client UX | Return `X-RateLimit-*` headers |
