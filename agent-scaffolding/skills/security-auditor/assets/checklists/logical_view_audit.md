# Logical View Security Audit Checklist

## Schema Security

- [ ] **JSONB Validation**: Are JSONB columns in PostgreSQL validated by Pydantic schemas in the application layer?
  - Verification: Review `FeatureVector` model for field constraints
  - Risk: JSON injection, data malformation

- [ ] **Max Depth Validation**: Does the Pydantic schema enforce maximum JSON nesting depth?
  - Verification: Send 100-level nested JSON; expect 422
  - Risk: JSON Bomb attacks exhausting memory

- [ ] **String Length Limits**: Are `constr(max_length=...)` constraints applied to string fields?
  - Verification: Send 10MB string payload; expect 422
  - Risk: DoS via oversized payloads

- [ ] **Character Set Validation**: Are allowed character sets defined for sensitive fields?
  - Verification: Send payloads with special characters; verify handling
  - Risk: Encoding-based injection attacks

---

## Authentication Model

- [ ] **Scope Separation**: Is there clear separation between training and inference scopes?
  - Required Scopes:
    - `mage:pipeline:read` / `mage:pipeline:execute` (Data Scientists)
    - `h2o:model:train` (ML Engineers)
    - `api:predict` (API Consumers)
  - Verification: Token with insufficient scope returns 403

- [ ] **Token Validation**: Does the application validate JWT signature, issuer, and audience?
  - Verification: Send modified JWT; expect 401
  - Risk: Token forgery, impersonation

- [ ] **OIDC Discovery**: Is token validation using the OIDC discovery document (JWKS)?
  - Verification: Rotate keys in IdP; verify new tokens work
  - Risk: Key rotation failures

---

## Data Flow Security

- [ ] **PII Identification**: Are PII fields identified in the system?
  - Fields to check: email, phone, SSN, name, address

- [ ] **Sanitization Blocks**: Do transformer blocks mask PII before persistence?
  - Verification: Run test pipeline with dummy PII; check DB for plaintext
  - Required: Use `hashlib` for identifiers

- [ ] **Log Sanitization**: Is PII excluded from stdout/stderr logging?
  - Verification: Grep logs for PII patterns
  - Risk: PII leakage via logging

- [ ] **Temporary File Handling**: Is raw data cleaned from temp files after transformation?
  - Verification: Check pipeline working directories
  - Risk: PII persistence in temporary storage

---

## Task Coverage

| Task ID | Description | Status |
|---------|-------------|--------|
| IAM-02 | Scope-Based Access Control | [ ] |
| API-02 | Deep JSON Schema Validation | [ ] |
| DATA-02 | PII Masking Transformer Audit | [ ] |
| DATA-03 | PostgreSQL Role Segregation | [ ] |
| MLSEC-03 | Statistical Input Guardrails | [ ] |
