"""
Dependency Injection Module

Provides shared dependencies for FastAPI routes including:
- Database connection pooling
- MOJO scorer instance
- Configuration management
"""

import os
from functools import lru_cache
from typing import Optional

import asyncpg


# =============================================================================
# CONFIGURATION
# =============================================================================

class Settings:
    """Application settings from environment variables."""
    
    # Database
    DB_HOST: str = os.environ.get('DB_HOST', 'localhost')
    DB_PORT: int = int(os.environ.get('DB_PORT', 5432))
    DB_NAME: str = os.environ.get('DB_NAME', 'agentic_ml')
    DB_USER: str = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD: str = os.environ.get('DB_PASSWORD', '')
    DB_MIN_CONNECTIONS: int = int(os.environ.get('DB_MIN_CONNECTIONS', 5))
    DB_MAX_CONNECTIONS: int = int(os.environ.get('DB_MAX_CONNECTIONS', 20))
    
    # MOJO
    MOJO_PATH: str = os.environ.get('MOJO_PATH', './models/model.zip')
    GENMODEL_JAR: str = os.environ.get('GENMODEL_JAR', './models/h2o-genmodel.jar')
    
    # API
    API_PREFIX: str = '/api/v1'
    DEBUG: bool = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# =============================================================================
# DATABASE
# =============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """Create and return database connection pool.
    
    Returns:
        asyncpg connection pool
    """
    settings = get_settings()
    
    pool = await asyncpg.create_pool(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        min_size=settings.DB_MIN_CONNECTIONS,
        max_size=settings.DB_MAX_CONNECTIONS,
    )
    
    return pool


async def get_db_connection(pool: asyncpg.Pool) -> asyncpg.Connection:
    """Get a database connection from the pool.
    
    Args:
        pool: Database connection pool
        
    Yields:
        Database connection
    """
    async with pool.acquire() as connection:
        yield connection


# =============================================================================
# MOJO SCORER
# =============================================================================

class MojoScorer:
    """Wrapper for H2O MOJO scoring.
    
    Note: This requires h2o-genmodel.jar and a MOJO file.
    For production, consider using H2O's REST scoring service.
    """
    
    def __init__(self, mojo_path: str, genmodel_jar: str):
        self.mojo_path = mojo_path
        self.genmodel_jar = genmodel_jar
        self._model = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load MOJO model using py4j or subprocess."""
        # Note: Full implementation requires Java bridge
        # This is a placeholder for the scoring interface
        import os
        if not os.path.exists(self.mojo_path):
            raise FileNotFoundError(f"MOJO not found: {self.mojo_path}")
    
    def predict(self, features: dict) -> dict:
        """Make prediction using MOJO model.
        
        Args:
            features: Dictionary of feature name -> value
            
        Returns:
            Prediction result dictionary
        """
        # Placeholder implementation
        # Real implementation would use h2o-genmodel or REST API
        return {
            'prediction': 0.0,
            'probability': [0.5, 0.5],
            'model_id': 'placeholder',
        }


def get_mojo_scorer() -> Optional[MojoScorer]:
    """Get MOJO scorer instance.
    
    Returns:
        MojoScorer instance or None if not configured
    """
    settings = get_settings()
    
    try:
        return MojoScorer(
            mojo_path=settings.MOJO_PATH,
            genmodel_jar=settings.GENMODEL_JAR,
        )
    except Exception:
        return None
