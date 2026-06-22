import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.models.hybrid_search_models import (
    HybridSearchResult,
    SearchResultItem,
)
from apps.memory_api.security import auth


@pytest.fixture
def client_with_mocks():
    # Set env vars to match conftest container or default expectations
    with patch.dict(
        os.environ,
        {
            "POSTGRES_USER": "rae",
            "POSTGRES_PASSWORD": "rae_password",
            "POSTGRES_DB": "rae",
            "POSTGRES_HOST": "localhost",
            "RAE_DB_MODE": "ignore",
        },
    ):
        # Mock app state
        app.state.pool = AsyncMock()
        app.state.rae_core_service = MagicMock()

        with TestClient(app) as c:
            yield c


@pytest.fixture
def mock_hybrid_search():
    with patch("apps.memory_api.routes.federation.HybridSearchService") as MockService:
        service_instance = MockService.return_value
        yield service_instance


def test_federation_query_unauthorized(client_with_mocks):
    """Test that federation endpoint requires authentication"""
    # Since auth might be disabled in test config, we verify the dependency is wired
    # by overriding it to raise an exception.

    def mock_verify_token_fail():
        raise HTTPException(status_code=403, detail="Not authenticated")

    app.dependency_overrides[auth.verify_token] = mock_verify_token_fail

    try:
        response = client_with_mocks.post(
            "/v2/federation/query",
            json={
                "query_text": "test",
                "tenant_id": "test-tenant",
                "project_id": "test-project",
                "limit": 5,
            },
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_federation_query_success(client_with_mocks, mock_hybrid_search):
    """Test successful federation query"""
    # Construct proper SearchResultItem objects
    item = SearchResultItem(
        memory_id=uuid4(),
        content="Federated content",
        hybrid_score=0.9,
        final_score=0.9,
        rank=1,
        metadata={"source": "local"},
        created_at=datetime.now(),
        search_strategies_used=["vector"],
    )

    mock_result = HybridSearchResult(
        results=[item],
        total_results=1,
        query_analysis={
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
        vector_results_count=1,
        semantic_results_count=0,
        graph_results_count=0,
        fulltext_results_count=0,
        total_time_ms=10,
        applied_weights={},
        reranking_used=False,
    )

    mock_hybrid_search.search = AsyncMock(return_value=mock_result)

    # Override auth dependency to simulate authenticated user
    app.dependency_overrides[auth.verify_token] = lambda: {
        "sub": "federation-user",
        "permissions": ["read"],
    }

    try:
        response = client_with_mocks.post(
            "/v2/federation/query",
            json={
                "query_text": "test query",
                "tenant_id": "t-1",
                "project_id": "p-1",
                "limit": 10,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["content_snippet"] == "Federated content"
        assert data["results"][0]["memory_id"] == str(item.memory_id)

    finally:
        app.dependency_overrides = {}
