# AsyncIO Concurrency: Event Loop Protection

## Overview

In Python's asyncio model used by FastAPI, a single thread (the Event Loop) manages all concurrent connections by suspending tasks awaiting I/O.

## The Mechanism

```python
# GOOD: Awaitable I/O suspends and yields control
async def get_user(user_id: int):
    user = await db.fetch_one(query)  # Loop continues
    return user

# BAD: Blocking call freezes the entire application
async def predict(features):
    result = h2o.predict(features)  # Loop STOPS
    return result
```

When `await db.fetch(...)` is called, the loop yields control. When data arrives, the loop resumes. This enables handling thousands of concurrent requests on a single thread.

## The Failure Mode: Death Spiral

If a function performs a CPU-bound calculation or blocking I/O without `await`, it holds control of the thread:

1. **Event Loop stops spinning**
2. **No other requests can be processed**
3. **No heartbeats sent to load balancer**
4. **Health checks fail**
5. **Service marked unhealthy and killed**

### Impact Calculation

In a system handling 1000 req/s:
- 100ms blocking call → 100 requests queue up
- Queue fills → Load balancer timeout
- Cascade failure across cluster

## The Remediation: run_in_executor

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def predict(features):
    loop = asyncio.get_event_loop()
    # Offload to thread pool, keep event loop free
    result = await loop.run_in_executor(executor, h2o.predict, features)
    return result
```

## Blocking Calls to Detect

| Call | Type | Remediation |
|------|------|-------------|
| `time.sleep()` | Blocking | Use `asyncio.sleep()` |
| `requests.get()` | Sync HTTP | Use `httpx.AsyncClient` |
| `h2o.predict()` | CPU-bound | Use `run_in_executor()` |
| `open().read()` | Sync I/O | Use `aiofiles` |
| `subprocess.run()` | Blocking | Use `asyncio.create_subprocess_exec()` |

## Detection Script

```bash
python scripts/detect_blocking_calls.py --source-dir ./src/service
```

## References

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [FastAPI Concurrency](https://fastapi.tiangolo.com/async/)
- [GIL and Threading](https://realpython.com/python-gil/)
