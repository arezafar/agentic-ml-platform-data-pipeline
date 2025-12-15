# Development View Orchestrator Checklist

## ML Artifact Integrity

### Pre-Review
- [ ] Identify model export blocks in Mage
- [ ] Check H2O version in requirements
- [ ] Verify deployment target runtime

### MOJO Mandate
- [ ] Pipeline calls `model.download_mojo()` (not `download_pojo()`)
- [ ] Output file extension is `.zip`
- [ ] `get_genmodel_jar=True` configured if needed
- [ ] No `.java` files in model output directory

### Version Pinning
- [ ] `requirements.txt` pins exact `h2o==x.y.z`
- [ ] Dockerfile downloads matching `h2o.jar`
- [ ] Version in daimojo runtime support matrix
- [ ] Train and inference environments match

### Monorepo Structure
- [ ] Clear separation: `src/pipeline` and `src/service`
- [ ] No direct imports from pipeline in service
- [ ] Shared code in `lib/shared` with versioning
- [ ] `mypy --strict` passes on core logic

## Acceptance Criteria Summary

| Story ID | Criteria | Status |
|----------|----------|--------|
| LEAD-DEV-01-01 | MOJO .zip output | ☐ |
| LEAD-DEV-01-02 | Pinned h2o version | ☐ |
| LEAD-DEV-01-03 | No cross-imports | ☐ |
