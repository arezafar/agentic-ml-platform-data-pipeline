# MOJO vs POJO: H2O Artifact Strategy

Technical reference for the **Artifact Integrity Scanner** superpower. Understanding why MOJO is mandatory and POJO causes "Jar Hell."

---

## Overview

H2O.ai provides two formats for exporting trained models:

| Aspect | MOJO | POJO |
|--------|------|------|
| Full Name | Model Object, Optimized | Plain Old Java Object |
| Format | `.zip` archive | `.java` source file |
| Runtime | C++ (daimojo) or Java | JVM only |
| Compilation | None required | Required at load time |
| Size Limit | Unlimited | 64KB method limit |
| Use Case | Production inference | Prototyping only |

---

## MOJO Architecture

### Structure

```
model.zip
├── model.ini           # Model metadata
├── domains/            # Categorical encodings
│   ├── d000.txt
│   └── d001.txt
├── trees/              # Tree structures (GBM/RF)
│   ├── t00_000.bin
│   └── t00_001.bin
└── experimental/       # Algorithm-specific data
```

### Loading Mechanism

```
┌────────────────────────────────────────────────────────────┐
│                    MOJO Loading                             │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Read model.ini → parse metadata                        │
│  2. Load domains → reconstruct categorical mappings        │
│  3. Load trees → build in-memory decision tree structure   │
│  4. Ready to predict → No compilation step                 │
│                                                             │
│  Time: ~100ms for large models                             │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Runtime Options

**Java (h2o-genmodel.jar):**
```java
import hex.genmodel.MojoModel;
import hex.genmodel.easy.EasyPredictModelWrapper;

MojoModel model = MojoModel.load("model.zip");
EasyPredictModelWrapper wrapper = new EasyPredictModelWrapper(model);
```

**C++ (daimojo / Python):**
```python
import daimojo

model = daimojo.load("model.zip")
predictions = model.predict(data)
```

**Why C++?**
- ~10x faster inference than Java
- No JVM overhead
- Lower memory footprint
- Better suited for FastAPI async architecture

---

## POJO Problems

### The 64KB Method Limit

Java has a hard limit: no method can exceed 64KB of bytecode.

```
┌────────────────────────────────────────────────────────────┐
│                    POJO Generation                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Model: Random Forest with 5000 trees                      │
│                                                             │
│  Generated Java:                                            │
│    class GBM_model_python_xxx {                            │
│        double[] score0(double[] data) {                    │
│            // 5000 decision trees inlined                  │
│            // 200,000+ lines of Java                       │
│            // Method exceeds 64KB → COMPILE ERROR          │
│        }                                                    │
│    }                                                        │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**Result:** Large models simply cannot be exported as POJO.

### Compilation Overhead

Even for models that fit within limits:

```
┌────────────────────────────────────────────────────────────┐
│                    POJO Loading                             │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Read .java file → parse source                         │
│  2. Invoke Java compiler (javac) → compile to bytecode     │
│  3. Load .class into JVM → class verification              │
│  4. JIT compile → optimize hot paths                       │
│  5. Ready to predict                                        │
│                                                             │
│  Time: 10-60 seconds for medium models                     │
│  Memory: 2-4GB during compilation                          │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Version Mismatch Risk

```python
# Training environment
h2o.download_pojo(model, "model.java")  # Generated for h2o==3.44.0

# Production environment
# JDK version different
# h2o-genmodel.jar version different
# → Runtime errors, incorrect predictions, crashes
```

---

## Detection Patterns

### Code Review Checks

```python
# ❌ WRONG: POJO export
model.download_pojo(path='./model.java')

# ❌ WRONG: Binary H2O save (not portable)
h2o.save_model(model, path='./model')

# ❌ WRONG: Pickle (security risk, not optimized)
import pickle
pickle.dump(model, open('model.pkl', 'wb'))

# ✅ CORRECT: MOJO export
model.download_mojo(path='./models/')
model.download_mojo(path='./models/', get_genmodel_jar=True)
```

### File Extension Validation

```python
def validate_artifact(path: str) -> bool:
    """Verify artifact is valid MOJO."""
    if not path.endswith('.zip'):
        raise ValueError(f"Expected .zip, got {path}")
    
    # Check MOJO signature
    import zipfile
    with zipfile.ZipFile(path) as zf:
        if 'model.ini' not in zf.namelist():
            raise ValueError("Invalid MOJO: missing model.ini")
    
    return True
```

### Pipeline Scanner

```python
# Scan Mage pipeline for artifact export
import ast

class MojoChecker(ast.NodeVisitor):
    def __init__(self):
        self.violations = []
        self.valid_exports = []
    
    def visit_Call(self, node):
        call_str = ast.unparse(node)
        
        if 'download_pojo' in call_str:
            self.violations.append({
                'type': 'POJO_EXPORT',
                'line': node.lineno,
                'message': 'Use download_mojo() instead of download_pojo()'
            })
        
        if 'download_mojo' in call_str:
            self.valid_exports.append(node.lineno)
        
        if 'pickle.dump' in call_str:
            self.violations.append({
                'type': 'PICKLE_EXPORT',
                'line': node.lineno,
                'message': 'Pickle is forbidden for model serialization'
            })
        
        self.generic_visit(node)
```

---

## Version Compatibility Matrix

### Training → Inference Alignment

| Training H2O Version | MOJO Runtime | daimojo Version |
|---------------------|--------------|-----------------|
| 3.44.0.x | h2o-genmodel 3.44.0.x | daimojo 2.1+ |
| 3.42.0.x | h2o-genmodel 3.42.0.x | daimojo 2.0+ |
| 3.40.0.x | h2o-genmodel 3.40.0.x | daimojo 1.10+ |

### Verification Script

```python
def verify_version_alignment():
    """Ensure H2O versions are aligned."""
    import h2o
    import daimojo
    
    # Get training version from MOJO
    mojo_version = extract_mojo_version('model.zip')
    
    # Get runtime versions
    h2o_version = h2o.__version__
    daimojo_version = daimojo.__version__
    
    # Major.Minor must match
    mojo_major_minor = '.'.join(mojo_version.split('.')[:2])
    
    if not daimojo_version_supports(mojo_major_minor):
        raise ValueError(
            f"daimojo {daimojo_version} does not support "
            f"MOJO from H2O {mojo_version}"
        )
```

---

## Best Practices

### 1. Always Export MOJO

```python
# In Mage Exporter block
@exporter
def export_model(model, *args, **kwargs):
    """Export model as MOJO only."""
    artifact_path = model.download_mojo(
        path='./artifacts/',
        get_genmodel_jar=True  # Include for validation
    )
    
    # Validate immediately
    assert artifact_path.endswith('.zip')
    
    # Log version for traceability
    import h2o
    logger.info(f"Exported MOJO with H2O {h2o.__version__}")
    
    return artifact_path
```

### 2. Pin Versions Strictly

```
# requirements.txt
h2o==3.44.0.3
daimojo==2.1.0
```

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Pin H2O version
RUN pip install h2o==3.44.0.3

# Pin daimojo version  
RUN pip install daimojo==2.1.0
```

### 3. Validate on Load

```python
def load_mojo_safely(path: str):
    """Load MOJO with validation."""
    import daimojo
    
    # Pre-load validation
    validate_artifact(path)
    
    # Load model
    model = daimojo.load(path)
    
    # Test prediction (smoke test)
    test_input = create_test_input(model)
    try:
        model.predict(test_input)
    except Exception as e:
        raise RuntimeError(f"MOJO smoke test failed: {e}")
    
    return model
```

---

## References

- [H2O MOJO Documentation](https://docs.h2o.ai/h2o/latest-stable/h2o-docs/productionizing.html)
- [daimojo Python Package](https://pypi.org/project/daimojo/)
- [64KB Method Limit](https://docs.oracle.com/javase/specs/jvms/se8/html/jvms-4.html#jvms-4.7.3)
