from uuid import UUID

import pytest

from rae_core.layers.longterm import LongTermLayer
from rae_core.models.memory import MemoryItem, MemoryLayer


@pytest.fixture
def longterm_layer(mock_memory_storage):
    return LongTermLayer(
        storage=mock_memory_storage,
        tenant_id="test_tenant",
        agent_id="test_agent",
    )


@pytest.mark.asyncio
async def test_add_memory_types(longterm_layer):
    """Test adding episodic and semantic memories."""
    # Add episodic (default)
    ep_id = await longterm_layer.add_memory("Episodic content", is_semantic=False)
    ep_mem = await longterm_layer.get_memory(ep_id)
    assert ep_mem.layer == MemoryLayer.EPISODIC
    assert ep_mem.metadata["is_semantic"] is False
    assert ep_mem.importance == 0.5  # Default episodic

    # Add semantic
    sem_id = await longterm_layer.add_memory("Semantic fact", is_semantic=True)
    sem_mem = await longterm_layer.get_memory(sem_id)
    assert sem_mem.layer == MemoryLayer.SEMANTIC
    assert sem_mem.metadata["is_semantic"] is True
    assert sem_mem.importance == 0.7  # Default semantic


@pytest.mark.asyncio
async def test_search_filtering(longterm_layer):
    """Test searching with layer filtering."""
    await longterm_layer.add_memory("Apple pie event", is_semantic=False)
    await longterm_layer.add_memory("Apple definition", is_semantic=True)

    # Search all
    all_results = await longterm_layer.search_memories("Apple")
    # Note: Mock search returns everything matching "Apple"
    assert len(all_results) == 2

    # Search episodic only
    ep_results = await longterm_layer.search_memories("Apple", episodic_only=True)
    assert len(ep_results) == 1
    assert ep_results[0].memory.content == "Apple pie event"

    # Search semantic only
    sem_results = await longterm_layer.search_memories("Apple", semantic_only=True)
    assert len(sem_results) == 1
    assert sem_results[0].memory.content == "Apple definition"


@pytest.mark.asyncio
async def test_consolidate_from_working(longterm_layer):
    """Test consolidating memory from working layer."""
    working_mem = MemoryItem(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        content="Important working memory",
        layer=MemoryLayer.WORKING,
        tenant_id="test_tenant",
        agent_id="test_agent",
        importance=0.6,
        tags=["work"],
    )

    # Consolidate as episodic
    new_id = await longterm_layer.consolidate_from_working(working_mem)
    new_mem = await longterm_layer.get_memory(new_id)

    assert new_mem.content == "Important working memory"
    assert new_mem.layer == MemoryLayer.EPISODIC
    assert new_mem.importance == 0.8  # 0.6 + 0.2
    assert "work" in new_mem.tags


@pytest.mark.asyncio
async def test_upgrade_to_semantic(longterm_layer):
    """Test upgrading episodic memory to semantic."""
    ep_id = await longterm_layer.add_memory(
        "User likes Python", is_semantic=False, importance=0.6
    )

    # Upgrade
    sem_id = await longterm_layer.upgrade_to_semantic(
        ep_id, generalized_content="Python preference"
    )

    sem_mem = await longterm_layer.get_memory(sem_id)
    assert sem_mem.layer == MemoryLayer.SEMANTIC
    assert sem_mem.content == "Python preference"
    assert sem_mem.metadata["derived_from_episodic"] == str(ep_id)
    assert sem_mem.importance == 0.7  # 0.6 + 0.1


@pytest.mark.asyncio
async def test_counts(longterm_layer):
    """Test counting logic."""
    await longterm_layer.add_memory("Ep 1", is_semantic=False)
    await longterm_layer.add_memory("Ep 2", is_semantic=False)
    await longterm_layer.add_memory("Sem 1", is_semantic=True)

    assert await longterm_layer.count_episodic() == 2
    assert await longterm_layer.count_semantic() == 1
