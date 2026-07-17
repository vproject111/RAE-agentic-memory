from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from qdrant_client.http import models
from qdrant_client.models import (
    CollectionDescription,
    CollectionsResponse,
    Distance,
    Record,
    ScoredPoint,
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
async def test_ensure_collection_exists(qdrant_store, mock_qdrant_client):
    # Mock collection already exists and matches
    mock_qdrant_client.get_collections.return_value = CollectionsResponse(
        collections=[CollectionDescription(name="test_collection")]
    )

    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors = {
        "dense": VectorParams(size=384, distance=Distance.COSINE)
    }
    mock_qdrant_client.get_collection.return_value = mock_collection_info

    await qdrant_store._ensure_collection()

    assert qdrant_store._initialized is True
    mock_qdrant_client.get_collections.assert_called_once()
    mock_qdrant_client.create_collection.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_collection_creates_if_missing(qdrant_store, mock_qdrant_client):
    mock_qdrant_client.get_collections.return_value = CollectionsResponse(
        collections=[]
    )

    await qdrant_store._ensure_collection()

    assert qdrant_store._initialized is True
    mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_collection_recreates_on_mismatch(
    qdrant_store, mock_qdrant_client
):
    mock_qdrant_client.get_collections.return_value = CollectionsResponse(
        collections=[CollectionDescription(name="test_collection")]
    )

    mock_collection_info = MagicMock()
    # Mismatch in size: 512 instead of 384
    mock_collection_info.config.params.vectors = {
        "dense": VectorParams(size=512, distance=Distance.COSINE)
    }
    mock_qdrant_client.get_collection.return_value = mock_collection_info

    await qdrant_store._ensure_collection()

    mock_qdrant_client.delete_collection.assert_called_once_with("test_collection")
    mock_qdrant_client.create_collection.assert_called_once()


@pytest.mark.asyncio
async def test_store_vector(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()
    emb = [0.1] * 384
    tenant_id = "tenant1"

    success = await qdrant_store.store_vector(mem_id, emb, tenant_id, {"meta": "data"})

    assert success is True
    mock_qdrant_client.upsert.assert_called_once()
    call_args = mock_qdrant_client.upsert.call_args[1]
    assert call_args["collection_name"] == "test_collection"
    assert len(call_args["points"]) == 1
    assert call_args["points"][0].id == str(mem_id)
    assert call_args["points"][0].vector["dense"] == emb
    assert call_args["points"][0].payload["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_batch_store_vectors_empty(qdrant_store, mock_qdrant_client):
    count = await qdrant_store.batch_store_vectors([], "tenant1")
    assert count == 0
    mock_qdrant_client.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_get_vector(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()
    tenant_id = "tenant1"

    mock_qdrant_client.retrieve.return_value = [
        Record(
            id=str(mem_id),
            vector={"dense": [0.1] * 384},
            payload={"tenant_id": tenant_id},
        )
    ]

    vec = await qdrant_store.get_vector(mem_id, tenant_id)
    assert vec == [0.1] * 384


@pytest.mark.asyncio
async def test_get_vector_not_found(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.retrieve.return_value = []

    vec = await qdrant_store.get_vector(uuid4(), "tenant1")
    assert vec is None


@pytest.mark.asyncio
async def test_get_vector_tenant_mismatch(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()

    mock_qdrant_client.retrieve.return_value = [
        Record(
            id=str(mem_id),
            vector={"dense": [0.1] * 384},
            payload={"tenant_id": "other_tenant"},
        )
    ]

    vec = await qdrant_store.get_vector(mem_id, "tenant1")
    assert vec is None


@pytest.mark.asyncio
async def test_delete_vector(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mem_id = uuid4()
    tenant_id = "tenant1"

    mock_qdrant_client.retrieve.return_value = [
        Record(id=str(mem_id), payload={"tenant_id": tenant_id})
    ]

    success = await qdrant_store.delete_vector(mem_id, tenant_id)
    assert success is True
    mock_qdrant_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_search_similar(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    query_emb = [0.1] * 384
    tenant_id = "tenant1"
    mem_id = uuid4()

    mock_qdrant_client.query_points.return_value = models.QueryResponse(
        points=[
            ScoredPoint(
                id=str(mem_id),
                version=1,
                score=0.95,
                payload={"memory_id": str(mem_id), "tenant_id": tenant_id},
                vector=None,
            )
        ]
    )

    results = await qdrant_store.search_similar(query_emb, tenant_id)
    assert len(results) == 1
    assert results[0] == (mem_id, 0.95)


@pytest.mark.asyncio
async def test_count_vectors(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_count_result = MagicMock()
    mock_count_result.count = 42
    mock_qdrant_client.count.return_value = mock_count_result

    count = await qdrant_store.count_vectors("tenant1")
    assert count == 42


@pytest.mark.asyncio
async def test_delete_by_layer(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    result = await qdrant_store.delete_by_layer("tenant1", "agent1", "working")
    assert result == 1
    mock_qdrant_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_close(qdrant_store, mock_qdrant_client):
    await qdrant_store.close()
    mock_qdrant_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_search_with_contradiction_penalty(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    query_emb = [1.0, 0.0]
    tenant_id = "tenant1"
    mem_id = uuid4()

    # Mock search_similar
    mock_qdrant_client.query_points.return_value = models.QueryResponse(
        points=[
            ScoredPoint(
                id=str(mem_id),
                version=1,
                score=0.9,
                payload={"memory_id": str(mem_id), "tenant_id": tenant_id},
            )
        ]
    )

    # Mock get_vector for contradiction (similarity < threshold)
    # query [1,0], memory [0,1] -> similarity 0
    mock_qdrant_client.retrieve.return_value = [
        Record(
            id=str(mem_id),
            vector={"dense": [0.0, 1.0]},
            payload={"tenant_id": tenant_id},
        )
    ]

    results = await qdrant_store.search_with_contradiction_penalty(
        query_emb, tenant_id, penalty_factor=0.5, contradiction_threshold=0.5
    )

    assert len(results) == 1
    assert results[0][0] == mem_id
    assert results[0][1] == 0.9 * 0.5


@pytest.mark.asyncio
async def test_ensure_vector_config_new(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    qdrant_store._known_vectors = {"dense"}

    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors = {
        "dense": VectorParams(size=384, distance=Distance.COSINE)
    }
    mock_qdrant_client.get_collection.return_value = mock_collection_info

    await qdrant_store.ensure_vector_config("new_vector", 128)

    mock_qdrant_client.update_collection.assert_called_once()
    assert "new_vector" in qdrant_store._known_vectors


@pytest.mark.asyncio
async def test_batch_store_named_vectors(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    qdrant_store._known_vectors = {"dense"}
    mem_id = uuid4()
    emb = {"dense": [0.1] * 384, "other": [0.2] * 128}

    mock_collection_info = MagicMock()
    mock_collection_info.config.params.vectors = {
        "dense": VectorParams(size=384, distance=Distance.COSINE)
    }
    mock_qdrant_client.get_collection.return_value = mock_collection_info

    await qdrant_store.batch_store_vectors([(mem_id, emb, {})], "tenant1")

    # Should trigger update_collection for "other"
    mock_qdrant_client.update_collection.assert_called_once()
    mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_client_initialization():
    with patch("rae_core.adapters.qdrant.AsyncQdrantClient") as mock_client_class:
        store = QdrantVectorStore(url="http://remote:6333", api_key="secret")
        mock_client_class.assert_called_once_with(
            url="http://remote:6333", api_key="secret"
        )


@pytest.mark.asyncio
async def test_ensure_collection_exception_logging(qdrant_store, mock_qdrant_client):
    mock_qdrant_client.get_collections.side_effect = Exception("Connection error")
    await qdrant_store._ensure_collection()
    assert qdrant_store._initialized is False


@pytest.mark.asyncio
async def test_batch_store_vectors_exception(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    mock_qdrant_client.upsert.side_effect = Exception("Upsert failed")

    count = await qdrant_store.batch_store_vectors(
        [(uuid4(), [0.1] * 384, {})], "tenant1"
    )
    assert count == 0


@pytest.mark.asyncio
async def test_add_vector_legacy(qdrant_store, mock_qdrant_client):
    qdrant_store._initialized = True
    success = await qdrant_store.add_vector(
        uuid4(), [0.1] * 384, "tenant1", agent_id="agent1", layer="working"
    )
    assert success is True
    mock_qdrant_client.upsert.assert_called_once()
