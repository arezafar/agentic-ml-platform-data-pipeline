# H2O MOJO Compatibility Guide

## Overview

H2O MOJO (Model Object, Optimized) artifacts provide a portable format for deploying H2O models outside of the H2O cluster. This document covers version compatibility between training and inference environments.

---

## Version Matrix

### H2O Cluster → MOJO → daimojo Compatibility

| H2O Cluster Version | MOJO Format | daimojo Version | Status |
|---------------------|-------------|-----------------|--------|
| 3.44.x | 2.x | 2.5.x+ | ✅ Recommended |
| 3.42.x | 2.x | 2.4.x+ | ✅ Supported |
| 3.40.x | 2.x | 2.3.x+ | ✅ Supported |
| 3.38.x | 2.x | 2.2.x+ | ⚠️ Legacy |
| 3.36.x | 2.x | 2.1.x+ | ⚠️ Legacy |
| 3.34.x and older | 1.x | N/A | ❌ Not Supported |

### Recommended Configuration

```yaml
# Pinned versions for reproducibility
h2o_cluster: "3.44.0.3"
daimojo: "2.5.0"
mojo_runtime: "2.5.0"
```

---

## MOJO vs Binary Model

| Aspect | MOJO (.zip/.mojo) | Binary (.bin) |
|--------|-------------------|---------------|
| Portability | ✅ JVM-independent | ❌ Requires H2O cluster |
| File Size | Larger | Smaller |
| Loading Speed | Fast | Fast |
| Version Compat | Better | Strict |
| Scoring Runtime | daimojo (C++) or genmodel (Java) | H2O cluster only |

**Recommendation**: Always use MOJO for production inference.

---

## daimojo Installation

### Standard Installation

```bash
pip install daimojo
```

### Version Pinning

```bash
pip install daimojo==2.5.0
```

### Platform-Specific Notes

**Linux (recommended)**:
```bash
pip install daimojo
```

**macOS**:
```bash
# May require additional C++ runtime
pip install daimojo
```

**Windows**:
```bash
# Requires Visual C++ Redistributable
pip install daimojo
```

---

## Common Compatibility Issues

### Issue 1: Version Mismatch

**Symptoms**:
- `RuntimeError: Unsupported MOJO version`
- Segmentation fault on model load
- Garbled predictions

**Solution**:
```python
def check_mojo_compatibility(mojo_path: str, daimojo_version: str):
    """Verify MOJO is compatible with daimojo version."""
    import zipfile
    import json
    
    with zipfile.ZipFile(mojo_path, 'r') as zf:
        with zf.open('experimental/modelDetails.json') as f:
            details = json.load(f)
    
    h2o_version = details.get('h2o_version', 'unknown')
    
    # Extract major.minor from versions
    h2o_parts = h2o_version.split('.')[:2]
    daimojo_parts = daimojo_version.split('.')[:2]
    
    if h2o_parts[0] != '3' or int(h2o_parts[1]) < 40:
        raise ValueError(f"H2O version {h2o_version} may not be compatible")
    
    return True
```

### Issue 2: Missing Dependencies

**Symptoms**:
- `ImportError: libmojo.so: cannot open shared object file`
- `OSError: [WinError 126] The specified module could not be found`

**Solution**:
```bash
# Linux
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(python -c "import daimojo; print(daimojo.__path__[0])")

# macOS
export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$(python -c "import daimojo; print(daimojo.__path__[0])")
```

### Issue 3: Floating-Point Precision

**Symptoms**:
- Predictions differ slightly between Java and C++
- `assert abs(java_pred - cpp_pred) < 1e-6` fails

**Background**:
Java and C++ may use different floating-point implementations. Differences of 1e-10 to 1e-6 are normal.

**Solution**:
```python
TOLERANCE = 1e-6

def predictions_match(java_preds: list, cpp_preds: list) -> bool:
    for j, c in zip(java_preds, cpp_preds):
        if abs(j - c) > TOLERANCE:
            return False
    return True
```

---

## MOJO Artifact Structure

```
model.mojo (or model.zip)
├── model.ini                 # Model configuration
├── domains/                  # Categorical domain mappings
│   ├── d000.txt
│   └── d001.txt
├── trees/                    # For tree-based models
│   └── tree_data.bin
└── experimental/
    └── modelDetails.json     # Model metadata (version, params)
```

### Required Files

| File | Purpose |
|------|---------|
| `model.ini` | Core configuration (algorithm, features) |
| `domains/*` | Categorical feature encoding |

### Optional Files

| File | Purpose |
|------|---------|
| `experimental/modelDetails.json` | Extended metadata, lineage |
| `experimental/variableImportances.json` | Feature importance |

---

## Validation Checklist

### Pre-Deployment

```python
def validate_mojo_for_deployment(mojo_path: str) -> bool:
    checks = []
    
    # 1. File exists and is readable
    checks.append(os.path.exists(mojo_path))
    
    # 2. Is valid zip
    checks.append(zipfile.is_zipfile(mojo_path))
    
    # 3. Contains model.ini
    with zipfile.ZipFile(mojo_path, 'r') as zf:
        files = zf.namelist()
        checks.append(any('model.ini' in f for f in files))
    
    # 4. Can be loaded by daimojo
    try:
        from daimojo import MojoModel
        model = MojoModel(mojo_path)
        checks.append(model is not None)
    except Exception:
        checks.append(False)
    
    return all(checks)
```

### Prediction Parity Test

```python
def test_prediction_parity(mojo_path: str, reference_csv: str):
    """Compare MOJO predictions against reference from H2O cluster."""
    import pandas as pd
    from daimojo import MojoModel
    
    model = MojoModel(mojo_path)
    reference = pd.read_csv(reference_csv)
    
    features = reference.drop('expected_prediction', axis=1)
    expected = reference['expected_prediction'].values
    
    actual = model.predict(features)
    
    for i, (exp, act) in enumerate(zip(expected, actual)):
        assert abs(exp - act) < 1e-6, f"Row {i}: expected {exp}, got {act}"
```

---

## Task Reference

| Task ID | Description |
|---------|-------------|
| IT-ML-01 | Cross-Version MOJO Loading Verification |
| IT-ML-02 | Numerical Precision and Prediction Parity |
| IT-ML-03 | Missing Value Handling Integration |
| IT-ML-04 | Artifact Metadata Validation |
