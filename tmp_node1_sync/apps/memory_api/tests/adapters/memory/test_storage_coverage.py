"""Additional unit tests for InMemoryStorage to achieve 100% coverage."""

from uuid import uuid4

import pytest

from rae_adapters.memory.storage import InMemoryStorage


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
        mid = await storage.store_memory("content", "layer", "tenant", "agent")
        success = await storage.save_embedding(mid, "model", [0.1, 0.2], "tenant")
        assert success is True

    @pytest.mark.asyncio
    async def test_save_embedding_access_denied(self, storage):
        """Test saving embedding with wrong tenant."""
        mid = await storage.store_memory("content", "layer", "tenant1", "agent")
        with pytest.raises(ValueError, match="Access Denied"):
            await storage.save_embedding(mid, "model", [0.1, 0.2], "tenant2")

    @pytest.mark.asyncio
    async def test_delete_memory_not_found_or_wrong_tenant(self, storage):
        """Test deleting non-existent memory or with wrong tenant."""
        mid = await storage.store_memory("content", "layer", "tenant1", "agent")

        # Wrong tenant
        success = await storage.delete_memory(mid, "tenant2")
        assert success is False

        # Non-existent
        success = await storage.delete_memory(uuid4(), "tenant1")
        assert success is False

    @pytest.mark.asyncio
    async def test_clear_tenant_with_multiple_memories(self, storage):
        """Test clearing tenant with multiple memories to cover the loop."""
        await storage.store_memory("c1", "l1", "t1", "a1")
        await storage.store_memory("c2", "l2", "t1", "a1")
        await storage.store_memory("c3", "l1", "t2", "a1")

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
        mid1 = await storage.store_memory("c1", "l1", "t1", "a1")
        mid2 = await storage.store_memory("c2", "l1", "t1", "a1")

        success = await storage.update_memory_access_batch([mid1, mid2], "t1")
        assert success is True

        m1 = await storage.get_memory(mid1, "t1")
        m2 = await storage.get_memory(mid2, "t1")
        assert m1["usage_count"] == 1
        assert m2["usage_count"] == 1

    @pytest.mark.asyncio
    async def test_adjust_importance_not_found(self, storage):
        """Test adjust_importance with non-existent ID."""
        val = await storage.adjust_importance(uuid4(), 0.1, "tenant")
        assert val == 0.0

    @pytest.mark.asyncio
    async def test_adjust_importance_clamping(self, storage):
        """Test adjust_importance clamping logic."""
        mid = await storage.store_memory("c", "l", "t", "a", importance=0.9)

        # Upward clamping
        new_val = await storage.adjust_importance(mid, 0.5, "t")
        assert new_val == 1.0

        # Downward clamping
        new_val = await storage.adjust_importance(mid, -1.5, "t")
        assert new_val == 0.0

    @pytest.mark.asyncio
    async def test_decay_importance_inconsistency(self, storage):
        """Test decay when memory exists in index but not in main dictionary (line 555)."""
        mid = await storage.store_memory("c1", "l1", "t1", "a1")

        # Manually create inconsistency
        async with storage._lock:
            del storage._memories[mid]

        count = await storage.decay_importance("t1", 0.1)
        assert count == 0

    @pytest.mark.asyncio
    async def test_delete_memory_internal_none(self, storage):
        """Test internal delete helper with None (should not raise)."""
        # This is harder to trigger via public API if not already covered
        # but we can try to call it if we really need 100%
        await storage._delete_memory_internal(uuid4())

    @pytest.mark.asyncio
    async def test_decay_importance(self, storage):
        """Test importance decay logic."""
        mid1 = await storage.store_memory("c1", "l1", "t1", "a1", importance=1.0)
        mid2 = await storage.store_memory("c2", "l1", "t1", "a1", importance=0.5)

        # Apply decay of 0.1
        count = await storage.decay_importance("t1", 0.1)
        assert count == 2

        m1 = await storage.get_memory(mid1, "t1")
        m2 = await storage.get_memory(mid2, "t1")
        assert m1["importance"] == 0.9
        assert m2["importance"] == 0.4

    @pytest.mark.asyncio
    async def test_decay_importance_with_access_stats(self, storage):
        """Test importance decay with access stats boost."""
        mid = await storage.store_memory("c1", "l1", "t1", "a1", importance=1.0)
        # Increase access count to slow down decay
        await storage.update_memory_access(mid, "t1")  # usage = 1

        # Apply decay of 0.1 with stats
        # dampening = 1.0 / (1.0 + ln(1+1)) = 1.0 / (1.0 + 0.693) = 0.59
        # decay = 0.1 * 0.59 = 0.059
        await storage.decay_importance("t1", 0.1, consider_access_stats=True)

        m = await storage.get_memory(mid, "t1")
        assert 0.94 < m["importance"] < 0.95

    @pytest.mark.asyncio
    async def test_decay_importance_no_memories(self, storage):
        """Test decay when no memories exist for tenant."""
        count = await storage.decay_importance("nonexistent", 0.1)
        assert count == 0
