# IAM Implementation Guide

## OAuth2/OIDC Integration with FastAPI

### Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   FastAPI   │────▶│ OIDC Provider│
│             │     │  (Resource) │     │ (Keycloak)  │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    Redis    │
                    │ (Blocklist) │
                    └─────────────┘
```

### Hybrid Authentication Model

**Problem**: Pure stateless JWTs cannot be immediately revoked.
**Solution**: Short-lived access tokens + Redis blocklist for revocation.

| Token Type | Lifetime | Storage | Purpose |
|------------|----------|---------|---------|
| Access Token (JWT) | 15 min | Client | API authorization |
| Refresh Token | 7 days | Redis | Session extension |
| JTI Blocklist | 15 min TTL | Redis | Revocation check |

---

## Implementation

### 1. OIDC Provider Configuration

```python
# config/auth.py
from pydantic import BaseSettings

class AuthSettings(BaseSettings):
    oidc_issuer: str = "https://keycloak.example.com/realms/mlops"
    oidc_client_id: str
    oidc_client_secret: str
    oidc_audience: str = "mlops-api"
    
    # Token settings
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    class Config:
        env_prefix = "AUTH_"
```

### 2. Token Validation Dependency

```python
# auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from functools import lru_cache
import httpx
import asyncio

security = HTTPBearer()

@lru_cache(maxsize=1)
def get_jwks():
    """Fetch JWKS from OIDC provider (cached)."""
    # NOTE: In production, use async with refresh
    response = httpx.get(f"{settings.oidc_issuer}/.well-known/openid-configuration")
    jwks_uri = response.json()["jwks_uri"]
    return httpx.get(jwks_uri).json()

async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    redis: Redis = Depends(get_redis)
) -> dict:
    """Validate JWT token with blocklist check."""
    token = credentials.credentials
    
    try:
        # CPU-bound: offload to thread pool
        loop = asyncio.get_event_loop()
        payload = await loop.run_in_executor(
            None,
            lambda: jwt.decode(
                token,
                get_jwks(),
                algorithms=["RS256"],
                audience=settings.oidc_audience,
                issuer=settings.oidc_issuer
            )
        )
        
        # Check blocklist
        jti = payload.get("jti")
        if jti and await redis.exists(f"blocklist:{jti}"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked"
            )
        
        return payload
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
```

### 3. Scope-Based Authorization

```python
# auth/scopes.py
from fastapi import Security
from fastapi.security import SecurityScopes

SCOPES = {
    "mage:pipeline:read": "View pipeline status",
    "mage:pipeline:execute": "Execute pipelines",
    "h2o:model:train": "Train ML models",
    "api:predict": "Call inference endpoint"
}

async def require_scopes(
    security_scopes: SecurityScopes,
    token: dict = Depends(validate_token)
) -> dict:
    """Enforce scope requirements."""
    token_scopes = token.get("scope", "").split()
    
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {scope}"
            )
    
    return token

# Usage in route
@app.post("/predict")
async def predict(
    request: PredictionRequest,
    user: dict = Security(require_scopes, scopes=["api:predict"])
):
    ...
```

### 4. Redis Session Revocation

```python
# auth/revocation.py
from redis.asyncio import Redis

async def revoke_token(redis: Redis, jti: str, ttl_seconds: int):
    """Add token JTI to blocklist."""
    await redis.setex(
        f"blocklist:{jti}",
        ttl_seconds,
        "revoked"
    )

async def revoke_user_sessions(redis: Redis, user_id: str):
    """Revoke all sessions for a user."""
    # Requires tracking active JTIs per user
    pattern = f"session:{user_id}:*"
    async for key in redis.scan_iter(pattern):
        jti = await redis.get(key)
        await revoke_token(redis, jti, 900)  # 15 min
        await redis.delete(key)
```

---

## Mage Integration

Configure Mage webhook authentication:

```python
# mage_pipeline/custom/auth_hook.py
import httpx
from mage_ai.orchestration.triggers.api import trigger_pipeline

def trigger_with_auth(pipeline_uuid: str, token: str):
    """Trigger Mage pipeline with OIDC token."""
    response = httpx.post(
        f"http://mage:6789/api/pipelines/{pipeline_uuid}/triggers",
        headers={"Authorization": f"Bearer {token}"},
        json={"trigger_type": "api"}
    )
    response.raise_for_status()
    return response.json()
```

---

## Verification Checklist

- [ ] Token without Bearer prefix returns 401
- [ ] Expired token returns 401
- [ ] Invalid signature returns 401
- [ ] Missing required scope returns 403
- [ ] Revoked token (in blocklist) returns 401
- [ ] Valid token with correct scopes returns 200
