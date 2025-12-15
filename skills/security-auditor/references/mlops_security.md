# MLOps Security Reference

## ML-Specific Threat Landscape

```
┌─────────────────────────────────────────────────────────────┐
│                   ML Pipeline Threats                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Training   │  │   Artifact  │  │  Inference  │         │
│  │   Phase     │──▶│   Storage   │──▶│   Phase     │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│  Threats:         Threats:         Threats:                  │
│  • Data poison    • Tampering      • Model inversion        │
│  • Backdoor       • Theft          • Adversarial inputs     │
│  • Label flip     • Unauthorized   • Sponge attacks         │
│                     access                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Model Artifact Security

### The MOJO Security Advantage

| Format | Execution | Arbitrary Code Risk | JVM Required |
|--------|-----------|---------------------|--------------|
| **Pickle** | Python eval | 🔴 Critical | No |
| **POJO** | Java class | 🟠 Medium (deser) | Yes |
| **MOJO** | Binary blob | 🟢 Low | No |
| **ONNX** | Runtime | 🟢 Low | No |

### Why MOJO is Safer

```
THESIS:     POJOs are simple Java classes
ANTITHESIS: Java deserialization vulnerabilities (e.g., Log4Shell)
SYNTHESIS:  MOJO binary format with C++ runtime (no JVM)
```

### Model Signing Implementation

```python
import hashlib
import hmac
from pathlib import Path

class ModelSigner:
    """Sign and verify ML model artifacts."""
    
    def __init__(self, secret_key: bytes):
        self.secret_key = secret_key
    
    def sign(self, model_path: Path) -> str:
        """Generate HMAC signature for model file."""
        h = hmac.new(self.secret_key, digestmod=hashlib.sha256)
        
        with open(model_path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        
        return h.hexdigest()
    
    def verify(self, model_path: Path, expected_signature: str) -> bool:
        """Verify model signature matches expected."""
        actual = self.sign(model_path)
        return hmac.compare_digest(actual, expected_signature)

# Usage in training pipeline (Mage)
signer = ModelSigner(secret_key=os.environ["MODEL_SIGNING_KEY"])
signature = signer.sign(Path("/models/model.mojo.zip"))

# Store signature in metadata
await db.execute(
    "INSERT INTO model_versions (path, signature, created_at) VALUES ($1, $2, NOW())",
    [model_path, signature]
)

# Usage in inference (FastAPI)
def load_model(model_path: Path) -> Model:
    """Load model only if signature is valid."""
    expected = get_signature_from_db(model_path)
    
    if not signer.verify(model_path, expected):
        raise SecurityError("Model signature mismatch - possible tampering")
    
    return daimojo.load(str(model_path))
```

---

## Pickle Elimination Strategy

### Why Pickle is Dangerous

```python
# Malicious pickle payload
import pickle
import os

class MaliciousPayload:
    def __reduce__(self):
        return (os.system, ("rm -rf /",))

# Loading this executes the command
pickle.loads(pickle.dumps(MaliciousPayload()))
```

### Detection and Prevention

```python
# scripts/check_pickle_usage.py
import ast
import sys
from pathlib import Path

DANGEROUS_IMPORTS = {
    "pickle",
    "cPickle", 
    "dill",
    "joblib",  # Uses pickle internally
}

DANGEROUS_CALLS = {
    "pickle.load",
    "pickle.loads",
    "joblib.load",
    "torch.load",  # Uses pickle by default
}

def scan_file(path: Path) -> list[str]:
    """Scan Python file for pickle usage."""
    issues = []
    
    with open(path) as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in DANGEROUS_IMPORTS:
                    issues.append(f"{path}:{node.lineno}: imports {alias.name}")
        
        elif isinstance(node, ast.ImportFrom):
            if node.module in DANGEROUS_IMPORTS:
                issues.append(f"{path}:{node.lineno}: imports from {node.module}")
    
    return issues

# Scan codebase
for path in Path(".").rglob("*.py"):
    for issue in scan_file(path):
        print(issue)
        sys.exit(1)
```

### Safe Alternatives

| Use Case | Dangerous | Safe Alternative |
|----------|-----------|------------------|
| ML Models | pickle, joblib | MOJO, ONNX, SavedModel |
| Data | pickle | JSON, Parquet, Arrow |
| Caching | pickle | JSON, msgpack |
| Sessions | pickle | JSON + Redis |

---

## Adversarial Input Protection

### Statistical Input Guardrails

```python
from pydantic import BaseModel, validator, constr, confloat
from typing import Optional

class FeatureVector(BaseModel):
    """Validated feature vector with statistical bounds."""
    
    # Numeric constraints based on training data statistics
    age: confloat(ge=0, le=120)
    income: confloat(ge=0, le=10_000_000)
    credit_score: confloat(ge=300, le=850)
    
    # String constraints
    category: constr(max_length=50, regex=r'^[a-zA-Z0-9_]+$')
    
    # JSON depth protection
    metadata: Optional[dict] = None
    
    @validator('metadata')
    def validate_metadata_depth(cls, v, values):
        if v is None:
            return v
        
        def check_depth(obj, depth=0, max_depth=5):
            if depth > max_depth:
                raise ValueError(f"JSON depth exceeds {max_depth}")
            if isinstance(obj, dict):
                for value in obj.values():
                    check_depth(value, depth + 1, max_depth)
            elif isinstance(obj, list):
                for item in obj:
                    check_depth(item, depth + 1, max_depth)
        
        check_depth(v)
        return v
    
    @validator('*', pre=True)
    def reject_nan_inf(cls, v):
        """Reject NaN and Inf values that could cause model issues."""
        if isinstance(v, float):
            import math
            if math.isnan(v) or math.isinf(v):
                raise ValueError("NaN and Inf values not allowed")
        return v
```

### Rate Limiting by Anomaly Score

```python
async def anomaly_aware_rate_limit(
    request: Request,
    redis: Redis
):
    """Apply stricter limits to anomalous requests."""
    features = await request.json()
    
    # Calculate anomaly score (simplified)
    anomaly_score = calculate_anomaly_score(features)
    
    if anomaly_score > 0.9:
        # Highly anomalous: very strict limit
        limit = 5
        window = 60
    elif anomaly_score > 0.7:
        # Somewhat anomalous: stricter limit
        limit = 20
        window = 60
    else:
        # Normal: standard limit
        limit = 100
        window = 60
    
    # Apply rate limit
    key = f"ratelimit:{get_client_id(request)}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, window)
    
    if count > limit:
        raise HTTPException(429, "Rate limit exceeded")
```

---

## Model Theft Prevention

### Inference API Hardening

```python
from fastapi import Request, Response

@app.middleware("http")
async def anti_extraction_middleware(request: Request, call_next):
    """Detect and mitigate model extraction attempts."""
    
    # Track request patterns per user
    user_id = get_user_id(request)
    
    # Check for high-frequency systematic queries
    pattern_score = await detect_extraction_pattern(user_id)
    
    if pattern_score > 0.8:
        # Potential extraction attack
        # Option 1: Add noise to predictions
        # Option 2: Return cached/rounded results
        # Option 3: Block and alert
        raise HTTPException(403, "Unusual query pattern detected")
    
    response = await call_next(request)
    return response

async def detect_extraction_pattern(user_id: str) -> float:
    """Detect model extraction via query patterns."""
    recent_queries = await get_recent_queries(user_id, window=3600)
    
    # Indicators of extraction:
    # 1. Systematic feature space coverage
    # 2. Boundary probing (values near decision boundaries)
    # 3. High query rate with varied inputs
    
    coverage_score = calculate_feature_coverage(recent_queries)
    boundary_score = calculate_boundary_probing(recent_queries)
    rate_score = len(recent_queries) / 1000  # Normalize
    
    return (coverage_score + boundary_score + rate_score) / 3
```

### Prediction Perturbation

```python
import numpy as np

def add_differential_privacy_noise(prediction: float, epsilon: float = 0.1) -> float:
    """Add Laplacian noise for differential privacy."""
    sensitivity = 1.0  # Max change in output
    scale = sensitivity / epsilon
    noise = np.random.laplace(0, scale)
    return prediction + noise

# Apply to high-sensitivity outputs
@app.post("/predict")
async def predict(request: PredictionRequest):
    raw_prediction = model.predict(request.features)
    
    # Add noise for external consumers
    if request.user.tier != "enterprise":
        raw_prediction = add_differential_privacy_noise(raw_prediction)
    
    return {"prediction": raw_prediction}
```

---

## Quick Reference

### ML Security Checklist

- [ ] No pickle/joblib usage in codebase
- [ ] Model artifacts are cryptographically signed
- [ ] Signature verification before model loading
- [ ] Input validation with statistical bounds
- [ ] JSON depth limits enforced
- [ ] NaN/Inf values rejected
- [ ] Rate limiting on inference endpoint
- [ ] Anomaly detection on query patterns
- [ ] Audit logging for all predictions
- [ ] Model versioning with rollback capability
