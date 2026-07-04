import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.memory_api.main import app
from apps.memory_api.security import auth

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def mock_env_and_settings(monkeypatch):
    envs = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_DB": "test_rae",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "postgres",
        "QDRANT_HOST": "localhost",
        "REDIS_URL": "redis://localhost:6379/0",
        "RAE_LLM_BACKEND": "openai",
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY") or "sk-test-key",
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY") or "sk-ant-test-key",
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY") or "gemini-test-key",
        "API_KEY": "test-api-key",
        "OAUTH_ENABLED": "False",
        "LOG_LEVEL": "INFO",
        "RAE_APP_LOG_LEVEL": "INFO",
        "ENABLE_API_KEY_AUTH": "False",
        "ENABLE_JWT_AUTH": "False",
        "ENABLE_RATE_LIMITING": "False",
        "RAE_DB_MODE": "migrate",
    }
    for k, v in envs.items():
        monkeypatch.setenv(k, v)

    from importlib import reload

    from apps.memory_api import config

    # Reload the config module to ensure settings are re-evaluated with mocked envs
    # This is crucial for Pydantic BaseSettings which load from env at import time
    config = reload(config)

    # Now, explicitly set the settings object in the config module to the newly instantiated one
    # This will ensure all modules importing 'settings' will get this updated instance
    monkeypatch.setattr(config, "settings", config.Settings())

    yield config.settings


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[auth.verify_api_key] = lambda: "test-api-key"
    app.dependency_overrides[auth.verify_token] = lambda: {
        "sub": "test-user",
        "scope": "admin",
    }
    yield
    app.dependency_overrides = {}


@pytest.fixture
def mock_app_state_pool():
    mock_pool = MagicMock()
    mock_pool.fetch = AsyncMock()
    mock_pool.fetchrow = AsyncMock()
    mock_pool.execute = AsyncMock()
    mock_pool.close = AsyncMock()

    mock_conn = MagicMock()
    mock_conn.fetchrow = AsyncMock()
    mock_conn.fetch = AsyncMock()
    mock_conn.fetchval = AsyncMock()
    mock_conn.execute = AsyncMock()

    mock_transaction_cm = AsyncMock()
    mock_transaction_cm.__aenter__.return_value = None
    mock_transaction_cm.__aexit__.return_value = None
    mock_conn.transaction.return_value = mock_transaction_cm

    mock_acquire_cm = AsyncMock()
    mock_acquire_cm.__aenter__.return_value = mock_conn
    mock_acquire_cm.__aexit__.return_value = None

    mock_pool.acquire.return_value = mock_acquire_cm

    app.state.pool = mock_pool
    yield mock_pool
    del app.state.pool


class DummyAsyncContextManager:
    """Helper class for mocking async context managers."""

    def __init__(self, value: Any):
        self._value = value

    def __await__(self):
        async def _impl():
            return self

        return _impl().__await__()

    async def __aenter__(self):
        return self._value

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def mock_pool():
    """Mock asyncpg connection pool."""
    pool = MagicMock()
    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.execute = AsyncMock(return_value="INSERT 0 1")
    conn.transaction = MagicMock(return_value=DummyAsyncContextManager(None))
    context_manager = DummyAsyncContextManager(conn)
    pool.acquire = MagicMock(return_value=context_manager)
    pool.close = AsyncMock()
    pool._test_conn = conn
    return pool


@pytest.fixture
def mock_rae_service(mock_pool):
    """Mock for RAECoreService."""
    from apps.memory_api.services.rae_core_service import RAECoreService

    service = AsyncMock(spec=RAECoreService)

    # Mock the 'db' property to return an actual provider wrapping our mock pool
    from rae_adapters.postgres_db import PostgresDatabaseProvider

    service.db = PostgresDatabaseProvider(mock_pool)

    # Mock enhanced_graph_repo property
    service.enhanced_graph_repo = AsyncMock()

    # Setup store_memory return
    service.store_memory.return_value = "test-memory-id"

    # Setup delete_memory return
    service.delete_memory.return_value = True

    # Setup list_memories return
    service.list_memories.return_value = []

    # Setup count_memories return
    service.count_memories.return_value = 10

    # Setup get_metric_aggregate return
    service.get_metric_aggregate.return_value = 0.7

    # Setup update_memory_access_batch
    service.update_memory_access_batch.return_value = 1

    return service


@pytest.fixture
def mock_embedding_service():
    """Mock for EmbeddingService."""
    service = MagicMock()
    service.generate_embeddings.return_value = [[0.1] * 384]
    service.generate_embeddings_async = AsyncMock(return_value=[[0.1] * 384])
    return service


@pytest.fixture
def mock_vector_store():
    """Mock for VectorStore."""
    store = AsyncMock()
    store.upsert.return_value = None
    store.delete.return_value = None
    store.query.return_value = []
    return store


@pytest.fixture
def client_with_overrides(
    mock_pool, mock_rae_service, mock_embedding_service, mock_vector_store
):
    """
    Test client with all necessary overrides for memory endpoints.
    """
    from fastapi.testclient import TestClient

    from apps.memory_api.dependencies import get_qdrant_client, get_rae_core_service
    from apps.memory_api.security.dependencies import get_and_verify_tenant_id

    # Setup mock pool
    app.state.pool = mock_pool

    # Override auth
    async def _mock_tenant():
        return "test-tenant"

    # Setup dependency overrides
    app.dependency_overrides[get_and_verify_tenant_id] = _mock_tenant
    app.dependency_overrides[get_rae_core_service] = lambda: mock_rae_service

    # Mock Qdrant client
    mock_qdrant = AsyncMock()
    mock_health = MagicMock()
    mock_health.status = "ok"
    mock_qdrant.health_check = AsyncMock(return_value=mock_health)
    app.dependency_overrides[get_qdrant_client] = lambda: mock_qdrant

    # Patch services obtained via functions (not DI in older parts)
    with (
        patch(
            "apps.memory_api.api.v1.memory.get_vector_store",
            return_value=mock_vector_store,
        ),
        patch(
            "rae_adapters.infra_factory.asyncpg.create_pool",
            new=AsyncMock(return_value=mock_pool),
        ),
        patch("apps.memory_api.main.rebuild_full_cache", new=AsyncMock()),
        patch(
            "apps.memory_api.services.pii_scrubber.scrub_text",
            side_effect=lambda x: x,  # Bypass PII scrubbing
        ),
    ):
        with TestClient(app) as client:
            yield client

    # Cleanup overrides
    app.dependency_overrides = {}
