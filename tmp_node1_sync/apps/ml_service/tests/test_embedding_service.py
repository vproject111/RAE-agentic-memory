from unittest.mock import patch

import pytest

from apps.ml_service.services.embedding_service import EmbeddingMLService


@pytest.fixture
def mock_litellm_embedding():
    with patch(
        "apps.ml_service.services.embedding_service.litellm.embedding"
    ) as mock_emb:
        mock_emb.return_value = {
            "data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]
        }
        yield mock_emb


@pytest.fixture
def mock_litellm_aembedding():
    with patch(
        "apps.ml_service.services.embedding_service.litellm.aembedding"
    ) as mock_emb:
        mock_emb.return_value = {
            "data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]
        }
        yield mock_emb


@pytest.fixture
def embedding_service():
    EmbeddingMLService._instance = None
    service = EmbeddingMLService(model_name="test-model")
    yield service
    EmbeddingMLService._instance = None


def test_embedding_service_init(embedding_service):
    """Test that the embedding service initializes correctly."""
    assert embedding_service.model_name == "test-model"


def test_embedding_service_singleton_behavior():
    """Test singleton behavior of EmbeddingMLService."""
    EmbeddingMLService._instance = None
    service1 = EmbeddingMLService(model_name="model-a")
    service2 = EmbeddingMLService(model_name="model-b")

    assert service1 is service2
    assert service1.model_name == "model-a"


def test_generate_embeddings_sync(embedding_service, mock_litellm_embedding):
    """Test generating embeddings synchronously."""
    texts = ["hello", "world"]
    embeddings = embedding_service.generate_embeddings(texts)

    mock_litellm_embedding.assert_called_once_with(model="test-model", input=texts)
    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]


@pytest.mark.asyncio
async def test_generate_embeddings_async(embedding_service, mock_litellm_aembedding):
    """Test generating embeddings asynchronously."""
    texts = ["hello", "world"]
    embeddings = await embedding_service.generate_embeddings_async(texts)

    mock_litellm_aembedding.assert_called_once_with(model="test-model", input=texts)
    assert embeddings == [[0.1, 0.2], [0.3, 0.4]]


def test_generate_embeddings_empty_list(embedding_service):
    """Test generating embeddings for an empty list of texts."""
    embeddings = embedding_service.generate_embeddings([])
    assert embeddings == []


def test_get_embedding_dimension(embedding_service):
    """Test getting the embedding dimension."""
    # Based on our implementation in EmbeddingMLService
    service = EmbeddingMLService(model_name="nomic-embed")
    assert service.get_embedding_dimension() == 768

    EmbeddingMLService._instance = None
    service2 = EmbeddingMLService(model_name="text-embedding-3-small")
    assert service2.get_embedding_dimension() == 1536
