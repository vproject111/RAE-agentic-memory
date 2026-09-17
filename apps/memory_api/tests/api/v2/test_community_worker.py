"""Unit tests for CommunitySynthesisWorker and /v2/reflections/communities/synthesize (Stage 3 / L5)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.main import app
from apps.memory_api.models.reflection_models import (
    SynthesizeCommunitiesResponse,
    SynthesizedCommunityItem,
)
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.workers.community_worker import (
    CommunitySynthesisWorker,
)
from rae_core.models.graph import EdgeType, GraphEdge


@pytest.fixture
def mock_rae_service():
    service = MagicMock(spec=RAECoreService)
    service.store_memory = AsyncMock(return_value=str(uuid4()))
    return service


@pytest.fixture
def client_with_mock_service(mock_pool, mock_rae_service):
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
        app.state.pool = mock_pool
        app.dependency_overrides[get_rae_core_service] = lambda: mock_rae_service

        with TestClient(app) as client:
            yield client, mock_rae_service

        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_community_synthesis_worker_run_synthesis(mock_rae_service):
    worker = CommunitySynthesisWorker(
        rae_service=mock_rae_service, min_community_size=3
    )

    n1, n2, n3 = uuid4(), uuid4(), uuid4()
    edges = [
        GraphEdge(
            source_id=n1,
            target_id=n2,
            edge_type=EdgeType.RELATES_TO,
            tenant_id="tenant-1",
        ),
        GraphEdge(
            source_id=n2,
            target_id=n3,
            edge_type=EdgeType.RELATES_TO,
            tenant_id="tenant-1",
        ),
    ]
    node_contents = {
        n1: "Authentication service handles JWT verification",
        n2: "Token refresh endpoint renews session credentials",
        n3: "Session storage manages active user tokens in Redis",
    }
    node_labels = {
        n1: "AuthService",
        n2: "TokenRefresher",
        n3: "SessionStore",
    }
    node_props = {
        n1: {"domain": "security"},
        n2: {"domain": "security"},
        n3: {"domain": "security"},
    }

    result = await worker.run_synthesis(
        tenant_id="tenant-1",
        project="security-core",
        custom_nodes=[n1, n2, n3],
        custom_edges=edges,
        custom_node_contents=node_contents,
        custom_node_labels=node_labels,
        custom_node_props=node_props,
    )

    assert result.synthesized_count == 1
    assert len(result.communities) == 1
    comm = result.communities[0]
    assert comm.member_count == 3
    assert comm.domain == "security"

    mock_rae_service.store_memory.assert_awaited_once()
    kwargs = mock_rae_service.store_memory.await_args.kwargs
    assert kwargs["layer"] == "reflective"
    assert kwargs["source"] == "community_synthesis_worker"
    assert "community_synthesis" in kwargs["tags"]
    assert "security" in kwargs["tags"]


@pytest.mark.asyncio
async def test_community_synthesis_worker_empty_graph(mock_rae_service):
    worker = CommunitySynthesisWorker(rae_service=mock_rae_service)
    result = await worker.run_synthesis(
        tenant_id="tenant-1",
        project="empty-proj",
        custom_nodes=[],
        custom_edges=[],
    )

    assert result.synthesized_count == 0
    assert result.communities == []
    mock_rae_service.store_memory.assert_not_awaited()


def test_synthesize_communities_endpoint(client_with_mock_service):
    client, mock_service = client_with_mock_service

    mock_response = SynthesizeCommunitiesResponse(
        synthesized_count=2,
        communities=[
            SynthesizedCommunityItem(
                community_id="comm-1",
                domain="auth",
                member_count=3,
                memory_id="mem-1",
                summary="Auth cluster overview",
            ),
            SynthesizedCommunityItem(
                community_id="comm-2",
                domain="billing",
                member_count=4,
                memory_id="mem-2",
                summary="Billing cluster overview",
            ),
        ],
        message="Successfully synthesized 2 community reflections",
    )

    with patch(
        "apps.memory_api.workers.community_worker.CommunitySynthesisWorker.run_synthesis",
        new=AsyncMock(return_value=mock_response),
    ):
        response = client.post(
            "/v2/reflections/communities/synthesize",
            json={
                "tenant_id": "test-tenant",
                "project": "main",
                "min_community_size": 3,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["synthesized_count"] == 2
        assert len(data["communities"]) == 2
        assert data["communities"][0]["domain"] == "auth"
        assert data["communities"][1]["domain"] == "billing"
