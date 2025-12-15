# Async Concurrency Deep Dive

Technical reference for the **Async Non-Blocking Radar** superpower. Understanding why blocking calls in async contexts cause "The Death Spiral."

---

## The Python Concurrency Model

### The Event Loop

Python's `asyncio` implements **cooperative multitasking** using a single-threaded Event Loop:

```
┌─────────────────────────────────────────────────────────────┐
│                    Event Loop (Single Thread)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Task A (await db.fetch)  ─┐                                │
│  Task B (await http.get)   ├── All suspended, loop spins    │
│  Task C (await redis.get) ─┘                                │
│                                                              │
│  When I/O completes → Resume task → Process → Suspend again │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight**: The loop only "spins" when tasks voluntarily yield control via `await`.

---

## The Global Interpreter Lock (GIL)

Python's GIL ensures only one thread executes Python bytecode at a time:

```
┌──────────────────────────────────────────────────────────┐
│                    GIL Behavior                           │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Thread Pool:  [T1] [T2] [T3] [T4]                       │
│                 │                                         │
│  GIL Token:    [*]  ← Only holder can execute Python     │
│                                                           │
│  BUT: GIL released during I/O and C extensions           │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Implication**: CPU-bound work in multiple threads doesn't parallelize in Python. But I/O releases the GIL, enabling concurrent network/disk operations.

---

## The Blocking Call Problem

### What Happens When You Block

```python
async def handle_request():
    # ❌ This blocks the ENTIRE event loop
    time.sleep(1)  # All other requests freeze for 1 second
```

**Timeline:**
```
Request 1 arrives  ────────┐
Request 2 arrives  ─────┐  │
Request 3 arrives  ──┐  │  │
                     │  │  │
                     ▼  ▼  ▼
                  [Event Loop]
                       │
                  time.sleep(1)
                       │
                  ████████████ Loop frozen!
                       │
                  1 second later...
                       │
                  All 3 requests timeout
```

### The Death Spiral

Under load, a single blocking call cascades:

1. **Request 1** hits blocking call → Loop frozen
2. **Requests 2-100** queue up → Memory grows
3. **Load balancer** health check fails → Server marked unhealthy
4. **Traffic redistributed** → Other servers get 2x load
5. **Other servers block** → Cascade failure
6. **Full outage** → All services down

---

## Detection Patterns

### Blocking Call Deny List

```python
# Category: Sleep
time.sleep()
threading.Event().wait()

# Category: Sync HTTP
requests.get()
requests.post()
requests.put()
requests.delete()
urllib.request.urlopen()
http.client.HTTPConnection()

# Category: Sync Database
psycopg2.connect()
pymysql.connect()
sqlite3.connect()

# Category: CPU-Bound
h2o.predict()
pandas.DataFrame.apply()  # Large dataframes
numpy heavy computations
sklearn.model.predict()

# Category: File I/O
open().read()
open().write()
pathlib.Path.read_text()
```

### AST Detection Example

```python
import ast

BLOCKING_CALLS = {
    'time.sleep',
    'requests.get', 'requests.post',
    'h2o.predict',
}

class BlockingDetector(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.in_async = False
    
    def visit_AsyncFunctionDef(self, node):
        self.in_async = True
        self.generic_visit(node)
        self.in_async = False
    
    def visit_Call(self, node):
        if self.in_async:
            call_name = self._get_call_name(node)
            if call_name in BLOCKING_CALLS:
                self.violations.append({
                    'call': call_name,
                    'line': node.lineno,
                })
        self.generic_visit(node)
```

---

## Remediation Patterns

### Pattern 1: Async Alternatives

```python
# ❌ Blocking
import requests
response = requests.get(url)

# ✅ Non-blocking
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url)
```

### Pattern 2: run_in_executor

For unavoidable blocking calls (ML inference, legacy libraries):

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Create dedicated executor
executor = ThreadPoolExecutor(max_workers=4)

async def predict(data):
    loop = asyncio.get_event_loop()
    # Offload to thread pool
    result = await loop.run_in_executor(
        executor, 
        model.predict,  # Blocking call
        data
    )
    return result
```

**How It Works:**
```
┌─────────────────────────────────────────────────────────┐
│                    run_in_executor                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Event Loop Thread:                                      │
│  [handle_request] → await run_in_executor →              │
│       │                                                  │
│       ▼                                                  │
│  Suspends, loop continues to process other requests      │
│                                                          │
│  Thread Pool:                                            │
│  [Worker Thread] → model.predict(data) → returns         │
│       │                                                  │
│       ▼                                                  │
│  Event Loop Thread resumes with result                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Pattern 3: ProcessPoolExecutor

For true CPU parallelism (bypasses GIL):

```python
from concurrent.futures import ProcessPoolExecutor

# For CPU-heavy work that benefits from multiple cores
process_executor = ProcessPoolExecutor(max_workers=4)

async def heavy_computation(data):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        process_executor,
        cpu_intensive_function,
        data
    )
    return result
```

**When to Use:**
- `ThreadPoolExecutor`: I/O blocking, GIL-releasing C extensions
- `ProcessPoolExecutor`: Pure Python CPU-bound work

---

## Performance Guidelines

### Sizing the Executor

```python
# Rule of thumb for ML inference
import os

# CPU cores for inference workers
n_workers = min(os.cpu_count(), 8)

# Limit to prevent context switching overhead
executor = ThreadPoolExecutor(
    max_workers=n_workers,
    thread_name_prefix="ml-inference"
)
```

### Monitoring

```python
import time
from functools import wraps

def track_blocking_time(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        result = await func(*args, **kwargs)
        duration = time.monotonic() - start
        
        if duration > 0.1:  # 100ms threshold
            logger.warning(
                f"Slow executor call: {func.__name__} took {duration:.3f}s"
            )
        return result
    return wrapper
```

---

## Testing for Blocking

### Using blockbuster

```python
import pytest
from blockbuster import blockbuster_ctx

@pytest.fixture
def detect_blocking():
    with blockbuster_ctx() as bb:
        yield bb

async def test_endpoint_non_blocking(detect_blocking, client):
    response = await client.get("/predict")
    assert response.status_code == 200
    # Test fails if any blocking call detected
```

### Manual Verification

```python
import asyncio
import time

async def test_concurrent_requests():
    """Verify requests don't block each other."""
    start = time.monotonic()
    
    # Fire 10 concurrent requests
    tasks = [client.get("/predict") for _ in range(10)]
    responses = await asyncio.gather(*tasks)
    
    duration = time.monotonic() - start
    
    # If blocking: ~10 * single_request_time
    # If non-blocking: ~1 * single_request_time
    assert duration < 2.0  # Should complete in parallel
```

---

## References

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [FastAPI Concurrency](https://fastapi.tiangolo.com/async/)
- [Understanding the GIL](https://realpython.com/python-gil/)
- [blockbuster library](https://github.com/cython/cython/wiki/FAQ-GIL)
