"""
Dashboard WebSocket Service - Real-time Updates

This service manages WebSocket connections for the dashboard and pushes
real-time updates including:
- System metrics changes
- New memories, reflections, semantic nodes
- Quality alerts and drift detection
- Trigger executions
- Health status changes
"""

import asyncio
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

import asyncpg
import structlog
from fastapi import WebSocket

from apps.memory_api.models.dashboard_models import (
    AlertMessage,
    DashboardEventType,
    HealthChangeMessage,
    HealthStatus,
    MetricPeriod,
    MetricsUpdateMessage,
    SystemHealth,
    SystemMetrics,
    WebSocketMessage,
    WebSocketSubscription,
)
from rae_adapters.postgres_db import PostgresDatabaseProvider
from rae_core.interfaces.database import IDatabaseProvider

logger = structlog.get_logger(__name__)


# ============================================================================
# Connection Manager
# ============================================================================


class ConnectionManager:
    """
    Manages WebSocket connections for dashboard clients.

    Handles connection lifecycle, message broadcasting, and subscriptions.
    """

    def __init__(self):
        """Initialize connection manager."""
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # Subscriptions: {connection_id: WebSocketSubscription}
        self.subscriptions: Dict[str, WebSocketSubscription] = {}

        # Tenant/project mapping: {(tenant_id, project_id): Set[connection_id]}
        self.tenant_connections: Dict[tuple, Set[str]] = {}

        logger.info("connection_manager_initialized")

    async def connect(
        self,
        websocket: WebSocket,
        tenant_id: str,
        project_id: str,
        event_types: Optional[List[DashboardEventType]] = None,
    ) -> str:
        """
        Accept WebSocket connection and register subscription.

        Args:
            websocket: WebSocket connection
            tenant_id: Tenant identifier
            project_id: Project identifier
            event_types: Event types to subscribe to

        Returns:
            Connection ID
        """
        await websocket.accept()

        connection_id = str(uuid4())

        # Register connection
        self.active_connections[connection_id] = websocket

        # Create subscription
        subscription = WebSocketSubscription(
            subscription_id=uuid4(),
            tenant_id=tenant_id,
            project_id=project_id,
            subscribed_events=event_types or list(DashboardEventType),
            update_interval_seconds=5,
        )
        self.subscriptions[connection_id] = subscription

        # Map tenant/project to connection
        key = (tenant_id, project_id)
        if key not in self.tenant_connections:
            self.tenant_connections[key] = set()
        self.tenant_connections[key].add(connection_id)

        logger.info(
            "websocket_connected",
            connection_id=connection_id,
            tenant_id=tenant_id,
            project_id=project_id,
        )

        # Send subscription confirmation
        await self._send_message(
            connection_id,
            {
                "type": "subscription_confirmed",
                "subscription_id": str(subscription.subscription_id),
                "subscribed_events": [e.value for e in subscription.subscribed_events],
            },
        )

        return connection_id

    def disconnect(self, connection_id: str):
        """
        Disconnect WebSocket and cleanup subscriptions.

        Args:
            connection_id: Connection identifier
        """
        if connection_id not in self.active_connections:
            return

        # Get subscription info for cleanup
        subscription = self.subscriptions.get(connection_id)

        # Remove from tenant mapping
        if subscription:
            key = (subscription.tenant_id, subscription.project_id)
            if key in self.tenant_connections:
                self.tenant_connections[key].discard(connection_id)
                if not self.tenant_connections[key]:
                    del self.tenant_connections[key]

        # Remove subscription and connection
        self.subscriptions.pop(connection_id, None)
        self.active_connections.pop(connection_id, None)

        logger.info("websocket_disconnected", connection_id=connection_id)

    async def broadcast_to_tenant(self, tenant_id: str, project_id: str, message: Dict):
        """
        Broadcast message to all connections for a tenant/project.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            message: Message to broadcast
        """
        key = (tenant_id, project_id)
        connection_ids = self.tenant_connections.get(key, set())

        # Filter by event type subscription
        event_type = message.get("event_type")

        for conn_id in list(
            connection_ids
        ):  # Copy to avoid modification during iteration
            subscription = self.subscriptions.get(conn_id)

            # Check if subscribed to this event type
            if subscription and event_type:
                try:
                    event_enum = DashboardEventType(event_type)
                    if event_enum not in subscription.subscribed_events:
                        continue
                except ValueError:
                    pass  # Unknown event type, send anyway

            await self._send_message(conn_id, message)

    async def broadcast_to_all(self, message: Dict):
        """
        Broadcast message to all active connections.

        Args:
            message: Message to broadcast
        """
        for conn_id in list(self.active_connections.keys()):
            await self._send_message(conn_id, message)

    async def _send_message(self, connection_id: str, message: Dict):
        """
        Send message to specific connection.

        Args:
            connection_id: Connection identifier
            message: Message to send
        """
        websocket = self.active_connections.get(connection_id)
        if not websocket:
            return

        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(
                "websocket_send_failed", connection_id=connection_id, error=str(e)
            )
            # Disconnect on error
            self.disconnect(connection_id)


# ============================================================================
# Dashboard WebSocket Service
# ============================================================================


class DashboardWebSocketService:
    """
    Service for dashboard WebSocket functionality.

    Manages real-time updates, metrics collection, and event broadcasting.
    """

    def __init__(self, pool: asyncpg.Pool | IDatabaseProvider):
        """
        Initialize dashboard WebSocket service.

        Args:
            pool: Database connection pool or IDatabaseProvider
        """
        self.db: IDatabaseProvider
        if isinstance(pool, (asyncpg.Pool, asyncpg.Connection)):
            self.db = PostgresDatabaseProvider(pool)
        else:
            self.db = pool
        self.connection_manager = ConnectionManager()

        # Background tasks
        self._metrics_task: Optional[asyncio.Task] = None
        self._health_task: Optional[asyncio.Task] = None

        # Cached data
        self._cached_metrics: Dict[tuple, SystemMetrics] = {}
        self._cached_health: Dict[tuple, SystemHealth] = {}

        logger.info("dashboard_websocket_service_initialized")

    async def start_background_tasks(self):
        """Start background tasks for metrics collection and health monitoring."""
        if self._metrics_task is None or self._metrics_task.done():
            self._metrics_task = asyncio.create_task(self._metrics_collection_loop())
            logger.info("metrics_collection_task_started")

        if self._health_task is None or self._health_task.done():
            self._health_task = asyncio.create_task(self._health_monitoring_loop())
            logger.info("health_monitoring_task_started")

    async def stop_background_tasks(self):
        """Stop background tasks."""
        if self._metrics_task and not self._metrics_task.done():
            self._metrics_task.cancel()
            try:
                await self._metrics_task
            except asyncio.CancelledError:
                pass

        if self._health_task and not self._health_task.done():
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        logger.info("background_tasks_stopped")

    # ========================================================================
    # Connection Management
    # ========================================================================

    async def handle_connection(
        self,
        websocket: WebSocket,
        tenant_id: str,
        project_id: str,
        event_types: Optional[List[DashboardEventType]] = None,
    ) -> str:
        """
        Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection
            tenant_id: Tenant identifier
            project_id: Project identifier
            event_types: Event types to subscribe to

        Returns:
            Connection ID
        """
        return await self.connection_manager.connect(
            websocket, tenant_id, project_id, event_types
        )

    def handle_disconnection(self, connection_id: str):
        """
        Handle WebSocket disconnection.

        Args:
            connection_id: Connection identifier
        """
        self.connection_manager.disconnect(connection_id)

    # ========================================================================
    # Event Broadcasting
    # ========================================================================

    async def broadcast_memory_created(
        self,
        tenant_id: str,
        project_id: str,
        memory_id: UUID,
        content: str,
        importance: float,
    ):
        """Broadcast memory creation event."""
        message = WebSocketMessage(
            event_type=DashboardEventType.MEMORY_CREATED,
            tenant_id=tenant_id,
            project_id=project_id,
            payload={
                "memory_id": str(memory_id),
                "content": content[:200],  # Truncate
                "importance": importance,
            },
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id, project_id, message.model_dump()
        )

    async def broadcast_reflection_generated(
        self,
        tenant_id: str,
        project_id: str,
        reflection_id: UUID,
        content: str,
        score: float,
    ):
        """Broadcast reflection generation event."""
        message = WebSocketMessage(
            event_type=DashboardEventType.REFLECTION_GENERATED,
            tenant_id=tenant_id,
            project_id=project_id,
            payload={
                "reflection_id": str(reflection_id),
                "content": content[:200],
                "score": score,
            },
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id, project_id, message.model_dump()
        )

    async def broadcast_semantic_node_created(
        self, tenant_id: str, project_id: str, node_id: UUID, label: str, node_type: str
    ):
        """Broadcast semantic node creation event."""
        message = WebSocketMessage(
            event_type=DashboardEventType.SEMANTIC_NODE_CREATED,
            tenant_id=tenant_id,
            project_id=project_id,
            payload={"node_id": str(node_id), "label": label, "node_type": node_type},
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id, project_id, message.model_dump()
        )

    async def broadcast_quality_alert(
        self,
        tenant_id: str,
        project_id: str,
        severity: str,
        title: str,
        description: str,
        actions: Optional[List[str]] = None,
    ):
        """Broadcast quality degradation alert."""
        alert_message = AlertMessage(
            event_type=DashboardEventType.QUALITY_ALERT,
            tenant_id=tenant_id,
            project_id=project_id,
            severity=severity,
            title=title,
            description=description,
            actions=actions or [],
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id, project_id, alert_message.model_dump()
        )

    async def broadcast_drift_detected(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        drift_severity: str,
        drift_magnitude: float,
        actions: Optional[List[str]] = None,
    ):
        """Broadcast drift detection alert."""
        alert_message = AlertMessage(
            event_type=DashboardEventType.DRIFT_DETECTED,
            tenant_id=tenant_id,
            project_id=project_id,
            severity=drift_severity,
            title=f"Drift Detected: {metric_name}",
            description=f"Distribution drift detected with magnitude {drift_magnitude:.3f}",
            actions=actions or [],
            payload={
                "metric_name": metric_name,
                "drift_severity": drift_severity,
                "drift_magnitude": drift_magnitude,
            },
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id, project_id, alert_message.model_dump()
        )

    async def broadcast_trigger_fired(
        self,
        tenant_id: str,
        project_id: str,
        trigger_id: UUID,
        trigger_name: str,
        event_type: str,
        actions_queued: int,
    ):
        """Broadcast trigger execution event."""
        message = WebSocketMessage(
            event_type=DashboardEventType.TRIGGER_FIRED,
            tenant_id=tenant_id,
            project_id=project_id,
            payload={
                "trigger_id": str(trigger_id),
                "trigger_name": trigger_name,
                "event_type": event_type,
                "actions_queued": actions_queued,
            },
        )

        await self.connection_manager.broadcast_to_tenant(
            tenant_id, project_id, message.model_dump()
        )

    # ========================================================================
    # Metrics Collection
    # ========================================================================

    async def _metrics_collection_loop(self):
        """Background task to collect and broadcast metrics periodically."""
        while True:
            try:
                # Collect metrics for each tenant/project with active connections
                for (tenant_id, project_id), conn_ids in list(
                    self.connection_manager.tenant_connections.items()
                ):
                    if not conn_ids:
                        continue

                    # Collect metrics
                    metrics = await self._collect_system_metrics(tenant_id, project_id)

                    # Check if metrics changed significantly
                    key = (tenant_id, project_id)
                    cached = self._cached_metrics.get(key)

                    if self._metrics_changed_significantly(cached, metrics):
                        # Broadcast update
                        message = MetricsUpdateMessage(
                            tenant_id=tenant_id, project_id=project_id, metrics=metrics
                        )

                        await self.connection_manager.broadcast_to_tenant(
                            tenant_id, project_id, message.model_dump()
                        )

                        # Update cache
                        self._cached_metrics[key] = metrics

                # Sleep for update interval
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                logger.info("metrics_collection_loop_cancelled")
                break
            except Exception as e:
                logger.error("metrics_collection_error", error=str(e))
                await asyncio.sleep(5)

    async def _collect_system_metrics(
        self, tenant_id: str, project_id: str
    ) -> SystemMetrics:
        """
        Collect system metrics for a tenant/project.
        """
        try:
            # 1. Fetch count per layer for this project
            # Explicitly cast tenant_id to UUID to match schema
            layer_counts = await self.db.fetch(
                """
                SELECT layer, COUNT(*) as count, AVG(importance) as avg_imp
                FROM memories
                WHERE tenant_id = $1::uuid AND (project = $2 OR agent_id = $2)
                GROUP BY layer
                """,
                tenant_id,
                project_id,
            )

            counts = {r["layer"]: r["count"] for r in layer_counts}
            avg_imps = {r["layer"]: float(r["avg_imp"] or 0.0) for r in layer_counts}

            # Map common variants to standard names
            counts.get("episodic", 0) + counts.get("em", 0)
            reflective = (
                counts.get("reflective", 0)
                + counts.get("reflections", 0)
                + counts.get("long-term", 0)
                + counts.get("rm", 0)
            )
            semantic = counts.get("semantic", 0) + counts.get("concepts", 0)

            total = sum(counts.values())

            # 2. Graph metrics
            graph_stats_row = await self.db.fetchrow(
                """
                SELECT
                    (SELECT COUNT(*) FROM knowledge_graph_nodes WHERE tenant_id = $1::uuid) as total_nodes,
                    (SELECT COUNT(*) FROM knowledge_graph_edges WHERE tenant_id = $1::uuid) as total_edges
                """,
                tenant_id,
            )
            graph_stats = graph_stats_row or {"total_nodes": 0, "total_edges": 0}

            # Build metrics object
            metrics = SystemMetrics(
                total_memories=total,
                memories_last_24h=0,  # Placeholder for now
                avg_memory_importance=avg_imps.get("episodic", 0.5),
                total_reflections=reflective,
                reflections_last_24h=0,
                avg_reflection_score=avg_imps.get("reflective", 0.0),
                total_semantic_nodes=semantic,
                semantic_nodes_last_24h=0,
                degraded_nodes_count=0,
                total_graph_nodes=graph_stats["total_nodes"] or 0,
                total_graph_edges=graph_stats["total_edges"] or 0,
                avg_node_degree=(
                    (2 * (graph_stats["total_edges"] or 0))
                    / max(1, (graph_stats["total_nodes"] or 1))
                ),
                active_triggers=0,
                trigger_executions_last_24h=0,
                trigger_success_rate=0.0,
                health_status=HealthStatus.HEALTHY,
                error_rate_last_hour=0.0,
                period=MetricPeriod.LAST_24H,
            )

            return metrics

        except Exception as e:
            logger.error("collect_system_metrics_failed", error=str(e))
            return SystemMetrics()

    def _metrics_changed_significantly(
        self, old: Optional[SystemMetrics], new: SystemMetrics
    ) -> bool:
        """
        Check if metrics changed significantly enough to warrant an update.

        Args:
            old: Previous metrics
            new: New metrics

        Returns:
            True if significantly changed
        """
        if old is None:
            return True

        # Check for significant changes (> 5% or > 5 absolute)
        thresholds = [
            (abs(new.total_memories - old.total_memories) > 5),
            (abs(new.memories_last_24h - old.memories_last_24h) > 5),
            (abs(new.total_reflections - old.total_reflections) > 2),
            (abs(new.total_semantic_nodes - old.total_semantic_nodes) > 5),
            (abs(new.degraded_nodes_count - old.degraded_nodes_count) > 2),
            (
                abs(new.trigger_executions_last_24h - old.trigger_executions_last_24h)
                > 10
            ),
            (new.health_status != old.health_status),
        ]

        return any(thresholds)

    # ========================================================================
    # Health Monitoring
    # ========================================================================

    async def _health_monitoring_loop(self):
        """Background task to monitor system health and broadcast changes."""
        while True:
            try:
                # Check health for each tenant/project with active connections
                for (tenant_id, project_id), conn_ids in list(
                    self.connection_manager.tenant_connections.items()
                ):
                    if not conn_ids:
                        continue

                    # Check health
                    health = await self._check_system_health(tenant_id, project_id)

                    # Check if health status changed
                    key = (tenant_id, project_id)
                    cached = self._cached_health.get(key)

                    if cached and health.overall_status != cached.overall_status:
                        # Broadcast health change
                        message = HealthChangeMessage(
                            tenant_id=tenant_id,
                            project_id=project_id,
                            old_status=cached.overall_status,
                            new_status=health.overall_status,
                            reason=f"System health changed to {health.overall_status.value}",
                        )

                        await self.connection_manager.broadcast_to_tenant(
                            tenant_id, project_id, message.model_dump()
                        )

                    # Update cache
                    self._cached_health[key] = health

                # Sleep for check interval
                await asyncio.sleep(10)

            except asyncio.CancelledError:
                logger.info("health_monitoring_loop_cancelled")
                break
            except Exception as e:
                logger.error("health_monitoring_error", error=str(e))
                await asyncio.sleep(10)

    async def _check_system_health(
        self, tenant_id: str, project_id: str
    ) -> SystemHealth:
        """
        Check system health for a tenant/project.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier

        Returns:
            SystemHealth
        """
        # Simple health check for now
        # In production, would check multiple components

        try:
            # Check database connectivity
            await self.db.fetchval("SELECT 1")

            return SystemHealth(
                overall_status=HealthStatus.HEALTHY,
                uptime_seconds=0.0,  # Would track actual uptime
                total_requests_last_hour=0,
                avg_response_time_ms=0.0,
                error_rate=0.0,
            )

        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return SystemHealth(
                overall_status=HealthStatus.CRITICAL,
                uptime_seconds=0.0,
                total_requests_last_hour=0,
                avg_response_time_ms=0.0,
                error_rate=1.0,
            )
