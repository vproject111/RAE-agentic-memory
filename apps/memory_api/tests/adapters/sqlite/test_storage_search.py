import pytest

from rae_adapters.sqlite.storage import SQLiteStorage


@pytest.fixture
async def sqlite_storage(tmp_path):
    db_path = tmp_path / "test_rae.db"
    storage = SQLiteStorage(str(db_path))
    await storage.initialize()
    return storage


@pytest.mark.asyncio
async def test_search_memories_fts5(sqlite_storage):
    # Setup test data
    tenant_id = "test-tenant"
    agent_id = "test-agent"

    await sqlite_storage.store_memory(
        content="The quick brown fox jumps over the lazy dog",
        layer="episodic",
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    await sqlite_storage.store_memory(
        content="Machine learning is a subset of artificial intelligence",
        layer="episodic",
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    # Test search 1: exact word
    results = await sqlite_storage.search_memories(
        query="fox", tenant_id=tenant_id, agent_id=agent_id, layer="episodic"
    )
    assert len(results) == 1
    assert "fox" in results[0]["memory"]["content"]

    # Test search 2: multiple words (FTS5)
    results = await sqlite_storage.search_memories(
        query="machine learning",
        tenant_id=tenant_id,
        agent_id=agent_id,
        layer="episodic",
    )
    assert len(results) == 1
    assert "intelligence" in results[0]["memory"]["content"]

    # Test search 3: no results
    results = await sqlite_storage.search_memories(
        query="nonexistent", tenant_id=tenant_id, agent_id=agent_id, layer="episodic"
    )
    assert len(results) == 0
