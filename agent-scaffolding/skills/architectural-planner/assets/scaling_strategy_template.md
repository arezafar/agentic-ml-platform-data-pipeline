# Horizontal Scaling Strategy Template

Scalability planning for distributed ML platforms.

---

## Project: {{ project_name }}

### Scaling Objective
Handle {{ target_load }} with {{ latency_sla }} latency.

---

## Service Classification

### Stateless Services

Services that maintain no local state between requests.

| Service | Current Load | Scaling Trigger | Target |
|---------|--------------|-----------------|--------|
| FastAPI Inference | {{ req/s }} | CPU >70% | {{ replicas }} |
| Mage Workers | {{ jobs/h }} | Queue depth | {{ replicas }} |

**Scaling Pattern**: Deployment + HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: request_queue_depth
        target:
          type: AverageValue
          averageValue: "10"
```

---

### Stateful Services

Services requiring stable identity and persistent storage.

| Service | State Type | Scaling Method | Constraints |
|---------|------------|----------------|-------------|
| H2O Cluster | In-memory DKV | StatefulSet resize | Cluster reformation |
| PostgreSQL | Disk-persistent | Shard addition | Rebalancing overhead |
| Redis | In-memory | Sentinel/Cluster | Slot migration |

**Scaling Pattern**: StatefulSet + Headless Service

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: h2o-cluster
spec:
  serviceName: h2o-headless
  replicas: 3
  podManagementPolicy: Parallel
  selector:
    matchLabels:
      app: h2o
  template:
    spec:
      containers:
        - name: h2o
          image: h2oai/h2o-open-source:latest
          env:
            - name: H2O_KUBERNETES_SERVICE_DNS
              value: h2o-headless.default.svc.cluster.local
```

---

## Bottleneck Mitigation

### Database Connection Limits

**Problem**: PostgreSQL `max_connections` (default 100) exhausted during scale-out.

**Solution**: Connection Pooling with PgBouncer

```yaml
# PgBouncer Configuration
[pgbouncer]
pool_mode = transaction
max_client_conn = 1000
default_pool_size = 20
reserve_pool_size = 5

[databases]
features = host=postgres port=5432
```

**Application Configuration**:
```python
# Point application to PgBouncer, not directly to Postgres
DATABASE_URL = "postgresql://pgbouncer:6432/features"
```

---

### Event Loop Saturation

**Problem**: CPU-bound inference blocks AsyncIO event loop.

**Solution**: Thread Pool Offloading

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def predict(features: dict) -> dict:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        executor,
        model.predict,  # Blocking call
        features
    )
    return result
```

---

### Cache Stampede

**Problem**: Popular key expires, all requests compute simultaneously.

**Solution**: Probabilistic Early Expiration

```python
import random

def get_with_early_expiry(key: str, ttl: int = 300) -> Any:
    result, remaining_ttl = redis.get_with_ttl(key)
    
    # Probabilistically refresh before expiry
    if remaining_ttl < ttl * 0.1:  # Last 10% of TTL
        probability = 1 - (remaining_ttl / (ttl * 0.1))
        if random.random() < probability:
            return None  # Force refresh
    
    return result
```

---

## Memory Management

### H2O JVM Configuration

**Formula**: `Container_Limit = JVM_Heap + Native_Overhead + Buffer`

| Container Size | JVM Heap (-Xmx) | Native/Python | Recommendation |
|----------------|-----------------|---------------|----------------|
| 16GB | 10GB | 6GB | Development |
| 32GB | 20GB | 12GB | Staging |
| 64GB | 40GB | 24GB | Production |

**Startup Command**:
```bash
java -Xmx40g -jar h2o.jar -flatfile /config/flatfile.txt
```

---

## Scaling Checklist

### Pre-Scaling
- [ ] Current bottleneck identified
- [ ] Scaling trigger defined (CPU, memory, queue depth)
- [ ] Target replicas calculated
- [ ] Resource limits verified

### Implementation
- [ ] HPA configured for stateless services
- [ ] StatefulSet configured for stateful services
- [ ] Connection pooling enabled
- [ ] Thread pools sized appropriately

### Validation
- [ ] Load test at target scale
- [ ] Latency SLA verified
- [ ] Cost projection reviewed
- [ ] Rollback plan documented

---

## Capacity Planning

### Inference Service

```
Target: 1000 req/s at p99 <50ms

Per-pod capacity: 100 req/s (measured)
Required pods: 1000 / 100 = 10 pods
Safety margin: 1.5x = 15 pods max

HPA: min=5, max=15, target CPU=70%
```

### PostgreSQL Shards

```
Target: 10TB data, 50k writes/s

Per-shard capacity: 3TB, 20k writes/s
Required shards: max(10/3, 50k/20k) = 4 shards
Replication factor: 2 (1 Primary + 1 Replica)

Total nodes: 4 shards × 2 = 8 nodes
```
