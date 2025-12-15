# Physical View Review Checklist

Code review checklist for **Physical View** alignment—resource allocation, network security, and persistence.

---

## Epic: REV-PHY-01 (Resource Isolation)

### ✅ Memory Split Verification (PHY-REV-01-01)

**Container Configuration Checks:**
- [ ] `JAVA_OPTS` contains `-Xmx` setting
- [ ] Container `memory` limit is defined
- [ ] Xmx ≤ 70% of container memory limit
- [ ] Sufficient headroom for Native memory (XGBoost, C++ libs)

**The Memory Equation:**
```
Container_Limit >= JVM_Heap + Native_Overhead + OS_Overhead

Safe Rule: JVM_Heap = 70% of Container_Limit
Example:   Container = 10GB → Xmx = 7GB → Native = 3GB
```

**Anti-Patterns:**
```yaml
# ❌ WRONG: Xmx equals container limit
services:
  h2o:
    environment:
      - JAVA_OPTS=-Xmx10g  # All memory to heap!
    deploy:
      resources:
        limits:
          memory: 10g  # No room for Native!

# ❌ WRONG: No memory limit
services:
  h2o:
    environment:
      - JAVA_OPTS=-Xmx16g  # Unbounded!
    # No memory limit defined
```

**Correct Patterns:**
```yaml
# ✅ CORRECT: Proper memory split
services:
  h2o:
    environment:
      - JAVA_OPTS=-Xmx7g -Xms7g  # 70% of limit
    deploy:
      resources:
        limits:
          memory: 10g  # 30% headroom for Native
```

**Kubernetes Equivalent:**
```yaml
# ✅ CORRECT: K8s resource limits
containers:
  - name: h2o
    env:
      - name: JAVA_OPTS
        value: "-Xmx7g -Xms7g"
    resources:
      limits:
        memory: "10Gi"
      requests:
        memory: "8Gi"
```

---

### ✅ Network Security Review (PHY-REV-01-02)

**Network Configuration Checks:**
- [ ] Postgres port (5432) NOT mapped to host (except dev)
- [ ] Redis port (6379) NOT mapped to host (except dev)
- [ ] Services communicate via internal Docker DNS
- [ ] Private bridge network defined

**Anti-Patterns:**
```yaml
# ❌ WRONG: Database exposed to host
services:
  postgres:
    ports:
      - "5432:5432"  # Exposed to host network!
  
  redis:
    ports:
      - "6379:6379"  # Exposed to host network!
```

**Correct Patterns:**
```yaml
# ✅ CORRECT: Internal network only
services:
  postgres:
    # No 'ports' mapping - internal only
    networks:
      - internal
  
  redis:
    networks:
      - internal
  
  api:
    ports:
      - "8000:8000"  # Only API exposed
    networks:
      - internal
    depends_on:
      - postgres
      - redis

networks:
  internal:
    driver: bridge
    internal: true  # No external access
```

**Internal DNS Usage:**
```python
# ✅ CORRECT: Service name as hostname
DATABASE_URL = "postgresql://user:pass@postgres:5432/db"
REDIS_URL = "redis://redis:6379"
# Uses Docker DNS, not localhost or IP
```

---

### ✅ Volume Persistence Check (PHY-REV-01-03)

**Persistent Storage Checks:**
- [ ] Postgres data directory on named volume or PVC
- [ ] Mage project directory on named volume or PVC
- [ ] API/Inference containers are stateless (no volumes required)
- [ ] Model artifacts stored in shared volume accessible by both pipeline and service

**Anti-Patterns:**
```yaml
# ❌ WRONG: Bind mount (not portable)
services:
  postgres:
    volumes:
      - ./data/postgres:/var/lib/postgresql/data  # Host-dependent!

# ❌ WRONG: No volume (data lost on restart)
services:
  postgres:
    image: postgres:15
    # No volumes defined!
```

**Correct Patterns:**
```yaml
# ✅ CORRECT: Named volumes
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  mage:
    volumes:
      - mage_project:/home/mage_code
      - model_artifacts:/home/mage_code/artifacts
  
  api:
    volumes:
      - model_artifacts:/app/models:ro  # Read-only

volumes:
  postgres_data:
  mage_project:
  model_artifacts:
```

**Kubernetes PVC:**
```yaml
# ✅ CORRECT: PersistentVolumeClaim
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
```

---

## Review Decision Matrix

| Finding | Severity | Action |
|---------|----------|--------|
| Xmx ≥ Container limit | 🔴 CRITICAL | Block PR |
| No container memory limit | 🔴 HIGH | Block PR |
| Database port exposed to host | 🔴 HIGH | Block PR |
| No named volume for Postgres | 🔴 HIGH | Block PR |
| Xmx > 80% of limit | 🟠 MEDIUM | Request change |
| Bind mount instead of named volume | 🟠 MEDIUM | Request change |
| Redis port exposed to host | 🟡 LOW | Suggest improvement |

---

## Related Task IDs
- `PHY-REV-01-01`: Memory Split Verification
- `PHY-REV-01-02`: Network Security Review
- `PHY-REV-01-03`: Volume Persistence Check
