"""
Job 1: Async Database Connection Pool

Configures asyncpg connection pool for non-blocking feature fetching.
Uses lifespan context manager for proper resource management.

CRITICAL: Do NOT use psycopg2 - it blocks the event loop.
Use asyncpg or SQLAlchemy 1.4+ async mode.

Success Criteria:
- Non-blocking database queries
- Connection pool prevents exhaustion
- Proper cleanup on shutdown
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
import os


class AsyncDatabasePool:
    """
    Async PostgreSQL connection pool using asyncpg.
    
    Configured with min/max connections to prevent exhaustion
    under high concurrency (1000 RPS).
    """
    
    def __init__(
        self,
        dsn: Optional[str] = None,
        host: str = "localhost",
        port: int = 5432,
        database: str = "mlops",
        user: str = "postgres",
        password: str = "",
        min_size: int = 5,
        max_size: int = 20,
    ):
        """
        Initialize database pool configuration.
        
        Args:
            dsn: Full connection string (overrides individual params)
            min_size: Minimum connections to maintain
            max_size: Maximum connections allowed
        """
        self.dsn = dsn or f"postgresql://{user}:{password}@{host}:{port}/{database}"
        self.min_size = min_size
        self.max_size = max_size
        self._pool = None
    
    async def connect(self) -> None:
        """Create the connection pool."""
        try:
            import asyncpg
            
            self._pool = await asyncpg.create_pool(
                self.dsn,
                min_size=self.min_size,
                max_size=self.max_size,
                command_timeout=30,
            )
            
            # Validate connection
            async with self._pool.acquire() as conn:
                version = await conn.fetchval("SELECT version()")
                print(f"[DB] Connected to PostgreSQL: {version[:50]}...")
                
        except ImportError:
            print("[DB] ⚠️ asyncpg not installed. Database disabled.")
            self._pool = None
            
        except Exception as e:
            print(f"[DB] ⚠️ Connection failed: {e}")
            self._pool = None
    
    async def disconnect(self) -> None:
        """Close all connections."""
        if self._pool:
            await self._pool.close()
            print("[DB] Connection pool closed")
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row."""
        if not self._pool:
            return None
        
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        if not self._pool:
            return []
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query (INSERT, UPDATE, DELETE)."""
        if not self._pool:
            return "SKIPPED"
        
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_features(
        self,
        entity_id: str,
        feature_table: str = "features",
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch features for inference.
        
        Optimized query for single-entity feature lookup.
        """
        query = f"""
            SELECT * FROM {feature_table}
            WHERE entity_id = $1
            ORDER BY created_at DESC
            LIMIT 1
        """
        return await self.fetch_one(query, entity_id)
    
    @asynccontextmanager
    async def transaction(self):
        """Context manager for transactions."""
        if not self._pool:
            yield None
            return
        
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                yield conn


# Global pool instance
_DB_POOL: Optional[AsyncDatabasePool] = None


async def get_db() -> AsyncDatabasePool:
    """Get the global database pool."""
    if _DB_POOL is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _DB_POOL


async def init_database(
    dsn: Optional[str] = None,
    min_size: int = 5,
    max_size: int = 20,
) -> AsyncDatabasePool:
    """Initialize database pool on app startup."""
    global _DB_POOL
    
    dsn = dsn or os.environ.get(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mlops"
    )
    
    _DB_POOL = AsyncDatabasePool(
        dsn=dsn,
        min_size=min_size,
        max_size=max_size,
    )
    await _DB_POOL.connect()
    return _DB_POOL


async def close_database() -> None:
    """Close database on app shutdown."""
    if _DB_POOL:
        await _DB_POOL.disconnect()


if __name__ == '__main__':
    import asyncio
    
    async def test():
        db = AsyncDatabasePool(
            host="localhost",
            database="test",
            user="postgres",
            password="postgres",
        )
        await db.connect()
        
        result = await db.fetch_one("SELECT 1 as test")
        print(f"Query result: {result}")
        
        await db.disconnect()
    
    asyncio.run(test())
