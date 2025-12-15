# Scenario View Review Checklist

Code review checklist for **Scenario View** alignment—end-to-end integration verification across the entire system.

---

## Epic: REV-SCN-01 (Integration Verification)

### ✅ Drift Detection Test Verification (SCN-REV-01-01)

**Integration Test Requirements:**
- [ ] Test simulates data drift (new feature distributions)
- [ ] Test verifies Mage retraining pipeline trigger
- [ ] Test confirms new MOJO artifact is exported
- [ ] Test validates new model is loaded by inference service

**Test Scenario Flow:**
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. Inject│───▶│ 2. Detect│───▶│ 3. Mage  │───▶│ 4. Verify│
│   Drift  │    │   Drift  │    │ Retrain  │    │ New MOJO │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

**Required Test Coverage:**
```python
# ✅ REQUIRED: Drift simulation test
def test_drift_triggers_retraining():
    """
    Test that data drift is detected and triggers retraining.
    """
    # 1. Insert drifted data into Feature Store
    inject_drifted_features(distribution_shift=0.3)
    
    # 2. Verify drift detection service detects change
    drift_result = await drift_detector.check()
    assert drift_result.is_drifted == True
    
    # 3. Verify Mage pipeline is triggered
    pipeline_run = await mage.trigger_pipeline('retrain')
    assert pipeline_run.status == 'completed'
    
    # 4. Verify new MOJO artifact exists
    new_mojo = list_artifacts(pattern='*.zip')
    assert len(new_mojo) > previous_count
```

**Anti-Patterns:**
```python
# ❌ WRONG: No drift simulation in tests
def test_model_training():
    # Only tests happy path, no drift handling
    model = train_model(static_data)
    assert model is not None

# ❌ WRONG: Manual trigger without automation
# Relies on manual intervention to retrain
```

---

### ✅ Zero-Downtime Swap Verification (SCN-REV-01-02)

**Load Test Requirements:**
- [ ] Load test runs DURING model swap operation
- [ ] No 500 errors during swap window
- [ ] p99 latency remains within SLO during swap
- [ ] Both old and new model versions serve requests during transition

**Test Scenario:**
```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 1. Start │───▶│ 2. Begin │───▶│ 3. Swap  │───▶│ 4. Verify│
│ Load Test│    │ Model v2 │    │ Completes│    │ No Errors│
│          │    │  Deploy  │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

**Required Test Coverage:**
```python
# ✅ REQUIRED: Zero-downtime swap test
async def test_zero_downtime_model_swap():
    """
    Verify model can be swapped without request failures.
    """
    # 1. Start continuous load
    load_task = asyncio.create_task(
        locust.spawn_users(100, duration=120)
    )
    
    # 2. Wait for steady state
    await asyncio.sleep(30)
    initial_error_count = get_error_count()
    
    # 3. Trigger model swap
    await model_manager.swap_model('model_v2.zip')
    
    # 4. Continue load during swap
    await asyncio.sleep(60)
    
    # 5. Verify no new errors during swap
    final_error_count = get_error_count()
    assert final_error_count == initial_error_count, \
        f"Errors during swap: {final_error_count - initial_error_count}"
    
    # 6. Verify p99 latency within SLO
    stats = await locust.get_stats()
    assert stats['p99'] < 50, f"p99 exceeded SLO: {stats['p99']}ms"
```

**Hot-Swap Implementation Check:**
```python
# ✅ CORRECT: Atomic model swap
class ModelManager:
    def __init__(self):
        self._model = load_mojo('model_v1.zip')
        self._lock = asyncio.Lock()
    
    async def swap_model(self, new_path: str):
        """Atomically swap model without blocking."""
        # Load new model before acquiring lock
        new_model = await run_in_executor(None, load_mojo, new_path)
        
        # Atomic swap
        async with self._lock:
            old_model = self._model
            self._model = new_model
        
        # Cleanup old model after swap
        await run_in_executor(None, old_model.close)
    
    async def predict(self, data):
        """Predictions use current model atomically."""
        model = self._model  # Atomic read
        return await run_in_executor(None, model.predict, data)
```

**Anti-Patterns:**
```python
# ❌ WRONG: Non-atomic swap
def swap_model(self, new_path):
    self._model.close()  # Gap where no model exists!
    self._model = load_mojo(new_path)

# ❌ WRONG: Blocking during swap
async def swap_model(self, new_path):
    async with self._lock:
        # Loading inside lock blocks all predictions!
        self._model = await run_in_executor(None, load_mojo, new_path)
```

---

## Integration Test Checklist

### PR Requirements:
- [ ] Integration test for drift detection exists
- [ ] Integration test for zero-downtime swap exists
- [ ] Tests run in CI/CD pipeline
- [ ] Tests use realistic load patterns
- [ ] Tests verify both success and failure paths

### Test Infrastructure:
- [ ] Staging environment mirrors production
- [ ] Locust or equivalent load testing tool configured
- [ ] Test fixtures for drifted data available
- [ ] Model artifacts for swap testing available

---

## Review Decision Matrix

| Finding | Severity | Action |
|---------|----------|--------|
| No drift detection test | 🔴 HIGH | Block PR |
| No zero-downtime swap test | 🔴 HIGH | Block PR |
| Non-atomic model swap implementation | 🔴 CRITICAL | Block PR |
| Load test without model swap | 🟠 MEDIUM | Request change |
| Missing SLO assertions in tests | 🟠 MEDIUM | Request change |
| Tests not in CI pipeline | 🟡 LOW | Suggest improvement |

---

## Related Task IDs
- `SCN-REV-01-01`: Drift Detection Test Verification
- `SCN-REV-01-02`: Zero-Downtime Swap Verification
