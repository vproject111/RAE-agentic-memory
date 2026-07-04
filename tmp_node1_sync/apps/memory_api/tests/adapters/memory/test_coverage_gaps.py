"""Coverage gap tests for InMemory adapters."""

import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

# Robust NumPy import
if "numpy" in sys.modules:
    np = sys.modules["numpy"]
else:
    pass

from rae_adapters.memory.cache import InMemoryCache
from rae_adapters.memory.storage import InMemoryStorage
from rae_adapters.memory.vector import InMemoryVectorStore


class TestInMemoryCacheCoverage:
    """Coverage tests for InMemoryCache."""

    @pytest.mark.asyncio
    async def test_increment_expired_key(self):
        """Test incrementing a key that exists but is expired."""
        cache = InMemoryCache()
        key = "expired_counter"

        # Set a key that expires immediately
        await cache.set(key, 10, ttl=-1)  # Expired 1 second ago

        # Manually force expiry to be in the past to be sure
        full_key = cache._get_full_key(key)
        cache._cache[full_key] = (10, datetime.now(timezone.utc) - timedelta(seconds=1))

        # Increment should reset it (or treat as 0 and increment)
        # The current implementation (based on my reading) sets it to delta (0+delta)
        # but keeps the OLD expiry? Let's check what happens.
        new_val = await cache.increment(key, 5)

        # If it treats as expired -> value 0 -> +5 = 5.
        assert new_val == 5

        # Verify if it is still expired or not.
        # Implementation: self._cache[key] = (new_value, expiry) where expiry is the OLD expiry.
        # So it should still be expired.
        val = await cache.get(key)
        assert val is None  # Should be expired/removed on get

    @pytest.mark.asyncio
    async def test_get_ttl_exists_but_expired(self):
        """Test get_ttl for a key that exists but is expired."""
        cache = InMemoryCache()
        key = "expired_ttl"

        await cache.set(key, "val", ttl=1)
        full_key = cache._get_full_key(key)
        cache._cache[full_key] = (
            "val",
            datetime.now(timezone.utc) - timedelta(seconds=1),
        )

        ttl = await cache.get_ttl(key)
        assert ttl is None

        # Should be removed
        assert full_key not in cache._cache

    @pytest.mark.asyncio
    async def test_set_if_not_exists_with_ttl(self):
        """Test set_if_not_exists method with a TTL value (line 277)."""
        cache = InMemoryCache()
        await cache.set_if_not_exists("key_with_ttl", "value", ttl=10)
        assert "key_with_ttl" in cache._cache
        val, expiry = cache._cache["key_with_ttl"]
        assert val == "value"
        assert expiry is not None


class TestInMemoryStorageCoverage:
    """Coverage tests for InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_count_memories_all_filters(self):
        """Test count_memories with agent_id AND layer filters."""
        storage = InMemoryStorage()
        t, a, layer = "t1", "a1", "l1"

        await storage.store_memory("m1", layer, t, a)
        await storage.store_memory("m2", "l2", t, a)
        await storage.store_memory("m3", layer, t, "a2")

        count = await storage.count_memories(t, agent_id=a, layer=layer)
        assert count == 1

    @pytest.mark.asyncio
    async def test_adjust_importance_missing_field(self):
        """Test adjust_importance on a memory without importance field."""
        storage = InMemoryStorage()
        mem_id = await storage.store_memory("m", "l", "t", "a")

        # Manually remove importance
        storage._memories[mem_id].pop("importance", None)

        # Default is 0.5, so +0.1 = 0.6
        new_imp = await storage.adjust_importance(mem_id, 0.1, "t")
        assert new_imp == 0.6
        assert storage._memories[mem_id]["importance"] == 0.6

    @pytest.mark.asyncio
    async def test_update_memory_layer_explicit(self):
        """Explicitly test layer update to hit lines 188-189."""
        storage = InMemoryStorage()
        mem_id = await storage.store_memory("m", "old_layer", "t", "a")

        # Verify index before
        assert mem_id in storage._by_layer[("t", "old_layer")]
        assert mem_id not in storage._by_layer[("t", "new_layer")]

        await storage.update_memory(mem_id, "t", {"layer": "new_layer"})

        # Verify index after
        assert mem_id not in storage._by_layer[("t", "old_layer")]
        assert mem_id in storage._by_layer[("t", "new_layer")]

    @pytest.mark.asyncio
    async def test_clear_tenant_with_tags(self):
        """Test clear_tenant removing memory with tags (covers 295)."""
        storage = InMemoryStorage()
        await storage.store_memory("c", "l", "t1", "a1", tags=["tag1"])
        await storage.clear_tenant("t1")
        assert ("t1", "tag1") not in storage._by_tags or not storage._by_tags[
            ("t1", "tag1")
        ]

    @pytest.mark.asyncio
    async def test_delete_memory_with_tags(self):
        """Test deleting a memory that has tags to cover lines 189, 295, 552."""
        storage = InMemoryStorage()
        mem_id = await storage.store_memory("c", "l", "t", "a", tags=["tag1", "tag2"])

        # Verify tag index
        assert mem_id in storage._by_tags[("t", "tag1")]

        # Delete (covers 189)
        await storage.delete_memory(mem_id, "t")
        assert (
            "t",
            "tag1",
        ) not in storage._by_tags or mem_id not in storage._by_tags.get(
            ("t", "tag1"), set()
        )

    @pytest.mark.asyncio
    async def test_delete_expired_with_tags(self):
        """Test delete_expired_memories removing memory with tags (covers 295)."""
        storage = InMemoryStorage()
        # Set expiry in the past
        past = datetime.now(timezone.utc) - timedelta(days=1)
        mem_id = await storage.store_memory(
            "c", "l", "t", "a", tags=["tag1"], expires_at=past
        )

        await storage.delete_expired_memories("t", "a", "l")
        assert mem_id not in storage._memories

    @pytest.mark.asyncio
    async def test_delete_memories_with_metadata_filter_with_tags(self):
        """Test delete_memories_with_metadata_filter removing memory with tags (covers 552)."""
        storage = InMemoryStorage()
        mem_id = await storage.store_memory(
            "c", "l", "t", "a", tags=["tag1"], metadata={"key": "val"}
        )

        await storage.delete_memories_with_metadata_filter(
            "t", "a", "l", {"key": "val"}
        )
        assert mem_id not in storage._memories


class TestInMemoryVectorStoreCoverage:
    """Coverage tests for InMemoryVectorStore."""

    @pytest.mark.asyncio
    async def test_search_threshold_filtering(self):
        """Test search with score_threshold filtering out results."""
        store = InMemoryVectorStore()
        mem_id = uuid4()
        # [1, 0] vs [0.5, 0.866] -> cos ~ 0.5
        await store.store_vector(mem_id, [1.0, 0.0], "t1", {"layer": "l1"})

        # Query [1, 0] -> score 1.0 (kept)
        # Query [0, 1] -> score 0.0 (filtered if threshold > 0)

        results = await store.search_similar([0.0, 1.0], "t1", score_threshold=0.1)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_delete_vector_wrong_tenant(self):
        """Test deleting vector from wrong tenant."""
        store = InMemoryVectorStore()
        mem_id = uuid4()
        await store.store_vector(mem_id, [1.0], "t1")

        success = await store.delete_vector(mem_id, "t2")
        assert success is False
        assert mem_id in store._vectors

    @pytest.mark.asyncio
    async def test_batch_store_exception(self):
        """Test batch store ignoring invalid vectors."""
        store = InMemoryVectorStore()
        mem_id1 = uuid4()
        mem_id2 = uuid4()

        # Second vector is invalid (None as embedding to trigger np.array failure?
        # np.array(None) creates object array, but maybe self._vectors assignment fails?
        # Let's try to mock or pass something that fails np.array conversion strictly if we pass dtype=float

        # Passing a string might fail conversion to float
        vectors = [
            (mem_id1, [1.0], {}),
            (
                mem_id2,
                ["invalid"],
                {},
            ),  # Should trigger ValueError on np.array(..., dtype=float)
        ]  # type: ignore

        count = await store.batch_store_vectors(vectors, "t1")  # type: ignore
        assert count == 1
        assert mem_id1 in store._vectors
        assert mem_id2 not in store._vectors
