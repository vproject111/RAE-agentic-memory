from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.vector import IVectorStore
from rae_core.search.strategies.vector import VectorSearchStrategy


@pytest.fixture
def mock_components():
    store = Mock(spec=IVectorStore)
    store.search_similar = AsyncMock()

    embedder = Mock(spec=IEmbeddingProvider)
    embedder.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])

    return store, embedder


@pytest.mark.asyncio
async def test_vector_strategy_flow(mock_components):
    store, embedder = mock_components

    strategy = VectorSearchStrategy(
        vector_store=store, embedding_provider=embedder, default_weight=0.5
    )

    expected_id = uuid4()
    store.search_similar.return_value = [(expected_id, 0.85)]

    results = await strategy.search("test query", "tenant_1")

    # Verify flow
    embedder.embed_text.assert_called_once_with("test query")
    store.search_similar.assert_called_once()

    # Verify args passed to store
    call_kwargs = store.search_similar.call_args.kwargs
    assert call_kwargs["query_embedding"] == [0.1, 0.2, 0.3]
    assert call_kwargs["tenant_id"] == "tenant_1"

    # Verify result
    assert len(results) == 1
    assert results[0] == (expected_id, 0.85)


@pytest.mark.asyncio
async def test_vector_strategy_filters(mock_components):
    store, embedder = mock_components
    strategy = VectorSearchStrategy(store, embedder)

    filters = {"layer": "episodic", "score_threshold": 0.9}

    await strategy.search("q", "t", filters=filters)

    call_kwargs = store.search_similar.call_args.kwargs
    assert call_kwargs["layer"] == "episodic"
    assert call_kwargs["score_threshold"] == 0.9


def test_vector_strategy_properties(mock_components):
    store, embedder = mock_components
    strategy = VectorSearchStrategy(store, embedder, default_weight=0.8)

    assert strategy.get_strategy_name() == "vector"
    assert strategy.get_strategy_weight() == 0.8
