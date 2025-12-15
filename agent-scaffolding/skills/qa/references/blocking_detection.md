# Event Loop Blocking Detection

## Overview

In async Python applications (FastAPI with uvicorn), blocking the event loop is a critical performance anti-pattern that can cause:
- Request latency spikes
- Timeout errors
- Thread starvation
- Service unavailability

This document explains the theory and tools for detecting blocking in the Agentic ML Platform.

---

## The Problem: Async vs Blocking

### How AsyncIO Works

```
┌──────────────────────────────────────────────────────────┐
│                    Event Loop (Single Thread)             │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Request 1 ───await db.fetch()──► [yields to loop]       │
│                     ↓                                     │
│  Request 2 ───await db.fetch()──► [yields to loop]       │
│                     ↓                                     │
│  Request 3 ───await db.fetch()──► [yields to loop]       │
│                     ↓                                     │
│  [All requests wait concurrently for I/O]                │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Key insight**: Async code **yields** control during I/O, allowing other requests to proceed.

### What Blocking Looks Like

```
┌──────────────────────────────────────────────────────────┐
│                    Event Loop (BLOCKED)                   │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  Request 1 ───h2o.predict()──► [HOLDS LOOP FOR 50ms]     │
│                     X                                     │
│  Request 2 ─── WAITING ───────────────────────────►      │
│  Request 3 ─── WAITING ───────────────────────────►      │
│  Request 4 ─── WAITING ───────────────────────────►      │
│                                                           │
│  [All other requests frozen during blocking call]        │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Result**: 50ms blocking call → All concurrent requests delayed by 50ms.

---

## Common Blocking Patterns in ML Platforms

### 1. Synchronous Database Drivers

```python
# ❌ BLOCKING - psycopg2 blocks the event loop
import psycopg2

async def get_features(user_id: str):
    conn = psycopg2.connect("...")  # BLOCKS
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM features WHERE user_id = %s", (user_id,))
    return cursor.fetchall()  # BLOCKS

# ✅ NON-BLOCKING - asyncpg yields to event loop
import asyncpg

async def get_features(user_id: str):
    conn = await asyncpg.connect("...")  # YIELDS
    return await conn.fetch("SELECT * FROM features WHERE user_id = $1", user_id)
```

### 2. ML Model Inference

```python
# ❌ BLOCKING - H2O prediction runs on main thread
async def predict(features: list):
    return h2o_model.predict(features)  # BLOCKS for 10-50ms

# ✅ NON-BLOCKING - Offload to thread pool
import asyncio

async def predict(features: list):
    return await asyncio.to_thread(h2o_model.predict, features)  # YIELDS
```

### 3. Time.sleep vs asyncio.sleep

```python
# ❌ BLOCKING - Freezes the entire event loop
import time

async def retry_with_backoff():
    time.sleep(1)  # BLOCKS for 1 second

# ✅ NON-BLOCKING - Other requests can proceed
import asyncio

async def retry_with_backoff():
    await asyncio.sleep(1)  # YIELDS for 1 second
```

---

## Detection Tools

### 1. Blockbuster

[blockbuster](https://github.com/cjwfuller/blockbuster) is a Python library that detects when the event loop is blocked.

**Installation**:
```bash
pip install blockbuster
```

**Usage in pytest**:
```python
from blockbuster import blockbuster_ctx

@pytest.fixture
def blocking_detector():
    with blockbuster_ctx(
        blocking_threshold_ms=10,  # Alert if blocked > 10ms
        raise_on_block=True,       # Raise exception
    ):
        yield
```

**Autouse for all tests**:
```python
# conftest.py
@pytest.fixture(autouse=True)
def detect_blocking():
    with blockbuster_ctx(blocking_threshold_ms=10, raise_on_block=True):
        yield
```

### 2. AsyncIO Debug Mode

Python's built-in debug mode detects slow callbacks:

```python
import asyncio

loop = asyncio.get_event_loop()
loop.set_debug(True)
loop.slow_callback_duration = 0.010  # 10ms threshold

# Slow callbacks will generate warnings
```

### 3. Custom Monitoring

```python
import time
import asyncio

class BlockingMonitor:
    def __init__(self, threshold_ms: float = 10):
        self.threshold_ms = threshold_ms
        self._last_check = time.monotonic()
    
    async def monitor(self):
        while True:
            now = time.monotonic()
            gap = (now - self._last_check) * 1000
            
            if gap > self.threshold_ms + 100:  # Expected ~100ms sleep
                print(f"⚠️ Event loop blocked for {gap - 100:.0f}ms")
            
            self._last_check = now
            await asyncio.sleep(0.1)
```

---

## The GIL Factor

### What is the GIL?

The **Global Interpreter Lock (GIL)** prevents multiple Python threads from executing Python bytecode simultaneously.

**Impact on threading**:
- Pure Python CPU work cannot parallelize across threads
- C extensions (like daimojo) can release the GIL during computation
- I/O operations release the GIL automatically

### GIL and run_in_executor

```python
# Using run_in_executor DOES NOT bypass the GIL for pure Python
def pure_python_work(n):
    return sum(i**2 for i in range(n))  # Holds GIL

# But C extensions can release it
def daimojo_predict(features):
    return scorer.predict(features)  # daimojo releases GIL
```

**Verification test**:
```python
@pytest.mark.asyncio
async def test_gil_release():
    """Verify C++ extensions release the GIL."""
    import time
    from concurrent.futures import ThreadPoolExecutor
    
    executor = ThreadPoolExecutor(max_workers=4)
    loop = asyncio.get_event_loop()
    
    start = time.perf_counter()
    tasks = [
        loop.run_in_executor(executor, daimojo_predict, features)
        for _ in range(4)
    ]
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - start
    
    single_time = 0.050  # 50ms per prediction
    
    # If GIL released, 4 predictions should complete in ~50ms
    # If GIL held, 4 predictions would take ~200ms
    assert elapsed < 0.100, f"GIL not released: {elapsed:.3f}s"
```

---

## Best Practices

### 1. Always Use Async Drivers

| Blocking | Async Alternative |
|----------|-------------------|
| `psycopg2` | `asyncpg` |
| `mysql-connector` | `aiomysql` |
| `redis-py` | `aioredis` |
| `requests` | `httpx` / `aiohttp` |

### 2. Offload CPU-Bound Work

```python
# In FastAPI endpoints
from starlette.concurrency import run_in_threadpool

@app.post("/predict")
async def predict(request: PredictRequest):
    # Offload to thread pool
    result = await run_in_threadpool(model.predict, request.features)
    return {"prediction": result}
```

### 3. Set Appropriate Timeouts

```python
# Connection timeouts
async with asyncpg.create_pool(
    dsn,
    min_size=5,
    max_size=20,
    command_timeout=5,      # Query timeout
    max_inactive_connection_lifetime=300,
) as pool:
    ...
```

### 4. Monitor in Production

```python
# Prometheus metrics for blocking detection
from prometheus_client import Histogram

LOOP_LAG = Histogram(
    'event_loop_lag_seconds',
    'Event loop lag (blocking detection)',
    buckets=[0.001, 0.005, 0.010, 0.050, 0.100, 0.500, 1.0]
)
```

---

## Task Reference

| Task ID | Description |
|---------|-------------|
| ST-CONC-01 | Automated Blocking Detection (blockbuster) |
| ST-CONC-02 | Thread Pool Offloading Verification |
| ST-CONC-03 | Async vs. Sync Endpoint Benchmark |
