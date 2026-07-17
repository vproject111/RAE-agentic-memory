from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.engine import EmeraldReranker, HybridSearchEngine


@pytest.mark.asyncio
async def test_emerald_reranker_logic():
    mock_embedding = MagicMock()
    mock_storage = MagicMock()
    reranker = EmeraldReranker(mock_embedding, mock_storage)

    candidates = [(uuid4(), 0.9, 0.5), (uuid4(), 0.8, 0.4)]
    res = await reranker.rerank("query", candidates, "tenant1", limit=1)
    assert len(res) == 1


@pytest.mark.asyncio
async def test_hybrid_search_engine_uses_reranker():
    id1, id2 = uuid4(), uuid4()
    mock_strategy = MagicMock()
    mock_strategy.search = AsyncMock(return_value=[(id1, 0.8, 0.5), (id2, 0.7, 0.4)])
    mock_strategy.get_strategy_weight.return_value = 1.0
    mock_strategy.get_strategy_name.return_value = "test"

    mock_reranker = MagicMock()
    # Reranker returns only one boosted result
    mock_reranker.rerank = AsyncMock(return_value=[(id1, 0.99, 0.5)])

    mock_embedding = MagicMock()
    mock_storage = MagicMock()
    mock_storage.get_memories_batch = AsyncMock(
        return_value=[
            {"id": id1, "content": "doc1", "metadata": {"importance": 0.5}},
            {"id": id2, "content": "doc2", "metadata": {"importance": 0.4}},
        ]
    )

    engine = HybridSearchEngine(
        strategies={"test": mock_strategy},
        embedding_provider=mock_embedding,
        memory_storage=mock_storage,
        reranker=mock_reranker,
    )

    # Force using the external reranker by clearing the internal one
    if hasattr(engine.fusion_strategy, "gateway"):
        engine.fusion_strategy.gateway.reranker = None

    res = await engine.search("query", "tenant1", enable_reranking=True)
    # The hybrid engine fuses results, typically keeping the candidate set size
    assert len(res) >= 1
    assert mock_reranker.rerank.called
