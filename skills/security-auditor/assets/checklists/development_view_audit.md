# Development View Security Audit Checklist

## Supply Chain Security

- [ ] **Multi-Stage Builds**: Are Dockerfiles using multi-stage builds with slim runtime images?
  - Required: `python:3.11-slim` or `distroless` as final stage
  - Verification: Inspect image layers; target <500MB
  - Risk: Expanded attack surface with build tools

- [ ] **Build Tools Removed**: Are build tools (gcc, g++, curl, git, pip) absent from production images?
  - Verification: `docker run --rm image which gcc` returns not found
  - Risk: Living off the Land (LotL) attacks

- [ ] **JDK Separation**: Does the FastAPI inference container exclude JDK/JRE?
  - Verification: `docker run --rm inference java -version` returns not found
  - Required: Use C++ MOJO runtime (libdaimojo.so) only
  - Risk: Java serialization vulnerabilities

---

## Dependency Management

- [ ] **Version Pinning**: Are all Python dependencies pinned to specific versions?
  - Required: `package==1.2.3` not `package>=1.2.0`
  - Verification: Check `requirements.txt` format
  - Risk: Supply chain attacks via version mutation

- [ ] **Lock Files**: Is a lock file (pip-tools, poetry.lock) committed?
  - Verification: Check for `requirements.lock` or `poetry.lock`
  - Risk: Inconsistent builds across environments

- [ ] **CVE Scanning**: Is automated vulnerability scanning integrated into CI/CD?
  - Tools: trivy, grype, safety
  - Verification: Intentionally downgrade library; expect build failure
  - Threshold: Block on Critical/High CVEs

- [ ] **SBOM Generation**: Is a Software Bill of Materials generated with each build?
  - Format: CycloneDX or SPDX
  - Verification: Check artifact repository for SBOM
  - Risk: Slow zero-day response without inventory

---

## Secure Coding Practices

- [ ] **SQL Bind Parameters**: Are all SQL queries using bind parameters, not string formatting?
  - Banned: f-strings, `.format()`, `%` for query construction
  - Verification: Run `bandit -r` with SQL injection rules
  - Risk: SQL injection via dynamic queries

- [ ] **JSON Key Safety**: Are JSONB keys handled safely in dynamic queries?
  - Verification: Review asyncpg queries for dynamic key access
  - Risk: SQL injection via JSON keys

- [ ] **Shell Injection Prevention**: Is `shlex.quote()` used for shell command arguments?
  - Verification: Static analysis for `subprocess`, `os.system` calls
  - Risk: Command injection in Mage blocks

- [ ] **URL Validation**: Are scraped URLs validated against an allow-list?
  - Verification: Attempt to scrape internal IPs; expect rejection
  - Risk: SSRF attacks via data loaders

- [ ] **Pickle Elimination**: Is `pickle`, `joblib.load`, or `dill` usage prohibited?
  - Required: Use `h2o.save_mojo` exclusively
  - Verification: `grep -r "import pickle"` returns empty
  - Risk: Arbitrary code execution via deserialization

---

## Code Quality

- [ ] **Static Analysis**: Is Bandit or Semgrep integrated into CI?
  - Verification: Check CI configuration for SAST step
  - Risk: Latent vulnerabilities in codebase

- [ ] **Dependency Confusion**: Are private packages using unique names or private registries?
  - Verification: Check for internal package naming collisions
  - Risk: Typosquatting attacks

---

## Task Coverage

| Task ID | Description | Status |
|---------|-------------|--------|
| CONT-01 | Multi-Stage Build Enforcement | [ ] |
| CONT-02 | Automated Dependency Scanning | [ ] |
| CONT-04 | H2O JVM/C++ Separation | [ ] |
| API-03 | SQL/JSON Injection Audit | [ ] |
| MLSEC-02 | Pickle Elimination Verification | [ ] |
