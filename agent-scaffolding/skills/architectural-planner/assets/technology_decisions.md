# Technology Decision Registry

Stack-specific constraints and mandated patterns for the Converged Data & ML Platform.

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Orchestration | Mage OSS | Latest | ETL pipelines, workflow |
| Persistence | PostgreSQL | 15+ | Feature store, registry |
| ML Runtime | H2O.ai | 3.x | AutoML, MOJO inference |
| Serving | FastAPI | 0.100+ | REST API, async I/O |
| Caching | Redis | 7+ | Look-aside cache |
| Container | Docker | 24+ | Packaging |
| Orchestration | Kubernetes | 1.28+ | Deployment |

---

## Mandated Patterns

### PostgreSQL

#### JSONB for Feature Vectors

**Mandate**: Use JSONB type, not JSON, for feature storage.

| Aspect | JSON | JSONB (Mandated) |
|--------|------|------------------|
| Storage | Text | Binary |
| Indexing | None | GIN indexable |
| Query Speed | Slow | Fast |

```sql
-- Required schema pattern
CREATE TABLE features (
    entity_id UUID NOT NULL,
    event_time TIMESTAMPTZ NOT NULL,
    feature_vector JSONB NOT NULL,  -- MANDATED: JSONB
    PRIMARY KEY (entity_id, event_time)
);

-- Required index
CREATE INDEX idx_features_vector_gin 
ON features USING GIN (feature_vector);

-- Optional: Vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE features ADD COLUMN embedding vector(768);
```

---

#### Connection Pooling

**Mandate**: PgBouncer in transaction mode for all production deployments.

```ini
# pgbouncer.ini
[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = scram-sha-256
pool_mode = transaction        # MANDATED
max_client_conn = 1000
default_pool_size = 20
reserve_pool_size = 5

[databases]
features = host=postgres port=5432
```

---

### H2O.ai

#### MOJO Export Only

**Mandate**: Use MOJO artifacts. POJOs are forbidden.

```python
# Training and export pattern
model = H2OGradientBoostingEstimator()
model.train(x=features, y=target, training_frame=train)

# MANDATED: MOJO export
mojo_path = model.download_mojo(path="models/", get_genmodel_jar=True)
```

#### Memory Configuration

**Mandate**: JVM Heap ≤ 70% of container memory.

```yaml
# Container resources
resources:
  limits:
    memory: "64Gi"
  
# H2O startup (62.5% of limit)
command: ["java", "-Xmx40g", "-jar", "h2o.jar"]
```

---

### FastAPI

#### Thread Pool for Inference

**Mandate**: All ML predictions offloaded to ThreadPoolExecutor.

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Global executor (sized to CPU cores)
inference_executor = ThreadPoolExecutor(max_workers=4)

async def predict_endpoint(request: PredictRequest) -> PredictResponse:
    loop = asyncio.get_running_loop()
    
    # MANDATED: Offload to thread pool
    result = await loop.run_in_executor(
        inference_executor,
        model.predict_sync,
        request.features
    )
    
    return PredictResponse(prediction=result)
```

---

#### Pydantic Models

**Mandate**: Shared contracts between producer and consumer.

```python
# shared/contracts/feature_vector.py
from pydantic import BaseModel, Field
from typing import Dict, Any

class FeatureVector(BaseModel):
    """Shared contract for feature data."""
    entity_id: str = Field(..., description="Unique entity identifier")
    features: Dict[str, Any] = Field(..., description="Feature key-value pairs")
    event_time: datetime = Field(default_factory=datetime.utcnow)

# Used in BOTH producer (Mage) and consumer (FastAPI)
```

---

### Redis

#### Look-Aside Caching

**Mandate**: Implement cache-aside pattern with TTL.

```python
async def get_prediction_cached(entity_id: str, features: dict) -> dict:
    cache_key = f"pred:{hash(frozenset(features.items()))}"
    
    # Step 1: Check cache
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Step 2: Compute
    result = await compute_prediction(features)
    
    # Step 3: Cache with TTL
    await redis.set(cache_key, json.dumps(result), ex=300)
    
    return result
```

---

### Mage OSS

#### Dynamic Blocks for Fan-Out

**Mandate**: Use Dynamic Blocks for parallel training.

```python
# Generator block - creates work items
@data_loader
def generate_training_configs() -> List[dict]:
    return [
        {"region": "us", "params": {...}},
        {"region": "eu", "params": {...}},
        {"region": "apac", "params": {...}},
    ]

# Dynamic block - runs in parallel per config
@transformer
def train_regional_model(config: dict) -> dict:
    h2o.init()
    model = train_model(config["params"])
    return {"region": config["region"], "model_path": save_mojo(model)}
```

---

### Kubernetes

#### StatefulSet for H2O

**Mandate**: Use StatefulSet with Headless Service for H2O cluster discovery.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: h2o-headless
spec:
  clusterIP: None  # Headless
  selector:
    app: h2o
  ports:
    - port: 54321
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: h2o
spec:
  serviceName: h2o-headless
  replicas: 3
  selector:
    matchLabels:
      app: h2o
  template:
    spec:
      containers:
        - name: h2o
          env:
            - name: H2O_KUBERNETES_SERVICE_DNS
              value: "h2o-headless.default.svc.cluster.local"
```

---

## Forbidden Patterns

| Pattern | Reason | Alternative |
|---------|--------|-------------|
| H2O POJO | JVM method size limits | MOJO |
| Direct Postgres connections | Connection exhaustion | PgBouncer |
| Sync predict in async route | Event loop blocking | run_in_executor |
| JSON type (not JSONB) | No indexing | JSONB |
| Range sharding for writes | Hotspots | Hash sharding |
| Docker-in-Docker | Security risk | Kaniko/BuildKit |

---

## Version Pinning

**Mandate**: Pin all dependencies in requirements.txt and Docker images.

```dockerfile
# Good: Pinned versions
FROM python:3.11.4-slim
RUN pip install h2o==3.42.0.1 fastapi==0.103.0

# Bad: Floating versions
FROM python:3.11
RUN pip install h2o fastapi
```

---

## Security Mandates

| Requirement | Implementation |
|-------------|----------------|
| No root containers | `runAsNonRoot: true` in SecurityContext |
| Secrets management | Kubernetes Secrets, not env vars |
| TLS everywhere | Ingress TLS termination |
| Network policies | Pod-to-pod isolation |
