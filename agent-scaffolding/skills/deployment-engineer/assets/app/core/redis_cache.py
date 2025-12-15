"""
Redis Look-Aside Cache for ML Inference
=============================================================================
PROC-02-02: Redis Look-Aside Cache Implementation

High-performance caching layer for ML predictions with:
- Feature vector hashing for cache keys
- Model version namespacing (prevents stale predictions after updates)
- TTL-based expiration for concept drift handling
- Async operations for non-blocking I/O

Key Patterns:
- Hash features -> Redis key with model version prefix
- On miss: compute prediction, store with TTL
- On hit: return immediately (bypasses inference engine)

Usage:
    cache = InferenceCache(redis_url="redis://localhost:6379/0")
    
    # Check cache before inference
    cached = await cache.get(features, model_version="v1.2.3")
    if cached:
        return cached
    
    # Compute and cache
    prediction = await model.predict(features)
    await cache.set(features, prediction, model_version="v1.2.3")
=============================================================================
"""

import hashlib
import json
import os
from typing import Any, Optional
from datetime import timedelta

import redis.asyncio as redis
from pydantic import BaseModel


# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_TTL = timedelta(hours=1)
KEY_PREFIX = "inference:prediction"


class CacheStats(BaseModel):
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class InferenceCache:
    """
    Async Redis cache for ML predictions.
    
    PROC-02-02: Implements look-aside caching pattern:
    1. Check cache before inference
    2. On miss, compute and store
    3. Version-aware keys prevent stale predictions
    """
    
    def __init__(
        self,
        redis_url: str = REDIS_URL,
        default_ttl: timedelta = DEFAULT_TTL,
        key_prefix: str = KEY_PREFIX,
    ):
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._client: Optional[redis.Redis] = None
        self._stats = CacheStats()
    
    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def _get_client(self) -> redis.Redis:
        """Lazy initialization of Redis client."""
        if self._client is None:
            await self.connect()
        return self._client
    
    def _hash_features(self, features: dict[str, Any]) -> str:
        """
        Create deterministic hash of feature vector.
        
        Uses sorted JSON to ensure consistent ordering.
        """
        # Sort keys for deterministic ordering
        sorted_features = json.dumps(features, sort_keys=True, default=str)
        return hashlib.sha256(sorted_features.encode()).hexdigest()[:16]
    
    def _make_key(self, feature_hash: str, model_version: str) -> str:
        """
        Create cache key with model version namespace.
        
        Format: inference:prediction:{model_version}:{feature_hash}
        
        Model version prefix ensures cache invalidation on model updates.
        """
        return f"{self.key_prefix}:{model_version}:{feature_hash}"
    
    async def get(
        self,
        features: dict[str, Any],
        model_version: str,
    ) -> Optional[dict[str, Any]]:
        """
        Look up cached prediction for features.
        
        Args:
            features: Input feature vector
            model_version: Current model version (for namespace isolation)
            
        Returns:
            Cached prediction dict or None on miss
        """
        client = await self._get_client()
        
        feature_hash = self._hash_features(features)
        key = self._make_key(feature_hash, model_version)
        
        try:
            cached = await client.get(key)
            if cached:
                self._stats.hits += 1
                return json.loads(cached)
            else:
                self._stats.misses += 1
                return None
        except Exception as e:
            # Cache failures should not break inference
            print(f"Cache get error: {e}")
            self._stats.misses += 1
            return None
    
    async def set(
        self,
        features: dict[str, Any],
        prediction: dict[str, Any],
        model_version: str,
        ttl: Optional[timedelta] = None,
    ) -> bool:
        """
        Store prediction in cache.
        
        Args:
            features: Input feature vector
            prediction: Model prediction to cache
            model_version: Current model version
            ttl: Optional custom TTL (defaults to DEFAULT_TTL)
            
        Returns:
            True if stored successfully
        """
        client = await self._get_client()
        
        feature_hash = self._hash_features(features)
        key = self._make_key(feature_hash, model_version)
        ttl = ttl or self.default_ttl
        
        try:
            await client.setex(
                key,
                int(ttl.total_seconds()),
                json.dumps(prediction, default=str),
            )
            return True
        except Exception as e:
            # Cache failures should not break inference
            print(f"Cache set error: {e}")
            return False
    
    async def invalidate_model(self, model_version: str) -> int:
        """
        Invalidate all cache entries for a specific model version.
        
        Called during model updates to prevent stale predictions.
        
        Args:
            model_version: Version to invalidate
            
        Returns:
            Number of keys deleted
        """
        client = await self._get_client()
        
        pattern = f"{self.key_prefix}:{model_version}:*"
        cursor = 0
        deleted = 0
        
        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            if keys:
                deleted += await client.delete(*keys)
            if cursor == 0:
                break
        
        return deleted
    
    async def get_stats(self) -> CacheStats:
        """Get cache performance statistics."""
        return self._stats
    
    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            client = await self._get_client()
            await client.ping()
            return True
        except Exception:
            return False


# Global cache instance (initialized on startup)
_cache: Optional[InferenceCache] = None


async def get_cache() -> InferenceCache:
    """Get or create global cache instance."""
    global _cache
    if _cache is None:
        _cache = InferenceCache()
        await _cache.connect()
    return _cache


async def close_cache() -> None:
    """Close global cache connection."""
    global _cache
    if _cache:
        await _cache.disconnect()
        _cache = None


# FastAPI integration helpers
async def cache_startup() -> None:
    """Call during FastAPI startup."""
    await get_cache()


async def cache_shutdown() -> None:
    """Call during FastAPI shutdown."""
    await close_cache()


# Test harness
if __name__ == "__main__":
    import asyncio
    
    async def test():
        cache = InferenceCache()
        await cache.connect()
        
        features = {"age": 35, "income": 75000, "tenure": 24}
        prediction = {"churn_probability": 0.15, "segment": "low_risk"}
        
        # Test set
        result = await cache.set(features, prediction, model_version="v1.0.0")
        print(f"Set result: {result}")
        
        # Test get
        cached = await cache.get(features, model_version="v1.0.0")
        print(f"Get result: {cached}")
        
        # Test miss with different version
        cached_miss = await cache.get(features, model_version="v2.0.0")
        print(f"Different version (should be None): {cached_miss}")
        
        # Stats
        stats = await cache.get_stats()
        print(f"Stats: hits={stats.hits}, misses={stats.misses}, rate={stats.hit_rate:.2%}")
        
        await cache.disconnect()
    
    asyncio.run(test())
