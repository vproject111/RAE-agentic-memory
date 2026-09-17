"""Tests for Retrieval Telemetry Bridge and Closed-Loop Optimization (Stage 4, L6, L7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.middleware.telemetry_bridge import (
    RetrievalTelemetryBridge,
    reset_telemetry_bridge,
)
from apps.memory_api.services.rae_core_service import (
    RAECoreService,
    get_rae_core_service,
)
from rae_core.models.evidence_package import EvidenceItem, EvidencePackage
from rae_core.search.optimizer import (
    MaturityMode,
    OptimizationRecommendation,
    RetrievalOptimizer,
)


def test_retrieval_optimizer_unit():
    """Verify RetrievalOptimizer reward and adaptation behavior."""
    optimizer = RetrievalOptimizer(mode=MaturityMode.ACTIVE)
    assert optimizer.mode == MaturityMode.ACTIVE

    # Test reward calculation
    reward = optimizer.compute_reward(
        quality=1.0,
        latency_ms=50.0,
        token_cost=0.0,
        is_failed=False,
    )
    assert reward > 0.60

    # Step in ACTIVE mode
    init_weight = optimizer.current_weights.get("vector", 0.5)
    rec = optimizer.step(
        strategy_name="vector",
        quality=0.95,
        latency_ms=60.0,
    )
    assert isinstance(rec, OptimizationRecommendation)
    assert rec.mode == MaturityMode.ACTIVE
    assert optimizer.current_weights["vector"] >= init_weight


def test_retrieval_optimizer_shadow_mode():
    """Verify SHADOW mode does not mutate active weights."""
    optimizer = RetrievalOptimizer(mode=MaturityMode.SHADOW)
    init_weights = dict(optimizer.current_weights)

    rec = optimizer.step(
        strategy_name="vector",
        quality=0.99,
        latency_ms=40.0,
    )
    assert rec.mode == MaturityMode.SHADOW
    assert optimizer.current_weights == init_weights


@pytest.mark.asyncio
async def test_telemetry_bridge_record():
    """Verify RetrievalTelemetryBridge attaches telemetry to EvidencePackage."""
    optimizer = RetrievalOptimizer(mode=MaturityMode.ACTIVE)
    bridge = RetrievalTelemetryBridge(optimizer=optimizer)

    package = EvidencePackage(
        package_id=uuid4(),
        query="test query",
        tenant_id="tenant-test",
        items=[
            EvidenceItem(
                memory_id=uuid4(),
                content="test content",
                relevance_score=0.95,
                strategy_source="semantic",
            )
        ],
        confidence_score=0.95,
        metadata={},
    )

    reward = await bridge.record_search_evidence(
        package=package,
        latency_ms=85.0,
        token_cost=0.0,
        strategy="hybrid",
    )
    assert reward > 0.50
    assert "telemetry" in package.metadata
    telemetry = package.metadata["telemetry"]
    assert telemetry["quality"] == 0.95
    assert telemetry["latency_ms"] == 85.0
    assert telemetry["reward"] == round(reward, 4)
    assert telemetry["is_failed"] is False


def test_evidence_search_api_with_telemetry(mock_pool):
    """Verify POST /v2/search/evidence returns EvidencePackage with telemetry bridge data."""
    app.state.pool = mock_pool

    mock_service = MagicMock(spec=RAECoreService)
    mock_service.szubar_mode = False

    dummy_item = EvidenceItem(
        memory_id=uuid4(),
        content="Evidence content for testing",
        relevance_score=0.92,
        strategy_source="semantic",
    )
    dummy_package = EvidencePackage(
        package_id=uuid4(),
        query="neural search test",
        tenant_id="tenant-telemetry",
        items=[dummy_item],
        confidence_score=0.92,
        metadata={},
    )

    async def mock_search_evidence(**kwargs):
        return dummy_package

    mock_service.search_evidence = AsyncMock(side_effect=mock_search_evidence)

    # Use fresh telemetry bridge
    reset_telemetry_bridge(RetrievalTelemetryBridge(mode=MaturityMode.ACTIVE))

    app.dependency_overrides[get_rae_core_service] = lambda: mock_service
    try:
        client = TestClient(app)
        payload = {
            "query": "neural search test",
            "tenant_id": "tenant-telemetry",
            "limit": 5,
            "auto_route": True,
        }
        response = client.post("/v2/search/evidence", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "neural search test"
        assert len(data["items"]) == 1

        # Check telemetry in metadata
        metadata = data.get("metadata", {})
        assert "telemetry" in metadata
        telemetry = metadata["telemetry"]
        assert "reward" in telemetry
        assert "latency_ms" in telemetry
        assert telemetry["quality"] == 0.92

        # Check latency header from TelemetryBridgeMiddleware
        assert "x-retrieval-latency-ms" in response.headers
    finally:
        app.dependency_overrides.pop(get_rae_core_service, None)


@pytest.mark.asyncio
async def test_telemetry_bridge_state_file_persistence(tmp_path):
    import json

    state_file = tmp_path / "bridge_optimizer.json"
    bridge = RetrievalTelemetryBridge(mode=MaturityMode.ACTIVE)
    bridge.state_file = str(state_file)

    dummy_item = EvidenceItem.from_memory_and_score(
        memory_id=uuid4(),
        content="State file persistence test content",
        score=0.9,
    )
    dummy_package = EvidencePackage(
        query="state test",
        tenant_id="tenant-1",
        items=[dummy_item],
        confidence_score=0.9,
    )

    await bridge.record_search_evidence(
        package=dummy_package,
        latency_ms=15.0,
        strategy="vector",
    )

    assert state_file.exists()
    with open(state_file, "r") as f:
        data = json.load(f)
    assert data["mode"] == "active"
    assert "vector" in data["current_weights"]
