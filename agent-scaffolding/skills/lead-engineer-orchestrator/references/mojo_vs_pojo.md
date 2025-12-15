# MOJO vs POJO: ML Artifact Strategy

## Overview

H2O provides two export formats for trained models. This document explains why MOJO is mandated.

## POJO (Plain Old Java Object)

Exports the model as a `.java` source file that requires compilation.

### Characteristics
- Output: `Model.java` source file
- Requires: Java compiler at runtime
- Size: Can exceed 100MB for large models

### Failure Modes

1. **64KB Method Limit**
   - Java bytecode has a hard limit of 64KB per method
   - Large models (Random Forest with 5000 trees) exceed this limit
   - **Compilation fails completely**

2. **Compilation Overhead**
   - Large Java files take 30-60 seconds to compile
   - Memory intensive (2-4GB during compilation)
   - Cold start latency unacceptable for production

3. **JVM Dependency**
   - Requires full JVM at inference time
   - Larger container images (~500MB)
   - Version compatibility issues

## MOJO (Model Object, Optimized)

Exports the model as a serialized binary/JSON format in a `.zip` file.

### Characteristics
- Output: `model.zip` file
- Contains: `model.ini`, serialized trees, metadata
- Size: 10-50MB typical (compact)

### Advantages

1. **No Compilation Required**
   - H2O GenModel library reads the MOJO directly
   - Reconstructs model in memory instantly
   - Cold start < 2 seconds

2. **C++ Runtime Support**
   - `daimojo` library enables Python inference without JVM
   - Container images 200-300MB smaller
   - Lower memory footprint

3. **Size Efficiency**
   - Binary format more compact than Java source
   - No 64KB limit concerns
   - Supports models with millions of parameters

## Comparison Table

| Aspect | POJO | MOJO |
|--------|------|------|
| File Type | `.java` | `.zip` |
| Size Limit | 64KB method limit | No practical limit |
| Compilation | Required | Not required |
| Cold Start | 30-60s | < 2s |
| Runtime | JVM only | JVM or C++ (daimojo) |
| Container Size | ~500MB | ~200MB |

## Implementation

### Training Pipeline (Mage)

```python
# ❌ WRONG: POJO export
model.download_pojo(path="/models")

# ✅ CORRECT: MOJO export
model.download_mojo(path="/models/model.zip")
```

### Inference Service (FastAPI)

```python
# Using daimojo (C++ runtime)
import daimojo

model = daimojo.load("/models/model.zip")
predictions = model.predict(frame)
```

## Detection Script

```bash
python scripts/verify_mojo_artifact.py --pipeline-dir ./src/pipeline
```

## References

- [H2O MOJO Documentation](https://docs.h2o.ai/h2o/latest-stable/h2o-docs/productionizing.html)
- [daimojo Python Package](https://pypi.org/project/daimojo/)
