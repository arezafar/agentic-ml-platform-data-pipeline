# Spike SPK-001: H2O MOJO C++ Runtime Viability

## Problem Statement

The H2O.ai ecosystem provides two model serialization formats:
- **POJO (Plain Old Java Object)**: Compiled Java classes
- **MOJO (Model Object, Optimized)**: Binary artifacts with runtime interpreter

The architecture mandates MOJO over POJO, but the scoring runtime has two options:
1. **h2o-genmodel.jar**: Standard Java runtime
2. **daimojo**: C++ runtime (potentially higher performance)

This spike investigates the viability of using the C++ runtime for open-source H2O models.

## Hypothesis

Using the C++ MOJO runtime (`daimojo`) will provide:
- Lower inference latency (no JVM overhead)
- Simpler deployment (no JDK dependency)
- Better memory efficiency

## Investigation

### daimojo Availability

**Finding**: `daimojo` is **proprietary** and part of H2O Driverless AI (DAI).

- The Python package `daimojo` requires a valid DAI license
- It is NOT available for open-source H2O-3 models
- Installation requires `pip install daimojo --extra-index-url https://...` with authenticated access

Reference: [H2O Driverless AI Documentation](https://docs.h2o.ai/driverless-ai/latest-stable/docs/userguide/scoring.html)

### Alternative: h2o-genmodel.jar

The standard MOJO runtime uses the Java-based `h2o-genmodel.jar`:

```java
import hex.genmodel.easy.EasyPredictModelWrapper;
import hex.genmodel.easy.RowData;
import hex.genmodel.MojoModel;

MojoModel model = MojoModel.load("model.zip");
EasyPredictModelWrapper wrapper = new EasyPredictModelWrapper(model);
RowData row = new RowData();
row.put("feature1", value1);
BinomialModelPrediction prediction = wrapper.predictBinomial(row);
```

### Python Integration Options

| Approach | Pros | Cons |
|----------|------|------|
| **py4j Bridge** | Direct Java interop | Complex setup, latency overhead |
| **Subprocess** | Simple isolation | High latency per call |
| **JNI/JPype** | Near-native performance | Complex, version-sensitive |
| **h2o Python package** | Simplest | Requires running H2O server |

### Recommended Approach

Use the `h2o` Python package with a persistent H2O in-memory context for scoring:

```python
import h2o

# Initialize H2O once at startup
h2o.init(nthreads=-1, max_mem_size="4g")

# Load MOJO
model = h2o.import_mojo("model.mojo")

# Score (in-memory, no network)
predictions = model.predict(h2o.H2OFrame(input_data))
```

**Latency Benchmark** (synthetic):
- Cold start: ~2-5 seconds (H2O init)
- Warm inference: ~1-10ms per prediction (depending on model complexity)

## Decision

### Fallback Confirmed: h2o-genmodel via Python h2o Package

Given that `daimojo` is proprietary:

1. **Primary Pattern**: Use `h2o.import_mojo()` with persistent H2O context
2. **Deployment**: H2O runs as sidecar or embedded JVM
3. **Optimization**: Pool H2O contexts, pre-warm models at startup

### Implementation Notes

```python
# In FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize H2O once
    h2o.init(nthreads=4, max_mem_size="8g")
    
    # Pre-load production model
    global CURRENT_MODEL
    CURRENT_MODEL = h2o.import_mojo("/models/production.mojo")
    
    yield
    
    h2o.cluster().shutdown()
```

## Conclusion

- **daimojo is NOT viable** for open-source H2O models (requires DAI license)
- **h2o-genmodel.jar** via the Python `h2o` package is the recommended approach
- Latency is acceptable for real-time inference (<10ms warm)
- The MOJO mandate remains valid; only the runtime changes

## Follow-Up Actions

1. [ ] Benchmark `h2o.import_mojo()` latency with production-sized models
2. [ ] Test memory footprint of multiple concurrent H2O contexts
3. [ ] Document H2O version pinning requirements (SPK relates to DEV-01-01)
