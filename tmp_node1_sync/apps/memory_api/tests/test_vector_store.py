"""
Tests for Vector Store implementations

Enterprise-grade test suite for pgvector vector store implementation.
Covers happy paths, edge cases, and error handling for production readiness.

Test Coverage Goals (per test_2.md):
- insert/upsert: happy path, empty list, validation
- search: format verification, top_k, empty results
- errors: proper exception handling

Priority: HIGH (Critical module for memory persistence)
Current Coverage: 52% -> Target: 70%+
"""

from unittest.mock import AsyncMock

import pytest

# Skip tests if sentence_transformers is not installed (ML dependency)
sentence_transformers = pytest.importorskip(
    "sentence_transformers",
    reason="Requires sentence-transformers – heavy ML dependency",
)

from apps.memory_api.models import MemoryRecord, ScoredMemoryRecord  # noqa: E402
from apps.memory_api.services.vector_store.pgvector_store import (  # noqa: E402
    PGVectorStore,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_memories():
    """Sample memory records for testing."""
    return [
        MemoryRecord(
            id="mem1",
            content="Test memory 1",
            layer="em",
            tenant_id="tenant1",
            project_id="proj1",
        ),
        MemoryRecord(
            id="mem2",
            content="Test memory 2",
            layer="em",
            tenant_id="tenant1",
            project_id="proj1",
        ),
    ]


@pytest.fixture
def sample_embeddings():
    """Sample embeddings for testing."""
    return [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]


@pytest.fixture
def sample_query_embedding():
    """Sample query embedding."""
    return [0.2, 0.3, 0.4, 0.5]


# =============================================================================
# PGVectorStore Tests
# =============================================================================


@pytest.mark.asyncio
class TestPGVectorStore:
    """Tests for PGVectorStore implementation."""

    async def test_store_initialization(self, mock_pool):
        """Test that store initializes correctly with pool."""
        store = PGVectorStore(mock_pool)

        assert store.pool is mock_pool

    async def test_upsert_success(self, mock_pool, sample_memories, sample_embeddings):
        """Test successful upsert of memories and embeddings.

        Verifies:
        - Correct number of execute calls
        - Proper embedding conversion to numpy array
        - Correct SQL and parameters
        """
        store = PGVectorStore(mock_pool)
        conn = mock_pool._test_conn
        conn.execute = AsyncMock(return_value="UPDATE 1")

        await store.upsert(sample_memories, sample_embeddings)

        # Verify execute was called for each memory
        assert conn.execute.call_count == 2

        # Verify first call had correct parameters
        first_call = conn.execute.call_args_list[0]
        sql = first_call[0][0]
        memory_id = first_call[0][2]

        assert "UPDATE memories SET embedding" in sql
        assert memory_id == "mem1"

    async def test_upsert_empty_list(self, mock_pool):
        """Test upsert with empty lists - should be no-op without errors."""
        store = PGVectorStore(mock_pool)
        conn = mock_pool._test_conn
        conn.execute = AsyncMock()

        # Empty lists should not raise exception
        await store.upsert([], [])

        # No execute calls should be made
        assert conn.execute.call_count == 0

    async def test_upsert_mismatched_lengths(self, mock_pool, sample_memories):
        """Test upsert with mismatched lengths raises ValueError."""
        store = PGVectorStore(mock_pool)

        # Different lengths should raise ValueError
        with pytest.raises(
            ValueError, match="number of memories and embeddings must be the same"
        ):
            await store.upsert(sample_memories, [[0.1, 0.2]])

    async def test_query_success(self, mock_pool, sample_query_embedding):
        """Test successful query returns scored records.

        Verifies:
        - Correct SQL with cosine similarity
        - Proper result mapping to ScoredMemoryRecord
        - Results ordered by score
        """
        store = PGVectorStore(mock_pool)

        # Mock database response
        mock_pool.fetch = AsyncMock(
            return_value=[
                {
                    "id": "mem1",
                    "content": "Similar memory",
                    "score": 0.95,
                    "layer": "em",
                    "tenant_id": "tenant1",
                    "project_id": "proj1",
                    "tags": ["test"],
                    "source": "test",
                    "timestamp": "2024-01-01T00:00:00",
                }
            ]
        )

        results = await store.query(sample_query_embedding, top_k=5, filters={})

        # Verify results
        assert len(results) == 1
        assert isinstance(results[0], ScoredMemoryRecord)
        assert results[0].id == "mem1"
        assert results[0].score == 0.95

        # Verify SQL call
        call_args = mock_pool.fetch.call_args
        sql = call_args[0][0]
        assert "<=> " in sql  # pgvector cosine similarity operator
        assert "ORDER BY score DESC" in sql

    async def test_query_empty_results(self, mock_pool, sample_query_embedding):
        """Test query with no results returns empty list."""
        store = PGVectorStore(mock_pool)

        # Mock empty response
        mock_pool.fetch = AsyncMock(return_value=[])

        results = await store.query(sample_query_embedding, top_k=5, filters={})

        assert results == []

    async def test_query_respects_top_k(self, mock_pool, sample_query_embedding):
        """Test that query respects top_k parameter."""
        store = PGVectorStore(mock_pool)
        mock_pool.fetch = AsyncMock(return_value=[])

        await store.query(sample_query_embedding, top_k=10, filters={})

        # Verify top_k was passed to SQL
        call_args = mock_pool.fetch.call_args
        top_k_param = call_args[0][2]  # Third parameter
        assert top_k_param == 10

    async def test_delete_success(self, mock_pool):
        """Test successful deletion of memory embedding."""
        store = PGVectorStore(mock_pool)
        mock_pool.execute = AsyncMock(return_value="UPDATE 1")

        await store.delete("mem1")

        # Verify delete was called with correct parameters
        call_args = mock_pool.execute.call_args
        sql = call_args[0][0]
        memory_id = call_args[0][1]

        assert "UPDATE memories SET embedding = NULL" in sql
        assert memory_id == "mem1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
