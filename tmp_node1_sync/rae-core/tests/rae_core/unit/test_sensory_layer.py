from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest

from rae_core.layers.sensory import SensoryLayer
from rae_core.models.memory import MemoryLayer


@pytest.fixture
def sensory_layer(mock_memory_storage):
    return SensoryLayer(
        storage=mock_memory_storage,
        tenant_id="test_tenant",
        agent_id="test_agent",
        default_ttl_seconds=60,
        max_capacity=5,
    )


@pytest.mark.asyncio
async def test_add_memory_defaults(sensory_layer):
    """Test adding memory with default TTL."""
    content = "Test content"
    memory_id = await sensory_layer.add_memory(content)

    assert isinstance(memory_id, UUID)

    memory = await sensory_layer.get_memory(memory_id)
    assert memory is not None
    assert memory.content == content
    assert memory.layer == MemoryLayer.SENSORY
    assert memory.importance == 0.1  # Default for sensory
    assert memory.expires_at is not None
    # Check if expiration is roughly 60 seconds from now
    now = datetime.now(timezone.utc)
    assert (memory.expires_at - now).total_seconds() > 50


@pytest.mark.asyncio
async def test_add_memory_custom_ttl(sensory_layer):
    """Test adding memory with custom TTL."""
    content = "Quick content"
    ttl = 10
    memory_id = await sensory_layer.add_memory(content, ttl_seconds=ttl)

    memory = await sensory_layer.get_memory(memory_id)
    now = datetime.now(timezone.utc)
    # Expiration should be roughly 10 seconds from now
    diff = (memory.expires_at - now).total_seconds()
    assert 5 < diff < 15


@pytest.mark.asyncio
async def test_get_memory_expired(sensory_layer):
    """Test getting an expired memory removes it."""
    # Add memory with negative TTL (expired 10 seconds ago)
    memory_id = await sensory_layer.add_memory("Old content", ttl_seconds=-10)

    # Try to get it - should trigger expiration check and return None
    memory = await sensory_layer.get_memory(memory_id)
    assert memory is None

    # Verify it's gone from storage
    # We can use the storage directly to check
    storage_memory = await sensory_layer.storage.get_memory(memory_id, "test_tenant")
    assert storage_memory is None


@pytest.mark.asyncio
async def test_cleanup(sensory_layer):
    """Test manual cleanup of expired memories."""
    # Add valid memory
    await sensory_layer.add_memory("Valid 1", ttl_seconds=60)

    # Add expired memories
    await sensory_layer.add_memory("Expired 1", ttl_seconds=-10)
    await sensory_layer.add_memory("Expired 2", ttl_seconds=-20)

    # Verify count before cleanup (3 memories in storage)
    count = await sensory_layer.storage.count_memories(
        "test_tenant", "test_agent", "sensory"
    )
    assert count == 3

    # Run cleanup
    deleted = await sensory_layer.cleanup()
    assert deleted == 2

    # Verify count after cleanup
    count = await sensory_layer.storage.count_memories(
        "test_tenant", "test_agent", "sensory"
    )
    assert count == 1


@pytest.mark.asyncio
async def test_search_memories(sensory_layer):
    """Test searching memories excludes expired ones."""
    await sensory_layer.add_memory("Apple pie recipe", ttl_seconds=60)
    await sensory_layer.add_memory("Apple juice (expired)", ttl_seconds=-10)

    results = await sensory_layer.search_memories("Apple")

    assert len(results) == 1
    assert results[0].memory.content == "Apple pie recipe"


@pytest.mark.asyncio
async def test_capacity_limit(sensory_layer):
    """Test that capacity limit triggers cleanup."""
    # Capacity is 5
    # Add 3 valid memories
    for i in range(3):
        await sensory_layer.add_memory(f"Valid {i}", ttl_seconds=60)

    # Add 3 expired memories
    for i in range(3):
        await sensory_layer.add_memory(f"Expired {i}", ttl_seconds=-10)

    # Total added: 6. Capacity: 5.
    # The last add should have triggered cleanup because count (6) > capacity (5)

    # Verify cleanup happened automatically
    # Expired ones should be gone. Valid ones should remain.
    count = await sensory_layer.storage.count_memories(
        "test_tenant", "test_agent", "sensory"
    )
    assert count == 3  # Only the 3 valid ones remain


@pytest.mark.asyncio
async def test_extend_ttl(sensory_layer):
    """Test extending TTL of a memory."""
    memory_id = await sensory_layer.add_memory("Content", ttl_seconds=60)
    memory = await sensory_layer.get_memory(memory_id)
    original_expires = memory.expires_at

    # Extend by 3600 seconds
    success = await sensory_layer.extend_ttl(memory_id, 3600)
    assert success is True

    updated_memory = await sensory_layer.get_memory(memory_id)
    assert updated_memory.expires_at > original_expires + timedelta(seconds=3500)
