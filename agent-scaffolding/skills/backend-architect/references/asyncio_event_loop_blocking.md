# Asyncio Event Loop Blocking

## The Problem

FastAPI uses Python's asyncio event loop to handle thousands of concurrent connections on a single thread. The event loop yields control during I/O waits, allowing other coroutines to execute.

**However, ML inference is CPU-bound.** When `h2o_model.predict()` executes, it consumes the thread for the full duration (e.g., 50ms).

## The Cascade

During blocking:
1. Event loop cannot accept new connections
2. Health checks are missed
3. Kubernetes marks pod as unhealthy
4. Pod restart, cascade failure

At 20 RPS with 50ms blocking → complete service unavailability.

## The Solution: run_in_executor

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Create at startup
executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 2)

async def predict(features):
    loop = asyncio.get_event_loop()
    # Offload blocking call to thread pool
    result = await loop.run_in_executor(executor, model.predict, features)
    return result
```

The `daimojo` C++ runtime releases the GIL during execution, enabling true parallelism.

## Detection

```bash
python scripts/validate_event_loop.py --source-dir ./src --threshold-ms 10
```

## Thread Pool Sizing

```
max_workers = cpu_count * 2
```

Balance throughput with context-switching overhead.
