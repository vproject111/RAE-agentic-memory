from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.models.hybrid_search_models import (
    HybridSearchResult,
    QueryAnalysis,
    RerankingModel,
    SearchResultItem,
    SearchStrategy,
)
from apps.memory_api.services.hybrid_search_service import HybridSearchService


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool


@pytest.fixture
def mock_query_analyzer():
    analyzer = AsyncMock()
    analyzer.analyze_intent.return_value = QueryAnalysis(
        intent="exploratory",
        confidence=0.9,
        key_entities=["entity1"],
        key_concepts=["concept1"],
        temporal_markers=[],
        relation_types=[],
        recommended_strategies=[SearchStrategy.VECTOR],
        strategy_weights={SearchStrategy.VECTOR: 1.0},
        original_query="test query",
    )
    analyzer.calculate_dynamic_weights.return_value = {
        SearchStrategy.VECTOR: 0.5,
        SearchStrategy.SEMANTIC: 0.3,
        SearchStrategy.GRAPH: 0.1,
        SearchStrategy.FULLTEXT: 0.1,
    }
    return analyzer


@pytest.fixture
def mock_ml_client():
    client = AsyncMock()
    client.get_embedding.return_value = [0.1, 0.2, 0.3]
    return client


@pytest.fixture
def mock_llm_provider():
    provider = AsyncMock()
    # Mock response for reranking
    response = MagicMock()
    response.text = '[{"index": 0, "score": 0.95, "reason": "Good"}, {"index": 1, "score": 0.8, "reason": "Ok"}]'
    provider.generate.return_value = response
    return provider


@pytest.fixture
def mock_rae_service(mock_pool):
    service = MagicMock()
    service.postgres_pool = mock_pool
    service.qdrant_client = AsyncMock()

    # Mock embedding provider as AsyncMock since it's awaited
    service.embedding_provider = AsyncMock()
    service.embedding_provider.embed_text.return_value = [0.1, 0.2, 0.3]

    # Mock DB as AsyncMock to simplify testing service logic without provider overhead
    service.db = AsyncMock()

    return service


@pytest.fixture
def service(mock_rae_service, mock_query_analyzer, mock_ml_client, mock_llm_provider):
    # Need to patch internal components
    with (
        patch(
            "apps.memory_api.services.hybrid_search_service.QueryAnalyzer",
            return_value=mock_query_analyzer,
        ),
        patch(
            "apps.memory_api.services.hybrid_search_service.MLServiceClient",
            return_value=mock_ml_client,
        ),
        patch(
            "apps.memory_api.services.hybrid_search_service.get_llm_provider",
            return_value=mock_llm_provider,
        ),
        patch(
            "apps.memory_api.services.hybrid_search_service.get_hybrid_cache",
            return_value=AsyncMock(),
        ),
        patch(
            "apps.memory_api.services.hybrid_search_service.TokenSavingsService",
            return_value=AsyncMock(),
        ),
    ):
        svc = HybridSearchService(mock_rae_service, enable_cache=True)
        # Manually attach mocks
        svc.query_analyzer = mock_query_analyzer
        svc.ml_client = mock_ml_client
        svc.llm_provider = mock_llm_provider
        return svc


@pytest.mark.asyncio
async def test_search_flow_uncached(service, mock_rae_service):
    # Setup db mocks for individual search strategies
    # Vector Search Mock
    mock_rae_service.db.fetch.side_effect = [
        # Vector results
        [
            {
                "id": uuid4(),
                "content": "Vector match",
                "similarity": 0.9,
                "metadata": {},
                "created_at": datetime.now(),
            }
        ],
        # Semantic Search Records
        [],
        # Graph Search Records
        [],
        # Fulltext Search Records
        [
            {
                "id": uuid4(),
                "content": "Fulltext match",
                "rank": 0.8,
                "metadata": {},
                "created_at": datetime.now(),
            }
        ],
    ]

    # Ensure cache miss
    service.cache.get.return_value = None

    result = await service.search(
        tenant_id="t-1",
        project_id="p-1",
        query="test query",
        k=5,
        enable_reranking=False,
    )

    assert isinstance(result, HybridSearchResult)
    assert len(result.results) > 0
    assert result.total_results > 0
    service.query_analyzer.analyze_intent.assert_called_once()


@pytest.mark.asyncio
async def test_search_cached(service):
    # Setup cache hit
    service.cache.get.return_value = {
        "results": [],
        "total_results": 0,
        "query_analysis": {
            "intent": "exploratory",
            "confidence": 1.0,
            "key_entities": [],
            "key_concepts": [],
            "temporal_markers": [],
            "relation_types": [],
            "recommended_strategies": [],
            "strategy_weights": {},
            "original_query": "q",
        },
        "vector_results_count": 0,
        "semantic_results_count": 0,
        "graph_results_count": 0,
        "fulltext_results_count": 0,
        "total_time_ms": 10,
        "applied_weights": {},
        "reranking_used": False,
    }

    result = await service.search("t", "p", "q", bypass_cache=False)

    assert result.total_results == 0
    service.query_analyzer.analyze_intent.assert_not_called()  # Should be skipped
    service.savings_service.track_savings.assert_called_once()


@pytest.mark.asyncio
async def test_fuse_results(service):
    # Manually invoke _fuse_results
    mem_id1 = str(uuid4())
    mem_id2 = str(uuid4())

    strategy_results = {
        SearchStrategy.VECTOR: [
            {
                "memory_id": mem_id1,
                "content": "c1",
                "score": 0.9,
                "metadata": {},
                "created_at": datetime.now(),
            }
        ],
        SearchStrategy.FULLTEXT: [
            {
                "memory_id": mem_id1,
                "content": "c1",
                "score": 0.5,
                "metadata": {},
                "created_at": datetime.now(),
            },
            {
                "memory_id": mem_id2,
                "content": "c2",
                "score": 0.8,
                "metadata": {},
                "created_at": datetime.now(),
            },
        ],
    }
    weights = {SearchStrategy.VECTOR: 0.8, SearchStrategy.FULLTEXT: 0.2}

    fused = service._fuse_results(strategy_results, weights, k=10)

    assert len(fused) == 2

    m1 = next(r for r in fused if str(r.memory_id) == mem_id1)
    # Check hybrid score calculation logic (RRF)
    # RRF_K = 60
    # mem_id1 rank 0 in VECTOR: 1/(60+0) * 0.8 = 0.8/60 = 0.01333...
    # mem_id1 rank 0 in FULLTEXT: 1/(60+0) * 0.2 = 0.2/60 = 0.00333...
    # Total: 1.0/60 = 0.01666...
    assert m1.hybrid_score == pytest.approx(1.0 / 60)


@pytest.mark.asyncio
async def test_rerank_results(service, mock_llm_provider):
    mem_id1 = str(uuid4())
    mem_id2 = str(uuid4())

    results = [
        SearchResultItem(
            memory_id=mem_id1,
            content="Content 1",
            hybrid_score=0.5,
            rank=1,
            search_strategies_used=[],
            created_at=datetime.now(),
            final_score=0.5,
        ),
        SearchResultItem(
            memory_id=mem_id2,
            content="Content 2",
            hybrid_score=0.4,
            rank=2,
            search_strategies_used=[],
            created_at=datetime.now(),
            final_score=0.4,
        ),
    ]

    reranked = await service._rerank_results(
        "query", results, RerankingModel.CLAUDE_HAIKU
    )

    assert len(reranked) == 2
    assert str(reranked[0].memory_id) == mem_id1
    assert reranked[0].rerank_score == 0.95
    # 0.95 * 0.7 + 0.5 * 0.3 = 0.665 + 0.15 = 0.815
    assert reranked[0].final_score == pytest.approx(0.815)


@pytest.mark.asyncio
async def test_vector_search_execution(service, mock_rae_service, mock_ml_client):
    mock_rae_service.db.fetch.return_value = [
        {
            "id": uuid4(),
            "content": "res",
            "similarity": 0.8,
            "metadata": {},
            "created_at": datetime.now(),
        }
    ]

    results = await service._vector_search("t", "p", "q", 5)

    assert len(results) == 1
    assert results[0]["score"] == 0.8
    # We mock internal client but the service actually uses rae_service.embedding_provider
    # So we check if that was called
    service.rae_service.embedding_provider.embed_text.assert_called_once()
    mock_rae_service.db.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_semantic_search_execution(service, mock_rae_service):
    # Mock search nodes
    mock_rae_service.db.fetch.side_effect = [
        # Nodes query
        [
            {
                "id": uuid4(),
                "label": "node1",
                "canonical_form": "node1",
                "importance_score": 0.9,
                "source_memory_ids": ["mem1"],
                "created_at": datetime.now(),
            }
        ],
        # Memories query
        [
            {
                "id": "mem1",
                "content": "content",
                "metadata": {},
                "created_at": datetime.now(),
            }
        ],
    ]

    results = await service._semantic_search("t", "p", "q", 5, ["concept"])

    assert len(results) == 1
    assert results[0]["memory_id"] == "mem1"
    assert results[0]["semantic_node"] is not None


@pytest.mark.asyncio
async def test_graph_search_execution(service, mock_rae_service):
    # Mock nodes found
    mock_rae_service.db.fetch.side_effect = [
        # Find nodes
        [{"id": 1, "node_id": "n1", "label": "entity", "properties": {}}],
        # Traverse
        [
            {
                "id": 1,
                "node_id": "n1",
                "label": "entity",
                "properties": {"source_memory_id": "mem1"},
            }
        ],
        # Fetch memories
        [
            {
                "id": "mem1",
                "content": "c",
                "importance": 0.8,
                "metadata": {},
                "created_at": datetime.now(),
            }
        ],
    ]

    results = await service._graph_search("t", "p", "q", ["entity"], 2, 5)

    assert len(results) == 1
    assert results[0]["memory_id"] == "mem1"
    assert results[0]["source"] == "graph_traversal"


@pytest.mark.asyncio
async def test_fulltext_search_execution(service, mock_rae_service):
    mock_rae_service.db.fetch.return_value = [
        {
            "id": uuid4(),
            "content": "res",
            "rank": 0.5,
            "metadata": {},
            "created_at": datetime.now(),
        }
    ]

    results = await service._fulltext_search("t", "p", "q", 5)

    assert len(results) == 1
    assert results[0]["score"] == 0.5


@pytest.mark.asyncio
async def test_search_with_manual_weights(service, mock_rae_service):
    """Test search with manual weights provided."""
    # Ensure cache miss
    service.cache.get.return_value = None

    # Mock vector search results
    mock_rae_service.db.fetch.return_value = [
        {
            "id": uuid4(),
            "content": "res",
            "similarity": 0.8,
            "metadata": {},
            "created_at": datetime.now(),
        }
    ]

    manual_weights = {"vector": 1.0, "semantic": 0.0}

    result = await service.search(
        tenant_id="t-1", project_id="p-1", query="test", manual_weights=manual_weights
    )

    # Should skip analysis
    service.query_analyzer.analyze_intent.assert_not_called()
    assert result.applied_weights["vector"] == 1.0


@pytest.mark.asyncio
async def test_vector_search_error_handling(service, mock_rae_service):
    """Test vector search error handling."""
    mock_rae_service.embedding_provider.embed_text.side_effect = Exception(
        "ML Service Down"
    )

    results = await service._vector_search("t", "p", "q", 5)

    assert results == []


@pytest.mark.asyncio
async def test_rerank_results_error_handling(service, mock_llm_provider):
    """Test reranking fallback on error."""
    mock_llm_provider.generate.side_effect = Exception("LLM Error")

    results = [
        SearchResultItem(
            memory_id=str(uuid4()),
            content="c",
            hybrid_score=0.5,
            rank=1,
            search_strategies_used=[],
            created_at=datetime.now(),
            final_score=0.5,
        )
    ]

    reranked = await service._rerank_results("q", results, RerankingModel.CLAUDE_HAIKU)

    # Should return original results
    assert len(reranked) == 1
    assert reranked[0].hybrid_score == 0.5
