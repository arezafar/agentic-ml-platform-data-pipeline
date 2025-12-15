# JVM Memory: Heap vs Native Allocation

## Overview

H2O is a hybrid system: JVM for the core engine, Native (C++) for XGBoost memory buffers. Proper memory configuration prevents OOM kills.

## The Problem: The Random OOM

### Scenario
- Container limit: 10GB RAM
- User sets: `JAVA_OPTS=-Xmx10g`
- JVM takes: 10GB for Heap
- XGBoost needs: 2GB for native buffers
- Total required: 12GB
- **Result: OOM killer terminates container**

This manifests as random crashes under load, difficult to diagnose because JVM monitoring shows "healthy" heap usage.

## The Solution: Memory Split

```
Container Limit: 10Gi
├── JVM Heap (-Xmx): 6-7Gi (60-70%)
└── Native Memory: 3-4Gi (30-40%)
    ├── XGBoost buffers
    ├── JNI overhead
    └── OS/container overhead
```

### Docker Compose Configuration

```yaml
services:
  h2o:
    image: h2oai/h2o-open-source-k8s:latest
    deploy:
      resources:
        limits:
          memory: 10G
    environment:
      - JAVA_OPTS=-Xmx7g -Xms7g  # 70% of 10G
```

### Kubernetes Configuration

```yaml
spec:
  containers:
  - name: h2o
    resources:
      limits:
        memory: 10Gi
    env:
    - name: JAVA_OPTS
      value: "-Xmx7g -Xms7g"
```

## XGBoost Native Memory Usage

XGBoost allocates native memory for:

| Component | Typical Size |
|-----------|-------------|
| DMatrix (training data) | 2-4GB |
| Histogram buffers | 0.5-1GB |
| Prediction output | 0.1-0.5GB |

### Estimation Formula

```
Native_Required = (Dataset_Size_MB * 2) + (Tree_Count * 10MB)
```

## Memory Calculation Rules

| Container Size | Safe -Xmx | Native Headroom |
|---------------|-----------|-----------------|
| 4Gi | 2.8Gi (70%) | 1.2Gi |
| 8Gi | 5.6Gi (70%) | 2.4Gi |
| 16Gi | 11.2Gi (70%) | 4.8Gi |
| 32Gi | 22.4Gi (70%) | 9.6Gi |

## Monitoring Native Memory

```bash
# Inside container
cat /sys/fs/cgroup/memory/memory.usage_in_bytes
cat /sys/fs/cgroup/memory/memory.limit_in_bytes

# Kubernetes
kubectl top pod h2o-0 --containers
```

### Prometheus Metrics

```yaml
# Alert when approaching limit
- alert: H2OMemoryPressure
  expr: container_memory_working_set_bytes{container="h2o"} / container_spec_memory_limit_bytes > 0.85
  for: 5m
```

## Common Mistakes

### ❌ Wrong: 100% Heap

```yaml
environment:
  - JAVA_OPTS=-Xmx10g  # Container limit is 10g!
```

### ❌ Wrong: No Limit

```yaml
# Missing memory limit
services:
  h2o:
    image: h2oai/h2o
    # No deploy.resources.limits.memory
```

### ✅ Correct: 70% Split

```yaml
deploy:
  resources:
    limits:
      memory: 10G
environment:
  - JAVA_OPTS=-Xmx7g -Xms7g
```

## Detection Script

```bash
python scripts/check_memory_allocation.py --compose-file ./docker-compose.yml
```

## References

- [H2O Memory Configuration](https://docs.h2o.ai/h2o/latest-stable/h2o-docs/starting-h2o.html)
- [XGBoost Memory Efficiency](https://xgboost.readthedocs.io/en/stable/tutorials/external_memory.html)
- [Kubernetes Memory Management](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/)
