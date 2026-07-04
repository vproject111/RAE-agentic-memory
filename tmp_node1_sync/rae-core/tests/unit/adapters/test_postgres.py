"""Unit tests for PostgreSQLStorage adapter."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.adapters.postgres import PostgreSQLStorage


class TestPostgreSQLStorage:
    """Test suite for PostgreSQLStorage."""

    @pytest.fixture
    def mock_pool(self):
        """Create a mock asyncpg pool."""
        pool = AsyncMock()
        # acquire is not async, it returns a context manager
        pool.acquire = MagicMock()
        return pool

    @pytest.fixture
    def mock_conn(self, mock_pool):
        """Create a mock connection."""
        conn = AsyncMock()
        # Setup acquire context manager
        mock_pool.acquire.return_value.__aenter__.return_value = conn
        return conn

    @pytest.fixture
    def pg_storage(self, mock_pool):
        """Create PostgreSQLStorage instance with mock pool."""
        # Patch asyncpg to avoid import errors
        with patch("rae_core.adapters.postgres.asyncpg") as mock_asyncpg:
            mock_asyncpg.create_pool.return_value = mock_pool

            storage = PostgreSQLStorage(
                dsn="postgresql://localhost/test", pool=mock_pool
            )
            return storage

    @pytest.mark.asyncio
    async def test_store_memory(self, pg_storage, mock_conn):
        """Test storing a memory."""
        mock_conn.execute.return_value = "INSERT 0 1"

        memory_id = await pg_storage.store_memory(
            content="test", layer="working", tenant_id="tenant1", agent_id="agent1"
        )

        assert memory_id is not None
        mock_conn.execute.assert_called_once()
        args = mock_conn.execute.call_args[0]
        assert args[1] == memory_id  # id matches
        assert args[2] == "test"  # content
        assert args[4] == "tenant1"  # tenant_id

    @pytest.mark.asyncio
    async def test_get_memory(self, pg_storage, mock_conn):
        """Test retrieving a memory."""
        memory_id = uuid4()
        now = datetime.now(timezone.utc)

        mock_conn.fetchrow.return_value = {
            "id": memory_id,
            "content": "test",
            "layer": "working",
            "tenant_id": "tenant1",
            "agent_id": "agent1",
            "tags": ["tag1"],
            "metadata": {"key": "val"},
            "embedding": [0.1, 0.2],
            "importance": 0.5,
            "usage_count": 0,
            "created_at": now,
            "last_accessed_at": now,
            "expires_at": None,
        }

        memory = await pg_storage.get_memory(memory_id, "tenant1")

        assert memory is not None
        assert memory["id"] == memory_id
        assert memory["content"] == "test"
        mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, pg_storage, mock_conn):
        """Test retrieving non-existent memory."""
        mock_conn.fetchrow.return_value = None

        memory = await pg_storage.get_memory(uuid4(), "tenant1")
        assert memory is None

    @pytest.mark.asyncio
    async def test_search_memories(self, pg_storage, mock_conn):
        """Test searching memories."""
        now = datetime.now(timezone.utc)
        memory_id = uuid4()

        mock_conn.fetch.return_value = [
            {
                "id": memory_id,
                "content": "test",
                "layer": "working",
                "tenant_id": "tenant1",
                "agent_id": "agent1",
                "tags": [],
                "metadata": {},
                "embedding": None,
                "importance": 0.5,
                "usage_count": 0,
                "created_at": now,
                "last_accessed_at": now,
                "expires_at": None,
                "score": 1.0,
            }
        ]

        results = await pg_storage.search_memories(
            query="test", tenant_id="tenant1", agent_id="agent1", layer="working"
        )

        assert len(results) == 1
        assert results[0]["memory"]["content"] == "test"
        assert results[0]["score"] == 1.0

    @pytest.mark.asyncio
    async def test_list_memories(self, pg_storage, mock_conn):
        """Test listing memories."""
        mock_conn.fetch.return_value = []

        results = await pg_storage.list_memories(
            tenant_id="tenant1", agent_id="agent1", layer="working"
        )

        assert results == []
        mock_conn.fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_memory(self, pg_storage, mock_conn):
        """Test updating memory."""
        mock_conn.execute.return_value = "UPDATE 1"

        result = await pg_storage.update_memory(
            memory_id=uuid4(), tenant_id="tenant1", updates={"content": "new"}
        )

        assert result is True
        mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_memory_fail(self, pg_storage, mock_conn):
        """Test updating memory fails."""
        mock_conn.execute.return_value = "UPDATE 0"

        result = await pg_storage.update_memory(
            memory_id=uuid4(), tenant_id="tenant1", updates={"content": "new"}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_memory(self, pg_storage, mock_conn):
        """Test deleting memory."""
        mock_conn.execute.return_value = "DELETE 1"

        result = await pg_storage.delete_memory(uuid4(), "tenant1")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_expired(self, pg_storage, mock_conn):
        """Test deleting expired memories."""
        mock_conn.execute.return_value = "DELETE 5"

        count = await pg_storage.delete_expired_memories("tenant1", "agent1", "working")
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_memories(self, pg_storage, mock_conn):
        """Test counting memories."""
        mock_conn.fetchval.return_value = 10

        count = await pg_storage.count_memories("tenant1", "agent1", "working")
        assert count == 10
