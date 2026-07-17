from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.search.engine import EmeraldReranker, HybridSearchEngine


class TestSearchEngineCoverage:
    @pytest.mark.asyncio
    async def test_emerald_reranker_missing_deps(self):
        reranker = EmeraldReranker(None, None)
        candidates = [(uuid4(), 0.5, 0.5)]
        results = await reranker.rerank("query", candidates, "t1")
        assert results == candidates

    @pytest.mark.asyncio
    async def test_emerald_reranker_unpack_error(self):
        reranker = EmeraldReranker(MagicMock(), MagicMock())
        with pytest.raises(ValueError, match="Invalid candidate tuple length"):
            reranker._unpack_candidate_with_audit((uuid4(),))

    @pytest.mark.asyncio
    async def test_hybrid_search_batch_fetch_failure(self):
        mock_storage = MagicMock()
        mock_storage.get_memories_batch = AsyncMock(
            side_effect=Exception("Batch failure")
        )

        mock_strategy = MagicMock()
        mock_strategy.search = AsyncMock(return_value=[(uuid4(), 1.0, 0.5)])

        mock_provider = MagicMock()

        engine = HybridSearchEngine(
            strategies={"vector": mock_strategy},
            embedding_provider=mock_provider,
            memory_storage=mock_storage,
            math_controller=MagicMock(),
        )

        # We need to make sure fusion_strategy.fuse works
        engine.fusion_strategy = MagicMock()
        engine.fusion_strategy.fuse = AsyncMock(return_value=[(uuid4(), 1.0, 0.5)])

        results = await engine.search("query", "t1")
        assert len(results) == 1
        # The exception should be caught and logged, not raised
        assert mock_storage.get_memories_batch.called

    @pytest.mark.asyncio
    async def test_emerald_reranker_exception(self):
        mock_provider = MagicMock()
        mock_provider.embed_text = AsyncMock(side_effect=Exception("Embed failure"))
        reranker = EmeraldReranker(mock_provider, MagicMock())
        candidates = [(uuid4(), 0.5, 0.5)]
        results = await reranker.rerank("query", candidates, "t1")
        assert results == candidates

    def test_unpack_candidate_length_4(self):
        reranker = EmeraldReranker(None, None)
        m_id = uuid4()
        res = reranker._unpack_candidate((m_id, 0.5, 0.6, {}))
        assert res == (m_id, 0.5, 0.6)

    def test_unpack_candidate_invalid(self):
        reranker = EmeraldReranker(None, None)
        with pytest.raises(ValueError):
            reranker._unpack_candidate((uuid4(),))
