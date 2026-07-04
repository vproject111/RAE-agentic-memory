from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_adapters.qdrant import QdrantVectorStore


@pytest.mark.asyncio
async def test_ensure_collection_multivector():
    """Test that _ensure_collection creates collection with multi-vector config."""
    mock_client = AsyncMock()
    # Mock get_collection to raise error (collection not found)
    mock_client.get_collection.side_effect = Exception("Not found")

    store = QdrantVectorStore(client=mock_client)
    await store._ensure_collection()

    # Verify create_collection call
    mock_client.create_collection.assert_called_once()
    call_args = mock_client.create_collection.call_args
    assert call_args is not None

    vectors_config = call_args[1]["vectors_config"]
    assert "dense" in vectors_config
    assert "openai" in vectors_config
    assert "ollama" in vectors_config
    assert vectors_config["dense"].size == 384
    assert vectors_config["openai"].size == 1536
    assert vectors_config["ollama"].size == 768


@pytest.mark.asyncio
async def test_add_vector_determines_name():
    """Test that add_vector uses correct vector name based on dimension."""
    mock_client = AsyncMock()
    store = QdrantVectorStore(client=mock_client)
    store._initialized = True  # Skip ensure_collection logic for this test

    memory_id = uuid4()

    # Test 1536 dim (OpenAI)
    embedding_openai = [0.1] * 1536
    await store.add_vector(memory_id, embedding_openai, "tenant", "agent", "layer")

    call_args = mock_client.upsert.call_args
    points = call_args[1]["points"]
    assert points[0].vector.get("openai") is not None

    # Test 768 dim (Ollama)
    embedding_ollama = [0.1] * 768
    await store.add_vector(memory_id, embedding_ollama, "tenant", "agent", "layer")

    call_args = mock_client.upsert.call_args
    points = call_args[1]["points"]
    assert points[0].vector.get("ollama") is not None


@pytest.mark.asyncio
async def test_search_uses_correct_vector():
    """Test that search_similar uses correct named vector."""
    mock_client = AsyncMock()
    mock_client.search.return_value = []
    store = QdrantVectorStore(client=mock_client)
    store._initialized = True

    # Search with 384 dim
    await store.search_similar([0.1] * 384, "tenant")

    call_args = mock_client.search.call_args
    query_vector = call_args[1]["query_vector"]
    assert query_vector.name == "dense"

    # Search with 1536 dim
    await store.search_similar([0.1] * 1536, "tenant")

    call_args = mock_client.search.call_args
    query_vector = call_args[1]["query_vector"]
    assert query_vector.name == "openai"
