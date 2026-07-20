"""
Dashboard API Routes - Real-time Monitoring and Visualization

This module provides FastAPI routes for dashboard operations including:
- Real-time metrics via WebSocket
- System health monitoring
- Interactive visualizations (reflection tree, semantic graph, etc.)
- Activity logs
- Quality trends
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.models.dashboard_models import (
    ActivityLog,
    ComplianceArea,
    ComponentHealth,
    DashboardEventType,
    GetAuditTrailRequest,
    GetAuditTrailResponse,
    GetComplianceMetricsRequest,
    GetComplianceMetricsResponse,
    GetComplianceReportRequest,
    GetComplianceReportResponse,
    GetDashboardMetricsRequest,
    GetDashboardMetricsResponse,
    GetRiskRegisterRequest,
    GetRiskRegisterResponse,
    GetSystemHealthRequest,
    GetSystemHealthResponse,
    GetVisualizationRequest,
    GetVisualizationResponse,
    HealthStatus,
    MemoryTimeline,
    MemoryTimelineEvent,
    MetricPeriod,
    QualityTrend,
    ReflectionTreeNode,
    RiskLevel,
    SemanticGraph,
    SemanticGraphEdge,
    SemanticGraphNode,
    SystemHealth,
    TimeSeriesMetric,
    VisualizationType,
)
from apps.memory_api.repositories.metrics_repository import MetricsRepository
from apps.memory_api.services.compliance_service import ComplianceService
from apps.memory_api.services.dashboard_websocket import DashboardWebSocketService
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Dashboard"])

# Global WebSocket service instance
_websocket_service: Optional[DashboardWebSocketService] = None


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_metrics_repo(
    rae_service: RAECoreService = Depends(get_rae_core_service),
) -> MetricsRepository:
    """Get metrics repository instance"""
    return MetricsRepository(rae_service.db)


async def get_compliance_service(
    rae_service: RAECoreService = Depends(get_rae_core_service),
) -> ComplianceService:
    """Get compliance service instance"""
    return ComplianceService(rae_service)


def get_websocket_service(
    rae_service: RAECoreService = Depends(get_rae_core_service),
) -> DashboardWebSocketService:
    """Get or create WebSocket service instance."""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = DashboardWebSocketService(rae_service.db)
        # Start background tasks
        asyncio.create_task(_websocket_service.start_background_tasks())
    return _websocket_service


# ============================================================================
# WebSocket Endpoint
# ============================================================================


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    tenant_id: str = Query(...),
    project: str = Query(...),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    WebSocket endpoint for real-time dashboard updates.

    **Connection:** ws://host/v2/dashboard/ws?tenant_id=X&project=Y

    **Query Parameters:**
    - tenant_id: Tenant identifier (required)
    - project: Project identifier (required)
    - event_types: Comma-separated list of event types to subscribe to (optional)

    **Messages Received:**
    - Subscription confirmation
    - Metrics updates (every 5 seconds)
    - Event notifications (memory_created, reflection_generated, etc.)
    - Quality alerts
    - Drift detection alerts
    - Health status changes

    **Use Case:** Real-time dashboard monitoring and live updates.
    """
    # Parse event types
    subscribed_events = None
    if event_types:
        try:
            subscribed_events = [
                DashboardEventType(et.strip())
                for et in event_types.split(",")
                if et.strip()
            ]
        except ValueError as e:
            logger.error("invalid_event_types", error=str(e))

    # Get WebSocket service
    service = get_websocket_service()

    # Connect
    connection_id = None
    try:
        connection_id = await service.handle_connection(
            websocket, tenant_id, project, subscribed_events
        )

        logger.info(
            "websocket_connection_established",
            connection_id=connection_id,
            tenant_id=tenant_id,
            project=project,
        )

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client (ping/pong, etc.)
                data = await websocket.receive_text()

                # Handle ping/pong
                if data == "ping":
                    await websocket.send_text("pong")

            except WebSocketDisconnect:
                logger.info(
                    "websocket_client_disconnected", connection_id=connection_id
                )
                break

    except Exception as e:
        logger.error("websocket_error", error=str(e), connection_id=connection_id)

    finally:
        if connection_id:
            service.handle_disconnection(connection_id)


# ============================================================================
# Metrics Endpoints
# ============================================================================


async def _get_dashboard_metrics_impl(
    rae_service: RAECoreService,
    request_data: Optional[GetDashboardMetricsRequest] = None,
    tenant_id: Optional[str] = None,
    project: Optional[str] = None,
    period: MetricPeriod = MetricPeriod.LAST_24H,
) -> GetDashboardMetricsResponse:
    """Shared implementation for dashboard metrics."""
    try:
        # Handle parameters from multiple sources
        t_id = tenant_id
        p_id = project or project  # Fallback to 'project'
        m_period = period

        if request_data:
            t_id = t_id or request_data.tenant_id
            p_id = p_id or request_data.project
            m_period = request_data.period

        # Final safety check
        if not t_id:
            t_id = "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b22"
        if not p_id:
            p_id = "default"

        # Get WebSocket service for metrics collection
        service = get_websocket_service(rae_service)

        # Collect current metrics
        system_metrics = await service._collect_system_metrics(t_id, p_id)

        # Get time series metrics
        time_series_metrics = await _get_time_series_metrics(
            rae_service.db,
            t_id,
            p_id,
            m_period,
        )

        # Get recent activity
        recent_activity = await _get_recent_activity(
            rae_service.db, t_id, p_id, limit=50
        )

        return GetDashboardMetricsResponse(
            system_metrics=system_metrics,
            time_series_metrics=time_series_metrics,
            recent_activity=recent_activity,
            message="Dashboard metrics retrieved successfully",
        )

    except Exception as e:
        logger.error("get_dashboard_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics", response_model=GetDashboardMetricsResponse)
async def get_dashboard_metrics_get(
    tenant_id: Optional[str] = Query(None),
    project: Optional[str] = Query(None),
    period: MetricPeriod = Query(MetricPeriod.LAST_24H),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Get dashboard metrics (GET)."""
    return await _get_dashboard_metrics_impl(
        rae_service=rae_service,
        tenant_id=tenant_id,
        project=project,
        period=period,
    )


@router.post("/metrics", response_model=GetDashboardMetricsResponse)
async def get_dashboard_metrics_post(
    request_data: GetDashboardMetricsRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Get dashboard metrics (POST)."""
    return await _get_dashboard_metrics_impl(
        rae_service=rae_service,
        request_data=request_data,
    )


@router.get("/metrics/timeseries/{metric_name}")
async def get_metric_timeseries(
    metric_name: str,
    tenant_id: str,
    project: str,
    period: MetricPeriod = MetricPeriod.LAST_24H,
    repo: MetricsRepository = Depends(get_metrics_repo),
):
    """
    Get time series data for a specific metric.

    Returns metric values over time with trend analysis.

    **Supported Metrics:**
    - memory_count
    - reflection_count
    - search_quality_mrr
    - avg_importance
    - degraded_nodes
    """
    try:
        # Calculate time range and aggregation interval
        end_time = datetime.now(timezone.utc)
        if period == MetricPeriod.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
            aggregation_interval = "5 minutes"
        elif period == MetricPeriod.LAST_24H:
            start_time = end_time - timedelta(hours=24)
            aggregation_interval = "1 hour"
        elif period == MetricPeriod.LAST_7D:
            start_time = end_time - timedelta(days=7)
            aggregation_interval = "6 hours"
        elif period == MetricPeriod.LAST_30D:
            start_time = end_time - timedelta(days=30)
            aggregation_interval = "1 day"
        else:
            start_time = end_time - timedelta(hours=24)
            aggregation_interval = "1 hour"

        # Fetch metric data from database
        data_points = await repo.get_timeseries(
            tenant_id=tenant_id,
            project=project,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation_interval=aggregation_interval,
        )

        # Transform data points to match model (metric_value -> value)
        formatted_data_points = [
            {
                "timestamp": dp["timestamp"],
                "value": dp["metric_value"],
                "metadata": {
                    k: v
                    for k, v in dp.items()
                    if k not in ["timestamp", "metric_value"]
                },
            }
            for dp in data_points
        ]

        # Convert to TimeSeriesMetric format
        time_series = TimeSeriesMetric(
            metric_name=metric_name,
            metric_label=metric_name.replace("_", " ").title(),
            data_points=formatted_data_points,
            period_start=start_time,
            period_end=end_time,
        )

        # Calculate trend if we have data using simple linear regression for stability
        if len(data_points) > 1:
            n = len(data_points)
            x = list(range(n))
            y = [dp["metric_value"] for dp in data_points]

            # Simple linear regression formula: slope = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - (sum(x))^2)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xx = sum(xi * xi for xi in x)
            sum_xy = sum(xi * yi for xi, yi in zip(x, y))

            denominator = n * sum_xx - sum_x * sum_x
            if denominator != 0:
                slope = (n * sum_xy - sum_x * sum_y) / denominator

                # Calculate percent change relative to the first point estimate (intercept)
                # or just use the overall slope trend.
                # For consistency with UI, we keep percent_change based on first/last but use slope for direction.
                first_val = y[0]
                last_val = y[-1]

                if first_val > 0:
                    percent_change = ((last_val - first_val) / first_val) * 100
                    time_series.percent_change = round(percent_change, 2)

                # Direction is decided by slope to avoid noise of single points
                if slope > 0.01:  # Positive slope
                    time_series.trend_direction = "up"
                elif slope < -0.01:  # Negative slope
                    time_series.trend_direction = "down"
                else:
                    time_series.trend_direction = "stable"

        logger.info(
            "timeseries_metric_retrieved",
            metric=metric_name,
            period=period.value,
            data_points=len(data_points),
        )

        return {
            "time_series": time_series.model_dump(),
            "message": f"Time series for {metric_name} retrieved",
        }

    except Exception as e:
        logger.error("get_metric_timeseries_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Visualization Endpoints
# ============================================================================


@router.post("/visualizations", response_model=GetVisualizationResponse)
async def get_visualization(
    request: GetVisualizationRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Generate visualization data.

    Returns data formatted for specific visualization types:
    - reflection_tree: Hierarchical reflection tree
    - semantic_graph: Knowledge graph with nodes and edges
    - memory_timeline: Chronological memory events
    - quality_trend: Quality metrics over time
    - cluster_map: Memory cluster visualization

    **Use Case:** Interactive visualizations in dashboard.
    """
    try:
        pool = rae_service.db
        response = GetVisualizationResponse(
            visualization_type=request.visualization_type
        )

        if request.visualization_type == VisualizationType.REFLECTION_TREE:
            response.reflection_tree = await _generate_reflection_tree(
                pool,
                request.tenant_id,
                request.project,
                request.root_reflection_id,
                request.max_depth,
            )

        elif request.visualization_type == VisualizationType.SEMANTIC_GRAPH:
            response.semantic_graph = await _generate_semantic_graph(
                pool, request.tenant_id, request.project, request.limit
            )

        elif request.visualization_type == VisualizationType.MEMORY_TIMELINE:
            response.memory_timeline = await _generate_memory_timeline(
                pool,
                request.tenant_id,
                request.project,
                request.start_time,
                request.end_time,
            )

        elif request.visualization_type == VisualizationType.QUALITY_TREND:
            response.quality_trend = await _generate_quality_trend(
                pool,
                request.tenant_id,
                request.project,
                request.start_time,
                request.end_time,
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Visualization type {request.visualization_type} not yet implemented",
            )

        logger.info(
            "visualization_generated",
            type=request.visualization_type.value,
            tenant_id=request.tenant_id,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_visualization_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Health Endpoints
# ============================================================================


@router.post("/health", response_model=GetSystemHealthResponse)
async def get_system_health(
    request: GetSystemHealthRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Get system health status.

    Returns overall health and component-level health indicators.

    **Use Case:** System monitoring, health dashboards.
    """
    try:
        # Get WebSocket service for health check
        service = get_websocket_service(rae_service)

        system_health = await service._check_system_health(
            request.tenant_id, request.project
        )

        # Add component details if requested
        if request.include_sub_components:
            system_health.components = await _get_component_health(rae_service.db)

        # Generate recommendations based on health
        recommendations = _generate_health_recommendations(system_health)

        logger.info(
            "system_health_retrieved",
            status=system_health.overall_status.value,
            tenant_id=request.tenant_id,
        )

        return GetSystemHealthResponse(
            system_health=system_health,
            recommendations=recommendations,
            message="System health retrieved successfully",
        )

    except Exception as e:
        logger.error("get_system_health_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/health/simple")
async def simple_health_check(
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Simple health check endpoint.

    Returns basic health status without detailed metrics.

    **Use Case:** Load balancer health checks, monitoring.
    """
    try:
        # Check database connectivity
        await rae_service.db.fetchval("SELECT 1")

        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "dashboard_api",
        }

    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy") from e


# ============================================================================
# Activity Log Endpoints
# ============================================================================


@router.get("/activity")
async def get_activity_log(
    tenant_id: str,
    project: str,
    limit: int = 100,
    event_types: Optional[str] = Query(None),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Get recent activity log.

    Returns chronological list of recent events and activities.

    **Use Case:** Activity feed, audit trail.
    """
    try:
        # Parse event type filter
        event_type_filter = None
        if event_types:
            event_type_filter = [et.strip() for et in event_types.split(",")]

        activity_logs = await _get_recent_activity(
            rae_service.db, tenant_id, project, limit, event_type_filter
        )

        logger.info(
            "activity_log_retrieved", count=len(activity_logs), tenant_id=tenant_id
        )

        return {
            "activity_logs": [log.model_dump() for log in activity_logs],
            "total_count": len(activity_logs),
            "message": "Activity log retrieved successfully",
        }

    except Exception as e:
        logger.error("get_activity_log_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_time_series_metrics(
    db, tenant_id: str, project: str, period: MetricPeriod
) -> List[TimeSeriesMetric]:
    """Generate time series metrics for dashboard."""
    try:
        repo = MetricsRepository(db)
        metrics = []

        # Calculate time range
        end_time = datetime.now(timezone.utc)
        if period == MetricPeriod.LAST_HOUR:
            start_time = end_time - timedelta(hours=1)
            aggregation_interval = "5 minutes"
        elif period == MetricPeriod.LAST_24H:
            start_time = end_time - timedelta(hours=24)
            aggregation_interval = "1 hour"
        elif period == MetricPeriod.LAST_7D:
            start_time = end_time - timedelta(days=7)
            aggregation_interval = "6 hours"
        elif period == MetricPeriod.LAST_30D:
            start_time = end_time - timedelta(days=30)
            aggregation_interval = "1 day"
        else:
            start_time = end_time - timedelta(hours=24)
            aggregation_interval = "1 hour"

        # Metrics to fetch
        metric_names = [
            "memory_count",
            "reflection_count",
            "semantic_node_count",
            "search_quality_mrr",
            "avg_importance",
        ]

        for metric_name in metric_names:
            try:
                # Fetch metric data
                data_points = await repo.get_timeseries(
                    tenant_id=tenant_id,
                    project=project,
                    metric_name=metric_name,
                    start_time=start_time,
                    end_time=end_time,
                    aggregation_interval=aggregation_interval,
                )

                # Fallback: If no historical data, create a 'live' point from memories table
                if not data_points:
                    try:
                        live_val = 0.0
                        if metric_name == "memory_count":
                            live_val = await db.fetchval(
                                "SELECT COUNT(*)::float FROM memories WHERE tenant_id = $1::uuid AND (project = $2 OR agent_id = $2)",
                                tenant_id,
                                project,
                            )
                        elif metric_name == "reflection_count":
                            live_val = await db.fetchval(
                                "SELECT COUNT(*)::float FROM memories WHERE tenant_id = $1::uuid AND (project = $2 OR agent_id = $2) AND layer IN ('reflective', 'rm')",
                                tenant_id,
                                project,
                            )

                        if live_val is not None and live_val >= 0:
                            data_points = [
                                {
                                    "timestamp": datetime.now(timezone.utc),
                                    "metric_value": float(live_val),
                                }
                            ]
                        else:
                            continue
                    except Exception as e:
                        logger.warning(
                            "live_metric_fallback_failed",
                            metric=metric_name,
                            error=str(e),
                        )
                        continue

                # Format data points
                formatted_data_points = [
                    {
                        "timestamp": dp["timestamp"],
                        "value": dp["metric_value"],
                        "metadata": {
                            k: v
                            for k, v in dp.items()
                            if k not in ["timestamp", "metric_value"]
                        },
                    }
                    for dp in data_points
                ]

                # Create metric object
                ts_metric = TimeSeriesMetric(
                    metric_name=metric_name,
                    metric_label=metric_name.replace("_", " ").title(),
                    data_points=formatted_data_points,
                    period_start=start_time,
                    period_end=end_time,
                )

                # Calculate trend
                if len(data_points) > 1:
                    first_val = data_points[0]["metric_value"]
                    last_val = data_points[-1]["metric_value"]

                    if first_val > 0:
                        percent_change = ((last_val - first_val) / first_val) * 100
                        ts_metric.percent_change = round(percent_change, 2)

                    if last_val > first_val:
                        ts_metric.trend_direction = "up"
                    elif last_val < first_val:
                        ts_metric.trend_direction = "down"
                    else:
                        ts_metric.trend_direction = "stable"

                metrics.append(ts_metric)

            except Exception as e:
                logger.warning("metric_fetch_failed", metric=metric_name, error=str(e))
                continue

        return metrics

    except Exception as e:
        logger.error("get_time_series_metrics_failed", error=str(e))
        return []


async def _get_recent_activity(
    db,
    tenant_id: str,
    project: str,
    limit: int = 50,
    event_types: Optional[List[str]] = None,
) -> List[ActivityLog]:
    """Fetch recent activity logs."""
    try:
        # Fetch recent memories
        memory_records = await db.fetch(
            """
            SELECT id, content, importance, created_at
            FROM memories
            WHERE tenant_id = $1 AND project = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            tenant_id,
            project,
            min(limit, 20),
        )

        activity_logs = []

        for record in memory_records:
            log = ActivityLog(
                log_id=uuid4(),
                event_type=DashboardEventType.MEMORY_CREATED,
                title="Memory Created",
                description=record["content"][:100],
                tenant_id=tenant_id,
                project=project,
                memory_id=record["id"],
                severity="info",
                occurred_at=record["created_at"],
            )
            activity_logs.append(log)

        # Fetch recent reflections
        reflection_records = await db.fetch(
            """
            SELECT id, content, score, created_at
            FROM reflections
            WHERE tenant_id = $1 AND project = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            tenant_id,
            project,
            min(limit, 10),
        )

        for record in reflection_records:
            log = ActivityLog(
                log_id=uuid4(),
                event_type=DashboardEventType.REFLECTION_GENERATED,
                title="Reflection Generated",
                description=record["content"][:100],
                tenant_id=tenant_id,
                project=project,
                reflection_id=record["id"],
                severity="info",
                occurred_at=record["created_at"],
            )
            activity_logs.append(log)

        # Sort by timestamp
        activity_logs.sort(key=lambda x: x.occurred_at, reverse=True)

        return activity_logs[:limit]

    except Exception as e:
        logger.error("get_recent_activity_failed", error=str(e))
        return []


async def _generate_reflection_tree(
    db, tenant_id: str, project: str, root_id: Optional[UUID], max_depth: int
) -> Optional[ReflectionTreeNode]:
    """Generate hierarchical reflection tree."""
    try:
        # If no root specified, get top-level reflections
        if root_id is None:
            records = await db.fetch(
                """
                SELECT id, content, type, score, depth_level,
                       parent_reflection_id, cluster_id,
                       array_length(source_memory_ids, 1) as source_count,
                       created_at
                FROM reflections
                WHERE tenant_id = $1 AND project = $2
                      AND parent_reflection_id IS NULL
                ORDER BY score DESC, created_at DESC
                LIMIT 1
                """,
                tenant_id,
                project,
            )
            if not records:
                return None
            root_record = records[0]
        else:
            root_record = await db.fetchrow(
                """
                SELECT id, content, type, score, depth_level,
                       parent_reflection_id, cluster_id,
                       array_length(source_memory_ids, 1) as source_count,
                       created_at
                FROM reflections
                WHERE id = $1 AND tenant_id = $2 AND project = $3
                """,
                root_id,
                tenant_id,
                project,
            )
            if not root_record:
                return None

        # Build tree node
        root_node = ReflectionTreeNode(
            reflection_id=root_record["id"],
            content=root_record["content"],
            type=root_record["type"],
            score=float(root_record["score"]),
            depth_level=root_record["depth_level"],
            parent_id=root_record["parent_reflection_id"],
            cluster_id=root_record["cluster_id"],
            source_memory_count=root_record["source_count"] or 0,
            created_at=root_record["created_at"],
        )

        # Recursively fetch children if within max depth
        if root_node.depth_level < max_depth:
            children_records = await db.fetch(
                """
                SELECT id, content, type, score, depth_level,
                       parent_reflection_id, cluster_id,
                       array_length(source_memory_ids, 1) as source_count,
                       created_at
                FROM reflections
                WHERE parent_reflection_id = $1
                      AND tenant_id = $2 AND project = $3
                ORDER BY score DESC
                """,
                root_node.reflection_id,
                tenant_id,
                project,
            )

            for child_record in children_records:
                child_node = await _generate_reflection_tree(
                    db, tenant_id, project, child_record["id"], max_depth
                )
                if child_node:
                    root_node.children.append(child_node)

        return root_node

    except Exception as e:
        logger.error("generate_reflection_tree_failed", error=str(e))
        return None


async def _generate_semantic_graph(
    db, tenant_id: str, project: str, limit: int
) -> Optional[SemanticGraph]:
    """Generate semantic knowledge graph."""
    try:
        # Fetch semantic nodes
        node_records = await db.fetch(
            """
            SELECT id, label, node_type, canonical_form,
                   importance_score, reinforcement_count, is_degraded
            FROM semantic_nodes
            WHERE tenant_id = $1 AND project = $2
            ORDER BY importance_score DESC
            LIMIT $3
            """,
            tenant_id,
            project,
            limit,
        )

        nodes = []
        node_ids = set()

        for record in node_records:
            node = SemanticGraphNode(
                node_id=record["id"],
                label=record["label"],
                node_type=record["node_type"],
                canonical_form=record["canonical_form"],
                importance_score=float(record["importance_score"]),
                reinforcement_count=record["reinforcement_count"],
                is_degraded=record["is_degraded"],
            )
            nodes.append(node)
            node_ids.add(record["id"])

        # Fetch edges between these nodes
        edge_records = await db.fetch(
            """
            SELECT source_node_id, target_node_id, relation_type,
                   edge_weight, confidence
            FROM knowledge_graph_edges
            WHERE tenant_id = $1 AND project = $2
                  AND source_node_id = ANY($3)
                  AND target_node_id = ANY($3)
            """,
            tenant_id,
            project,
            list(node_ids),
        )

        edges = []
        for record in edge_records:
            edge = SemanticGraphEdge(
                source_node_id=record["source_node_id"],
                target_node_id=record["target_node_id"],
                relation_type=record["relation_type"],
                weight=float(record["edge_weight"] or 1.0),
                confidence=float(record["confidence"] or 0.8),
            )
            edges.append(edge)

        graph = SemanticGraph(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            avg_degree=(2 * len(edges)) / max(1, len(nodes)),
        )

        return graph

    except Exception as e:
        logger.error("generate_semantic_graph_failed", error=str(e))
        return None


async def _generate_memory_timeline(
    db,
    tenant_id: str,
    project: str,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> Optional[MemoryTimeline]:
    """Generate memory timeline."""
    try:
        # Default time range if not specified
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # Fetch memory events
        records = await db.fetch(
            """
            SELECT id, content, importance, created_at
            FROM memories
            WHERE tenant_id = $1 AND project = $2
                  AND created_at BETWEEN $3 AND $4
            ORDER BY created_at DESC
            LIMIT 100
            """,
            tenant_id,
            project,
            start_time,
            end_time,
        )

        events = []
        for record in records:
            event = MemoryTimelineEvent(
                event_id=uuid4(),
                event_type="memory_created",
                title="Memory Created",
                description=record["content"][:100],
                memory_id=record["id"],
                importance=float(record["importance"]),
                occurred_at=record["created_at"],
            )
            events.append(event)

        timeline = MemoryTimeline(
            events=events,
            start_time=start_time,
            end_time=end_time,
            total_events=len(events),
            event_density=len(events) / max(1, (end_time - start_time).days),
        )

        return timeline

    except Exception as e:
        logger.error("generate_memory_timeline_failed", error=str(e))
        return None


async def _generate_quality_trend(
    db,
    tenant_id: str,
    project: str,
    start_time: Optional[datetime],
    end_time: Optional[datetime],
) -> Optional[QualityTrend]:
    """Generate quality metrics trend."""
    try:
        repo = MetricsRepository(db)

        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # Get MRR data
        data_points = await repo.get_timeseries(
            tenant_id=tenant_id,
            project=project,
            metric_name="search_quality_mrr",
            start_time=start_time,
            end_time=end_time,
            aggregation_interval="1 day",  # Daily trend
        )

        if not data_points:
            # Return empty but valid trend if no data
            return QualityTrend(
                metric_name="mrr",
                time_points=[],
                values=[],
                trend_direction="stable",
                percent_change=0.0,
                current_value=0.0,
                is_healthy=True,
            )

        # Format for QualityTrend
        time_points = [dp["timestamp"] for dp in data_points]
        values = [dp["metric_value"] for dp in data_points]

        # Calculate stats
        current_value = values[-1]

        percent_change = 0.0
        trend_direction = "stable"

        if len(values) > 1:
            first_val = values[0]
            if first_val > 0:
                percent_change = ((current_value - first_val) / first_val) * 100

            if current_value > first_val:
                trend_direction = "up"
            elif current_value < first_val:
                trend_direction = "down"

        # Determine health (example threshold)
        is_healthy = current_value >= 0.5  # Assuming MRR range 0-1

        return QualityTrend(
            metric_name="mrr",
            time_points=time_points,
            values=values,
            trend_direction=trend_direction,
            percent_change=round(percent_change, 2),
            current_value=current_value,
            is_healthy=is_healthy,
        )

    except Exception as e:
        logger.error("generate_quality_trend_failed", error=str(e))
        return None


async def _get_component_health(db) -> List[ComponentHealth]:
    """Get health status for all components."""
    components = []

    # Database component
    try:
        await db.fetchval("SELECT 1")
        db_health = ComponentHealth(
            component_name="database",
            status=HealthStatus.HEALTHY,
            message="Database connection healthy",
        )
    except Exception as e:
        db_health = ComponentHealth(
            component_name="database",
            status=HealthStatus.CRITICAL,
            message=f"Database error: {str(e)}",
        )
    components.append(db_health)

    # Additional components would be checked here
    # (search, LLM provider, cache, etc.)

    return components


def _generate_health_recommendations(health: SystemHealth) -> List[str]:
    """Generate recommendations based on health status."""
    recommendations = []

    if health.overall_status == HealthStatus.DEGRADED:
        recommendations.append("Monitor system closely for further degradation")
        recommendations.append("Review recent changes and deployments")

    elif health.overall_status == HealthStatus.WARNING:
        recommendations.append("Investigate warning conditions")
        recommendations.append("Consider scaling resources if needed")

    elif health.overall_status == HealthStatus.CRITICAL:
        recommendations.append("URGENT: Immediate investigation required")
        recommendations.append("Check all system components")
        recommendations.append("Review logs for errors")

    if health.error_rate > 0.05:
        recommendations.append(f"High error rate detected: {health.error_rate:.2%}")
        recommendations.append("Review application logs for error patterns")

    if health.degraded_components > 0:
        recommendations.append(f"{health.degraded_components} components degraded")
        recommendations.append("Check component-level health details")

    return recommendations


# ============================================================================
# System Information
# ============================================================================


@router.get("/info")
async def get_dashboard_info():
    """
    Get information about the dashboard system.

    Returns available visualizations, metrics, and capabilities.
    """
    return {
        "visualizations": {
            "reflection_tree": "Hierarchical reflection tree with parent-child relationships",
            "semantic_graph": "Knowledge graph showing semantic node relationships",
            "memory_timeline": "Chronological timeline of memory events",
            "quality_trend": "Quality metrics trends over time",
            "search_heatmap": "Search activity patterns",
            "cluster_map": "Memory cluster visualization",
        },
        "metrics": {
            "system_metrics": [
                "total_memories",
                "total_reflections",
                "total_semantic_nodes",
                "degraded_nodes_count",
                "active_triggers",
                "search_quality_mrr",
            ],
            "time_series_metrics": [
                "memory_count",
                "reflection_count",
                "search_quality",
                "avg_importance",
                "trigger_executions",
            ],
        },
        "real_time_features": {
            "websocket_endpoint": "/v2/dashboard/ws",
            "event_types": [e.value for e in DashboardEventType],
            "update_interval_seconds": 5,
        },
        "health_monitoring": {
            "components": ["database", "search", "llm_provider", "cache"],
            "status_levels": [s.value for s in HealthStatus],
        },
        "compliance": {
            "iso42001_enabled": True,
            "compliance_endpoints": [
                "/v2/dashboard/compliance/report",
                "/v2/dashboard/compliance/metrics",
                "/v2/dashboard/compliance/risks",
                "/v2/dashboard/compliance/audit-trail",
                "/v2/dashboard/compliance/rls-status",
            ],
        },
    }


# Compliance endpoints migrated to compliance.py
