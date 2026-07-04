"""Extended tests for search strategies (Fulltext, Sparse/BM25)."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.search.strategies.fulltext import FullTextStrategy
from rae_core.search.strategies.sparse import SparseVectorStrategy


@pytest.fixture
def mock_storage():
    storage = Mock()
    storage.list_memories = AsyncMock()
    return storage


class TestFullTextStrategy:
    def test_compute_match_score(self, mock_storage):
        strat = FullTextStrategy(memory_storage=mock_storage)

        # Exact phrase match
        score = strat._compute_match_score("quick brown", "The quick brown fox", [])
        assert score == 1.0

        # Tag match
        score = strat._compute_match_score(
            "important", "content", ["important", "news"]
        )
        assert score >= 0.8

        # Word match
        score = strat._compute_match_score("python", "coding in python", [])
        assert score > 0

    @pytest.mark.asyncio
    async def test_search_fulltext(self, mock_storage):
        strat = FullTextStrategy(memory_storage=mock_storage)
        mem_id = uuid4()
        mock_storage.list_memories.return_value = [
            {"id": mem_id, "content": "Hello World", "tags": []}
        ]

        results = await strat.search("hello", "t1")
        assert len(results) == 1
        assert results[0][0] == mem_id
        assert results[0][1] > 0


class TestSparseVectorStrategy:
    @pytest.mark.asyncio
    async def test_bm25_scoring(self, mock_storage):
        strat = SparseVectorStrategy(memory_storage=mock_storage)

        id1, id2 = uuid4(), uuid4()
        # Corpus: "python coding", "java coding"
        # Query: "python" -> only id1 matches
        mock_storage.list_memories.return_value = [
            {"id": id1, "content": "python coding"},
            {"id": id2, "content": "java coding"},
        ]

        results = await strat.search("python", "t1")
        assert len(results) == 1
        assert results[0][0] == id1
        assert results[0][1] > 0

    def test_tokenize(self, mock_storage):
        strat = SparseVectorStrategy(memory_storage=mock_storage)
        tokens = strat._tokenize("Hello World!")
        assert tokens == ["hello", "world!"]
