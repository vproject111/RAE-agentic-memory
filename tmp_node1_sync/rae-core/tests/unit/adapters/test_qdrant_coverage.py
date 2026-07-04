"""Unit tests for QdrantVectorStore to achieve 100% coverage."""

import sys
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestQdrantVectorStoreCoverage:
    """Test suite for QdrantVectorStore coverage gaps."""

    @pytest.mark.asyncio
    async def test_init_no_qdrant_client(self):
        """Test initialization when qdrant-client is not available."""
        with patch.dict(sys.modules, {"qdrant_client": None}):
            # We need to reload or bypass the sys.modules check in __init__
            from rae_core.adapters.qdrant import QdrantVectorStore

            with patch("rae_core.adapters.qdrant.QdrantClient", None):
                with pytest.raises(ImportError, match="qdrant-client is required"):
                    QdrantVectorStore()

    @pytest.mark.asyncio
    async def test_add_vector_failure(self):
        """Test add_vector returning False on exception."""
        from rae_core.adapters.qdrant import QdrantVectorStore

        mock_client = AsyncMock()
        mock_client.upsert.side_effect = Exception("Upsert failed")

        with patch("rae_core.adapters.qdrant.QdrantClient", return_value=mock_client):
            store = QdrantVectorStore(client=mock_client)
            res = await store.add_vector(uuid4(), [0.1], "t1", "a1", "l1")
            assert res is False

    @pytest.mark.asyncio
    async def test_update_vector(self):
        """Test the update_vector wrapper."""
        from rae_core.adapters.qdrant import QdrantVectorStore

        mock_client = AsyncMock()
        with patch("rae_core.adapters.qdrant.QdrantClient", return_value=mock_client):
            store = QdrantVectorStore(client=mock_client)
            mid = uuid4()
            res = await store.update_vector(mid, [0.1], "t1", {"agent_id": "a1"})
            assert res is True
            assert mock_client.upsert.call_count == 1

    @pytest.mark.asyncio
    async def test_search_similar_with_filters(self):
        """Test search_similar with layer and threshold to cover those branches."""
        from rae_core.adapters.qdrant import QdrantVectorStore

        mock_client = AsyncMock()
        mock_client.search.return_value = []
        with patch("rae_core.adapters.qdrant.QdrantClient", return_value=mock_client):
            store = QdrantVectorStore(client=mock_client)
            await store.search_similar(
                [0.1], "t1", layer="working", score_threshold=0.5
            )

            call_args = mock_client.search.call_args
            assert "score_threshold" in call_args.kwargs
            assert call_args.kwargs["score_threshold"] == 0.5
            # Filter should contain layer match
            assert "query_filter" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_delete_vector_not_found(self):
        """Test delete_vector when vector is not found."""
        from rae_core.adapters.qdrant import QdrantVectorStore

        mock_client = AsyncMock()
        mock_client.retrieve.return_value = []
        with patch("rae_core.adapters.qdrant.QdrantClient", return_value=mock_client):
            store = QdrantVectorStore(client=mock_client)
            res = await store.delete_vector(uuid4(), "t1")
            assert res is False
            assert mock_client.delete.call_count == 0

    @pytest.mark.asyncio
    async def test_delete_vector_wrong_tenant(self):
        """Test delete_vector when tenant doesn't match."""
        from rae_core.adapters.qdrant import QdrantVectorStore

        mock_client = AsyncMock()
        mock_res = MagicMock()
        mock_res.payload = {"tenant_id": "other"}
        mock_client.retrieve.return_value = [mock_res]
        with patch("rae_core.adapters.qdrant.QdrantClient", return_value=mock_client):
            store = QdrantVectorStore(client=mock_client)
            res = await store.delete_vector(uuid4(), "t1")
            assert res is False
            assert mock_client.delete.call_count == 0
