"""Final coverage tests for InMemoryStorage."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from rae_core.adapters.memory.storage import InMemoryStorage
from rae_core.utils.clock import IClock


class MockClock(IClock):
    def __init__(self, now_val: datetime):
        self._now = now_val

    def now(self) -> datetime:
        return self._now


@pytest.mark.asyncio
async def test_search_similar_bloom_filter_and_tags_subset():
    """Test Bloom filter and strict tag subset matching (Lines 176-178, 186-189, 209-218)."""
    storage = InMemoryStorage()

    # Store memory with tags
    mid1 = await storage.store_memory(
        tenant_id="t1", tags=["tag1", "tag2"], embedding=[1.0, 0.0]
    )
    mid2 = await storage.store_memory(
        tenant_id="t1", tags=["tag1"], embedding=[1.0, 0.0]
    )
    mid3 = await storage.store_memory(
        tenant_id="t1", tags=["tag3"], embedding=[1.0, 0.0]
    )

    # 1. Test Bloom Filter Rejection
    # Search for "tag2". mid1 has it, mid2 and mid3 don't.
    results = await storage.search_similar([1.0, 0.0], "t1", filters={"tags": ["tag2"]})
    assert len(results) == 1
    assert results[0][0] == mid1

    # 2. Test Strict Tag Subset (Line 215)
    # Search for ["tag1", "tag2"]. mid1 has both, mid2 only has tag1.
    results = await storage.search_similar(
        [1.0, 0.0], "t1", filters={"tags": ["tag1", "tag2"]}
    )
    assert len(results) == 1
    assert results[0][0] == mid1

    # Search for ["tag1"]. Both mid1 and mid2 have tag1.
    results = await storage.search_similar([1.0, 0.0], "t1", filters={"tags": ["tag1"]})
    assert len(results) == 2


@pytest.mark.asyncio
async def test_search_similar_metadata_mismatches():
    """Test metadata filter mismatches (Lines 216-217, 220-222, 224)."""
    storage = InMemoryStorage()
    mid = await storage.store_memory(
        tenant_id="t1",
        tags=["tag1"],
        embedding=[1.0, 0.0],
        metadata={"category": "science"},
    )

    # Tag subset mismatch (Line 216-217)
    results = await storage.search_similar([1.0, 0.0], "t1", filters={"tags": ["tag2"]})
    assert len(results) == 0

    # Other metadata mismatch (Line 220-222)
    results = await storage.search_similar(
        [1.0, 0.0], "t1", filters={"category": "art"}
    )
    assert len(results) == 0


@pytest.mark.asyncio
async def test_get_vector_not_found_fallback():
    """Test get_vector returning None when not found even after fallback (Line 282)."""
    storage = InMemoryStorage()
    assert await storage.get_vector(uuid4(), "t1") is None


@pytest.mark.asyncio
async def test_store_memory_dict_embedding():
    """Test store_memory with dict-based embedding (Lines 475-476)."""
    storage = InMemoryStorage()
    mid = await storage.store_memory(tenant_id="t1", embedding={"model1": [1.0, 0.0]})
    vec = await storage.get_vector(mid, "t1")
    assert vec == pytest.approx([1.0, 0.0], abs=1e-3)


@pytest.mark.asyncio
async def test_get_memories_batch_coverage():
    """Test get_memories_batch (Lines 524-530)."""
    storage = InMemoryStorage()
    mid1 = await storage.store_memory(tenant_id="t1")
    mid2 = await storage.store_memory(tenant_id="t2")

    mems = await storage.get_memories_batch([mid1, mid2, uuid4()], "t1")
    assert len(mems) == 1
    assert mems[0]["id"] == mid1


@pytest.mark.asyncio
async def test_save_embedding_access_denied():
    """Test save_embedding raises ValueError on tenant mismatch (Lines 475-476)."""
    storage = InMemoryStorage()
    mid = await storage.store_memory(tenant_id="t1")

    with pytest.raises(ValueError, match="Access Denied"):
        await storage.save_embedding(mid, "default", [0.1, 0.2], "t2")


@pytest.mark.asyncio
async def test_count_memories_no_tenant():
    """Test count_memories without tenant_id (Line 655)."""
    storage = InMemoryStorage()
    await storage.store_memory(tenant_id="t1")
    await storage.store_memory(tenant_id="t2")

    assert await storage.count_memories() == 2


@pytest.mark.asyncio
async def test_delete_expired_memories_tenant_mismatch():
    """Test delete_expired_memories tenant check (Line 809)."""
    now = datetime.now(timezone.utc)
    clock = MockClock(now)
    storage = InMemoryStorage(clock=clock)

    # Expired memory for t1
    await storage.store_memory(tenant_id="t1", expires_at=now - timedelta(seconds=1))

    # Try to delete expired for t2
    count = await storage.delete_expired_memories(tenant_id="t2")
    assert count == 0
    assert await storage.count_memories("t1") == 1


@pytest.mark.asyncio
async def test_get_metric_aggregate_tenant_and_filters():
    """Test get_metric_aggregate tenant check and filters (Lines 875, 879-885)."""
    storage = InMemoryStorage()
    await storage.store_memory(tenant_id="t1", importance=1.0, agent_id="a1")
    await storage.store_memory(tenant_id="t1", importance=0.5, agent_id="a2")

    # Tenant mismatch (Line 875)
    assert await storage.get_metric_aggregate("t2", "importance", "sum") == 0.0

    # With filters (Lines 879-885)
    val = await storage.get_metric_aggregate(
        "t1", "importance", "sum", filters={"agent_id": "a1"}
    )
    assert val == 1.0

    val = await storage.get_metric_aggregate(
        "t1", "importance", "sum", filters={"agent_id": "a2"}
    )
    assert val == 0.5

    # Filter mismatch
    val = await storage.get_metric_aggregate(
        "t1", "importance", "sum", filters={"agent_id": "a3"}
    )
    assert val == 0.0


@pytest.mark.asyncio
async def test_delete_memory_vector_cleanup():
    """Ensure delete_memory cleans up vector indices (Lines 601-603)."""
    storage = InMemoryStorage()
    mid = await storage.store_memory(tenant_id="t1", embedding=[0.1, 0.2])

    assert mid in storage._vector_indices["default"]
    await storage.delete_memory(mid, "t1")
    assert mid not in storage._vector_indices["default"]
    assert mid not in storage._vector_metadata["default"]


@pytest.mark.asyncio
async def test_update_memory_layer_change():
    """Test update_memory layer change index update (Lines 601-603 in old report? Wait)."""
    # Let me re-check the line numbers for update_memory layer change
    # In my cat -n output:
    # 577:             # Handle layer updates (update index)
    # 578:             if "layer" in updates:
    # 579:                 old_layer = memory.get("layer")
    # 580:                 new_layer = updates.get("layer")
    # 581:
    # 582:                 if old_layer != new_layer:
    # 583:                     self._by_layer[(tenant_id, cast(str, old_layer))].discard(memory_id)
    # 584:                     self._by_layer[(tenant_id, cast(str, new_layer))].add(memory_id)

    storage = InMemoryStorage()
    mid = await storage.store_memory(tenant_id="t1", layer="l1")
    assert mid in storage._by_layer[("t1", "l1")]

    await storage.update_memory(mid, "t1", {"layer": "l2"})
    assert mid not in storage._by_layer[("t1", "l1")]
    assert mid in storage._by_layer[("t1", "l2")]

    # Update to same layer
    await storage.update_memory(mid, "t1", {"layer": "l2"})
    assert mid in storage._by_layer[("t1", "l2")]
