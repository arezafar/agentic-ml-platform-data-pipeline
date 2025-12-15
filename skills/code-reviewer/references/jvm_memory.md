# JVM Memory Management

Technical reference for the **Resource Isolation Sight** superpower. Understanding JVM Heap vs Native memory and preventing "The Random OOM."

---

## The Memory Equation

### Container Memory Components

```
┌────────────────────────────────────────────────────────────┐
│              Container Memory Allocation                    │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Container Limit (e.g., 10GB)                              │
│  ├── JVM Heap (-Xmx)            [User controlled]         │
│  ├── JVM Metaspace              [Classes, method data]    │
│  ├── JVM Code Cache             [JIT compiled code]       │
│  ├── JVM Thread Stacks          [1MB per thread]          │
│  ├── Native Memory              [C/C++ allocations]       │
│  │   ├── XGBoost buffers                                  │
│  │   ├── Native libraries                                 │
│  │   └── Direct ByteBuffers                               │
│  └── OS Overhead                [Kernel, filesystem]      │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### The Rule

```
Container_Limit >= JVM_Heap + Native_Memory + OS_Overhead

Safe Default: JVM_Heap = 70% of Container_Limit
              Native   = 25% of Container_Limit
              OS       = 5% of Container_Limit
```

---

## The Random OOM Problem

### What Happens

```
┌────────────────────────────────────────────────────────────┐
│              The Random OOM Failure                         │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Configuration:                                             │
│    Container Limit: 10GB                                   │
│    JAVA_OPTS: -Xmx10g    ← All 10GB to heap!              │
│                                                             │
│  Runtime:                                                   │
│    JVM Heap allocates 10GB                                 │
│    ↓                                                        │
│    XGBoost training starts                                 │
│    ↓                                                        │
│    XGBoost allocates 2GB native buffer                     │
│    ↓                                                        │
│    Container usage = 12GB > 10GB limit                     │
│    ↓                                                        │
│    Linux OOM Killer → SIGKILL                              │
│    ↓                                                        │
│    Container dies with no error message                    │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Why It's "Random"

- OOM only triggers when Native allocation happens
- May work fine in development (small data)
- Fails unpredictably in production (large data)
- No Java exception—just sudden death
- dmesg shows: `oom-kill: ... h2o-3`

---

## H2O Specific Considerations

### H2O Memory Usage

```
┌────────────────────────────────────────────────────────────┐
│              H2O Memory Breakdown                           │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  JVM Heap (H2O Java):                                      │
│  ├── H2O Frames (DataFrames)                               │
│  ├── Model objects                                         │
│  ├── Algorithm temporary data                              │
│  └── Cross-validation folds                                │
│                                                             │
│  Native Memory (C++/XGBoost):                              │
│  ├── XGBoost DMatrix buffers                               │
│  ├── XGBoost tree structures                               │
│  ├── Gradient/Hessian arrays                               │
│  └── MOJO runtime (if daimojo)                             │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Algorithm-Specific Native Usage

| Algorithm | Native Memory Usage |
|-----------|-------------------|
| GLM | Low (mostly JVM) |
| GBM | Medium (tree structures) |
| Random Forest | Medium (tree structures) |
| XGBoost | **HIGH** (native buffers) |
| Deep Learning | **HIGH** (native arrays) |
| Word2Vec | High (embeddings) |

---

## Correct Configuration

### Docker Compose

```yaml
services:
  h2o:
    image: h2oai/h2o-open-source-k8s:3.44.0.3
    environment:
      # 70% of 10GB = 7GB for heap
      - JAVA_OPTS=-Xmx7g -Xms7g
    deploy:
      resources:
        limits:
          memory: 10g        # Container limit
        reservations:
          memory: 8g         # Guaranteed memory
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: h2o
spec:
  template:
    spec:
      containers:
        - name: h2o
          image: h2oai/h2o-open-source-k8s:3.44.0.3
          env:
            - name: JAVA_OPTS
              value: "-Xmx7g -Xms7g"
          resources:
            limits:
              memory: "10Gi"
            requests:
              memory: "8Gi"
```

### Environment Variable Pattern

```bash
# Calculate dynamically based on container limit
CONTAINER_LIMIT_MB=$((10 * 1024))  # 10GB in MB
HEAP_PERCENTAGE=70
HEAP_SIZE_MB=$((CONTAINER_LIMIT_MB * HEAP_PERCENTAGE / 100))

export JAVA_OPTS="-Xmx${HEAP_SIZE_MB}m -Xms${HEAP_SIZE_MB}m"
```

---

## Detection Script Logic

```python
import re
import yaml

class MemoryConfigValidator:
    """Validate container memory configuration."""
    
    def __init__(self, config_content: str, config_type: str):
        self.content = config_content
        self.config_type = config_type  # 'docker-compose' or 'kubernetes'
        self.violations = []
    
    def validate(self):
        if self.config_type == 'docker-compose':
            self._validate_docker_compose()
        elif self.config_type == 'kubernetes':
            self._validate_kubernetes()
        return self.violations
    
    def _validate_docker_compose(self):
        config = yaml.safe_load(self.content)
        
        for service_name, service in config.get('services', {}).items():
            self._check_service(service_name, service)
    
    def _check_service(self, name: str, service: dict):
        # Get container memory limit
        container_limit = self._parse_memory_limit(service)
        if not container_limit:
            self.violations.append({
                'service': name,
                'type': 'NO_MEMORY_LIMIT',
                'severity': 'HIGH',
                'message': f'Service {name} has no memory limit defined'
            })
            return
        
        # Get JVM heap setting
        java_opts = self._get_java_opts(service)
        if not java_opts:
            return  # Not a JVM service
        
        heap_size = self._parse_xmx(java_opts)
        if not heap_size:
            self.violations.append({
                'service': name,
                'type': 'NO_XMX_DEFINED',
                'severity': 'MEDIUM',
                'message': f'Service {name} has JAVA_OPTS without -Xmx'
            })
            return
        
        # Check ratio
        ratio = heap_size / container_limit
        if ratio > 0.8:
            self.violations.append({
                'service': name,
                'type': 'HEAP_TOO_LARGE',
                'severity': 'CRITICAL',
                'message': (
                    f'Service {name}: Xmx ({heap_size}MB) is {ratio:.0%} of '
                    f'container limit ({container_limit}MB). '
                    f'Should be ≤70% to leave room for native memory.'
                ),
                'heap_mb': heap_size,
                'limit_mb': container_limit,
                'ratio': ratio
            })
        elif ratio > 0.7:
            self.violations.append({
                'service': name,
                'type': 'HEAP_BORDERLINE',
                'severity': 'MEDIUM',
                'message': (
                    f'Service {name}: Xmx is {ratio:.0%} of limit. '
                    f'Consider reducing to 70% for safety margin.'
                )
            })
    
    def _parse_memory_limit(self, service: dict) -> int:
        """Extract memory limit in MB."""
        # Docker Compose v3.x format
        deploy = service.get('deploy', {})
        resources = deploy.get('resources', {})
        limits = resources.get('limits', {})
        memory = limits.get('memory')
        
        if memory:
            return self._parse_memory_string(memory)
        return None
    
    def _get_java_opts(self, service: dict) -> str:
        """Extract JAVA_OPTS from environment."""
        env = service.get('environment', [])
        if isinstance(env, list):
            for item in env:
                if item.startswith('JAVA_OPTS='):
                    return item.split('=', 1)[1]
        elif isinstance(env, dict):
            return env.get('JAVA_OPTS')
        return None
    
    def _parse_xmx(self, java_opts: str) -> int:
        """Extract -Xmx value in MB."""
        match = re.search(r'-Xmx(\d+)([gGmMkK]?)', java_opts)
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            if unit == 'g':
                return value * 1024
            elif unit == 'k':
                return value // 1024
            return value  # Assume MB
        return None
    
    def _parse_memory_string(self, memory: str) -> int:
        """Parse Docker memory string to MB."""
        match = re.match(r'(\d+)([gGmM]?)', str(memory))
        if match:
            value = int(match.group(1))
            unit = match.group(2).lower()
            if unit == 'g':
                return value * 1024
            return value  # Assume MB
        return None
```

---

## Monitoring

### JVM Memory Metrics

```bash
# Inside container
jcmd 1 VM.native_memory summary

# Output:
# Native Memory Tracking:
# Total: reserved=12GB, committed=10GB
# - Java Heap: reserved=7GB, committed=7GB
# - Thread: reserved=500MB
# - Code: reserved=250MB
# - Internal: reserved=300MB
# - Other: reserved=4GB  ← Native allocations
```

### Container Memory Metrics

```bash
# View container memory usage
docker stats h2o-container

# Output:
# CONTAINER   MEM USAGE / LIMIT
# h2o         9.2GB / 10GB        ← Getting close!
```

### Kubernetes Monitoring

```bash
# View pod memory
kubectl top pod h2o-pod

# Check OOM events
kubectl describe pod h2o-pod | grep -A5 "Last State"
```

---

## Best Practices

1. **Always set -Xmx ≤ 70% of container limit**
2. **Set -Xms = -Xmx** to avoid heap resizing
3. **Monitor native memory** with `jcmd VM.native_memory`
4. **Set container memory limits** always
5. **Increase limit before heap** if OOM occurs
6. **Test with production-sized data** before deployment

---

## References

- [JVM Memory Settings](https://docs.oracle.com/javase/8/docs/technotes/tools/unix/java.html)
- [Container Memory Limits](https://docs.docker.com/config/containers/resource_constraints/)
- [H2O Memory Tuning](https://docs.h2o.ai/h2o/latest-stable/h2o-docs/faq/java.html)
- [XGBoost Memory Usage](https://xgboost.readthedocs.io/en/latest/tutorials/memory.html)
