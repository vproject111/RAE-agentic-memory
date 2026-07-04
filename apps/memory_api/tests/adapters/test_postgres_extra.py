from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_adapters.postgres import PostgreSQLStorage


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    pool.acquire = MagicMock()

    conn = MagicMock()
    conn.fetchrow = AsyncMock()
    conn.fetch = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()

    # Setup context manager for pool.acquire()
    acq_ctx = MagicMock()
    acq_ctx.__aenter__ = AsyncMock(return_value=conn)
    acq_ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire.return_value = acq_ctx

    return pool, conn


@pytest.mark.asyncio
async def test_get_memory_not_found(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.fetchrow.return_value = None
    res = await storage.get_memory(uuid4(), "t1")
    assert res is None


@pytest.mark.asyncio
async def test_list_memories_empty(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.fetch.return_value = []
    res = await storage.list_memories("t1")
    assert res == []


@pytest.mark.asyncio
async def test_list_memories_with_data(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.fetch.return_value = [
        {
            "id": uuid4(),
            "content": "c1",
            "layer": "episodic",
            "tenant_id": "t1",
            "agent_id": "a1",
            "tags": ["tag1"],
            "metadata": {},
            "embedding": None,
            "importance": 0.5,
            "usage_count": 1,
            "created_at": datetime.now(),
            "last_accessed_at": None,
            "expires_at": None,
            "project": None,
            "session_id": None,
            "source": None,
            "memory_type": "text",
            "strength": 1.0,
            "info_class": "internal",
            "governance": {},
        }
    ]

    # Test with tags filter to cover 333-335
    res = await storage.list_memories("t1", tags=["tag1"])
    assert len(res) == 1
    assert res[0]["content"] == "c1"


@pytest.mark.asyncio
async def test_decay_importance_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "UPDATE 5"
    count = await storage.decay_importance("t1", 0.1)
    assert count == 5

    # Test invalid status string
    conn.execute.return_value = "INVALID"
    count = await storage.decay_importance("t1", 0.1)
    assert count == 0

    # Test IndexError
    conn.execute.return_value = "UPDATE"
    count = await storage.decay_importance("t1", 0.1)
    assert count == 0

    # Test ValueError
    conn.execute.return_value = "UPDATE abc"
    count = await storage.decay_importance("t1", 0.1)
    assert count == 0


@pytest.mark.asyncio
async def test_save_embedding_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    # Mock existence check
    conn.fetchval.return_value = 1

    res = await storage.save_embedding(uuid4(), "model1", [0.1, 0.2], "t1")
    assert res is True
    assert conn.execute.called
    assert conn.fetchval.called  # SEC-02 check


@pytest.mark.asyncio
async def test_postgres_save_embedding_access_denied(mock_pool):
    """Test save_embedding access denial (line 927) with proper async exception handling."""
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    # Mock exists check to return None (not found)
    conn.fetchval.return_value = None

    # Try to save embedding for tenant 2 - should raise ValueError
    with pytest.raises(ValueError, match="Access Denied"):
        await storage.save_embedding(uuid4(), "model", [0.1], "t2")


@pytest.mark.asyncio
async def test_search_memories_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.fetch.return_value = [
        {
            "id": uuid4(),
            "content": "c1",
            "layer": "episodic",
            "tenant_id": "t1",
            "agent_id": "a1",
            "tags": [],
            "metadata": {},
            "embedding": None,
            "importance": 0.5,
            "usage_count": 1,
            "created_at": datetime.now(),
            "last_accessed_at": None,
            "expires_at": None,
            "score": 0.9,
            "project": None,
            "session_id": None,
            "source": None,
            "memory_type": "text",
            "strength": 1.0,
            "info_class": "internal",
            "governance": {},
        }
    ]

    res = await storage.search_memories("query", "t1", "a1", "episodic")
    assert len(res) == 1

    # Test with filters
    await storage.search_memories(
        "query",
        "t1",
        "a1",
        "episodic",
        filters={"not_expired": True, "tags": ["tag1"], "min_importance": 0.5},
    )
    assert conn.fetch.called


@pytest.mark.asyncio
async def test_update_memory_access_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "UPDATE 1"
    res = await storage.update_memory_access(uuid4(), "t1")
    assert res is True


@pytest.mark.asyncio
async def test_update_memory_expiration_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "UPDATE 1"
    res = await storage.update_memory_expiration(uuid4(), "t1", datetime.now())
    assert res is True


@pytest.mark.asyncio
async def test_get_metric_aggregate_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.fetchval.return_value = 0.75
    res = await storage.get_metric_aggregate("t1", "importance", "avg")
    assert res == 0.75

    # Test with filters
    await storage.get_metric_aggregate(
        "t1", "importance", "avg", filters={"agent_id": "a1"}
    )
    assert conn.fetchval.called


@pytest.mark.asyncio
async def test_update_memory_access_batch_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "UPDATE 2"
    res = await storage.update_memory_access_batch([uuid4(), uuid4()], "t1")
    assert res is True


@pytest.mark.asyncio
async def test_delete_expired_memories_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "DELETE 3"
    count = await storage.delete_expired_memories("t1", "a1", "episodic")
    assert count == 3


@pytest.mark.asyncio
async def test_delete_memories_below_importance_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "DELETE 4"
    count = await storage.delete_memories_below_importance("t1", "a1", "episodic", 0.3)
    assert count == 4

    # Test invalid status
    conn.execute.return_value = "INVALID"
    count = await storage.delete_memories_below_importance("t1", "a1", "episodic", 0.3)
    assert count == 0


@pytest.mark.asyncio
async def test_increment_access_count_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "UPDATE 1"
    res = await storage.increment_access_count(uuid4(), "t1")
    assert res is True


@pytest.mark.asyncio
async def test_delete_memory_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "DELETE 1"
    res = await storage.delete_memory(uuid4(), "t1")
    assert res is True


@pytest.mark.asyncio
async def test_update_memory_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    conn.execute.return_value = "UPDATE 1"
    res = await storage.update_memory(uuid4(), "t1", {"content": "new"})
    assert res is True


@pytest.mark.asyncio
async def test_delete_memories_with_metadata_filter_coverage(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool

    # Setup mock for fetch
    conn.fetch.return_value = [
        {"id": uuid4(), "metadata": {"key": "val"}},
        {"id": uuid4(), "metadata": {"num": 10}},
        {"id": uuid4(), "metadata": {"num": 20}},
    ]

    # Case where some matches
    conn.execute.return_value = "DELETE 1"
    count = await storage.delete_memories_with_metadata_filter(
        "t1", "a1", "episodic", {"key": "val"}
    )
    assert count == 1

    # Case where num__lt matches
    conn.execute.return_value = "DELETE 1"
    count = await storage.delete_memories_with_metadata_filter(
        "t1", "a1", "episodic", {"num__lt": 15}
    )
    assert count == 1

    # Case where no matches (to cover 653-654)
    count = await storage.delete_memories_with_metadata_filter(
        "t1", "a1", "episodic", {"num__lt": 5}
    )
    assert count == 0


@pytest.mark.asyncio
async def test_adjust_importance_not_found(mock_pool):
    pool, conn = mock_pool
    storage = PostgreSQLStorage(dsn="postgresql://localhost/db")
    storage._pool = pool
    conn.fetchval.return_value = None
    with pytest.raises(ValueError, match="Memory not found"):
        await storage.adjust_importance(uuid4(), 0.9, "t1")
