import pytest

from rae_core.layers.working import WorkingLayer


@pytest.fixture
def working_layer(mock_memory_storage):
    return WorkingLayer(
        storage=mock_memory_storage,
        tenant_id="test_tenant",
        agent_id="test_agent",
        max_capacity=3,  # Small capacity for easy testing
        importance_threshold=0.5,
    )


@pytest.mark.asyncio
async def test_add_memory_capacity_eviction(working_layer):
    """Test that adding memories beyond capacity evicts the least important one."""
    # Add 3 memories (full capacity) with varying importance
    await working_layer.add_memory("High Imp", importance=0.9)
    await working_layer.add_memory("Med Imp", importance=0.7)
    await working_layer.add_memory("Low Imp", importance=0.6)

    # Verify count
    count = await working_layer.storage.count_memories(
        "test_tenant", "test_agent", "working"
    )
    assert count == 3

    # Add one more with high importance
    # The "Low Imp" (0.6) should be evicted because it's the lowest among existing.
    # Wait, 0.6 is lowest? Yes.
    await working_layer.add_memory("New High", importance=0.8)

    # Verify count is still 3 (max capacity)
    count = await working_layer.storage.count_memories(
        "test_tenant", "test_agent", "working"
    )
    assert count == 3

    # Verify "Low Imp" is gone
    memories = await working_layer.storage.list_memories(
        "test_tenant", "test_agent", "working"
    )
    contents = [m["content"] for m in memories]
    assert "Low Imp" not in contents
    assert "High Imp" in contents
    assert "Med Imp" in contents
    assert "New High" in contents


@pytest.mark.asyncio
async def test_add_memory_below_threshold(working_layer):
    """Test that adding memory below threshold bumps it to threshold."""
    # Working layer forces minimum importance
    memory_id = await working_layer.add_memory("Low importance", importance=0.1)

    memory = await working_layer.get_memory(memory_id)
    assert memory.importance == 0.5  # Bumped to threshold


@pytest.mark.asyncio
async def test_get_memory_updates_access(working_layer):
    """Test getting memory updates last_accessed_at."""
    memory_id = await working_layer.add_memory("Content")

    # Initial count should be 0
    initial = await working_layer.storage.get_memory(memory_id, "test_tenant")
    assert initial["usage_count"] == 0

    # Call get_memory (should trigger update in storage)
    await working_layer.get_memory(memory_id)

    # Verify storage was updated
    updated = await working_layer.storage.get_memory(memory_id, "test_tenant")
    assert updated["usage_count"] == 1
    assert updated["last_accessed_at"] > initial["last_accessed_at"]


@pytest.mark.asyncio
async def test_cleanup(working_layer):
    """Test cleanup of low importance memories."""
    # Bypass add_memory validation to insert low importance memory directly into storage
    await working_layer.storage.store_memory(
        content="Garbage",
        layer="working",
        tenant_id="test_tenant",
        agent_id="test_agent",
        importance=0.1,  # Below threshold 0.5
    )

    count = await working_layer.storage.count_memories(
        "test_tenant", "test_agent", "working"
    )
    assert count == 1

    # Cleanup
    deleted = await working_layer.cleanup()
    assert deleted == 1

    count = await working_layer.storage.count_memories(
        "test_tenant", "test_agent", "working"
    )
    assert count == 0


@pytest.mark.asyncio
async def test_get_capacity_status(working_layer):
    """Test capacity status reporting."""
    await working_layer.add_memory("One")
    await working_layer.add_memory("Two")

    status = await working_layer.get_capacity_status()

    assert status["current_count"] == 2
    assert status["max_capacity"] == 3
    assert status["available_slots"] == 1
    assert status["is_full"] is False
    assert status["utilization_pct"] == (2 / 3) * 100
