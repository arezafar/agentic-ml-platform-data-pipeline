# Container Security Reference

## Supply Chain Security

### The Container Attack Surface

```
┌─────────────────────────────────────────────────────────────┐
│                     Attack Surface                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Base Image  │  │ OS Packages │  │ Python Deps │         │
│  │ (Debian)    │  │ (apt)       │  │ (pip)       │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                   │
│                  ┌──────────────┐                           │
│                  │ Application  │                           │
│                  │    Code      │                           │
│                  └──────────────┘                           │
│                                                              │
│  Threat Vectors:                                            │
│  • CVEs in base image                                       │
│  • Typosquatted Python packages                             │
│  • Malicious transitive dependencies                        │
│  • Build tool exploitation (LotL)                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Image Minimization Strategy

### Base Image Selection

| Image | Size | Use Case | Security |
|-------|------|----------|----------|
| `python:3.11` | ~900MB | Development | ❌ Too large |
| `python:3.11-slim` | ~150MB | Production | ✅ Recommended |
| `python:3.11-alpine` | ~50MB | Minimal | ⚠️ Compatibility issues |
| `gcr.io/distroless/python3` | ~50MB | Maximum security | ✅ Best security |

### Multi-Stage Build Benefits

```dockerfile
# Builder stage: 900MB+
FROM python:3.11 AS builder
RUN apt-get install build-essential gcc
RUN pip install numpy pandas h2o

# Runtime stage: ~200MB
FROM python:3.11-slim AS runtime
COPY --from=builder /opt/venv /opt/venv
# No gcc, no pip, no attack surface
```

### Items to Exclude from Production Image

| Item | Risk | Verification |
|------|------|--------------|
| `gcc`, `g++` | Compile exploits on target | `which gcc` |
| `pip` | Install malicious packages | `which pip` |
| `curl`, `wget` | Download payloads | `which curl` |
| `git` | Clone malicious repos | `which git` |
| `ssh` | Backdoor access | `which ssh` |
| JDK/JRE | Java deserialization attacks | `java -version` |
| Package managers | Persistent compromise | `which apt` |

---

## Dependency Scanning

### Vulnerability Scanning Tools

| Tool | Type | Integration |
|------|------|-------------|
| **trivy** | Container + Dependencies | CI/CD, CLI |
| **grype** | Container + SBOM | CLI, GitLab |
| **safety** | Python packages | pip, CI/CD |
| **Snyk** | Full stack | GitHub, CLI |

### CI/CD Integration

```yaml
# .github/workflows/security.yml
name: Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build image
        run: docker build -t app:${{ github.sha }} .
      
      - name: Run trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'app:${{ github.sha }}'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'  # Fail on findings
          
      - name: Generate SBOM
        run: |
          trivy image --format cyclonedx \
            --output sbom.json \
            app:${{ github.sha }}
      
      - name: Upload SBOM
        uses: actions/upload-artifact@v3
        with:
          name: sbom
          path: sbom.json
```

### Python Dependency Scanning

```bash
# Install safety
pip install safety

# Scan requirements
safety check -r requirements.txt

# Scan with JSON output
safety check --json > safety-report.json
```

---

## SBOM (Software Bill of Materials)

### Why SBOM?

- **Zero-day response**: Know which services are affected within minutes
- **Compliance**: Required by Executive Order 14028
- **Supply chain visibility**: Track transitive dependencies

### SBOM Generation

```bash
# Generate CycloneDX SBOM from image
trivy image --format cyclonedx --output sbom.cdx.json myimage:latest

# Generate from Python project
pip install cyclonedx-bom
cyclonedx-py --format json --output sbom.cdx.json

# Generate SPDX format
trivy image --format spdx-json --output sbom.spdx.json myimage:latest
```

### SBOM Contents

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.4",
  "components": [
    {
      "type": "library",
      "name": "fastapi",
      "version": "0.104.1",
      "purl": "pkg:pypi/fastapi@0.104.1"
    }
  ]
}
```

---

## Runtime Security

### Non-Root Execution

```dockerfile
# Create user
RUN groupadd -r app && useradd -r -g app app

# Set ownership
COPY --chown=app:app ./src /app

# Switch to non-root
USER app
```

### Read-Only Filesystem

```yaml
# docker-compose.yml
services:
  app:
    read_only: true
    tmpfs:
      - /tmp:mode=1777,size=50M
```

### Capability Dropping

```yaml
# docker-compose.yml
services:
  app:
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if needed for ports < 1024
```

### Seccomp Profile

```yaml
# docker-compose.yml
services:
  app:
    security_opt:
      - seccomp:seccomp-profile.json
```

---

## Kubernetes Security

### Pod Security Standards

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: inference-policy
spec:
  podSelector:
    matchLabels:
      app: inference
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: nginx
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
        - podSelector:
            matchLabels:
              app: redis
```

---

## Quick Reference

### Image Security Checklist

```bash
# 1. Check image size
docker images myimage:latest --format "{{.Size}}"
# Target: < 500MB

# 2. Scan for CVEs
trivy image myimage:latest --severity CRITICAL,HIGH

# 3. Check for root user
docker run --rm myimage:latest whoami
# Expected: non-root user

# 4. Verify no build tools
docker run --rm myimage:latest which gcc pip curl
# Expected: all "not found"

# 5. Check for sensitive files
docker run --rm myimage:latest find / -name "*.key" -o -name "*.pem"
# Expected: empty or expected certs only
```
