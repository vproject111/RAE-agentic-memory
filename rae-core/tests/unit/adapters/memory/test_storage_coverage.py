"""Additional unit tests for InMemoryStorage to achieve 100% coverage."""

from uuid import uuid4

import pytest

from rae_core.adapters.memory.storage import InMemoryStorage


class TestInMemoryStorageCoverage:
    """Test suite for InMemoryStorage coverage gaps."""

    @pytest.fixture
    async def storage(self):
        """Create storage instance for testing."""
        return InMemoryStorage()

    @pytest.mark.asyncio
    async def test_save_embedding_nonexistent(self, storage):
        """Test saving embedding for non-existent memory."""
        success = await storage.save_embedding(uuid4(), "model", [0.1, 0.2], "tenant")
        assert success is False

    @pytest.mark.asyncio
    async def test_save_embedding_success(self, storage):
        """Test saving embedding for existing memory."""
        mid = await storage.store_memory(
            content="content", layer="layer", tenant_id="tenant", agent_id="agent"
        )
        success = await storage.save_embedding(mid, "model", [0.1, 0.2], "tenant")
        assert success is True

    @pytest.mark.asyncio
    async def test_save_embedding_access_denied(self, storage):
        """Test saving embedding with wrong tenant."""
        mid = await storage.store_memory(
            content="content", layer="layer", tenant_id="tenant1", agent_id="agent"
        )
        with pytest.raises(ValueError, match="Access Denied"):
            await storage.save_embedding(mid, "model", [0.1, 0.2], "tenant2")

    @pytest.mark.asyncio
    async def test_delete_memory_not_found_or_wrong_tenant(self, storage):
        """Test deleting non-existent memory or with wrong tenant."""
        mid = await storage.store_memory(
            content="content", layer="layer", tenant_id="tenant1", agent_id="agent"
        )

        # Wrong tenant
        success = await storage.delete_memory(mid, "tenant2")
        assert success is False

        # Non-existent
        success = await storage.delete_memory(uuid4(), "tenant1")
        assert success is False

    @pytest.mark.asyncio
    async def test_clear_tenant_with_multiple_memories(self, storage):
        """Test clearing tenant with multiple memories to cover the loop."""
        await storage.store_memory(
            content="c1", layer="l1", tenant_id="t1", agent_id="a1"
        )
        await storage.store_memory(
            content="c2", layer="l2", tenant_id="t1", agent_id="a1"
        )
        await storage.store_memory(
            content="c3", layer="l1", tenant_id="t2", agent_id="a1"
        )

        await storage.clear_tenant("t1")
        assert await storage.count_memories("t1") == 0
        assert await storage.count_memories("t2") == 1

    @pytest.mark.asyncio
    async def test_update_memory_access_not_found(self, storage):
        """Test update_memory_access with non-existent ID."""
        success = await storage.update_memory_access(uuid4(), "tenant")
        assert success is False

    @pytest.mark.asyncio
    async def test_update_memory_expiration_not_found(self, storage):
        """Test update_memory_expiration with non-existent ID."""
        success = await storage.update_memory_expiration(uuid4(), "tenant", None)
        assert success is False

    @pytest.mark.asyncio
    async def test_get_metric_aggregate_stub(self, storage):
        """Test the stub get_metric_aggregate."""
        val = await storage.get_metric_aggregate("t1", "m", "f")
        assert val == 0.0

    @pytest.mark.asyncio
    async def test_update_memory_access_batch(self, storage):
        """Test update_memory_access_batch."""
        mid1 = await storage.store_memory(
            content="c1", layer="l1", tenant_id="t1", agent_id="a1"
        )
        mid2 = await storage.store_memory(
            content="c2", layer="l1", tenant_id="t1", agent_id="a1"
        )

        success = await storage.update_memory_access_batch([mid1, mid2], "t1")
        assert success is True

        m1 = await storage.get_memory(mid1, "t1")
        m2 = await storage.get_memory(mid2, "t1")
        assert m1["access_count"] == 1
        assert m2["access_count"] == 1

    @pytest.mark.asyncio
    async def test_adjust_importance_not_found(self, storage):
        """Test adjust_importance with non-existent ID."""
        val = await storage.adjust_importance(uuid4(), 0.1, "tenant")
        assert val == 0.0

    @pytest.mark.asyncio
    async def test_adjust_importance_clamping(self, storage):
        """Test adjust_importance clamping logic."""
        mid = await storage.store_memory(
            content="c", layer="l", tenant_id="t", agent_id="a", importance=0.9
        )

        # Upward clamping
        new_val = await storage.adjust_importance(mid, 0.5, "t")
        assert new_val == 1.0

        # Downward clamping
        new_val = await storage.adjust_importance(mid, -1.5, "t")
        assert new_val == 0.0

    @pytest.mark.asyncio
    async def test_delete_memory_internal_none(self, storage):
        """Test internal delete helper with None (should not raise)."""
        # Call the actual private method to test it
        storage._delete_memory_sync(uuid4())

    @pytest.mark.asyncio
    async def test_search_memories_tags_mismatch(self, storage):
        """Test search with tags that are not a subset of memory tags."""
        await storage.store_memory(
            content="c", layer="l", tenant_id="t", agent_id="a", tags=["t1", "t2"]
        )

        # Filter with tag that doesn't exist in memory
        results = await storage.search_memories(
            query="c", tenant_id="t", agent_id="a", filters={"tags": ["t3"]}
        )
        assert len(results) == 0

        # Filter with one existing and one non-existing tag
        results = await storage.search_memories(
            query="c", tenant_id="t", agent_id="a", filters={"tags": ["t1", "t3"]}
        )
        assert len(results) == 0
