# Process View Review Checklist

Code review checklist for **Process View** alignment—concurrency, event loop protection, and async/sync separation.

---

## Epic: REV-PROC-01 (Event Loop Protection)

### ✅ Blocking Call Isolation (PROC-REV-01-01)

**Async Function Checks:**
- [ ] No `time.sleep()` in `async def` functions
- [ ] No `requests` library calls (use `httpx` instead)
- [ ] CPU-bound operations wrapped in `run_in_executor`
- [ ] No `h2o.predict()` directly in async context
- [ ] No blocking file I/O (`open()` → use `aiofiles`)

**Blocking Call Deny List:**
```python
# ❌ FORBIDDEN in async context:
time.sleep()
requests.get(), requests.post(), requests.*
urllib.request.*
h2o.predict(), h2o.automl.*
pandas.read_csv()  # Large files
model.predict()  # ML inference
open().read()  # Sync file I/O
```

**Anti-Patterns:**
```python
# ❌ WRONG: Blocking sleep in async
async def process_request():
    time.sleep(1)  # BLOCKS EVENT LOOP
    
# ❌ WRONG: Sync HTTP in async
async def fetch_data():
    response = requests.get(url)  # BLOCKS EVENT LOOP
    
# ❌ WRONG: ML inference blocking loop
async def predict(data):
    result = model.predict(data)  # CPU-BOUND, BLOCKS LOOP
```

**Correct Patterns:**
```python
# ✅ CORRECT: Async sleep
async def process_request():
    await asyncio.sleep(1)
    
# ✅ CORRECT: Async HTTP client
async def fetch_data():
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        
# ✅ CORRECT: Executor offloading
async def predict(data):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, model.predict, data)
```

---

### ✅ DB Connection Pooling Gate (PROC-REV-01-02)

**Database Driver Checks:**
- [ ] API layer uses `asyncpg` NOT `psycopg2`
- [ ] Connection pool initialized in `startup` event
- [ ] No per-request connection creation
- [ ] Pool size configured appropriately

**Anti-Patterns:**
```python
# ❌ WRONG: Sync driver in async API
import psycopg2
conn = psycopg2.connect(...)  # Blocks!

# ❌ WRONG: Connection per request
async def get_data():
    pool = await asyncpg.create_pool(...)  # Pool per request!
```

**Correct Patterns:**
```python
# ✅ CORRECT: Async driver with startup pool
from asyncpg import create_pool

@app.on_event("startup")
async def startup():
    app.state.db = await create_pool(DATABASE_URL)

@app.on_event("shutdown") 
async def shutdown():
    await app.state.db.close()

async def get_data():
    async with app.state.db.acquire() as conn:
        return await conn.fetch("SELECT * FROM features")
```

---

### ✅ Redis Caching Pattern Review (PROC-REV-01-03)

**Caching Requirements:**
- [ ] Look-Aside pattern: Get → Miss → Compute → Set
- [ ] Cache keys include Model Version (prevent stale predictions)
- [ ] All SET operations include TTL (`ex` parameter)
- [ ] Fallback logic exists for Redis connection failure

**Cache Key Format:**
```python
# ✅ CORRECT: Version-aware cache key
cache_key = f"predict:{model_version}:{hash(input_data)}"
```

**Anti-Patterns:**
```python
# ❌ WRONG: No TTL on cache
await redis.set(key, value)

# ❌ WRONG: No model version in key
cache_key = f"predict:{hash(input)}"  # Stale after model update!

# ❌ WRONG: No Redis failure handling
value = await redis.get(key)  # Crashes if Redis down
```

**Correct Patterns:**
```python
# ✅ CORRECT: Look-Aside with TTL and fallback
async def cached_predict(input_data):
    cache_key = f"predict:v{MODEL_VERSION}:{hash(input_data)}"
    
    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except RedisError:
        pass  # Fallback to compute
    
    result = await run_in_executor(None, model.predict, input_data)
    
    try:
        await redis.set(cache_key, json.dumps(result), ex=3600)
    except RedisError:
        pass  # Cache write failure non-fatal
    
    return result
```

---

## Review Decision Matrix

| Finding | Severity | Action |
|---------|----------|--------|
| `time.sleep()` in async function | 🔴 CRITICAL | Block PR |
| `requests` library in async | 🔴 CRITICAL | Block PR |
| ML inference without executor | 🔴 CRITICAL | Block PR |
| `psycopg2` in API layer | 🔴 HIGH | Block PR |
| Per-request connection pool | 🟠 MEDIUM | Request change |
| Cache SET without TTL | 🟠 MEDIUM | Request change |
| No Redis fallback | 🟡 LOW | Suggest improvement |

---

## Related Task IDs
- `PROC-REV-01-01`: Blocking Call Isolation
- `PROC-REV-01-02`: DB Connection Pooling Gate
- `PROC-REV-01-03`: Redis Caching Pattern Review
