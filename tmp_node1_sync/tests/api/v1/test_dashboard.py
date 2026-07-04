from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException, WebSocket, WebSocketDisconnect

from apps.memory_api.models.dashboard_models import (
    GetDashboardMetricsRequest,
    GetSystemHealthRequest,
    GetVisualizationRequest,
    HealthStatus,
    MetricPeriod,
    SystemHealth,
    VisualizationType,
)
from apps.memory_api.routes.dashboard import get_metric_timeseries

# --- Fixtures & Mocks ---


@pytest.fixture
def mock_metrics_repo():
    with patch("apps.memory_api.routes.dashboard.get_metrics_repo") as mock_get:
        repo_mock = AsyncMock()
        # Default timeseries response
        repo_mock.get_timeseries.return_value = [
            {"timestamp": datetime.now(timezone.utc), "metric_value": 10},
            {"timestamp": datetime.now(timezone.utc), "metric_value": 20},
        ]
        mock_get.return_value = repo_mock
        yield repo_mock


@pytest.fixture
def mock_compliance_service():
    with patch("apps.memory_api.routes.dashboard.get_compliance_service") as mock_get:
        service_mock = AsyncMock()
        mock_get.return_value = service_mock
        yield service_mock


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    pool.fetchval.return_value = 1
    pool.fetch.return_value = []
    pool.fetchrow.return_value = None
    return pool


@pytest.fixture
def mock_rae_service(mock_pool):
    rae_mock = MagicMock()
    rae_mock.postgres_pool = mock_pool
    rae_mock.redis_client = AsyncMock()
    rae_mock.qdrant_client = AsyncMock()

    # Mock the 'db' property to return an actual provider wrapping our mock pool
    from rae_adapters.postgres_db import PostgresDatabaseProvider

    rae_mock.db = PostgresDatabaseProvider(mock_pool)

    return rae_mock


@pytest.fixture
def mock_websocket_service(mock_rae_service):
    with patch("apps.memory_api.routes.dashboard.get_websocket_service") as mock_get:
        service_mock = MagicMock()
        mock_get.return_value = service_mock
        yield service_mock


# --- Tests ---


@pytest.mark.asyncio
async def test_get_system_health(mock_rae_service, mock_websocket_service):
    from apps.memory_api.routes.dashboard import get_system_health

    mock_websocket_service._check_system_health = AsyncMock(
        return_value=SystemHealth(
            overall_status=HealthStatus.HEALTHY,
            component_statuses={"db": "healthy"},
            last_check_time=datetime.now(timezone.utc),
            error_rate=0.0,
            latency_ms=10.0,
            active_connections=5,
            degraded_components=0,
        )
    )

    request_data = GetSystemHealthRequest(
        tenant_id="test-tenant", project_id="test-project", include_sub_components=True
    )

    response = await get_system_health(request_data, mock_rae_service)

    assert response.system_health.overall_status == HealthStatus.HEALTHY
    assert response.recommendations == []
    mock_websocket_service._check_system_health.assert_called_once()


@pytest.mark.asyncio
async def test_get_dashboard_metrics(mock_rae_service, mock_websocket_service):
    from apps.memory_api.models.dashboard_models import SystemMetrics
    from apps.memory_api.routes.dashboard import get_dashboard_metrics

    mock_websocket_service._collect_system_metrics = AsyncMock(
        return_value=SystemMetrics(total_memories=100)
    )

    request_data = GetDashboardMetricsRequest(
        tenant_id="test-tenant", project_id="test-project", period=MetricPeriod.LAST_24H
    )

    response = await get_dashboard_metrics(
        request_data=request_data, rae_service=mock_rae_service
    )

    assert response.system_metrics.total_memories == 100
    assert response.recent_activity == []


@pytest.mark.asyncio
async def test_get_activity_log(mock_rae_service):
    from apps.memory_api.routes.dashboard import get_activity_log

    mock_rae_service.postgres_pool.fetch.side_effect = [
        [
            {
                "id": uuid4(),
                "content": "Test Memory",
                "importance": 0.8,
                "created_at": datetime.now(timezone.utc),
            }
        ],
        [
            {
                "id": uuid4(),
                "content": "Test Reflection",
                "score": 0.9,
                "created_at": datetime.now(timezone.utc),
            }
        ],
    ]

    response = await get_activity_log(
        tenant_id="t1",
        project_id="p1",
        limit=10,
        event_types=None,
        rae_service=mock_rae_service,
    )

    assert response["total_count"] == 2
    assert len(response["activity_logs"]) == 2


@pytest.mark.asyncio
async def test_websocket_endpoint(mock_websocket_service, mock_rae_service):
    from apps.memory_api.routes.dashboard import websocket_endpoint

    mock_ws = AsyncMock(spec=WebSocket)
    mock_ws.receive_text.side_effect = ["ping", WebSocketDisconnect()]

    mock_websocket_service.handle_connection = AsyncMock(return_value="conn-123")

    await websocket_endpoint(
        websocket=mock_ws,
        tenant_id="t1",
        project_id="p1",
        event_types="memory_created,reflection_generated",
        rae_service=mock_rae_service,
    )

    mock_websocket_service.handle_connection.assert_called_once()
    mock_ws.send_text.assert_called_with("pong")
    mock_websocket_service.handle_disconnection.assert_called_with("conn-123")


@pytest.mark.asyncio
async def test_compliance_report(mock_compliance_service):
    from apps.memory_api.models.dashboard_models import (
        ComplianceReport,
        ComplianceStatus,
        GetComplianceReportRequest,
    )
    from apps.memory_api.routes.dashboard import get_compliance_report

    mock_report = ComplianceReport(
        tenant_id="t1",
        project_id="p1",
        overall_compliance_score=95.0,
        overall_status=ComplianceStatus.COMPLIANT,
    )
    mock_compliance_service.generate_compliance_report.return_value = mock_report
    # Ensure verify_rls_status returns None (or a valid object) to avoid AsyncMock leak
    mock_compliance_service.verify_rls_status.return_value = None

    req = GetComplianceReportRequest(
        tenant_id="t1", project_id="p1", report_type="full"
    )
    response = await get_compliance_report(req, mock_compliance_service)

    assert response.compliance_report.overall_compliance_score == 95.0


@pytest.mark.asyncio
async def test_risk_register(mock_compliance_service):
    from apps.memory_api.models.dashboard_models import RiskMetric
    from apps.memory_api.routes.dashboard import (
        GetRiskRegisterRequest,
        RiskLevel,
        get_risk_register,
    )

    mock_risk = RiskMetric(
        risk_id="r1",
        risk_description="desc",
        category="cat",
        probability=0.5,
        impact=0.5,
        risk_score=0.25,
        risk_level=RiskLevel.HIGH,
        status="open",
        identified_at=datetime.now(timezone.utc),
        last_reviewed_at=datetime.now(timezone.utc),
    )

    mock_compliance_service._get_active_risks.return_value = [mock_risk]
    req = GetRiskRegisterRequest(
        tenant_id="t1", project_id="p1", risk_level=RiskLevel.HIGH
    )
    response = await get_risk_register(req, mock_compliance_service)

    assert response.high_priority_count == 1


# --- New Tests ---


@pytest.mark.asyncio
async def test_get_metric_timeseries_trend_up(mock_metrics_repo):
    """Test trend calculation (up)."""
    t1 = datetime.now(timezone.utc)
    t2 = datetime.now(timezone.utc)

    mock_metrics_repo.get_timeseries.return_value = [
        {"timestamp": t1, "metric_value": 10},
        {"timestamp": t2, "metric_value": 20},  # slope will be positive
    ]

    result = await get_metric_timeseries(
        "memory_count", "t1", "p1", MetricPeriod.LAST_24H, mock_metrics_repo
    )

    ts = result["time_series"]
    assert ts["metric_name"] == "memory_count"
    assert ts["trend_direction"] == "up"


@pytest.mark.asyncio
async def test_get_metric_timeseries_trend_stable(mock_metrics_repo):
    """Test trend calculation (stable)."""
    t1 = datetime.now(timezone.utc)
    t2 = datetime.now(timezone.utc)

    mock_metrics_repo.get_timeseries.return_value = [
        {"timestamp": t1, "metric_value": 100},
        {"timestamp": t2, "metric_value": 100},  # slope 0
    ]

    result = await get_metric_timeseries(
        "memory_count", "t1", "p1", MetricPeriod.LAST_24H, mock_metrics_repo
    )
    assert result["time_series"]["trend_direction"] == "stable"


@pytest.mark.asyncio
async def test_get_visualization_reflection_tree(mock_rae_service):
    from apps.memory_api.routes.dashboard import get_visualization

    # Mock root reflection fetch
    root_record = {
        "id": uuid4(),
        "content": "Root",
        "type": "meta",
        "score": 1.0,
        "depth_level": 0,
        "parent_reflection_id": None,
        "cluster_id": "c1",
        "source_count": 5,
        "created_at": datetime.now(timezone.utc),
    }
    mock_rae_service.postgres_pool.fetch.side_effect = [
        [root_record],
        [],
    ]  # Root search, then children

    req = GetVisualizationRequest(
        tenant_id="t1",
        project_id="p1",
        visualization_type=VisualizationType.REFLECTION_TREE,
    )
    resp = await get_visualization(req, mock_rae_service)

    assert resp.reflection_tree is not None
    assert resp.reflection_tree.content == "Root"


@pytest.mark.asyncio
async def test_get_visualization_semantic_graph(mock_rae_service):
    from apps.memory_api.routes.dashboard import get_visualization

    # Nodes
    nodes = [
        {
            "id": uuid4(),
            "label": "Node1",
            "node_type": "concept",
            "canonical_form": "node1",
            "importance_score": 0.8,
            "reinforcement_count": 1,
            "is_degraded": False,
        }
    ]
    # Edges
    edges = [
        {
            "source_node_id": nodes[0]["id"],
            "target_node_id": uuid4(),
            "relation_type": "related",
            "edge_weight": 1.0,
            "confidence": 0.9,
        }
    ]

    mock_rae_service.postgres_pool.fetch.side_effect = [nodes, edges]

    req = GetVisualizationRequest(
        tenant_id="t1",
        project_id="p1",
        visualization_type=VisualizationType.SEMANTIC_GRAPH,
    )
    resp = await get_visualization(req, mock_rae_service)

    assert resp.semantic_graph is not None
    assert len(resp.semantic_graph.nodes) == 1
    assert len(resp.semantic_graph.edges) == 1


@pytest.mark.asyncio
async def test_get_visualization_unsupported(mock_rae_service):
    from apps.memory_api.routes.dashboard import get_visualization

    req = GetVisualizationRequest(
        tenant_id="t1",
        project_id="p1",
        visualization_type=VisualizationType.CLUSTER_MAP,
    )

    with pytest.raises(HTTPException) as exc:
        await get_visualization(req, mock_rae_service)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_error_handling_dashboard_metrics(
    mock_rae_service, mock_websocket_service
):
    from apps.memory_api.routes.dashboard import get_dashboard_metrics

    mock_websocket_service._collect_system_metrics.side_effect = Exception("DB Error")

    req = GetDashboardMetricsRequest(tenant_id="t1", project_id="p1")

    with pytest.raises(HTTPException) as exc:
        await get_dashboard_metrics(req, mock_rae_service)

    assert exc.value.status_code == 500
