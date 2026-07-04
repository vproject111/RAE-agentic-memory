from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.models.hybrid_search_models import (
    HybridSearchResult,
    QueryAnalysis,
    QueryIntent,
)


# Create a fixture for the client that overrides dependencies
@pytest.fixture
def client_with_mock_service():
    # Setup mock pool
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()

    with patch(
        "apps.memory_api.routes.hybrid_search.HybridSearchService"
    ) as MockService:
        instance = MockService.return_value
        instance.search = AsyncMock()

        # We need to mock the pool dependency as well to avoid actual DB connection
        with (
            patch(
                "apps.memory_api.routes.hybrid_search.get_pool",
                return_value=AsyncMock(),
            ),
            patch(
                "rae_adapters.infra_factory.asyncpg.create_pool",
                new=AsyncMock(return_value=mock_pool),
            ),
            patch("apps.memory_api.main.rebuild_full_cache", new=AsyncMock()),
        ):
            with TestClient(app) as client:
                yield client, instance


@pytest.mark.asyncio
async def test_hybrid_search_success(client_with_mock_service):
    """Test POST /v1/search/hybrid with successful search"""
    client, mock_service = client_with_mock_service

    # Create a proper Pydantic model for the result
    mock_result = HybridSearchResult(
        results=[],
        total_results=5,
        query_analysis=QueryAnalysis(
            intent=QueryIntent.FACTUAL,
            confidence=0.9,
            original_query="authentication system",
            key_entities=[],
            key_concepts=[],
            temporal_markers=[],
            relation_types=[],
            recommended_strategies=["vector", "semantic"],
            strategy_weights={
                "vector": 0.4,
                "semantic": 0.3,
                "graph": 0.2,
                "fulltext": 0.1,
            },
            requires_temporal_filtering=False,
            requires_graph_traversal=False,
            suggested_depth=2,
            analyzed_at=datetime.now(timezone.utc),
        ),
        vector_results_count=2,
        semantic_results_count=1,
        graph_results_count=1,
        fulltext_results_count=1,
        total_time_ms=123,
        query_analysis_time_ms=50,
        search_time_ms=73,
        applied_weights={"vector": 0.4, "semantic": 0.3, "graph": 0.2, "fulltext": 0.1},
        reranking_used=False,
    )

    mock_service.search.return_value = mock_result

    payload = {
        "tenant_id": "test-tenant",
        "project_id": "test-project",
        "query": "authentication system",
        "k": 10,
        "enable_vector_search": True,
        "enable_semantic_search": True,
        "enable_graph_search": True,
        "enable_fulltext_search": True,
    }

    response = client.post(
        "/v1/search/hybrid", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "search_result" in data
    assert "message" in data
    assert data["search_result"]["total_results"] == 5


@pytest.mark.asyncio
async def test_hybrid_search_with_reranking(client_with_mock_service):
    """Test hybrid search with LLM re-ranking enabled"""
    client, mock_service = client_with_mock_service

    mock_result = HybridSearchResult(
        results=[],
        total_results=3,
        query_analysis=QueryAnalysis(
            intent=QueryIntent.EXPLORATORY,
            confidence=0.8,
            original_query="explain the authentication flow",
            key_entities=[],
            key_concepts=[],
            temporal_markers=[],
            relation_types=[],
            recommended_strategies=["vector", "graph"],
            strategy_weights={"vector": 0.5, "semantic": 0.3, "graph": 0.2},
            requires_temporal_filtering=False,
            requires_graph_traversal=True,
            suggested_depth=3,
            analyzed_at=datetime.now(timezone.utc),
        ),
        vector_results_count=1,
        semantic_results_count=1,
        graph_results_count=1,
        fulltext_results_count=0,
        total_time_ms=250,
        query_analysis_time_ms=50,
        search_time_ms=100,
        reranking_time_ms=100,
        applied_weights={"vector": 0.5, "semantic": 0.3, "graph": 0.2},
        reranking_used=True,
    )

    mock_service.search.return_value = mock_result

    payload = {
        "tenant_id": "test-tenant",
        "project_id": "test-project",
        "query": "explain the authentication flow",
        "k": 5,
        "enable_vector_search": True,
        "enable_semantic_search": True,
        "enable_graph_search": True,
        "enable_fulltext_search": False,
        "enable_reranking": True,
        "reranking_model": "claude-3-5-sonnet-20241022",
    }

    response = client.post(
        "/v1/search/hybrid", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "search_result" in data
    assert data["search_result"]["reranking_used"] is True


@pytest.mark.asyncio
async def test_hybrid_search_with_filters(client_with_mock_service):
    """Test hybrid search with temporal and tag filters"""
    client, mock_service = client_with_mock_service

    mock_result = HybridSearchResult(
        results=[],
        total_results=2,
        query_analysis=QueryAnalysis(
            intent=QueryIntent.TEMPORAL,
            confidence=0.85,
            original_query="recent security updates",
            key_entities=[],
            key_concepts=[],
            temporal_markers=["recent"],
            relation_types=[],
            recommended_strategies=["vector", "fulltext"],
            strategy_weights={"vector": 0.6, "semantic": 0.4},
            requires_temporal_filtering=True,
            requires_graph_traversal=False,
            suggested_depth=1,
            analyzed_at=datetime.now(timezone.utc),
        ),
        vector_results_count=1,
        semantic_results_count=1,
        graph_results_count=0,
        fulltext_results_count=0,
        total_time_ms=89,
        query_analysis_time_ms=40,
        search_time_ms=49,
        applied_weights={"vector": 0.6, "semantic": 0.4},
        reranking_used=False,
    )

    mock_service.search.return_value = mock_result

    payload = {
        "tenant_id": "test-tenant",
        "project_id": "test-project",
        "query": "recent security updates",
        "k": 10,
        "enable_vector_search": True,
        "enable_semantic_search": True,
        "enable_graph_search": False,
        "enable_fulltext_search": True,
        "temporal_filter": "2025-01-01T00:00:00Z",
        "tag_filter": ["security", "updates"],
        "min_importance": 0.5,
    }

    response = client.post(
        "/v1/search/hybrid", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "search_result" in data


@pytest.mark.asyncio
async def test_hybrid_search_service_error(client_with_mock_service):
    """Test hybrid search when service fails"""
    client, mock_service = client_with_mock_service
    mock_service.search.side_effect = Exception("Service error")

    payload = {
        "tenant_id": "test-tenant",
        "project_id": "test-project",
        "query": "test query",
        "k": 10,
        "enable_vector_search": True,
        "enable_semantic_search": True,
        "enable_graph_search": False,
        "enable_fulltext_search": False,
    }

    response = client.post(
        "/v1/search/hybrid", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "500"
    assert "Service error" in data["error"]["message"]
