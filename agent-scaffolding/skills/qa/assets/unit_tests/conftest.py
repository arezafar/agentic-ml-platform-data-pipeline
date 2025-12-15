"""
QA Skill - Pytest Configuration

This conftest.py provides common fixtures for testing:
- Mage block execution context mocking
- Async database session management
- Blocking detector integration (optional)
- Transaction rollback isolation

Usage:
    Place this file in your test directory root.
    Fixtures are automatically discovered by pytest.
"""

import os
import sys
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

# Set Mage environment to 'test' before any imports
os.environ["ENV"] = "test"
os.environ["MAGE_ENV"] = "test"


# =============================================================================
# Mage Block Testing Fixtures
# =============================================================================


@pytest.fixture
def mock_global_vars() -> dict[str, Any]:
    """
    Provide mock global variables for Mage block testing.
    
    Simulates the global_vars dict passed to blocks at runtime.
    Override specific values in your tests as needed.
    """
    return {
        "env": "test",
        "target_column": "target",
        "primary_metric": "auc",
        "performance_threshold": 0.85,
        "batch_size": 1000,
        "h2o_cluster_url": "http://localhost:54321",
    }


@pytest.fixture
def mock_kwargs() -> dict[str, Any]:
    """
    Provide mock kwargs for Mage block testing.
    
    Simulates the kwargs dict containing upstream block outputs.
    """
    return {
        "execution_date": "2024-01-15",
        "pipeline_uuid": "test-pipeline",
        "block_uuid": "test-block",
    }


@pytest.fixture
def mock_mage_context(mock_global_vars: dict, mock_kwargs: dict) -> dict[str, Any]:
    """
    Combined Mage execution context for block testing.
    """
    return {
        "global_vars": mock_global_vars,
        "kwargs": mock_kwargs,
    }


# =============================================================================
# Database Testing Fixtures
# =============================================================================


@pytest.fixture
def mock_db_session() -> Generator[MagicMock, None, None]:
    """
    Provide a mock synchronous database session.
    
    Use for testing blocks that don't require real DB connectivity.
    """
    session = MagicMock()
    session.execute = MagicMock(return_value=MagicMock(fetchall=lambda: []))
    session.commit = MagicMock()
    session.rollback = MagicMock()
    yield session


@pytest.fixture
async def async_db_session():
    """
    Provide a real async database session with transaction rollback.
    
    Requires asyncpg and a running PostgreSQL instance.
    Configure via DATABASE_URL environment variable.
    
    Example:
        export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/testdb"
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/test"
        )
        
        engine = create_async_engine(database_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        
        async with async_session() as session:
            async with session.begin():
                yield session
                # Rollback after test - ensures isolation
                await session.rollback()
                
    except ImportError:
        pytest.skip("asyncpg/SQLAlchemy not installed")


# =============================================================================
# Blocking Detection Fixtures (Optional)
# =============================================================================


@pytest.fixture(autouse=False)
def enable_blocking_detection():
    """
    Enable blocking detection for async tests.
    
    Raises BlockingError if the event loop is blocked > threshold.
    
    Usage in test:
        @pytest.mark.usefixtures("enable_blocking_detection")
        async def test_my_async_endpoint():
            ...
    
    Or enable globally by setting autouse=True.
    """
    try:
        from blockbuster import blockbuster_ctx
        
        with blockbuster_ctx(
            blocking_threshold_ms=10,  # Fail if blocked > 10ms
            raise_on_block=True,
        ):
            yield
    except ImportError:
        # blockbuster not installed, skip detection
        yield


# =============================================================================
# HTTP Client Mocking
# =============================================================================


@pytest.fixture
def mock_httpx_client() -> Generator[MagicMock, None, None]:
    """
    Mock httpx.AsyncClient for testing data loaders.
    
    Example usage:
        def test_api_loader(mock_httpx_client):
            mock_httpx_client.get.return_value = Response(200, json={"data": []})
            result = my_loader_block()
            assert result is not None
    """
    with patch("httpx.AsyncClient") as mock_client:
        instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = instance
        yield instance


@pytest.fixture
def mock_requests() -> Generator[MagicMock, None, None]:
    """
    Mock requests library for testing synchronous data loaders.
    """
    with patch("requests.get") as mock_get:
        yield mock_get


# =============================================================================
# Pandas DataFrame Fixtures
# =============================================================================


@pytest.fixture
def sample_dataframe():
    """
    Provide a sample pandas DataFrame for testing.
    """
    try:
        import pandas as pd
        
        return pd.DataFrame({
            "id": [1, 2, 3, 4, 5],
            "feature_1": [0.1, 0.2, 0.3, 0.4, 0.5],
            "feature_2": [1.0, 2.0, 3.0, 4.0, 5.0],
            "target": [0, 1, 0, 1, 0],
        })
    except ImportError:
        pytest.skip("pandas not installed")


@pytest.fixture
def sample_feature_vectors():
    """
    Provide sample feature vectors for pgvector testing.
    """
    import random
    
    # Default dimension for testing (e.g., 128 for smaller embeddings)
    dimension = int(os.getenv("MODEL_DIMENSIONS", "128"))
    
    return [
        [random.random() for _ in range(dimension)]
        for _ in range(10)
    ]


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (require external services)"
    )
    config.addinivalue_line(
        "markers", "load: Load tests (performance, long-running)"
    )
    config.addinivalue_line(
        "markers", "blocking: Tests that enable blocking detection"
    )
    config.addinivalue_line(
        "markers", "slow: Tests that take longer than usual"
    )
