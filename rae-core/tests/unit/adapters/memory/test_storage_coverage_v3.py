"""Additional unit tests for InMemoryStorage to achieve 100% coverage."""

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

    def advance(self, delta: timedelta):
        self._now += delta


class TestInMemoryStorageCoverageV3:
    """Test suite for InMemoryStorage coverage gaps."""

    @pytest.fixture
    async def storage(self):
        """Create storage instance for testing."""
        return InMemoryStorage()

    @pytest.mark.asyncio
    async def test_store_vector_missing_memory(self, storage):
        """Test store_vector with non-existent memory ID."""
        success = await storage.store_vector(uuid4(), [0.1, 0.2], "t1")
        assert success is False

    @pytest.mark.asyncio
    async def test_store_vector_invalid_types(self, storage):
        """Test store_vector with invalid types to cover error handling."""
        mid = await storage.store_memory(tenant_id="t1")

        # Invalid embedding type (Line 96)
        success = await storage.store_vector(mid, "not a list or dict", "t1")
        assert success is False

        # Invalid vector type in dict (Line 100)
        success = await storage.store_vector(mid, {"default": "not a list"}, "t1")
        assert success is False

    @pytest.mark.asyncio
    async def test_store_vector_dimension_mismatch(self, storage):
        """Test store_vector dimension mismatch (Line 107)."""
        mid = await storage.store_memory(tenant_id="t1")
        await storage.store_vector(mid, [0.1, 0.2], "t1")

        with pytest.raises(ValueError, match="Dimension mismatch"):
            await storage.store_vector(mid, [0.1, 0.2, 0.3], "t1")

    @pytest.mark.asyncio
    async def test_search_similar_nonexistent_model(self, storage):
        """Test search_similar with non-existent model (Line 155)."""
        res = await storage.search_similar([0.1, 0.2], "t1", model_name="ghost")
        assert res == []

    @pytest.mark.asyncio
    async def test_search_similar_dimension_mismatch(self, storage):
        """Test search_similar with dimension mismatch (Line 165)."""
        mid = await storage.store_memory(tenant_id="t1")
        await storage.store_vector(mid, [0.1, 0.2, 0.3], "t1")

        # Query with different dimension
        results = await storage.search_similar([0.1, 0.2], "t1")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_similar_filters_extended(self, storage):
        """Test search_similar with various filters (Line 194-203)."""
        mid = await storage.store_memory(tenant_id="t1", agent_id="a1", layer="l1")
        await storage.store_vector(
            mid,
            [1.0, 0.0],
            "t1",
            metadata={
                "agent_id": "a1",
                "layer": "l1",
                "session_id": "s1",
                "project": "p1",
            },
        )

        # Wrong tenant (Line 194)
        assert await storage.search_similar([1.0, 0.0], "t2") == []
        # Wrong layer (Line 197)
        assert await storage.search_similar([1.0, 0.0], "t1", layer="l2") == []
        # Wrong agent (Line 199)
        assert await storage.search_similar([1.0, 0.0], "t1", agent_id="a2") == []
        # Wrong session (Line 201)
        assert await storage.search_similar([1.0, 0.0], "t1", session_id="s2") == []
        # Wrong project (Line 203)
        assert await storage.search_similar([1.0, 0.0], "t1", project="p2") == []

    @pytest.mark.asyncio
    async def test_search_similar_scores(self, storage):
        """Test score filtering in search_similar (Line 235, 238)."""
        mid = await storage.store_memory(tenant_id="t1")
        # Orthogonal vector gives 0 similarity
        await storage.store_vector(mid, [1.0, 0.0], "t1")

        # score <= 0.0 (Line 235)
        res = await storage.search_similar([0.0, 1.0], "t1")
        assert res == []

        # score < score_threshold (Line 238)
        res = await storage.search_similar([1.0, 0.0], "t1", score_threshold=0.99)
        # Note: quantization might make it slightly less than 1.0
        # If it is 1.0, we need a lower threshold or a different vector
        await storage.store_vector(mid, [0.8, 0.6], "t1")
        res = await storage.search_similar([1.0, 0.0], "t1", score_threshold=0.9)
        assert res == []

    @pytest.mark.asyncio
    async def test_search_similar_batch(self, storage):
        """Test search_similar_batch (Line 256-260)."""
        mid = await storage.store_memory(tenant_id="t1", embedding=[1.0, 0.0])
        res = await storage.search_similar_batch([[1.0, 0.0], [0.0, 1.0]], "t1")
        assert len(res) == 2
        assert len(res[0]) == 1
        assert len(res[1]) == 0

    @pytest.mark.asyncio
    async def test_get_vector_wrong_tenant(self, storage):
        """Test get_vector with wrong tenant (Line 294)."""
        mid = await storage.store_memory(tenant_id="t1", embedding=[0.1, 0.2])
        assert await storage.get_vector(mid, "t2") is None

    @pytest.mark.asyncio
    async def test_delete_vector_coverage(self, storage):
        """Test delete_vector (Line 304-316)."""
        mid = await storage.store_memory(tenant_id="t1")
        await storage.store_vector(mid, {"m1": [0.1, 0.2], "m2": [0.3, 0.4]}, "t1")

        # Wrong tenant
        assert await storage.delete_vector(mid, "t2") is False
        assert mid in storage._vector_indices["m1"]

        # Success
        assert await storage.delete_vector(mid, "t1") is True
        assert mid not in storage._vector_indices["m1"]
        assert mid not in storage._vector_indices["m2"]

    @pytest.mark.asyncio
    async def test_update_vector(self, storage):
        """Test update_vector (Line 326)."""
        mid = await storage.store_memory(tenant_id="t1")
        await storage.store_vector(mid, [0.1, 0.2], "t1")
        assert await storage.update_vector(mid, [0.3, 0.4], "t1") is True
        vec = await storage.get_vector(mid, "t1")
        assert vec == pytest.approx([0.3, 0.4], abs=1e-3)

    @pytest.mark.asyncio
    async def test_batch_store_vectors(self, storage):
        """Test batch_store_vectors (Line 336-340)."""
        mid1 = await storage.store_memory(tenant_id="t1")
        mid2 = await storage.store_memory(tenant_id="t1")
        count = await storage.batch_store_vectors(
            [(mid1, [0.1, 0.2], {}), (mid2, [0.3, 0.4], {})], "t1"
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_delete_memory_with_tags(self, storage):
        """Test delete_memory with tags (Line 593)."""
        mid = await storage.store_memory(tenant_id="t1", tags=["t1"])
        assert mid in storage._by_tags[("t1", "t1")]
        await storage.delete_memory(mid, "t1")
        assert mid not in storage._by_tags[("t1", "t1")]

    @pytest.mark.asyncio
    async def test_delete_memories_with_metadata_filter_mismatches(self, storage):
        """Test delete_memories_with_metadata_filter mismatches (Line 712, 714, 716)."""
        mid = await storage.store_memory(tenant_id="t1", agent_id="a1", layer="l1")

        # Wrong tenant (Line 712)
        assert await storage.delete_memories_with_metadata_filter(tenant_id="t2") == 0
        # Wrong agent (Line 714)
        assert (
            await storage.delete_memories_with_metadata_filter(
                tenant_id="t1", agent_id="a2"
            )
            == 0
        )
        # Wrong layer (Line 716)
        assert (
            await storage.delete_memories_with_metadata_filter(
                tenant_id="t1", layer="l2"
            )
            == 0
        )

        assert await storage.count_memories("t1") == 1

    @pytest.mark.asyncio
    async def test_delete_expired_memories_mismatches(self, storage):
        """Test delete_expired_memories mismatches (Line 811, 813)."""
        now = datetime.now(timezone.utc)
        clock = MockClock(now)
        storage = InMemoryStorage(clock=clock)
        await storage.store_memory(
            tenant_id="t1",
            agent_id="a1",
            layer="l1",
            expires_at=now - timedelta(seconds=10),
        )

        # Wrong agent (Line 811)
        assert await storage.delete_expired_memories(tenant_id="t1", agent_id="a2") == 0
        # Wrong layer (Line 813)
        assert await storage.delete_expired_memories(tenant_id="t1", layer="l2") == 0

        assert await storage.count_memories("t1") == 1

    @pytest.mark.asyncio
    async def test_close_and_other_stubs(self, storage):
        """Test close() and other stubs (Line 968)."""
        await storage.close()  # Should do nothing but hit the line

    @pytest.mark.asyncio
    async def test_delete_memory_sync_full(self, storage):
        """Test _delete_memory_sync with tags and vectors (Line 998, 1002-1004)."""
        mid = await storage.store_memory(
            tenant_id="t1", tags=["t1"], embedding=[0.1, 0.2]
        )
        # Call via a method that uses _delete_memory_sync
        await storage.clear_tenant("t1")
        # Verify it's gone
        assert mid not in storage._memories
        assert mid not in storage._by_tags[("t1", "t1")]
        assert mid not in storage._vector_indices["default"]

    @pytest.mark.asyncio
    async def test_get_vector_fallback(self, storage):
        """Test get_vector fallback to non-default model."""
        mid = await storage.store_memory(tenant_id="t1")
        # Store vector in "custom" model, not "default"
        await storage.store_vector(mid, {"custom": [0.1, 0.2]}, "t1")

        # Should find it in "custom" via fallback
        vec = await storage.get_vector(mid, "t1")
        assert vec == pytest.approx([0.1, 0.2], abs=1e-3)

    @pytest.mark.asyncio
    async def test_store_reflection_audit(self, storage):
        """Test store_reflection_audit."""
        audit_id = await storage.store_reflection_audit(
            query_id="q1",
            tenant_id="t1",
            fsi_score=0.8,
            final_decision="APPROVED",
            l1_report={},
            l2_report={},
            l3_report={},
        )
        assert audit_id in storage._reflection_audits

    @pytest.mark.asyncio
    async def test_update_memory_tags_and_layer(self, storage):
        """Test update_memory with tag and layer updates."""
        mid = await storage.store_memory(tenant_id="t1", layer="l1", tags=["t1"])
        await storage.update_memory(mid, "t1", {"tags": ["t2"], "layer": "l2"})
        m = await storage.get_memory(mid, "t1")
        assert m["tags"] == ["t2"]
        assert m["layer"] == "l2"

    @pytest.mark.asyncio
    async def test_get_metric_aggregate_funcs(self, storage):
        """Test all aggregate functions."""
        await storage.store_memory(tenant_id="t1", importance=1.0)
        await storage.store_memory(tenant_id="t1", importance=0.0)
        assert await storage.get_metric_aggregate("t1", "importance", "sum") == 1.0
        assert await storage.get_metric_aggregate("t1", "importance", "avg") == 0.5
        assert await storage.get_metric_aggregate("t1", "importance", "max") == 1.0
        assert await storage.get_metric_aggregate("t1", "importance", "min") == 0.0
        assert await storage.get_metric_aggregate("t1", "importance", "count") == 2.0
        assert await storage.get_metric_aggregate("t1", "importance", "unknown") == 0.0

    @pytest.mark.asyncio
    async def test_decay_importance_ghost(self, storage):
        """Test decay_importance with ghost memory."""
        await storage.store_memory(tenant_id="t1", importance=1.0)
        storage._by_tenant["t1"].add(uuid4())
        assert await storage.decay_importance("t1", 0.5) == 1
