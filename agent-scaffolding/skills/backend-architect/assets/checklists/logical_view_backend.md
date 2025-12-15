# Logical View Backend Checklist

## Feature Store Schema

- [ ] Relational columns for `entity_id`, `event_timestamp`
- [ ] JSONB column for `dynamic_features`
- [ ] GIN index with `jsonb_path_ops` operator class
- [ ] Containment queries (@>) use index scan
- [ ] Index size <20% of table size

## Pydantic Validation

- [ ] Shared models in `/src/shared/models.py`
- [ ] Pydantic v2 with strict mode
- [ ] Used by both Mage and FastAPI
- [ ] Schema drift detection in CI

## Model Registry

- [ ] `ModelRegistry` table created
- [ ] MOJO S3 URI tracked
- [ ] `git_commit_sha` linked
- [ ] `h2o_version` recorded
- [ ] Records are immutable

## Acceptance Criteria

| Story ID | Criteria | Status |
|----------|----------|--------|
| BA-LOG-01 | GIN index works | ☐ |
| BA-LOG-02 | Validation shared | ☐ |
| BA-LOG-03 | Model traceable | ☐ |
