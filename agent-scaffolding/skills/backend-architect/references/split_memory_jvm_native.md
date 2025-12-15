# Split Memory: JVM vs Native Allocation

## The Problem

H2O uses a hybrid memory model:
- **JVM Heap**: DataFrames, model metadata
- **Native (off-heap)**: XGBoost buffers, C++ algorithms

In containers, this creates danger:

```
Container: 16GB limit
JVM: -Xmx15g (93%)
XGBoost: needs 2GB native
Total: 17GB → OOM KILL
```

The process is silently killed with no stack trace.

## The 70/30 Formula

```
JVM Heap = Container Limit × 0.70
Native = Container Limit × 0.30
```

| Container | JVM (-Xmx) | Native Headroom |
|-----------|------------|-----------------|
| 8GB | 5.6GB | 2.4GB |
| 16GB | 11.2GB | 4.8GB |
| 32GB | 22.4GB | 9.6GB |

## Configuration

```yaml
# Kubernetes manifest
env:
  - name: JAVA_OPTS
    value: "-Xmx11g -Xms11g"
resources:
  limits:
    memory: 16Gi
```

## Calculation Script

```bash
python scripts/calculate_memory_split.py --container-limit 16g --output jvm-args.env
```

## Validation

XGBoost-heavy workloads may need more native headroom. Adjust to 60/40 if OOM persists.
