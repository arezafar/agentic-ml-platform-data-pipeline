# Circuit Breaker Patterns

## The State Machine

```
CLOSED ──[failures]──> OPEN ──[timeout]──> HALF-OPEN
  ↑                                           │
  └────────────[success]──────────────────────┘
```

## States

### CLOSED (Normal)
- Requests pass through
- Failures increment counter
- If failures > `fail_max` → OPEN

### OPEN (Failing Fast)
- Requests return fallback immediately
- No calls to dependency
- After `reset_timeout` → HALF-OPEN

### HALF-OPEN (Probing)
- Allow one canary request
- Success → CLOSED
- Failure → OPEN

## Configuration

```python
from aiobreaker import CircuitBreaker

redis_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60
)

@redis_breaker
async def get_from_cache(key):
    return await redis.get(key)
```

## Fallback Cascade

```python
async def get_features(entity_id):
    try:
        return await get_from_cache(entity_id)  # Primary
    except CircuitOpenError:
        return await get_from_db(entity_id)  # Fallback 1
    except DatabaseError:
        return default_features()  # Fallback 2
```

## Critical Rule

**Never return 500 on circuit open.** Always have a fallback that returns 200 with degraded data.

## Testing

```bash
python scripts/test_circuit_breaker.py --dependency redis --fail-count 5
```
