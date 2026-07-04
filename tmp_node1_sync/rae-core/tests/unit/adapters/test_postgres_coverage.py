"""Unit tests for PostgreSQLStorage to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.adapters.postgres import PostgreSQLStorage


class TestPostgreSQLStorageCoverage:
    """Test suite for PostgreSQLStorage coverage gaps."""

    @pytest.mark.asyncio
    async def test_init_no_asyncpg(self):
        """Test initialization when asyncpg is not available."""
        with patch("rae_core.adapters.postgres.asyncpg", None):
            with pytest.raises(ImportError, match="asyncpg is required"):
                PostgreSQLStorage(dsn="test")

    @pytest.mark.asyncio
    async def test_get_pool_no_dsn_or_pool(self):
        """Test _get_pool raises error when no dsn or pool provided."""
        # Patch asyncpg to avoid import error
        with patch("rae_core.adapters.postgres.asyncpg", MagicMock()):
            storage = PostgreSQLStorage()
            with pytest.raises(ValueError, match="Either dsn or pool must be provided"):
                await storage._get_pool()

    @pytest.mark.asyncio
    async def test_close_with_pool(self):
        """Test close method actually closes the pool."""
        mock_pool = AsyncMock()
        with patch("rae_core.adapters.postgres.asyncpg", MagicMock()):
            storage = PostgreSQLStorage(pool=mock_pool)
            await storage.close()
            mock_pool.close.assert_called_once()
            assert storage._pool is None

    @pytest.mark.asyncio
    async def test_list_memories_with_many_filters(self):
        """Test list_memories with since, min_importance, and memory_ids filters."""
        mock_pool = MagicMock()  # Changed to MagicMock for acquire
        conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []

        with patch("rae_core.adapters.postgres.asyncpg", MagicMock()):
            storage = PostgreSQLStorage(pool=mock_pool)
            from datetime import datetime, timezone

            since = datetime.now(timezone.utc)
            ids = [uuid4()]

            await storage.list_memories(
                tenant_id="t1",
                filters={"since": since, "min_importance": 0.8, "memory_ids": ids},
            )

            query = conn.fetch.call_args[0][0]
            assert "created_at >= $2" in query
            assert "importance >= $3" in query
            assert "id = ANY($4::uuid[])" in query

    @pytest.mark.asyncio
    async def test_search_memories_no_agent_or_layer(self):
        """Test search_memories with minimal required filters."""
        mock_pool = MagicMock()
        conn = AsyncMock()
        mock_pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetch.return_value = []

        with patch("rae_core.adapters.postgres.asyncpg", MagicMock()):
            storage = PostgreSQLStorage(pool=mock_pool)
            # search_memories requires agent_id and layer
            await storage.search_memories(
                "query", tenant_id="t1", agent_id="a1", layer="l1"
            )

            query = conn.fetch.call_args[0][0]
            # When agent_id and layer are provided, tenant_id is $1
            assert "tenant_id = $1" in query
            assert "agent_id = $2" in query
            assert "layer = $3" in query

    @pytest.mark.asyncio
    async def test_update_memory_no_updates(self):
        """Test update_memory with empty updates dictionary."""
        mock_pool = MagicMock()
        with patch("rae_core.adapters.postgres.asyncpg", MagicMock()):
            storage = PostgreSQLStorage(pool=mock_pool)
            # update_memory returns False if no valid set_clauses built
            res = await storage.update_memory(uuid4(), "t1", {})
            assert res is False
            assert mock_pool.acquire.call_count == 0

    @pytest.mark.asyncio
    async def test_get_pool_lazy_init(self):
        """Test lazy initialization of the connection pool."""
        with patch("rae_core.adapters.postgres.asyncpg") as mock_asyncpg:
            mock_pool = MagicMock()
            mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

            storage = PostgreSQLStorage(dsn="postgresql://localhost/test")
            assert storage._pool is None

            pool = await storage._get_pool()
            assert pool == mock_pool
            assert storage._pool == mock_pool
            mock_asyncpg.create_pool.assert_called_once_with(
                "postgresql://localhost/test"
            )
