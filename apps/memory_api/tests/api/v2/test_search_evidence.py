"""Tests for POST /v2/search/evidence endpoint and service integration (Stage 1)."""

import os
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.services.rae_core_service import (
    RAECoreService,
    get_rae_core_service,
)
from rae_core.models.evidence_package import EvidenceItem, EvidencePackage


@pytest.fixture
def sample_evidence_package():
    mem_id = uuid4()
    return EvidencePackage(
        query="what is RAE Engine?",
        tenant_id="test-tenant",
        items=[
            EvidenceItem.from_memory_and_score(
                memory_id=mem_id,
                content="RAE Engine is a self-tuning memory manifold.",
                score=0.95,
                strategy="hybrid_fused",
            )
        ],
        strategies_used=["vector", "fulltext"],
        confidence_score=0.92,
    )


@pytest.fixture
def client_with_mock_service(mock_pool, sample_evidence_package):
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
        mock_service = MagicMock(spec=RAECoreService)
        mock_service.search_evidence = AsyncMock(return_value=sample_evidence_package)

        app.dependency_overrides[get_rae_core_service] = lambda: mock_service

        with TestClient(app) as client:
            yield client, mock_service

        app.dependency_overrides.clear()


def test_search_evidence_endpoint_success(
    client_with_mock_service, sample_evidence_package
):
    client, mock_service = client_with_mock_service

    payload = {
        "query": "what is RAE Engine?",
        "tenant_id": "test-tenant",
        "project": "core-project",
        "agent_id": "agent-007",
        "layer": "episodic",
        "limit": 5,
        "auto_route": True,
        "strategies": ["vector", "fulltext"],
        "enable_reranking": True,
        "force_2pass": False,
    }

    response = client.post("/v2/search/evidence", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "what is RAE Engine?"
    assert data["tenant_id"] == "test-tenant"
    assert len(data["items"]) == 1
    assert data["items"][0]["content"] == "RAE Engine is a self-tuning memory manifold."
    assert data["confidence_score"] == 0.92

    mock_service.search_evidence.assert_awaited_once_with(
        query="what is RAE Engine?",
        tenant_id="test-tenant",
        project="core-project",
        agent_id="agent-007",
        layer="episodic",
        limit=5,
        strategies=["vector", "fulltext"],
        custom_weights=None,
        auto_route=True,
        enable_reranking=True,
        force_2pass=False,
        filters=None,
    )


def test_search_evidence_endpoint_validation_error(client_with_mock_service):
    client, _ = client_with_mock_service

    # Missing query
    response = client.post("/v2/search/evidence", json={"tenant_id": "test"})
    assert response.status_code == 422

    # Empty query
    response = client.post(
        "/v2/search/evidence", json={"query": "", "tenant_id": "test"}
    )
    assert response.status_code == 422


def test_search_evidence_endpoint_server_error(client_with_mock_service):
    client, mock_service = client_with_mock_service
    mock_service.search_evidence = AsyncMock(
        side_effect=RuntimeError("Storage connection dropped")
    )

    response = client.post(
        "/v2/search/evidence",
        json={"query": "faulty query", "tenant_id": "test-tenant"},
    )
    assert response.status_code == 500
    data = response.json()
    err_msg = data.get("detail") or data.get("error", {}).get("message", "")
    assert "Storage connection dropped" in err_msg
