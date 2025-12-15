# Physical View Security Audit Checklist

## Network Isolation

- [ ] **Database Access**: Is PostgreSQL accessible only via internal Docker network?
  - Verification: `nmap` external port 5432 returns closed
  - Risk: Direct database access from internet

- [ ] **Redis Access**: Is Redis accessible only via internal Docker network?
  - Verification: `nmap` external port 6379 returns closed
  - Risk: Cache poisoning, session hijacking

- [ ] **Service Mesh**: Is internal traffic encrypted via mTLS or service mesh?
  - Verification: `tcpdump` internal traffic is encrypted
  - Risk: MITM attacks on internal network

- [ ] **Docker Socket**: Is `/var/run/docker.sock` NOT mounted into any container?
  - Verification: `grep docker.sock docker-compose.yml` returns empty
  - Risk: Container escape via Docker API

---

## Least Privilege

- [ ] **Non-Root Containers**: Do all containers run as non-root users?
  - Required: `USER app` in Dockerfile
  - Verification: `docker exec container whoami` returns non-root
  - Risk: Container escape with root privileges

- [ ] **File Permissions**: Are application directories owned by non-root user?
  - Required: `chown -R app:app /app`
  - Verification: `ls -la /app` shows app ownership
  - Risk: Privilege escalation via writable root-owned files

- [ ] **Read-Only Mounts**: Are write permissions restricted where possible?
  - Verification: Check volume mounts for `:ro` suffix
  - Risk: Unauthorized file modification

- [ ] **Database Roles**: Are minimal database roles used?
  - Required Roles:
    - `mage_writer`: INSERT, UPDATE, SELECT
    - `api_reader`: SELECT only
  - Verification: DROP TABLE fails from api_reader
  - Risk: Destructive operations from application

---

## Encryption

- [ ] **Database TLS**: Is `sslmode=verify-full` enforced on database connections?
  - Verification: `tcpdump` on DB port shows encrypted payload
  - Required: Mount CA certificates into containers
  - Risk: MITM on database traffic

- [ ] **Redis TLS**: Is TLS enabled for Redis connections?
  - Verification: Check Redis connection string for `rediss://`
  - Risk: Session data interception

- [ ] **Nginx TLS**: Is HTTPS terminated at Nginx with modern cipher suites?
  - Required: TLS 1.2+ only, HSTS enabled
  - Verification: `sslscan` or `testssl.sh` on endpoint
  - Risk: Downgrade attacks

- [ ] **Weak Cipher Disablement**: Are TLS 1.0/1.1 and weak ciphers disabled?
  - Verification: `nmap --script ssl-enum-ciphers` shows TLS 1.2+ only
  - Risk: Protocol downgrade attacks

---

## Header Security

- [ ] **HSTS Header**: Is `Strict-Transport-Security` header set?
  - Required: `max-age=31536000; includeSubDomains`
  - Verification: `curl -I` shows HSTS header
  - Risk: SSL stripping attacks

- [ ] **Content Security**: Are security headers configured?
  - Required Headers:
    - `X-Content-Type-Options: nosniff`
    - `X-Frame-Options: DENY`
    - `Content-Security-Policy`
  - Verification: `curl -I` shows all headers

- [ ] **Forwarded Header Trust**: Does Nginx strip `X-Forwarded-For` from ingress?
  - Verification: Attempt IP spoofing via header; check logs
  - Risk: Rate limiting bypass via IP spoofing

---

## Artifact Security

- [ ] **MOJO Storage Permissions**: Is MOJO artifact storage properly secured?
  - Required: `chmod 0640`, owned by shared group
  - Permissions: Only Mage can write, only FastAPI can read
  - Verification: Write attempt from FastAPI container fails
  - Risk: Model poisoning via artifact tampering

- [ ] **Volume Encryption**: Is the artifact volume encrypted at rest?
  - Verification: Check for LUKS or cloud KMS encryption
  - Risk: Model theft from disk access

---

## Task Coverage

| Task ID | Description | Status |
|---------|-------------|--------|
| IAM-04 | Secure Secrets Injection | [ ] |
| API-04 | Nginx Header Security Hardening | [ ] |
| CONT-03 | Non-Root User Configuration | [ ] |
| DATA-01 | Database Connection Encryption | [ ] |
| DATA-04 | Artifact Access Control | [ ] |
