from unittest.mock import AsyncMock, patch

import pytest

from apps.memory_api.config import settings
from apps.memory_api.services.embedding import EmbeddingService


@pytest.mark.asyncio
async def test_embedding_service_distributed_routing():
    """Test that EmbeddingService routes to MLServiceClient when in distributed mode."""
    # Setup
    original_profile = settings.RAE_PROFILE
    original_ml_url = settings.ML_SERVICE_URL

    settings.RAE_PROFILE = "distributed"
    settings.ML_SERVICE_URL = "http://node1:8001"

    service = EmbeddingService()

    # Mock MLServiceClient
    with patch(
        "apps.memory_api.services.ml_service_client.MLServiceClient"
    ) as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.generate_embeddings = AsyncMock(
            return_value={"embeddings": [[0.1, 0.2, 0.3]], "dimension": 3}
        )
        mock_instance.close = AsyncMock()

        # Execute
        texts = ["hello"]
        result = await service.generate_embeddings_async(texts)

        # Verify
        assert result == [[0.1, 0.2, 0.3]]
        MockClient.assert_called_once_with(base_url="http://node1:8001")
        mock_instance.generate_embeddings.assert_called_once_with(texts)
        mock_instance.close.assert_called_once()

    # Cleanup
    settings.RAE_PROFILE = original_profile
    settings.ML_SERVICE_URL = original_ml_url


@pytest.mark.asyncio
@pytest.mark.skip("Requires OPENAI_API_KEY for embedding generation or litellm mocking")
async def test_embedding_service_local_fallback():
    """Test that EmbeddingService falls back to local when not in distributed mode."""
    # Setup
    original_profile = settings.RAE_PROFILE
    settings.RAE_PROFILE = "standard"

    # Mock SentenceTransformer to avoid torch/cuda warnings during initialization
    with patch("apps.memory_api.services.embedding.EmbeddingService._initialize_model"):
        service = EmbeddingService()

        # Mock local generate_embeddings (sync)
        with patch.object(
            service, "generate_embeddings", return_value=[[0.4, 0.5, 0.6]]
        ) as mock_sync:
            # Execute
            texts = ["local"]
            result = await service.generate_embeddings_async(texts)

            # Verify
            # When LiteLLM fallback is used, it returns zeros or actual embeddings
            # We check if it returns a list of lists of floats
            assert isinstance(result, list)
            assert len(result) == 1
            assert len(result[0]) > 0
            assert isinstance(result[0][0], float)
            mock_sync.assert_called_once_with(texts)

    # Cleanup
    settings.RAE_PROFILE = original_profile
