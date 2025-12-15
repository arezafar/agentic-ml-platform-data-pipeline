# Scenarios View Security Audit Checklist

## Incident Response

- [ ] **Model Rollback**: Can the system revert to a previous signed artifact instantly?
  - Required: Zero-downtime rollback capability
  - Verification: Trigger rollback; verify prediction continuity
  - Scenario: Model poisoning detected in production

- [ ] **Token Revocation**: Can all tokens for a compromised user be revoked immediately?
  - Verification: Revoke user; verify all active sessions terminated
  - Scenario: Account compromise detected

- [ ] **Secret Rotation**: Can secrets be rotated without downtime?
  - Required: Hot reload of configuration
  - Verification: Rotate DB password; verify connection continuity
  - Scenario: Credential exposure detected

- [ ] **Audit Logging**: Are security events logged for forensic analysis?
  - Required Events:
    - Authentication failures
    - Authorization denials
    - Rate limit triggers
    - Model loads
  - Verification: Check centralized logging for events
  - Scenario: Post-incident investigation

---

## Breach Containment

- [ ] **Mage Container Isolation**: Does Mage container network policy prevent lateral movement?
  - Required: Mage cannot reach production inference API directly
  - Verification: `curl` from Mage to FastAPI fails
  - Scenario: Mage container compromised

- [ ] **Database Segmentation**: Can compromised application access only required tables?
  - Required: RLS or schema-level isolation
  - Verification: Query unauthorized table fails
  - Scenario: SQL injection successful

- [ ] **Redis Isolation**: Are Redis namespaces segregated by function?
  - Required: Separate key prefixes for cache vs sessions
  - Verification: Session keys cannot be enumerated from cache context
  - Scenario: Cache poisoning attempt

---

## Attack Simulation

- [ ] **Credential Stuffing**: Does rate limiting prevent brute force attacks?
  - Verification: 100 failed logins trigger lockout
  - Threshold: 5 failures per 15 minutes per account
  - Scenario: Credential stuffing attack

- [ ] **Model Inversion**: Do input guardrails reject probing inputs?
  - Verification: Statistical outliers rejected (422)
  - Scenario: Attacker attempts model extraction

- [ ] **DoS Resilience**: Does the system degrade gracefully under load?
  - Verification: 10x normal load returns 429, not 500
  - Scenario: Application layer DDoS

- [ ] **Sponge Attack**: Are oversized/complex inputs rejected before hitting ML engine?
  - Verification: Complex JSON rejected at API layer
  - Scenario: Attacker sends compute-intensive feature vectors

---

## Recovery Testing

- [ ] **Backup Verification**: Are database backups tested for restoration?
  - Frequency: Monthly restoration drill
  - Verification: Restore to staging; verify data integrity
  - Scenario: Ransomware attack

- [ ] **DR Failover**: Can the system failover to secondary region?
  - RTO: <4 hours
  - RPO: <1 hour
  - Verification: Conduct DR drill quarterly
  - Scenario: Primary region outage

---

## Compliance Scenarios

- [ ] **Right to Erasure**: Can PII be deleted on request?
  - Verification: Delete user; verify cascade through feature store
  - Scenario: GDPR Article 17 request

- [ ] **Access Request**: Can all data for a user be exported?
  - Verification: Export produces complete dataset
  - Scenario: GDPR Article 15 request

- [ ] **Breach Notification**: Is there a process for 72-hour breach notification?
  - Verification: Document exists and is tested
  - Scenario: Data breach detected

---

## Task Coverage

| Scenario | Related Tasks | Status |
|----------|---------------|--------|
| Model Poisoning | MLSEC-01 (Artifact Signing) | [ ] |
| Compromised Token | IAM-03 (Session Revocation) | [ ] |
| Container Escape | CONT-03 (Non-Root), Physical Isolation | [ ] |
| Injection Attack | API-03 (SQL/JSON Audit), API-02 (Validation) | [ ] |
| DoS Attack | API-01 (Rate Limiting) | [ ] |
