# OAuth2/OIDC Security Patterns

## Hybrid JWT/Session Architecture

### The Async Authentication Dilemma

```
THESIS:     Stateless JWTs for high-throughput APIs (>1000 req/s)
ANTITHESIS: Pure stateless tokens cannot be immediately revoked
SYNTHESIS:  Hybrid model with short-lived JWTs + Redis session state
```

### Token Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Login     │────▶│ Access Token│────▶│   API Call  │
│             │     │  (15 min)   │     │             │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │ Refresh     │
                    │ (7 days)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Redis       │
                    │ Blocklist   │
                    └─────────────┘
```

---

## better-auth Integration Principles

### 1. Schema-Driven Authentication

All authentication flows must be strictly typed:

```python
from pydantic import BaseModel, Field

class TokenPayload(BaseModel):
    """Validated JWT payload."""
    sub: str = Field(..., description="Subject (user ID)")
    iss: str = Field(..., description="Issuer URL")
    aud: str = Field(..., description="Audience")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID for revocation")
    scope: str = Field(default="", description="Space-separated scopes")
    
    @property
    def scopes(self) -> list[str]:
        return self.scope.split() if self.scope else []
```

### 2. Non-Blocking Token Validation

Token validation involves cryptographic operations (CPU-bound) and potentially network calls (fetching JWKS). These must not block the async event loop:

```python
import asyncio
from jose import jwt

async def validate_token_async(token: str, jwks: dict) -> TokenPayload:
    """Non-blocking token validation."""
    loop = asyncio.get_event_loop()
    
    # Offload CPU-bound crypto to thread pool
    payload = await loop.run_in_executor(
        None,  # Default executor
        lambda: jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer
        )
    )
    
    return TokenPayload(**payload)
```

### 3. OIDC Discovery Document Caching

```python
from functools import lru_cache
import httpx

@lru_cache(maxsize=1)
def get_oidc_config(issuer: str) -> dict:
    """Fetch and cache OIDC discovery document."""
    response = httpx.get(
        f"{issuer}/.well-known/openid-configuration",
        timeout=10.0
    )
    response.raise_for_status()
    return response.json()

@lru_cache(maxsize=1)
def get_jwks(issuer: str) -> dict:
    """Fetch and cache JWKS."""
    config = get_oidc_config(issuer)
    response = httpx.get(config["jwks_uri"], timeout=10.0)
    response.raise_for_status()
    return response.json()

# Schedule periodic refresh (not on every request)
async def refresh_jwks_periodically():
    while True:
        await asyncio.sleep(3600)  # 1 hour
        get_jwks.cache_clear()
        get_oidc_config.cache_clear()
```

---

## Scope Design Patterns

### Platform Scope Hierarchy

```
mlops:                          # Root namespace
├── mage:                       # Mage orchestrator
│   ├── pipeline:read           # View pipelines
│   ├── pipeline:execute        # Trigger pipelines
│   └── pipeline:admin          # Manage configurations
├── h2o:                        # H2O cluster
│   ├── model:read              # View models
│   ├── model:train             # Train models
│   └── model:admin             # Manage cluster
└── api:                        # Inference API
    ├── predict                 # Single predictions
    ├── batch-predict           # Batch predictions
    └── admin                   # API administration
```

### Role-to-Scope Mapping

| Role | Scopes |
|------|--------|
| Data Scientist | mage:pipeline:read, mage:pipeline:execute, h2o:model:read, h2o:model:train |
| ML Engineer | mage:pipeline:*, h2o:model:*, api:predict |
| API Consumer | api:predict |
| Platform Admin | * |

### Scope Enforcement Pattern

```python
from fastapi import Security
from fastapi.security import SecurityScopes

def require_any_scope(*required_scopes: str):
    """Require at least one of the specified scopes."""
    async def checker(
        security_scopes: SecurityScopes,
        token: TokenPayload = Depends(validate_token)
    ) -> TokenPayload:
        if not any(s in token.scopes for s in required_scopes):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of: {required_scopes}"
            )
        return token
    return checker

# Usage
@app.get("/models")
async def list_models(
    user: TokenPayload = Security(
        require_any_scope,
        scopes=["h2o:model:read", "h2o:model:admin"]
    )
):
    ...
```

---

## Session Revocation Strategies

### Immediate Revocation via Redis Blocklist

```python
class TokenBlocklist:
    """Redis-backed JWT blocklist."""
    
    def __init__(self, redis: Redis, prefix: str = "blocklist"):
        self.redis = redis
        self.prefix = prefix
    
    async def revoke(self, jti: str, ttl_seconds: int):
        """Add token to blocklist."""
        key = f"{self.prefix}:{jti}"
        await self.redis.setex(key, ttl_seconds, "revoked")
    
    async def is_revoked(self, jti: str) -> bool:
        """Check if token is revoked."""
        key = f"{self.prefix}:{jti}"
        return await self.redis.exists(key) > 0
    
    async def revoke_all_for_user(self, user_id: str, ttl_seconds: int):
        """Revoke all tokens for a user (requires session tracking)."""
        pattern = f"session:{user_id}:*"
        async for key in self.redis.scan_iter(pattern):
            jti = await self.redis.get(key)
            if jti:
                await self.revoke(jti, ttl_seconds)
```

### Token Lifecycle Management

```python
async def issue_tokens(user_id: str, scopes: list[str]) -> dict:
    """Issue access and refresh tokens."""
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    
    access_token = jwt.encode({
        "sub": user_id,
        "jti": jti,
        "scope": " ".join(scopes),
        "exp": now + timedelta(minutes=15),
        "iat": now
    }, private_key, algorithm="RS256")
    
    # Track session in Redis
    await redis.setex(
        f"session:{user_id}:{jti}",
        timedelta(days=7).total_seconds(),
        jti
    )
    
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 900
    }
```

---

## Service-to-Service Authentication

### Internal API Tokens

For Mage → FastAPI and FastAPI → H2O communication:

```python
# Generate long-lived service token
service_token = jwt.encode({
    "sub": "mage-orchestrator",
    "iss": "internal",
    "scope": "internal:service",
    "exp": datetime.utcnow() + timedelta(days=365)
}, service_secret, algorithm="HS256")
```

### mTLS Alternative

For zero-trust internal networks:

```yaml
# docker-compose.yml
services:
  inference:
    environment:
      - SSL_CERT_FILE=/certs/client.crt
      - SSL_KEY_FILE=/certs/client.key
    volumes:
      - ./certs:/certs:ro
```

---

## Anti-Patterns

| Anti-Pattern | Risk | Solution |
|--------------|------|----------|
| Token in URL | Logged in access logs | Bearer header only |
| Hardcoded secrets | Credential exposure | Environment variables |
| Long-lived access tokens | Extended compromise window | 15-minute expiry |
| Blocking JWKS fetch | Event loop starvation | Cached + async refresh |
| No scope validation | Privilege escalation | Enforce scopes on every route |
