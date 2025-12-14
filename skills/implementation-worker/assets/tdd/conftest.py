"""
TDD Fixtures - conftest.py

This module provides pytest fixtures using Testcontainers for
integration testing with real PostgreSQL and Redis instances.

The Iron Law of TDD:
    Tests must run against real infrastructure, not mocks.
    Testcontainers provides ephemeral, hermetic environments.

Usage:
    def test_feature_insertion(postgres_session):
        # postgres_session is a real SQLAlchemy session
        # connected to an ephemeral PostgreSQL container
        pass
"""

import pytest
from datetime import datetime, timezone
from typing import Generator
from uuid import uuid4

# These imports are conditional - only used when running tests
try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    PostgresContainer = None
    RedisContainer = None

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker, Session
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Skip markers for missing dependencies
requires_testcontainers = pytest.mark.skipif(
    not TESTCONTAINERS_AVAILABLE,
    reason="testcontainers not installed"
)

requires_sqlalchemy = pytest.mark.skipif(
    not SQLALCHEMY_AVAILABLE,
    reason="sqlalchemy not installed"
)

requires_redis = pytest.mark.skipif(
    not REDIS_AVAILABLE,
    reason="redis not installed"
)


@pytest.fixture(scope="session")
def postgres_container():
    """
    Spin up a PostgreSQL container for the test session.
    
    The container is automatically destroyed when tests complete.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")
    
    container = PostgresContainer(
        image="postgres:15-alpine",
        user="test",
        password="test",
        dbname="test_db"
    )
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture(scope="session")
def postgres_engine(postgres_container):
    """Create SQLAlchemy engine connected to the test container."""
    if not SQLALCHEMY_AVAILABLE:
        pytest.skip("sqlalchemy not available")
    
    connection_url = postgres_container.get_connection_url()
    engine = create_engine(connection_url)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def postgres_session(postgres_engine) -> Generator[Session, None, None]:
    """
    Provide a transactional session for each test.
    
    Changes are rolled back after each test for isolation.
    """
    # Import Base here to avoid circular imports
    # In real usage, import from schemas module
    from sqlalchemy.orm import DeclarativeBase
    
    class Base(DeclarativeBase):
        pass
    
    # Create tables
    Base.metadata.create_all(postgres_engine)
    
    # Create session
    SessionLocal = sessionmaker(bind=postgres_engine)
    session = SessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def redis_container():
    """Spin up a Redis container for the test session."""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")
    
    container = RedisContainer(image="redis:7-alpine")
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture(scope="function")
def redis_client(redis_container):
    """Provide a Redis client connected to the test container."""
    if not REDIS_AVAILABLE:
        pytest.skip("redis not available")
    
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    
    client = redis.Redis(host=host, port=int(port), db=0)
    
    yield client
    
    # Clean up after each test
    client.flushdb()
    client.close()


# Sample data fixtures
@pytest.fixture
def sample_feature_data():
    """Provide sample feature data for testing."""
    return {
        "entity_id": uuid4(),
        "entity_type": "user",
        "event_timestamp": datetime.now(timezone.utc),
        "country_code": "USA",
        "segment": "high_value",
        "dynamic_features": {
            "last_login_days": 3,
            "purchase_count": 15,
            "cart_value": 249.99
        }
    }


@pytest.fixture
def sample_feature_batch():
    """Provide a batch of sample features."""
    now = datetime.now(timezone.utc)
    return [
        {
            "entity_id": uuid4(),
            "entity_type": "user",
            "event_timestamp": now,
            "segment": f"segment_{i}",
            "dynamic_features": {"score": i * 0.1}
        }
        for i in range(10)
    ]


# Mock H2O fixture for unit testing
@pytest.fixture
def mock_h2o_model():
    """
    Provide a mock H2O model for unit testing.
    
    This allows testing prediction logic without H2O cluster.
    """
    class MockH2OModel:
        def __init__(self):
            self.model_id = "mock_model_001"
            self.predict_calls = []
        
        def predict(self, data):
            self.predict_calls.append(data)
            # Return mock predictions
            return {"predict": [0.75], "p0": [0.25], "p1": [0.75]}
        
        def download_mojo(self, path):
            # Create a mock MOJO file
            with open(f"{path}/mock_model.mojo", "wb") as f:
                f.write(b"MOCK_MOJO_CONTENT")
            return f"{path}/mock_model.mojo"
    
    return MockH2OModel()


# Async fixtures for FastAPI testing
@pytest.fixture
def async_client():
    """
    Provide an async HTTP client for testing FastAPI endpoints.
    
    Usage:
        async def test_predict(async_client):
            response = await async_client.post("/predict", json={...})
            assert response.status_code == 200
    """
    try:
        from httpx import AsyncClient
    except ImportError:
        pytest.skip("httpx not available")
    
    # Note: In real tests, import app from your FastAPI module
    # from app.main import app
    # return AsyncClient(app=app, base_url="http://test")
    
    return AsyncClient(base_url="http://test")
