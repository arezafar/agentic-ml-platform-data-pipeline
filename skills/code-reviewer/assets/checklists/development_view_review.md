# Development View Review Checklist

Code review checklist for **Development View** alignment—ML artifacts, version pinning, and code organization.

---

## Epic: REV-DEV-01 (ML Artifact Integrity)

### ✅ MOJO Mandate Enforcement (DEV-REV-01-01)

**Pipeline Export Checks:**
- [ ] Model exported using `model.download_mojo()` NOT `download_pojo()`
- [ ] Output artifact has `.zip` extension
- [ ] Export includes `get_genmodel_jar=True` if needed for validation
- [ ] No `model.save()` or `pickle.dump()` for model serialization

**Why MOJO Not POJO:**
| Aspect | MOJO (.zip) | POJO (.java) |
|--------|-------------|--------------|
| Compilation | None required | JVM compilation at load |
| Size Limit | Unlimited | 64KB method limit |
| Runtime | C++ (daimojo) | JVM required |
| Latency | Lower | Higher (compilation) |

**Anti-Patterns:**
```python
# ❌ WRONG: POJO export
model.download_pojo('model.java')

# ❌ WRONG: Pickle serialization
import pickle
pickle.dump(model, open('model.pkl', 'wb'))

# ❌ WRONG: H2O binary save
h2o.save_model(model, 'model')  # Not portable
```

**Correct Patterns:**
```python
# ✅ CORRECT: MOJO export
mojo_path = model.download_mojo(path='./models/', get_genmodel_jar=True)

# ✅ CORRECT: Verify extension
assert mojo_path.endswith('.zip'), "MOJO must be .zip"

# ✅ CORRECT: In Mage Exporter block
@exporter
def export_model(model, *args, **kwargs):
    model.download_mojo(path='./artifacts/')
```

---

### ✅ H2O Version Pinning (DEV-REV-01-02)

**Version Consistency Checks:**
- [ ] `requirements.txt` or `pyproject.toml` pins exact H2O version
- [ ] Dockerfile downloads matching `h2o.jar` version
- [ ] Training environment matches inference environment
- [ ] `daimojo` runtime version compatible with MOJO

**Version Alignment Matrix:**
```
Training (Mage)     ←→  h2o==3.44.0.3
H2O Cluster         ←→  h2o.jar 3.44.0.3  
Inference (FastAPI) ←→  daimojo-2.1.0
```

**Anti-Patterns:**
```python
# ❌ WRONG: Unpinned version
# requirements.txt
h2o>=3.40

# ❌ WRONG: Version mismatch
# Training uses h2o==3.44.0.3
# Inference uses daimojo for h2o==3.42.0.1
```

**Correct Patterns:**
```python
# ✅ CORRECT: Pinned versions
# requirements.txt
h2o==3.44.0.3

# Dockerfile
RUN wget https://h2o-release.s3.amazonaws.com/h2o/rel-3.44.0/3/h2o-3.44.0.3.zip

# Inference requirements
daimojo==2.1.0  # Compatible with 3.44.x
```

---

### ✅ Monorepo Structure Check (DEV-REV-01-03)

**Directory Organization:**
- [ ] Pipeline code in `src/pipeline/` (Mage blocks, training)
- [ ] Service code in `src/service/` (FastAPI, inference)
- [ ] Shared utilities in `src/common/` or `src/lib/`
- [ ] No direct imports from `pipeline` in `service`

**Expected Structure:**
```
src/
├── pipeline/           # Mage ETL & Training
│   ├── blocks/
│   ├── pipelines/
│   └── models/
├── service/            # FastAPI Inference
│   ├── api/
│   ├── inference/
│   └── main.py
└── common/             # Shared code only
    ├── schemas.py
    └── config.py
```

**Anti-Patterns:**
```python
# ❌ WRONG: Service importing from pipeline
# In src/service/inference/predictor.py
from src.pipeline.blocks.train import TrainingBlock  # Coupling!

# ❌ WRONG: Mixed concerns
# src/api/train_and_serve.py  # Training in service layer
```

**Correct Patterns:**
```python
# ✅ CORRECT: Shared schemas
# In src/service/inference/predictor.py
from src.common.schemas import PredictionRequest

# ✅ CORRECT: Artifact-based communication
# Service loads MOJO from shared artifact storage
mojo = daimojo.load('./artifacts/model.zip')
```

---

## Review Decision Matrix

| Finding | Severity | Action |
|---------|----------|--------|
| `download_pojo()` usage | 🔴 CRITICAL | Block PR |
| `pickle` for model serialization | 🔴 CRITICAL | Block PR |
| Unpinned H2O version | 🔴 HIGH | Block PR |
| Version mismatch train/infer | 🔴 HIGH | Block PR |
| Direct pipeline→service import | 🟠 MEDIUM | Request change |
| Mixed concerns in directory | 🟡 LOW | Suggest improvement |

---

## Related Task IDs
- `DEV-REV-01-01`: MOJO Mandate Enforcement
- `DEV-REV-01-02`: H2O Version Pinning
- `DEV-REV-01-03`: Monorepo Structure Check
