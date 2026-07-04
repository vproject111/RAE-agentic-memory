"""
Tests for Dashboard WebSocket - Real-time Updates

Tests cover:
- WebSocket connection management
- Event broadcasting
- Metrics collection
- Health monitoring
- Subscription filtering
"""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.memory_api.models.dashboard_models import (
    DashboardEventType,
    HealthStatus,
    SystemMetrics,
)
from apps.memory_api.services.dashboard_websocket import (
    ConnectionManager,
    DashboardWebSocketService,
)


@pytest.fixture
def connection_manager():
    return ConnectionManager()


@pytest.fixture
def mock_pool():
    return AsyncMock()


@pytest.fixture
def dashboard_service(mock_pool):
    return DashboardWebSocketService(mock_pool)


@pytest.fixture
def mock_websocket():
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


# Connection Management Tests
@pytest.mark.asyncio
async def test_websocket_connect(connection_manager, mock_websocket):
    """Test WebSocket connection"""
    conn_id = await connection_manager.connect(
        mock_websocket, "test-tenant", "test-project"
    )

    assert conn_id is not None
    assert conn_id in connection_manager.active_connections
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_disconnect(connection_manager, mock_websocket):
    """Test WebSocket disconnection"""
    conn_id = await connection_manager.connect(
        mock_websocket, "test-tenant", "test-project"
    )

    connection_manager.disconnect(conn_id)

    assert conn_id not in connection_manager.active_connections


@pytest.mark.asyncio
async def test_subscription_filtering(connection_manager, mock_websocket):
    """Test event type subscription filtering"""
    # Connect with specific event types
    conn_id = await connection_manager.connect(
        mock_websocket,
        "test-tenant",
        "test-project",
        event_types=[DashboardEventType.MEMORY_CREATED],
    )

    subscription = connection_manager.subscriptions[conn_id]
    assert DashboardEventType.MEMORY_CREATED in subscription.subscribed_events


# Broadcasting Tests
@pytest.mark.asyncio
async def test_broadcast_to_tenant(connection_manager, mock_websocket):
    """Test broadcasting message to tenant"""
    await connection_manager.connect(mock_websocket, "test-tenant", "test-project")

    message = {"event_type": "memory_created", "payload": {"id": str(uuid4())}}

    await connection_manager.broadcast_to_tenant("test-tenant", "test-project", message)

    mock_websocket.send_json.assert_called()


@pytest.mark.asyncio
async def test_broadcast_all(connection_manager):
    """Test broadcasting to all connections"""
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()

    await connection_manager.connect(ws1, "tenant1", "project1")
    await connection_manager.connect(ws2, "tenant2", "project2")

    message = {"type": "system_update"}
    await connection_manager.broadcast_to_all(message)

    ws1.send_json.assert_called()
    ws2.send_json.assert_called()


# Metrics Collection Tests
@pytest.mark.asyncio
async def test_collect_system_metrics(dashboard_service, mock_pool):
    """Test system metrics collection"""
    mock_pool.fetchrow = AsyncMock(
        return_value={
            "total_memories": 100,
            "memories_last_24h": 20,
            "avg_importance": 0.75,
            "total_reflections": 10,
            "reflections_last_24h": 2,
            "avg_score": 0.8,
            "total_nodes": 50,
            "nodes_last_24h": 5,
            "degraded_count": 2,
            "total_edges": 75,
            "active_triggers": 3,
            "executions_last_24h": 15,
            "success_rate": 0.95,
        }
    )

    metrics = await dashboard_service._collect_system_metrics(
        "test-tenant", "test-project"
    )

    assert isinstance(metrics, SystemMetrics)
    assert metrics.total_memories >= 0


@pytest.mark.asyncio
async def test_metrics_changed_significantly(dashboard_service):
    """Test significant metrics change detection"""
    old_metrics = SystemMetrics(
        total_memories=100, memories_last_24h=10, total_reflections=5
    )

    new_metrics = SystemMetrics(
        total_memories=110,
        memories_last_24h=10,
        total_reflections=5,  # +10 changed
    )

    changed = dashboard_service._metrics_changed_significantly(old_metrics, new_metrics)
    assert changed is True


# Health Monitoring Tests
@pytest.mark.asyncio
async def test_check_system_health(dashboard_service, mock_pool):
    """Test system health check"""
    mock_pool.fetchval = AsyncMock(return_value=1)  # DB connectivity OK

    health = await dashboard_service._check_system_health("test-tenant", "test-project")

    assert health.overall_status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_health_monitoring_failure(dashboard_service, mock_pool):
    """Test health check failure"""
    mock_pool.fetchval = AsyncMock(side_effect=Exception("DB error"))

    health = await dashboard_service._check_system_health("test-tenant", "test-project")

    assert health.overall_status == HealthStatus.CRITICAL


# Event Broadcasting Tests
@pytest.mark.asyncio
async def test_broadcast_memory_created(dashboard_service, connection_manager):
    """Test broadcasting memory creation event"""
    dashboard_service.connection_manager = connection_manager

    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()

    await connection_manager.connect(ws, "test-tenant", "test-project")

    await dashboard_service.broadcast_memory_created(
        "test-tenant", "test-project", uuid4(), "Test memory content", 0.8
    )

    ws.send_json.assert_called()


@pytest.mark.asyncio
async def test_broadcast_quality_alert(dashboard_service, connection_manager):
    """Test broadcasting quality alert"""
    dashboard_service.connection_manager = connection_manager

    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()

    await connection_manager.connect(ws, "test-tenant", "test-project")

    await dashboard_service.broadcast_quality_alert(
        "test-tenant",
        "test-project",
        "warning",
        "Quality Degraded",
        "MRR dropped below threshold",
        ["Review recent changes"],
    )

    ws.send_json.assert_called()
