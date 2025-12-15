# Mage Dynamic Blocks: Fan-Out Control

## The Pattern

Dynamic Blocks enable parallel execution by "fanning out" based on upstream configuration.

```python
@data_loader
def generate_configs():
    """Upstream block yields configurations."""
    return [
        [{"learning_rate": 0.01, "max_depth": 5}],
        [{"learning_rate": 0.05, "max_depth": 3}],
        [{"learning_rate": 0.1, "max_depth": 7}],
        # Each inner list spawns a parallel task
    ]
```

## The Problem

Without limits: 50 tasks × 4GB each = 200GB required.

Kubernetes responds with OOM kills, preemption, or node crashes.

## The Solution: max_parallel_blocks

```python
# In block config
max_parallel_blocks = floor(node_memory / task_memory)

# For 64GB node, 4GB tasks:
max_parallel_blocks = 64 / 4 = 16
```

Additional tasks queue and execute as slots free.

## Configuration

```yaml
# In block metadata
parallelism:
  max_parallel_blocks: 16
```

## Memory Estimation

```
Task Memory = H2O DataFrame + Model + Overhead
            = (~2-4GB typical for AutoML)
```

## Champion Selection

```python
@reducer
def select_champion(results):
    """Reducer block aggregates all parallel results."""
    best = max(results, key=lambda r: r['auc'])
    register_to_model_registry(best['model_path'])
    return best
```

## Monitoring

- Track parallel task count vs limit
- Alert if queue grows faster than drain rate
- Dashboard for cluster memory utilization
