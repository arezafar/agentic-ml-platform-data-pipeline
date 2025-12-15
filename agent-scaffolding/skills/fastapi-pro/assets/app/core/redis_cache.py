"""
Job 1: Redis Look-Aside Cache

Implements async caching layer for sub-50ms latency.
Uses deterministic feature hashing for cache keys with
model version prefix for automatic invalidation.

Pattern: Check cache (async) → Miss? → Predict (thread) → Write-back (async)

Success Criteria:
- Cache hits return in <5ms
- Async Redis client (non-blocking)
- TTL-based drift management
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional, Callable, TypeVar
from functools import wraps

T = TypeVar('T')


class RedisCache:
    """
    Async Redis look-aside cache for prediction results.
    
    Uses redis-py async client for non-blocking operations.
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl: int = 3600,  # 1 hour
        key_prefix: str = "pred",
    ):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            key_prefix: Prefix for all cache keys
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._client = None
        
    async def connect(self) -> None:
        """Establish async Redis connection."""
        try:
            import redis.asyncio as redis
            
            self._client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            
            # Validate connection
            await self._client.ping()
            print(f"[CACHE] Connected to Redis: {self.redis_url}")
            
        except ImportError:
            print("[CACHE] ⚠️ redis-py not installed. Cache disabled.")
            self._client = None
            
        except Exception as e:
            print(f"[CACHE] ⚠️ Redis connection failed: {e}. Cache disabled.")
            self._client = None
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            print("[CACHE] Redis connection closed")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached value (async, non-blocking).
        
        Returns None if not found or cache disabled.
        """
        if not self._client:
            return None
        
        try:
            value = await self._client.get(f"{self.key_prefix}:{key}")
            
            if value:
                return json.loads(value)
            return None
            
        except Exception as e:
            print(f"[CACHE] GET error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set cached value with TTL (async, non-blocking).
        
        TTL ensures stale predictions expire for drift management.
        """
        if not self._client:
            return False
        
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value)
            
            await self._client.setex(
                f"{self.key_prefix}:{key}",
                ttl,
                serialized,
            )
            return True
            
        except Exception as e:
            print(f"[CACHE] SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete a cached key."""
        if not self._client:
            return False
        
        try:
            await self._client.delete(f"{self.key_prefix}:{key}")
            return True
        except Exception as e:
            print(f"[CACHE] DELETE error: {e}")
            return False
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.
        
        Used when deploying new model version:
        await cache.invalidate_pattern("pred:v1:*")
        """
        if not self._client:
            return 0
        
        try:
            keys = []
            async for key in self._client.scan_iter(f"{self.key_prefix}:{pattern}"):
                keys.append(key)
            
            if keys:
                await self._client.delete(*keys)
            
            print(f"[CACHE] Invalidated {len(keys)} keys matching: {pattern}")
            return len(keys)
            
        except Exception as e:
            print(f"[CACHE] INVALIDATE error: {e}")
            return 0


def cached_prediction(
    cache: RedisCache,
    key_generator: Callable[[Dict], str],
    ttl: Optional[int] = None,
):
    """
    Decorator for cached predictions.
    
    Usage:
        @cached_prediction(cache, lambda x: predictor.generate_cache_key(x))
        async def predict(features):
            return await predictor.predict_async(features)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(features: Dict[str, Any], *args, **kwargs):
            # Generate cache key
            cache_key = key_generator(features)
            
            # Check cache (async, non-blocking)
            cached = await cache.get(cache_key)
            if cached:
                cached['cache_hit'] = True
                return cached
            
            # Cache miss - execute prediction
            result = await func(features, *args, **kwargs)
            result['cache_hit'] = False
            
            # Write-back (async, non-blocking)
            await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global cache instance
_CACHE: Optional[RedisCache] = None


async def get_cache() -> RedisCache:
    """Get or create the global cache instance."""
    global _CACHE
    if _CACHE is None:
        _CACHE = RedisCache()
        await _CACHE.connect()
    return _CACHE


async def init_cache(redis_url: str = "redis://localhost:6379") -> RedisCache:
    """Initialize cache on app startup."""
    global _CACHE
    _CACHE = RedisCache(redis_url=redis_url)
    await _CACHE.connect()
    return _CACHE


if __name__ == '__main__':
    import asyncio
    
    async def test():
        cache = RedisCache()
        await cache.connect()
        
        # Test set/get
        await cache.set("test_key", {"prediction": 1, "probability": 0.85})
        result = await cache.get("test_key")
        print(f"Cached result: {result}")
        
        await cache.disconnect()
    
    asyncio.run(test())
