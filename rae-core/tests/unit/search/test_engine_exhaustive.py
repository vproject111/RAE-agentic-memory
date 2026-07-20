"""Exhaustive unit tests for Hybrid Search Engine and Emerald Reranker."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.search.engine import EmeraldReranker, HybridSearchEngine
from rae_core.search.strategies import SearchStrategy


@pytest.mark.asyncio
async def test_emerald_reranker_exhaustive():
    emb_provider = AsyncMock(spec=IEmbeddingProvider)
    storage = AsyncMock(spec=IMemoryStorage)

    reranker = EmeraldReranker(emb_provider, storage)

    # 1. Test None provider/storage
    reranker_none = EmeraldReranker(None, None)
    candidates = [(uuid4(), 0.9, 0.5)]
    res = await reranker_none.rerank("query", candidates, "tenant")
    assert res == candidates

    # 2. Test full reranking logic
    m_id = uuid4()
    candidates = [(m_id, 0.5, 0.8, {"original": "data"})]

    emb_provider.embed_text.side_effect = [
        [1.0, 0.0],  # query embedding
        [1.0, 0.0],  # memory embedding
    ]

    memory_mock = MagicMock()
    memory_mock.content = "Memory content"
    storage.get_memory.return_value = memory_mock

    res = await reranker.rerank("query", candidates, "tenant")
    assert len(res) == 1
    assert res[0][0] == m_id
    assert (
        res[0][1] > 0.5
    )  # semantic (1.0 * 0.7) + original (0.5 * 0.3) = 0.7 + 0.15 = 0.85

    # 3. Test memory not found
    storage.get_memory.return_value = None
    res = await reranker.rerank("query", candidates, "tenant")
    assert res[0][0] == m_id

    # 4. Test exception handling
    emb_provider.embed_text.side_effect = Exception("Embed failed")
    res = await reranker.rerank("query", candidates, "tenant")
    assert res == candidates

    # 5. Test unpackers
    assert reranker._unpack_candidate_with_audit((m_id, 0.5)) == (m_id, 0.5, 0.0, {})
    assert reranker._unpack_candidate_with_audit((m_id, 0.5, 0.8)) == (
        m_id,
        0.5,
        0.8,
        {},
    )
    with pytest.raises(ValueError):
        reranker._unpack_candidate_with_audit((m_id,))

    assert reranker._unpack_candidate((m_id, 0.5, 0.8, {})) == (m_id, 0.5, 0.8)
    assert reranker._unpack_candidate((m_id, 0.5)) == (m_id, 0.5, 0.0)
    with pytest.raises(ValueError):
        reranker._unpack_candidate((m_id,))


@pytest.mark.asyncio
async def test_hybrid_search_engine_exhaustive():
    strategy_mock = AsyncMock(spec=SearchStrategy)
    emb_provider = AsyncMock(spec=IEmbeddingProvider)
    storage = AsyncMock(spec=IMemoryStorage)

    strategies = {"vector": strategy_mock}
    engine = HybridSearchEngine(strategies, emb_provider, storage)

    m_id = uuid4()
    strategy_mock.search.return_value = [(m_id, 0.9)]

    # Mock storage.get_memories_batch
    storage.get_memories_batch = AsyncMock(
        return_value=[{"id": m_id, "content": "test", "metadata": {}}]
    )

    # 1. Successful search
    results = await engine.search("query", "tenant")
    assert len(results) > 0

    # 2. No active strategies
    results_empty = await engine.search("query", "tenant", strategies=["nonexistent"])
    assert results_empty == []

    # 3. Strategy failure
    strategy_mock.search.side_effect = Exception("Strategy failed")
    results_fail = await engine.search("query", "tenant")
    assert results_fail == []

    # 4. Batch fetch failure
    strategy_mock.search.side_effect = None
    strategy_mock.search.return_value = [(m_id, 0.9)]
    storage.get_memories_batch.side_effect = Exception("Batch failed")
    results_batch_fail = await engine.search("query", "tenant")
    assert len(results_batch_fail) > 0


@pytest.mark.asyncio
async def test_hybrid_search_engine_reranking_branches():
    strategy_mock = AsyncMock(spec=SearchStrategy)
    emb_provider = AsyncMock(spec=IEmbeddingProvider)
    storage = AsyncMock(spec=IMemoryStorage)

    strategies = {"vector": strategy_mock}
    engine = HybridSearchEngine(strategies, emb_provider, storage)

    m1, m2 = uuid4(), uuid4()
    strategy_mock.search.return_value = [(m1, 0.9), (m2, 0.8)]
    storage.get_memories_batch = AsyncMock(return_value=[])

    # 1. Reranking skip if fusion_strategy has reranker
    engine.fusion_strategy.gateway = AsyncMock()
    engine.fusion_strategy.gateway.reranker = MagicMock()
    engine.fusion_strategy.gateway.fuse = AsyncMock(return_value=[(m1, 0.95)])

    res = await engine.search("query", "tenant", enable_reranking=True)
    assert len(res) > 0

    # 2. Reranking with default EmeraldReranker
    engine.fusion_strategy.gateway.reranker = None
    m3 = uuid4()
    # Mock EmeraldReranker
    with patch("rae_core.search.engine.EmeraldReranker") as MockReranker:
        mock_instance = MockReranker.return_value
        mock_instance.rerank = AsyncMock(return_value=[(m1, 1.0, 1.0)])

        # Fuse must return > 1 results to trigger reranking
        engine.fusion_strategy.gateway.fuse = AsyncMock(
            return_value=[(m1, 0.95), (m3, 0.9)]
        )

        res = await engine.search("query", "tenant", enable_reranking=True)
        assert len(res) == 1
        assert res[0][1] == 1.0
