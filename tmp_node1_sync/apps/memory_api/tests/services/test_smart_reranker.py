import pytest

from apps.memory_api.config import settings
from apps.memory_api.services.smart_reranker import SmartReranker


@pytest.mark.asyncio
async def test_reranker_disabled():
    reranker = SmartReranker()
    original_setting = settings.ENABLE_SMART_RERANKER
    settings.ENABLE_SMART_RERANKER = False

    candidates = [{"id": "1", "final_score": 0.5}]
    result = await reranker.rerank(candidates, "query", limit=1)

    assert result == candidates
    settings.ENABLE_SMART_RERANKER = original_setting


@pytest.mark.asyncio
async def test_reranker_heuristic_boost():
    reranker = SmartReranker()
    original_setting = settings.ENABLE_SMART_RERANKER
    settings.ENABLE_SMART_RERANKER = True

    # Candidate 1: Exact match (should get boost)
    # Candidate 2: No match
    candidates = [
        {"id": "1", "content": "This is a test query match", "final_score": 0.5},
        {"id": "2", "content": "Irrelevant content", "final_score": 0.5},
    ]

    result = await reranker.rerank(candidates, "test query", limit=2)

    # Candidate 1 should be first and have higher smart_score
    assert result[0]["id"] == "1"
    assert result[0]["smart_score"] > result[1].get("smart_score", 0.0)
    assert result[0]["smart_score"] > 0.5  # Base score + boost

    settings.ENABLE_SMART_RERANKER = original_setting


@pytest.mark.asyncio
async def test_reranker_limit():
    reranker = SmartReranker()
    original_setting = settings.ENABLE_SMART_RERANKER
    settings.ENABLE_SMART_RERANKER = True

    candidates = [
        {"id": str(i), "content": "content", "final_score": 0.5} for i in range(5)
    ]

    result = await reranker.rerank(candidates, "query", limit=2)
    assert len(result) == 2

    settings.ENABLE_SMART_RERANKER = original_setting
