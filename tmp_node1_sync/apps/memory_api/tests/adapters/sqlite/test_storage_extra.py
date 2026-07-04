import pytest

from rae_adapters.sqlite.storage import SQLiteStorage


@pytest.fixture
async def storage(tmp_path):
    db_path = tmp_path / "test_rae.db"
    storage = SQLiteStorage(str(db_path))
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.mark.asyncio
async def test_sqlite_decay_importance(storage):
    """Test importance decay in SQLite storage."""
    tenant_id = "tenant-1"
    agent_id = "agent-1"

    mid1 = await storage.store_memory("c1", "l1", tenant_id, agent_id, importance=1.0)
    mid2 = await storage.store_memory("c2", "l1", tenant_id, agent_id, importance=0.5)

    # Apply decay of 0.1
    count = await storage.decay_importance(tenant_id, 0.1)
    assert count == 2

    m1 = await storage.get_memory(mid1, tenant_id)
    m2 = await storage.get_memory(mid2, tenant_id)

    assert m1["importance"] == 0.9
    assert m2["importance"] == 0.4


@pytest.mark.asyncio
async def test_sqlite_decay_importance_with_access_stats(storage):
    """Test importance decay with access stats in SQLite."""
    tenant_id = "tenant-1"
    agent_id = "agent-1"

    mid = await storage.store_memory("c1", "l1", tenant_id, agent_id, importance=1.0)
    await storage.update_memory_access(mid, tenant_id)  # usage = 1

    # Apply decay of 0.1 with stats
    await storage.decay_importance(tenant_id, 0.1, consider_access_stats=True)

    m = await storage.get_memory(mid, tenant_id)
    # dampening = 1.0 / (1.0 + ln(1+1)) = 0.59
    # decay = 0.059
    assert 0.94 <= m["importance"] <= 0.95
