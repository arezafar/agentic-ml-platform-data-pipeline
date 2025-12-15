# Development View Backend Checklist

## Monorepo Structure

- [ ] Shared models in `/src/shared`
- [ ] Models consumed by both Mage and FastAPI
- [ ] No circular imports

## GraphQL Schema

- [ ] Custom JSON Scalar for `dynamic_features`
- [ ] DataLoaders for all relation resolvers
- [ ] Query depth limit (max_depth=5)
- [ ] No N+1 query patterns
- [ ] Query complexity analysis active

## Version Pinning

- [ ] Single `versions.env` file exists
- [ ] H2O_VERSION defined
- [ ] DAIMOJO_VERSION defined
- [ ] GENMODEL_VERSION defined
- [ ] Both Dockerfiles source this file

## Build Artifacts

- [ ] Docker builds use ARG/ENV from versions.env
- [ ] pip install uses exact versions
- [ ] JAR downloaded with exact version
- [ ] Build fails on version mismatch
- [ ] Artifact hashes logged

## Acceptance Criteria

| Story ID | Criteria | Status |
|----------|----------|--------|
| BA-DEV-02 | DataLoader used | ☐ |
| BA-DEV-03 | Depth limited | ☐ |
| BA-PHY-04 | Single version file | ☐ |
