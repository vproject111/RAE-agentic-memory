from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from qdrant_client.http import models
from qdrant_client.models import (
    CollectionDescription,
    CollectionsResponse,
    Distance,
    Record,
    VectorParams,
)

from rae_core.adapters.qdrant import QdrantVectorStore


@pytest.fixture
def mock_qdrant_client():
    client = MagicMock()
    client.get_collections = AsyncMock()
    client.get_collection = AsyncMock()
    client.create_collection = AsyncMock()
    client.delete_collection = AsyncMock()
    client.update_collection = AsyncMock()
    client.upsert = AsyncMock()
    client.retrieve = AsyncMock()
    client.delete = AsyncMock()
    client.query_points = AsyncMock()
    client.count = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.fixture
def qdrant_store(mock_qdrant_client):
    return QdrantVectorStore(
        client=mock_qdrant_client, collection_name="test_collection"
    )


@pytest.mark.asyncio
async def test_qdrant_init_default_url():
    with patch("rae_core.adapters.qdrant.AsyncQdrantClient") as mock_client_class:
        store = QdrantVectorStore(client=None, url=None)
        mock_client_class.assert_called_once_with(
            url="http://localhost:6333", api_key=None
        )


@pytest.mark.asyncio
async def test_ensure_collection_single_vector(qdrant_store, mock_qdrant_client):
    # Mock collection exists but with single unnamed vector (not a dict)
    mock_qdrant_client.get_collections.return_value = CollectionsResponse(
        collections=[CollectionDescription(name="test_collection")]
    )

    mock_collection_info = MagicMock()
    # vectors is NOT a dict
    mock_collection_info.config.params.vectors = VectorParams(
        size=384, distance=Distance.COSINE
    )
    mock_qdrant_client.get_collection.return_value = mock_collection_info

    # We want "dense" vector (self.vector_name="dense")
    # This should trigger the 'else' block at line 94
    await qdrant_store._ensure_collection()
    assert qdrant_store._initialized is True


@pytest.mark.asyncio
async def test_ensure_vector_config_already_known(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    qdrant_store._known_vectors = {"already_there"}

    await qdrant_store.ensure_vector_config("already_there", 128)
    mock_qdrant_client.get_collection.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_vector_config_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.get_collection.side_effect = Exception("API error")

    # Should not raise exception but log it
    await qdrant_store.ensure_vector_config("new_one", 128)
    # Line 152 covered


@pytest.mark.asyncio
async def test_build_filter_extended(qdrant_store):
    f = qdrant_store._build_filter(
        tenant_id="t1", session_id="s1", project="p1", extra_filters={"foo": "bar"}
    )

    keys = [cond.key for cond in f.must]
    assert "session_id" in keys
    assert "project" in keys
    assert "foo" in keys


@pytest.mark.asyncio
async def test_batch_store_vectors_detailed_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True

    class DetailedException(Exception):
        def __init__(self, msg, content=None, response=None):
            super().__init__(msg)
            self.content = content
            self.response = response

    mock_qdrant_client.upsert.side_effect = DetailedException(
        "fail", content="bad payload", response="400"
    )

    res = await qdrant_store.batch_store_vectors([(uuid4(), [0.1] * 384, {})], "t1")
    assert res == 0


@pytest.mark.asyncio
async def test_get_vector_unnamed(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()

    mock_qdrant_client.retrieve.return_value = [
        Record(
            id=str(mem_id),
            vector=[0.1] * 384,  # Not a dict
            payload={"tenant_id": "t1"},
        )
    ]

    vec = await qdrant_store.get_vector(mem_id, "t1")
    assert vec == [0.1] * 384


@pytest.mark.asyncio
async def test_get_vector_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.retrieve.side_effect = Exception("Retrieve fail")

    vec = await qdrant_store.get_vector(uuid4(), "t1")
    assert vec is None


@pytest.mark.asyncio
async def test_get_vector_no_vector(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()

    mock_qdrant_client.retrieve.return_value = [
        Record(
            id=str(mem_id), vector=None, payload={"tenant_id": "t1"}  # Missing vector
        )
    ]

    vec = await qdrant_store.get_vector(mem_id, "t1")
    assert vec is None


@pytest.mark.asyncio
async def test_update_vector(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()
    res = await qdrant_store.update_vector(mem_id, [0.1] * 384, "t1")
    assert res is True
    mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_delete_vector_tenant_mismatch(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()
    mock_qdrant_client.retrieve.return_value = [
        Record(id=str(mem_id), payload={"tenant_id": "wrong"})
    ]

    res = await qdrant_store.delete_vector(mem_id, "correct")
    assert res is False
    mock_qdrant_client.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_vector_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.retrieve.side_effect = Exception("DB error")
    res = await qdrant_store.delete_vector(uuid4(), "t1")
    assert res is False


@pytest.mark.asyncio
async def test_search_similar_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.query_points.side_effect = Exception("Search error")
    res = await qdrant_store.search_similar([0.1] * 384, "t1")
    assert res == []


@pytest.mark.asyncio
async def test_count_vectors_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.count.side_effect = Exception("Count error")
    res = await qdrant_store.count_vectors("t1")
    assert res == 0


@pytest.mark.asyncio
async def test_delete_by_layer_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.delete.side_effect = Exception("Delete error")
    res = await qdrant_store.delete_by_layer("t1", "a1", "l1")
    assert res == 0


@pytest.mark.asyncio
async def test_search_with_contradiction_penalty_no_results(
    qdrant_store, mock_qdrant_client
):
    qdrant_store._initialized = True
    mock_qdrant_client.query_points.return_value = models.QueryResponse(points=[])
    res = await qdrant_store.search_with_contradiction_penalty([0.1] * 384, "t1")
    assert res == []
