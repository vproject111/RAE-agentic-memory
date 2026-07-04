"""
Tests for EnhancedGraphRepository ensuring database agnosticism.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.memory_api.repositories.graph_repository_enhanced import (
    EnhancedGraphRepository,
)
from rae_core.interfaces.database import IDatabaseProvider


class MockDatabaseProvider(IDatabaseProvider):
    def __init__(self):
        self.fetchrow_mock = AsyncMock()
        self.fetch_mock = AsyncMock()
        self.fetchval_mock = AsyncMock()
        self.execute_mock = AsyncMock()
        self.executemany_mock = AsyncMock()
        self.acquire_mock = MagicMock()
        self.close_mock = AsyncMock()

    async def fetchrow(self, query: str, *args):
        return await self.fetchrow_mock(query, *args)

    async def fetch(self, query: str, *args):
        return await self.fetch_mock(query, *args)

    async def fetchval(self, query: str, *args):
        return await self.fetchval_mock(query, *args)

    async def execute(self, query: str, *args):
        return await self.execute_mock(query, *args)

    async def executemany(self, query: str, args: list):
        return await self.executemany_mock(query, args)

    async def close(self):
        return await self.close_mock()

    def acquire(self):
        # Must return an async context manager yielding IDatabaseConnection
        conn = MagicMock()
        conn.execute = AsyncMock()
        conn.fetch = AsyncMock()
        conn.fetchrow = AsyncMock()
        conn.fetchval = AsyncMock()
        conn.executemany = AsyncMock()
        conn.transaction = MagicMock()

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=conn)
        cm.__aexit__ = AsyncMock(return_value=None)
        self.acquire_mock.return_value = cm
        return self.acquire_mock()


@pytest.fixture
def mock_db():
    return MockDatabaseProvider()


@pytest.mark.asyncio
async def test_repository_initialization_with_provider(mock_db):
    """Test that repository accepts IDatabaseProvider."""
    repo = EnhancedGraphRepository(mock_db)
    assert repo.db == mock_db
    assert not hasattr(
        repo, "pool"
    )  # Should not have pool attribute if provider passed


@pytest.mark.asyncio
async def test_create_node_uses_provider(mock_db):
    """Test that create_node uses provider methods, not asyncpg directly."""
    repo = EnhancedGraphRepository(mock_db)

    mock_db.fetchrow_mock.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "node_id": "test-node",
        "tenant_id": "tenant1",
        "project_id": "proj1",
        "label": "Test",
        "properties": {},
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }

    await repo.create_node("tenant1", "proj1", "test-node", "Test")

    assert mock_db.fetchrow_mock.called
    args = mock_db.fetchrow_mock.call_args
    assert "INSERT INTO knowledge_graph_nodes" in args[0][0]
