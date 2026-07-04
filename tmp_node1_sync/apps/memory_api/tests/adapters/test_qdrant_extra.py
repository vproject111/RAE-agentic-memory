from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_adapters.qdrant import QdrantVectorStore


@pytest.mark.asyncio
async def test_batch_store_vectors_empty():
    store = QdrantVectorStore()
    assert await store.batch_store_vectors([], "t1") == 0


@pytest.mark.asyncio
async def test_search_similar_with_session_id():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()
    mock_client.search = AsyncMock(return_value=[])

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    await store.search_similar([0.1], "t1", session_id="s1")
    call_args = mock_client.search.call_args
    # Check if session_id is in filter
    filter_keys = [c["key"] for c in call_args.kwargs["query_filter"]["must"]]
    assert "session_id" in filter_keys


@pytest.mark.asyncio
async def test_search_with_contradiction_penalty_missing_vectors():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()
    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    id1 = uuid4()
    id2 = uuid4()
    id3 = uuid4()

    with patch.object(
        store,
        "search_similar",
        AsyncMock(return_value=[(id1, 0.9), (id2, 0.8), (id3, 0.7)]),
    ):
        # Mock get_vector to return vector for id1 and id3, but NOT for id2
        # This will cover lines 470 and 474
        with patch.object(
            store,
            "get_vector",
            AsyncMock(
                side_effect=lambda memory_id, tenant_id: (
                    [1.0] if memory_id != id2 else None
                )
            ),
        ):
            results = await store.search_with_contradiction_penalty([1.0], "t1")
            assert len(results) == 3
            # id2 should have no penalty
            id2_res = next(r for r in results if r[0] == id2)
            assert id2_res[1] == 0.8  # Original score


@pytest.mark.asyncio
async def test_search_similar_with_agent_id():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()
    mock_client.search = AsyncMock(return_value=[])

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    await store.search_similar([0.1], "t1", agent_id="a1")
    call_args = mock_client.search.call_args
    filter_keys = [c["key"] for c in call_args.kwargs["query_filter"]["must"]]
    assert "agent_id" in filter_keys


@pytest.mark.asyncio
async def test_count_vectors_with_layer():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()

    mock_res = MagicMock()
    mock_res.count = 5
    mock_client.count = AsyncMock(return_value=mock_res)

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    count = await store.count_vectors("t1", layer="episodic")
    assert count == 5
    call_args = mock_client.count.call_args
    assert "layer" in str(call_args.kwargs["count_filter"])


@pytest.mark.asyncio
async def test_all_qdrant_methods_exception_handling():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()
    # Trigger exception in every client method
    mock_client.upsert = AsyncMock(side_effect=Exception("Error"))
    mock_client.search = AsyncMock(side_effect=Exception("Error"))
    mock_client.retrieve = AsyncMock(side_effect=Exception("Error"))
    mock_client.delete = AsyncMock(side_effect=Exception("Error"))
    mock_client.count = AsyncMock(side_effect=Exception("Error"))

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    # Test exceptions in all methods
    assert await store.add_vector(uuid4(), [0.1], "t1", "a1", "l1") is False
    assert await store.batch_store_vectors([(uuid4(), [0.1], {})], "t1") == 0
    assert await store.search_similar([0.1], "t1") == []
    assert await store.get_vector(uuid4(), "t1") is None
    assert await store.delete_vector(uuid4(), "t1") is False
    assert await store.delete_by_layer("t1", "a1", "l1") == 0
    assert await store.count_vectors("t1") == 0


@pytest.mark.asyncio
async def test_qdrant_init_with_url():
    # Mock AsyncQdrantClient
    with patch("rae_adapters.qdrant.AsyncQdrantClient") as mock_client_cls:
        QdrantVectorStore(url="http://localhost:6333", api_key="test-key")
        mock_client_cls.assert_called_once_with(
            url="http://localhost:6333", api_key="test-key"
        )


@pytest.mark.asyncio
async def test_search_similar_exception():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()
    mock_client.search = AsyncMock(side_effect=Exception("Error"))

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    results = await store.search_similar([0.1, 0.2], "t1")
    assert results == []


@pytest.mark.asyncio
async def test_get_vector_tenant_mismatch():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()

    mock_result = MagicMock()
    mock_result.payload = {"tenant_id": "other_tenant"}
    mock_client.retrieve = AsyncMock(return_value=[mock_result])

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    res = await store.get_vector(uuid4(), "t1")
    assert res is None


@pytest.mark.asyncio
async def test_delete_vector_not_found_or_tenant_mismatch():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()

    # Not found
    mock_client.retrieve = AsyncMock(return_value=[])
    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    assert await store.delete_vector(uuid4(), "t1") is False

    # Tenant mismatch
    mock_result = MagicMock()
    mock_result.payload = {"tenant_id": "other"}
    mock_client.retrieve = AsyncMock(return_value=[mock_result])
    assert await store.delete_vector(uuid4(), "t1") is False


@pytest.mark.asyncio
async def test_search_with_contradiction_penalty_low_results():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    # Mock search_similar to return 1 result
    with patch.object(
        store, "search_similar", AsyncMock(return_value=[(uuid4(), 0.9)])
    ):
        results = await store.search_with_contradiction_penalty([0.1], "t1")
        assert len(results) == 1


@pytest.mark.asyncio
async def test_search_with_contradiction_penalty_full_logic():
    mock_client = AsyncMock()
    mock_client.get_collection = AsyncMock()

    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    id1 = uuid4()
    id2 = uuid4()

    # Mock search_similar
    with patch.object(
        store, "search_similar", AsyncMock(return_value=[(id1, 0.9), (id2, 0.8)])
    ):
        # Mock get_vector to return contradictory vectors (e.g. opposite)
        # Similarity should be < 0.15
        with patch.object(
            store, "get_vector", AsyncMock(side_effect=[[1.0, 0.0], [-1.0, 0.0]])
        ):
            results = await store.search_with_contradiction_penalty(
                [1.0, 0.0], "t1", penalty_factor=0.5
            )
            # Both should be penalized since they contradict each other
            assert len(results) == 2
            # 0.9 * 0.5 = 0.45, 0.8 * 0.5 = 0.4
            assert results[0][1] == pytest.approx(0.45)
            assert results[1][1] == pytest.approx(0.4)


def test_cosine_similarity_edge_cases():
    store = QdrantVectorStore()

    # Different lengths
    assert store._cosine_similarity([1.0], [1.0, 2.0]) == 0.0

    # Zero magnitudes
    assert store._cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    assert store._cosine_similarity([1.0, 1.0], [0.0, 0.0]) == 0.0
