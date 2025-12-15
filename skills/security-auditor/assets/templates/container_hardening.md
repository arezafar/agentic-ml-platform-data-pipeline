# Container Hardening Guide

## Multi-Stage Build Pattern

### Secure Dockerfile Template

```dockerfile
# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim AS builder

# Install build dependencies (will not be in final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# =============================================================================
# Stage 2: Runtime (Minimal)
# =============================================================================
FROM python:3.11-slim AS runtime

# Security: Create non-root user
RUN groupadd -r app && useradd -r -g app app

# Install only runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=app:app ./src /app

# Security: Switch to non-root user
USER app

# Security: Drop all capabilities
# (Set in docker-compose or K8s securityContext)

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## H2O MOJO Inference Container (No JVM)

```dockerfile
# =============================================================================
# MOJO Inference Container (C++ Runtime Only)
# =============================================================================
FROM python:3.11-slim AS runtime

# Security: Non-root user
RUN groupadd -r app && useradd -r -g app app

# Install MOJO C++ runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-built daimojo wheel
COPY --chown=app:app ./wheels/daimojo-*.whl /tmp/
RUN pip install /tmp/daimojo-*.whl && rm /tmp/daimojo-*.whl

# Copy Python dependencies
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY --chown=app:app ./src /app

USER app

# Verification: No JVM present
RUN which java 2>/dev/null && exit 1 || true

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Docker Compose Security Settings

```yaml
version: "3.8"

services:
  inference:
    build:
      context: .
      dockerfile: Dockerfile
    
    # Security settings
    security_opt:
      - no-new-privileges:true
    
    # Read-only root filesystem
    read_only: true
    
    # Temporary directories for runtime
    tmpfs:
      - /tmp:mode=1777,size=50M
    
    # Drop all capabilities
    cap_drop:
      - ALL
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
    
    # User mapping
    user: "1000:1000"
    
    # Network isolation
    networks:
      - internal
    
    # No Docker socket access
    # volumes:
    #   - /var/run/docker.sock:/var/run/docker.sock  # NEVER DO THIS

  postgres:
    image: postgres:15-alpine
    
    security_opt:
      - no-new-privileges:true
    
    # Internal network only
    networks:
      - internal
    
    # No port exposure
    # ports:  # NEVER expose in production
    #   - "5432:5432"

networks:
  internal:
    driver: bridge
    internal: true  # No external access
  
  external:
    driver: bridge
```

---

## Kubernetes Security Context

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      
      containers:
        - name: inference
          image: inference:latest
          
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          
          resources:
            limits:
              cpu: "2"
              memory: 2Gi
            requests:
              cpu: "500m"
              memory: 512Mi
```

---

## Verification Commands

```bash
# Check image size (target < 500MB)
docker images inference:latest --format "{{.Size}}"

# Verify no build tools
docker run --rm inference:latest which gcc
# Expected: exit 1 (not found)

# Verify no JVM
docker run --rm inference:latest java -version
# Expected: exit 127 (not found)

# Verify non-root user
docker run --rm inference:latest whoami
# Expected: app

# Verify read-only filesystem
docker run --rm inference:latest touch /test
# Expected: Read-only file system error

# Scan for vulnerabilities
trivy image inference:latest --severity CRITICAL,HIGH
```

---

## Checklist

- [ ] Multi-stage build separates build and runtime
- [ ] Final image uses slim/distroless base
- [ ] Non-root USER directive present
- [ ] No build tools (gcc, pip, git) in final image
- [ ] No JVM in inference container
- [ ] Docker socket NOT mounted
- [ ] Capabilities dropped
- [ ] Resource limits configured
- [ ] Health check defined
