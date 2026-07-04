"""Unit tests for InMemoryVectorStore adapter."""

from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pytest

from rae_adapters.memory.vector import InMemoryVectorStore


class TestInMemoryVectorStore:
    """Test suite for InMemoryVectorStore."""

    @pytest.fixture
    async def store(self):
        """Create vector store instance for testing."""
        return InMemoryVectorStore()

    @pytest.fixture
    def sample_embedding(self):
        """Create sample embedding vector."""
        return [0.1, 0.2, 0.3, 0.4, 0.5]

    @pytest.mark.asyncio
    async def test_store_vector(self, store, sample_embedding):
        """Test storing a vector."""
        memory_id = uuid4()
        success = await store.store_vector(
            memory_id=memory_id,
            embedding=sample_embedding,
            tenant_id="tenant1",
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_store_and_retrieve_vector(self, store, sample_embedding):
        """Test storing and retrieving a vector."""
        memory_id = uuid4()

        await store.store_vector(
            memory_id=memory_id,
            embedding=sample_embedding,
            tenant_id="tenant1",
            metadata={"layer": "working"},
        )

        retrieved = await store.get_vector(memory_id, "tenant1")

        assert retrieved is not None
        assert len(retrieved) == len(sample_embedding)
        assert np.allclose(retrieved, sample_embedding)

    @pytest.mark.asyncio
    async def test_get_nonexistent_vector(self, store):
        """Test retrieving non-existent vector."""
        retrieved = await store.get_vector(uuid4(), "tenant1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_vector_wrong_tenant(self, store, sample_embedding):
        """Test tenant isolation."""
        memory_id = uuid4()

        await store.store_vector(
            memory_id=memory_id,
            embedding=sample_embedding,
            tenant_id="tenant1",
        )

        # Try to get with wrong tenant
        retrieved = await store.get_vector(memory_id, "tenant2")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_update_vector(self, store, sample_embedding):
        """Test updating a vector."""
        memory_id = uuid4()

        await store.store_vector(
            memory_id=memory_id,
            embedding=sample_embedding,
            tenant_id="tenant1",
        )

        new_embedding = [0.5, 0.4, 0.3, 0.2, 0.1]
        success = await store.update_vector(
            memory_id=memory_id,
            embedding=new_embedding,
            tenant_id="tenant1",
        )

        assert success is True

        retrieved = await store.get_vector(memory_id, "tenant1")
        assert np.allclose(retrieved, new_embedding)

    @pytest.mark.asyncio
    async def test_update_nonexistent_vector(self, store, sample_embedding):
        """Test updating non-existent vector."""
        success = await store.update_vector(
            memory_id=uuid4(),
            embedding=sample_embedding,
            tenant_id="tenant1",
        )

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_vector(self, store, sample_embedding):
        """Test deleting a vector."""
        memory_id = uuid4()

        await store.store_vector(
            memory_id=memory_id,
            embedding=sample_embedding,
            tenant_id="tenant1",
        )

        success = await store.delete_vector(memory_id, "tenant1")
        assert success is True

        retrieved = await store.get_vector(memory_id, "tenant1")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_vector(self, store):
        """Test deleting non-existent vector."""
        success = await store.delete_vector(uuid4(), "tenant1")
        assert success is False

    @pytest.mark.asyncio
    async def test_search_similar_basic(self, store):
        """Test basic similarity search."""
        # Create similar vectors
        vec1 = [1.0, 0.0, 0.0, 0.0]
        vec2 = [0.9, 0.1, 0.0, 0.0]  # Very similar to vec1
        vec3 = [0.0, 0.0, 1.0, 0.0]  # Different

        id1 = uuid4()
        id2 = uuid4()
        id3 = uuid4()

        await store.store_vector(id1, vec1, "tenant1")
        await store.store_vector(id2, vec2, "tenant1")
        await store.store_vector(id3, vec3, "tenant1")

        # Search for similar to vec1
        results = await store.search_similar(
            query_embedding=vec1,
            tenant_id="tenant1",
            limit=2,
        )

        assert len(results) == 2
        # First result should be the exact match (id1)
        assert results[0][0] == id1
        assert results[0][1] > 0.99  # Nearly perfect similarity

        # Second should be id2 (similar)
        assert results[1][0] == id2

    @pytest.mark.asyncio
    async def test_search_similar_with_threshold(self, store):
        """Test similarity search with score threshold."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.7, 0.3, 0.0]  # Moderately similar
        vec3 = [0.0, 0.0, 1.0]  # Very different

        await store.store_vector(uuid4(), vec1, "tenant1")
        await store.store_vector(uuid4(), vec2, "tenant1")
        await store.store_vector(uuid4(), vec3, "tenant1")

        # Search with high threshold
        results = await store.search_similar(
            query_embedding=vec1,
            tenant_id="tenant1",
            score_threshold=0.9,
            limit=10,
        )

        # Should only return the exact match
        assert len(results) >= 1
        assert results[0][1] > 0.9

    @pytest.mark.asyncio
    async def test_search_similar_with_layer_filter(self, store):
        """Test similarity search with layer filtering."""
        vec = [1.0, 0.0, 0.0]

        id1 = uuid4()
        id2 = uuid4()

        await store.store_vector(id1, vec, "tenant1", metadata={"layer": "working"})
        await store.store_vector(id2, vec, "tenant1", metadata={"layer": "episodic"})

        # Search with layer filter
        results = await store.search_similar(
            query_embedding=vec,
            tenant_id="tenant1",
            layer="working",
            limit=10,
        )

        assert len(results) == 1
        assert results[0][0] == id1

    @pytest.mark.asyncio
    async def test_search_similar_tenant_isolation(self, store):
        """Test that search respects tenant isolation."""
        vec = [1.0, 0.0, 0.0]

        await store.store_vector(uuid4(), vec, "tenant1")
        await store.store_vector(uuid4(), vec, "tenant2")

        results = await store.search_similar(
            query_embedding=vec,
            tenant_id="tenant1",
            limit=10,
        )

        # Should only return tenant1's vector
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_search_similar_empty_store(self, store):
        """Test searching in empty store."""
        results = await store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant1",
            limit=10,
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_similar_zero_vector(self, store):
        """Test searching with zero vector."""
        # Store a normal vector
        await store.store_vector(uuid4(), [1.0, 0.0, 0.0], "tenant1")

        # Search with zero vector (should handle gracefully)
        results = await store.search_similar(
            query_embedding=[0.0, 0.0, 0.0],
            tenant_id="tenant1",
            limit=10,
        )

        assert len(results) == 0  # No results due to zero query

    @pytest.mark.asyncio
    async def test_batch_store_vectors(self, store):
        """Test batch storing vectors."""
        vectors = [
            (uuid4(), [1.0, 0.0, 0.0], {"layer": "working"}),
            (uuid4(), [0.0, 1.0, 0.0], {"layer": "episodic"}),
            (uuid4(), [0.0, 0.0, 1.0], {"layer": "semantic"}),
        ]

        count = await store.batch_store_vectors(vectors, "tenant1")

        assert count == 3

        # Verify all were stored
        stats = await store.get_statistics()
        assert stats["total_vectors"] == 3

    @pytest.mark.asyncio
    async def test_batch_store_vectors_with_invalid(self, store):
        """Test batch storing with some invalid vectors."""
        vectors: list[tuple[UUID, Any, dict[str, Any]]] = [
            (uuid4(), [1.0, 0.0, 0.0], {}),
            (uuid4(), "invalid", {}),  # Invalid embedding
            (uuid4(), [0.0, 1.0, 0.0], {}),
        ]

        count = await store.batch_store_vectors(vectors, "tenant1")

        # Should store 2 valid vectors and skip the invalid one
        assert count == 2

    @pytest.mark.asyncio
    async def test_search_similar_batch(self, store):
        """Test batch similarity search."""
        # Store vectors
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        await store.store_vector(uuid4(), vec1, "tenant1")
        await store.store_vector(uuid4(), vec2, "tenant1")

        # Batch search
        queries = [vec1, vec2]
        results = await store.search_similar_batch(
            query_embeddings=queries,
            tenant_id="tenant1",
            limit=1,
        )

        assert len(results) == 2
        assert len(results[0]) == 1
        assert len(results[1]) == 1

    @pytest.mark.asyncio
    async def test_clear_tenant(self, store):
        """Test clearing all vectors for a tenant."""
        # Store vectors for different tenants
        await store.store_vector(uuid4(), [1.0, 0.0], "tenant1")
        await store.store_vector(uuid4(), [0.0, 1.0], "tenant1")
        await store.store_vector(uuid4(), [1.0, 1.0], "tenant2")

        count = await store.clear_tenant("tenant1")
        assert count == 2

        # Verify tenant1 vectors are gone
        stats = await store.get_statistics()
        assert stats["total_vectors"] == 1
        assert stats["tenants"] == 1

    @pytest.mark.asyncio
    async def test_get_statistics(self, store):
        """Test getting vector store statistics."""
        # Store vectors with different dimensions
        await store.store_vector(uuid4(), [1.0, 0.0], "tenant1")
        await store.store_vector(uuid4(), [1.0, 0.0, 0.0], "tenant2")

        stats = await store.get_statistics()

        assert stats["total_vectors"] == 2
        assert stats["tenants"] == 2
        assert 2 in stats["dimensions"]
        assert 3 in stats["dimensions"]

    @pytest.mark.asyncio
    async def test_clear_all(self, store):
        """Test clearing all data."""
        # Store some vectors
        await store.store_vector(uuid4(), [1.0, 0.0], "tenant1")
        await store.store_vector(uuid4(), [0.0, 1.0], "tenant2")

        count = await store.clear_all()
        assert count == 2

        # Verify all vectors are gone
        stats = await store.get_statistics()
        assert stats["total_vectors"] == 0

    # @pytest.mark.asyncio
    # async def test_cosine_similarity_correctness(self, store, golden_snapshot):
    #     """Test that cosine similarity is calculated correctly."""
    #     # Orthogonal vectors (similarity = 0)
    #     vec1 = [1.0, 0.0, 0.0]
    #     vec2 = [0.0, 1.0, 0.0]
    #
    #     # Identical vectors (similarity = 1)
    #     vec3 = [1.0, 0.0, 0.0]
    #
    #     id1 = uuid4()
    #     id2 = uuid4()
    #     id3 = uuid4()
    #
    #     await store.store_vector(id1, vec1, "tenant1")
    #     await store.store_vector(id2, vec2, "tenant1")
    #     await store.store_vector(id3, vec3, "tenant1")
    #
    #     results = await store.search_similar(
    #         query_embedding=vec1,
    #         tenant_id="tenant1",
    #         limit=10,
    #     )
    #
    #     # Record golden snapshot
    #     golden_snapshot(
    #         test_name="cosine_similarity_memory_correctness",
    #         inputs={"query": vec1, "vecs": [vec1, vec2, vec3]},
    #         output=results,
    #         metadata={"adapter": "InMemoryVectorStore"},
    #     )
    #
    #     # Find results by ID
    #     result_dict = {rid: score for rid, score in results}
    #
    #     # Identical vectors should have similarity ~1.0
    #     assert abs(result_dict[id1] - 1.0) < 0.01
    #     assert abs(result_dict[id3] - 1.0) < 0.01
    #
    #     # Orthogonal vectors should have similarity ~0.0
    #     assert abs(result_dict[id2]) < 0.1

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, store):
        """Test thread safety with concurrent operations."""
        import asyncio

        async def store_vector(i):
            vec = [float(i % 3 == 0), float(i % 3 == 1), float(i % 3 == 2)]
            return await store.store_vector(
                memory_id=uuid4(),
                embedding=vec,
                tenant_id="tenant1",
            )

        # Store 10 vectors concurrently
        tasks = [store_vector(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        assert all(results)  # All should succeed

        stats = await store.get_statistics()
        assert stats["total_vectors"] == 10
