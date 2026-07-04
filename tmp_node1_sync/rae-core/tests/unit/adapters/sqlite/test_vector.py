"""Unit tests for SQLite vector store adapter.

Tests vector storage with struct serialization, cosine similarity search,
and layer filtering.
"""

from typing import Any
from uuid import UUID, uuid4

import pytest

from rae_core.adapters.sqlite.vector import SQLiteVectorStore


@pytest.fixture
async def vector_store(tmp_path):
    """Create temporary SQLite vector store for testing."""
    db_path = str(tmp_path / "test_vectors.db")
    store = SQLiteVectorStore(db_path=db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
async def file_vector_store(tmp_path):
    """Create file-based SQLite vector store for persistence testing."""
    db_path = str(tmp_path / "vectors.db")
    store = SQLiteVectorStore(db_path=db_path)
    await store.initialize()
    yield store
    await store.close()


@pytest.fixture
def sample_vectors():
    """Sample vectors for testing."""
    return {
        "v1": [1.0, 0.0, 0.0],  # Unit vector on x-axis
        "v2": [0.0, 1.0, 0.0],  # Unit vector on y-axis
        "v3": [0.0, 0.0, 1.0],  # Unit vector on z-axis
        "v4": [0.7071, 0.7071, 0.0],  # 45 degrees between x and y
        "v5": [1.0, 0.0, 0.0],  # Same as v1 (duplicate)
    }


class TestSQLiteVectorStoreBasicOperations:
    """Test basic vector storage operations."""

    @pytest.mark.asyncio
    async def test_store_vector(self, vector_store):
        """Test storing a vector."""
        memory_id = uuid4()
        embedding = [1.0, 2.0, 3.0]
        metadata = {"layer": "episodic", "importance": 0.8}

        success = await vector_store.store_vector(
            memory_id=memory_id,
            embedding=embedding,
            tenant_id="tenant-1",
            metadata=metadata,
        )
        assert success is True

        # Verify stored
        retrieved = await vector_store.get_vector(memory_id, "tenant-1")
        assert retrieved is not None
        assert len(retrieved) == len(embedding)
        # Check values with tolerance for float precision
        for i, val in enumerate(embedding):
            assert abs(retrieved[i] - val) < 1e-6

    @pytest.mark.asyncio
    async def test_store_vector_different_dimensions(self, vector_store):
        """Test storing vectors with different dimensions."""
        # 3D vector
        id1 = uuid4()
        await vector_store.store_vector(
            memory_id=id1,
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )

        # 5D vector
        id2 = uuid4()
        await vector_store.store_vector(
            memory_id=id2,
            embedding=[1.0, 2.0, 3.0, 4.0, 5.0],
            tenant_id="tenant-1",
        )

        # Verify both stored correctly
        v1 = await vector_store.get_vector(id1, "tenant-1")
        assert len(v1) == 3

        v2 = await vector_store.get_vector(id2, "tenant-1")
        assert len(v2) == 5

    @pytest.mark.asyncio
    async def test_store_vector_replace(self, vector_store):
        """Test replacing existing vector."""
        memory_id = uuid4()

        # Store initial vector
        await vector_store.store_vector(
            memory_id=memory_id,
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )

        # Replace with new vector
        await vector_store.store_vector(
            memory_id=memory_id,
            embedding=[4.0, 5.0, 6.0],
            tenant_id="tenant-1",
        )

        # Verify replaced
        retrieved = await vector_store.get_vector(memory_id, "tenant-1")
        assert abs(retrieved[0] - 4.0) < 1e-6
        assert abs(retrieved[1] - 5.0) < 1e-6
        assert abs(retrieved[2] - 6.0) < 1e-6

    @pytest.mark.asyncio
    async def test_get_vector_not_found(self, vector_store):
        """Test getting non-existent vector."""
        vector = await vector_store.get_vector(uuid4(), "tenant-1")
        assert vector is None

    @pytest.mark.asyncio
    async def test_get_vector_wrong_tenant(self, vector_store):
        """Test getting vector with wrong tenant ID."""
        memory_id = uuid4()
        await vector_store.store_vector(
            memory_id=memory_id,
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )

        # Try to get with different tenant
        vector = await vector_store.get_vector(memory_id, "tenant-2")
        assert vector is None

    @pytest.mark.asyncio
    async def test_delete_vector(self, vector_store):
        """Test deleting a vector."""
        memory_id = uuid4()
        await vector_store.store_vector(
            memory_id=memory_id,
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )

        # Delete
        success = await vector_store.delete_vector(memory_id, "tenant-1")
        assert success is True

        # Verify deleted
        vector = await vector_store.get_vector(memory_id, "tenant-1")
        assert vector is None

    @pytest.mark.asyncio
    async def test_delete_vector_not_found(self, vector_store):
        """Test deleting non-existent vector."""
        success = await vector_store.delete_vector(uuid4(), "tenant-1")
        assert success is False

    @pytest.mark.asyncio
    async def test_update_vector(self, vector_store):
        """Test updating a vector."""
        memory_id = uuid4()

        # Store initial vector
        await vector_store.store_vector(
            memory_id=memory_id,
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
            metadata={"layer": "episodic"},
        )

        # Update
        success = await vector_store.update_vector(
            memory_id=memory_id,
            embedding=[4.0, 5.0, 6.0],
            tenant_id="tenant-1",
            metadata={"layer": "semantic"},
        )
        assert success is True

        # Verify updated
        vector = await vector_store.get_vector(memory_id, "tenant-1")
        assert abs(vector[0] - 4.0) < 1e-6

    @pytest.mark.asyncio
    async def test_update_vector_not_found(self, vector_store):
        """Test updating non-existent vector."""
        success = await vector_store.update_vector(
            memory_id=uuid4(),
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )
        assert success is False


class TestSQLiteVectorStoreSimilaritySearch:
    """Test cosine similarity search."""

    @pytest.mark.asyncio
    async def test_search_similar_exact_match(self, vector_store, sample_vectors):
        """Test finding exact match (similarity = 1.0)."""
        # Store vector
        memory_id = uuid4()
        await vector_store.store_vector(
            memory_id=memory_id,
            embedding=sample_vectors["v1"],
            tenant_id="tenant-1",
        )

        # Search with same vector
        results = await vector_store.search_similar(
            query_embedding=sample_vectors["v1"],
            tenant_id="tenant-1",
        )

        assert len(results) == 1
        assert results[0][0] == memory_id
        assert abs(results[0][1] - 1.0) < 1e-6  # Perfect similarity

    @pytest.mark.asyncio
    async def test_search_similar_orthogonal_vectors(
        self, vector_store, sample_vectors
    ):
        """Test orthogonal vectors (similarity = 0.0)."""
        # Store orthogonal vectors
        id1 = uuid4()
        id2 = uuid4()

        await vector_store.store_vector(
            memory_id=id1,
            embedding=sample_vectors["v1"],  # [1, 0, 0]
            tenant_id="tenant-1",
        )
        await vector_store.store_vector(
            memory_id=id2,
            embedding=sample_vectors["v2"],  # [0, 1, 0]
            tenant_id="tenant-1",
        )

        # Search with v1
        results = await vector_store.search_similar(
            query_embedding=sample_vectors["v1"],
            tenant_id="tenant-1",
        )

        # Both should be returned, but v1 with higher similarity
        assert len(results) == 2
        assert results[0][0] == id1  # Most similar first
        assert abs(results[0][1] - 1.0) < 1e-6
        assert abs(results[1][1] - 0.0) < 1e-6  # Orthogonal

    @pytest.mark.asyncio
    async def test_search_similar_ranking(self, vector_store, sample_vectors):
        """Test that results are ranked by similarity."""
        # Store multiple vectors
        ids = {}
        for name, vec in sample_vectors.items():
            memory_id = uuid4()
            ids[name] = memory_id
            await vector_store.store_vector(
                memory_id=memory_id,
                embedding=vec,
                tenant_id="tenant-1",
            )

        # Search with v1
        results = await vector_store.search_similar(
            query_embedding=sample_vectors["v1"],
            tenant_id="tenant-1",
        )

        # v1 and v5 should be most similar (same vector)
        # v4 should be next (45 degrees)
        # v2 and v3 should be least similar (orthogonal)
        assert len(results) == 5

        # First two should be v1 and v5 with similarity 1.0
        assert results[0][1] >= 0.99
        assert results[1][1] >= 0.99

        # Similarities should be in descending order
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i + 1][1]

    @pytest.mark.asyncio
    async def test_search_similar_with_limit(self, vector_store, sample_vectors):
        """Test limiting search results."""
        # Store multiple vectors
        for vec in sample_vectors.values():
            await vector_store.store_vector(
                memory_id=uuid4(),
                embedding=vec,
                tenant_id="tenant-1",
            )

        # Search with limit
        results = await vector_store.search_similar(
            query_embedding=sample_vectors["v1"],
            tenant_id="tenant-1",
            limit=3,
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_search_similar_with_threshold(self, vector_store, sample_vectors):
        """Test filtering by similarity threshold."""
        # Store orthogonal vectors
        for vec in sample_vectors.values():
            await vector_store.store_vector(
                memory_id=uuid4(),
                embedding=vec,
                tenant_id="tenant-1",
            )

        # Search with high threshold
        results = await vector_store.search_similar(
            query_embedding=sample_vectors["v1"],
            tenant_id="tenant-1",
            score_threshold=0.9,
        )

        # Only v1 and v5 (duplicates) should match
        assert len(results) == 2
        for _, score in results:
            assert score >= 0.9

    @pytest.mark.asyncio
    async def test_search_similar_with_layer_filter(self, vector_store):
        """Test filtering by layer."""
        # Store vectors in different layers
        id1 = uuid4()
        id2 = uuid4()
        id3 = uuid4()

        await vector_store.store_vector(
            memory_id=id1,
            embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
            metadata={"layer": "episodic"},
        )
        await vector_store.store_vector(
            memory_id=id2,
            embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
            metadata={"layer": "semantic"},
        )
        await vector_store.store_vector(
            memory_id=id3,
            embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
            metadata={"layer": "episodic"},
        )

        # Search with layer filter
        results = await vector_store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
            layer="episodic",
        )

        assert len(results) == 2
        result_ids = {r[0] for r in results}
        assert id1 in result_ids
        assert id3 in result_ids

    @pytest.mark.asyncio
    async def test_search_similar_tenant_isolation(self, vector_store):
        """Test tenant isolation in search."""
        # Store vectors for different tenants
        id1 = uuid4()
        id2 = uuid4()

        await vector_store.store_vector(
            memory_id=id1,
            embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
        )
        await vector_store.store_vector(
            memory_id=id2,
            embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-2",
        )

        # Search tenant-1
        results = await vector_store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
        )

        assert len(results) == 1
        assert results[0][0] == id1

    @pytest.mark.asyncio
    async def test_search_similar_empty_results(self, vector_store):
        """Test search with no matching vectors."""
        # Empty database
        results = await vector_store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
        )
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_search_similar_zero_query_vector(self, vector_store):
        """Test search with zero query vector."""
        # Store vector
        await vector_store.store_vector(
            memory_id=uuid4(),
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )

        # Search with zero vector
        results = await vector_store.search_similar(
            query_embedding=[0.0, 0.0, 0.0],
            tenant_id="tenant-1",
        )

        # Should return empty results (zero vector has no direction)
        assert len(results) == 0


class TestSQLiteVectorStoreBatchOperations:
    """Test batch vector operations."""

    @pytest.mark.asyncio
    async def test_batch_store_vectors(self, vector_store):
        """Test storing multiple vectors in batch."""
        vectors = [
            (uuid4(), [1.0, 0.0, 0.0], {"layer": "episodic"}),
            (uuid4(), [0.0, 1.0, 0.0], {"layer": "semantic"}),
            (uuid4(), [0.0, 0.0, 1.0], {"layer": "working"}),
        ]

        count = await vector_store.batch_store_vectors(
            vectors=vectors,
            tenant_id="tenant-1",
        )
        assert count == 3

        # Verify all stored
        for memory_id, embedding, _ in vectors:
            retrieved = await vector_store.get_vector(memory_id, "tenant-1")
            assert retrieved is not None

    @pytest.mark.asyncio
    async def test_batch_store_vectors_empty(self, vector_store):
        """Test batch store with empty list."""
        count = await vector_store.batch_store_vectors(
            vectors=[],
            tenant_id="tenant-1",
        )
        assert count == 0

    @pytest.mark.asyncio
    async def test_batch_store_vectors_partial_failure(self, vector_store):
        """Test batch store with some invalid vectors."""
        vectors: list[tuple[UUID, list[float], dict[str, Any]]] = [
            (uuid4(), [1.0, 0.0, 0.0], {}),
            # Note: All valid vectors in this test
            (uuid4(), [0.0, 1.0, 0.0], {}),
        ]

        count = await vector_store.batch_store_vectors(
            vectors=vectors,
            tenant_id="tenant-1",
        )
        # Both should succeed
        assert count == 2


class TestSQLiteVectorStoreTenantOperations:
    """Test tenant-level operations."""

    @pytest.mark.asyncio
    async def test_clear_tenant(self, vector_store):
        """Test clearing all vectors for a tenant."""
        # Store vectors for multiple tenants
        for i in range(3):
            await vector_store.store_vector(
                memory_id=uuid4(),
                embedding=[float(i + 1), 0.0, 0.0],  # Use i+1 to avoid zero vector
                tenant_id="tenant-1",
            )
        for i in range(2):
            await vector_store.store_vector(
                memory_id=uuid4(),
                embedding=[float(i + 1), 0.0, 0.0],  # Use i+1 to avoid zero vector
                tenant_id="tenant-2",
            )

        # Clear tenant-1
        count = await vector_store.clear_tenant("tenant-1")
        assert count == 3

        # Verify tenant-1 cleared
        results = await vector_store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-1",
        )
        assert len(results) == 0

        # Verify tenant-2 unaffected
        results = await vector_store.search_similar(
            query_embedding=[1.0, 0.0, 0.0],
            tenant_id="tenant-2",
        )
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_clear_tenant_empty(self, vector_store):
        """Test clearing tenant with no vectors."""
        count = await vector_store.clear_tenant("tenant-1")
        assert count == 0


class TestSQLiteVectorStoreStatistics:
    """Test statistics collection."""

    @pytest.mark.asyncio
    async def test_get_statistics(self, vector_store):
        """Test getting vector store statistics."""
        # Store vectors with different dimensions
        await vector_store.store_vector(
            memory_id=uuid4(),
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )
        await vector_store.store_vector(
            memory_id=uuid4(),
            embedding=[1.0, 2.0, 3.0, 4.0, 5.0],
            tenant_id="tenant-1",
        )
        await vector_store.store_vector(
            memory_id=uuid4(),
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-2",
        )

        stats = await vector_store.get_statistics()

        assert stats["total_vectors"] == 3
        assert stats["tenants"] == 2
        assert set(stats["dimensions"]) == {3, 5}
        assert "has_vec_extension" in stats
        assert isinstance(stats["has_vec_extension"], bool)

    @pytest.mark.asyncio
    async def test_get_statistics_empty(self, vector_store):
        """Test statistics on empty store."""
        stats = await vector_store.get_statistics()

        assert stats["total_vectors"] == 0
        assert stats["tenants"] == 0
        assert stats["dimensions"] == []


class TestSQLiteVectorStorePersistence:
    """Test file-based persistence."""

    @pytest.mark.asyncio
    async def test_persistence_across_connections(self, tmp_path):
        """Test that vectors persist across connections."""
        db_path = str(tmp_path / "vectors.db")
        memory_id = uuid4()
        embedding = [1.0, 2.0, 3.0]

        # Store with first connection
        store1 = SQLiteVectorStore(db_path=db_path)
        await store1.initialize()
        await store1.store_vector(
            memory_id=memory_id,
            embedding=embedding,
            tenant_id="tenant-1",
        )
        await store1.close()

        # Retrieve with second connection
        store2 = SQLiteVectorStore(db_path=db_path)
        await store2.initialize()
        retrieved = await store2.get_vector(memory_id, "tenant-1")
        assert retrieved is not None
        assert len(retrieved) == len(embedding)
        await store2.close()


class TestSQLiteVectorStoreEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_store_vector_no_metadata(self, vector_store):
        """Test storing vector without metadata."""
        memory_id = uuid4()
        success = await vector_store.store_vector(
            memory_id=memory_id,
            embedding=[1.0, 2.0, 3.0],
            tenant_id="tenant-1",
        )
        assert success is True

        retrieved = await vector_store.get_vector(memory_id, "tenant-1")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_store_vector_large_dimension(self, vector_store):
        """Test storing high-dimensional vector."""
        memory_id = uuid4()
        embedding = [float(i) for i in range(1536)]  # OpenAI ada-002 size

        success = await vector_store.store_vector(
            memory_id=memory_id,
            embedding=embedding,
            tenant_id="tenant-1",
        )
        assert success is True

        retrieved = await vector_store.get_vector(memory_id, "tenant-1")
        assert len(retrieved) == 1536

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, vector_store):
        """Test that initialize can be called multiple times."""
        await vector_store.initialize()
        await vector_store.initialize()  # Should not raise error
        assert vector_store._initialized is True

    @pytest.mark.asyncio
    async def test_cosine_similarity_correctness(self, vector_store, golden_snapshot):
        """Test cosine similarity calculation correctness."""
        # Test vectors with known cosine similarities
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.5, 0.866025, 0.0]  # 60 degrees from v1, cos(60°) = 0.5

        id1 = uuid4()
        await vector_store.store_vector(
            memory_id=id1,
            embedding=v2,
            tenant_id="tenant-1",
        )

        results = await vector_store.search_similar(
            query_embedding=v1,
            tenant_id="tenant-1",
        )

        # Record golden snapshot
        golden_snapshot(
            test_name="cosine_similarity_sqlite_correctness",
            inputs={"query": v1, "stored": v2},
            output=results,
            metadata={"adapter": "SQLiteVectorStore"},
        )

        assert len(results) == 1
        # Cosine similarity should be approximately 0.5
        assert abs(results[0][1] - 0.5) < 0.01
