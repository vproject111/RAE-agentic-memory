from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.adapters.sqlite.graph import SQLiteGraphStore
from rae_core.adapters.sqlite.storage import SQLiteStorage
from rae_core.adapters.sqlite.vector import SQLiteVectorStore


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.mark.asyncio
async def test_sqlite_graph_extra(db_path):
    adapter = SQLiteGraphStore(db_path)
    await adapter.initialize()

    mock_db = AsyncMock()
    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[])
    mock_db.execute.return_value = mock_cursor

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock()

    # Test with edge_type
    await adapter.get_neighbors(uuid4(), "t1", edge_type="friend")

    with patch("aiosqlite.connect", return_value=mock_ctx):
        # Trigger exception inside create_node's try-except
        mock_db.execute.side_effect = Exception("Error")
        assert await adapter.create_node(uuid4(), "type", "t1") is False

        # We don't test delete_node/edge here because they don't have try-except
        # and our mock configuration returns None which fails the assert


@pytest.mark.asyncio
async def test_sqlite_storage_extra(db_path):
    storage = SQLiteStorage(db_path)
    await storage.initialize()

    mid = await storage.store_memory("c", "l", "t", "a", expires_at="tomorrow")
    await storage.update_memory(mid, "t", {"tags": ["t1"], "metadata": {"m": 1}})

    # search_memories with empty query
    assert await storage.search_memories("", "t1", "a1", "l1") == []

    # update_memory_expiration without isoformat
    await storage.update_memory_expiration(mid, "t", "next week")

    # get_metric_aggregate with filters
    await storage.get_metric_aggregate("t", "importance", "avg", filters={"key": "val"})

    # update_memory_access (661-674)
    assert await storage.update_memory_access(mid, "t") is True

    # delete_memories_with_metadata_filter no matches (538)
    assert (
        await storage.delete_memories_with_metadata_filter(
            "t", "a", "l", {"nonexistent": 1}
        )
        == 0
    )


@pytest.mark.asyncio
async def test_sqlite_vector_extra(db_path):
    store = SQLiteVectorStore(db_path)
    await store.initialize()

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=Exception("Error"))
    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
    mock_ctx.__aexit__ = AsyncMock()

    with patch("aiosqlite.connect", return_value=mock_ctx):
        res = await store.batch_store_vectors([(uuid4(), [0.1], {})], "t1")
        assert res == 0
