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

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

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
    project_id: str = Query(...),
    event_types: Optional[str] = Query(None, description="Comma-separated event types"),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    WebSocket endpoint for real-time dashboard updates.

    **Connection:** ws://host/v1/dashboard/ws?tenant_id=X&project_id=Y

    **Query Parameters:**
    - tenant_id: Tenant identifier (required)
    - project_id: Project identifier (required)
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
            websocket, tenant_id, project_id, subscribed_events
        )

        logger.info(
            "websocket_connection_established",
            connection_id=connection_id,
            tenant_id=tenant_id,
            project_id=project_id,
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


@router.api_route(
    "/metrics", methods=["GET", "POST"], response_model=GetDashboardMetricsResponse
)
async def get_dashboard_metrics(
    request_data: Optional[GetDashboardMetricsRequest] = None,
    tenant_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    project: Optional[str] = Query(None),  # Alternative for Streamlit
    period: MetricPeriod = Query(MetricPeriod.LAST_24H),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Get dashboard metrics for a time period.
    Supports both POST (JSON body) and GET (Query params).
    """
    try:
        # Handle parameters from multiple sources
        t_id = tenant_id
        p_id = project_id or project  # Fallback to 'project'
        m_period = period

        if request_data:
            t_id = t_id or request_data.tenant_id
            p_id = p_id or request_data.project_id
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


@router.get("/metrics/timeseries/{metric_name}")
async def get_metric_timeseries(
    metric_name: str,
    tenant_id: str,
    project_id: str,
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
            project_id=project_id,
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
                request.project_id,
                request.root_reflection_id,
                request.max_depth,
            )

        elif request.visualization_type == VisualizationType.SEMANTIC_GRAPH:
            response.semantic_graph = await _generate_semantic_graph(
                pool, request.tenant_id, request.project_id, request.limit
            )

        elif request.visualization_type == VisualizationType.MEMORY_TIMELINE:
            response.memory_timeline = await _generate_memory_timeline(
                pool,
                request.tenant_id,
                request.project_id,
                request.start_time,
                request.end_time,
            )

        elif request.visualization_type == VisualizationType.QUALITY_TREND:
            response.quality_trend = await _generate_quality_trend(
                pool,
                request.tenant_id,
                request.project_id,
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
            request.tenant_id, request.project_id
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
    project_id: str,
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
            rae_service.db, tenant_id, project_id, limit, event_type_filter
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
    db, tenant_id: str, project_id: str, period: MetricPeriod
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
                    project_id=project_id,
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
                                project_id,
                            )
                        elif metric_name == "reflection_count":
                            live_val = await db.fetchval(
                                "SELECT COUNT(*)::float FROM memories WHERE tenant_id = $1::uuid AND (project = $2 OR agent_id = $2) AND layer IN ('reflective', 'rm')",
                                tenant_id,
                                project_id,
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
    project_id: str,
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
            project_id,
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
                project_id=project_id,
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
            WHERE tenant_id = $1 AND project_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            tenant_id,
            project_id,
            min(limit, 10),
        )

        for record in reflection_records:
            log = ActivityLog(
                log_id=uuid4(),
                event_type=DashboardEventType.REFLECTION_GENERATED,
                title="Reflection Generated",
                description=record["content"][:100],
                tenant_id=tenant_id,
                project_id=project_id,
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
    db, tenant_id: str, project_id: str, root_id: Optional[UUID], max_depth: int
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
                WHERE tenant_id = $1 AND project_id = $2
                      AND parent_reflection_id IS NULL
                ORDER BY score DESC, created_at DESC
                LIMIT 1
                """,
                tenant_id,
                project_id,
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
                WHERE id = $1 AND tenant_id = $2 AND project_id = $3
                """,
                root_id,
                tenant_id,
                project_id,
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
                      AND tenant_id = $2 AND project_id = $3
                ORDER BY score DESC
                """,
                root_node.reflection_id,
                tenant_id,
                project_id,
            )

            for child_record in children_records:
                child_node = await _generate_reflection_tree(
                    db, tenant_id, project_id, child_record["id"], max_depth
                )
                if child_node:
                    root_node.children.append(child_node)

        return root_node

    except Exception as e:
        logger.error("generate_reflection_tree_failed", error=str(e))
        return None


async def _generate_semantic_graph(
    db, tenant_id: str, project_id: str, limit: int
) -> Optional[SemanticGraph]:
    """Generate semantic knowledge graph."""
    try:
        # Fetch semantic nodes
        node_records = await db.fetch(
            """
            SELECT id, label, node_type, canonical_form,
                   importance_score, reinforcement_count, is_degraded
            FROM semantic_nodes
            WHERE tenant_id = $1 AND project_id = $2
            ORDER BY importance_score DESC
            LIMIT $3
            """,
            tenant_id,
            project_id,
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
            WHERE tenant_id = $1 AND project_id = $2
                  AND source_node_id = ANY($3)
                  AND target_node_id = ANY($3)
            """,
            tenant_id,
            project_id,
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
    project_id: str,
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
            project_id,
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
    project_id: str,
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
            project_id=project_id,
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
            "websocket_endpoint": "/v1/dashboard/ws",
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
                "/v1/dashboard/compliance/report",
                "/v1/dashboard/compliance/metrics",
                "/v1/dashboard/compliance/risks",
                "/v1/dashboard/compliance/audit-trail",
                "/v1/dashboard/compliance/rls-status",
            ],
        },
    }


# ============================================================================
# ISO/IEC 42001 Compliance Endpoints
# ============================================================================


@router.post(
    "/compliance/report",
    response_model=GetComplianceReportResponse,
    summary="Get ISO 42001 Compliance Report",
)
async def get_compliance_report(
    request: GetComplianceReportRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get comprehensive ISO/IEC 42001 compliance report.

    Returns:
    - Overall compliance score
    - Compliance metrics by area (governance, risk management, data management, etc.)
    - Active risks from risk register
    - Data retention metrics
    - Source trust metrics
    - Audit trail completeness
    - Critical gaps and recommendations
    - Certification readiness status

    This endpoint aggregates compliance data from multiple sources to provide
    a complete view of ISO 42001 compliance status.
    """
    try:
        logger.info(
            "compliance_report_requested",
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            report_type=request.report_type,
        )

        # Generate compliance report
        compliance_report = await compliance_service.generate_compliance_report(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            report_type=request.report_type,
            compliance_area=request.compliance_area,
        )

        # Get RLS status if requested
        rls_status = None
        if request.include_audit_trail:
            rls_status = await compliance_service.verify_rls_status(
                tenant_id=request.tenant_id
            )

        logger.info(
            "compliance_report_generated",
            tenant_id=request.tenant_id,
            overall_score=compliance_report.overall_compliance_score,
            status=compliance_report.overall_status,
        )

        return GetComplianceReportResponse(
            compliance_report=compliance_report,
            rls_status=rls_status,
            message=f"Compliance report generated successfully. Overall score: {compliance_report.overall_compliance_score:.1f}%",
        )

    except Exception as e:
        logger.error(
            "compliance_report_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate compliance report: {str(e)}"
        ) from e


@router.post(
    "/compliance/metrics",
    response_model=GetComplianceMetricsResponse,
    summary="Get Compliance Metrics by Area",
)
async def get_compliance_metrics(
    request: GetComplianceMetricsRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get compliance metrics filtered by area.

    Allows filtering by specific compliance area (governance, risk management, etc.)
    and optionally includes historical data for trend analysis.
    """
    try:
        # For now, generate full report and filter
        # In production, this would be optimized to only fetch requested area
        full_report = await compliance_service.generate_compliance_report(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            report_type="area_specific" if request.compliance_area else "full",
            compliance_area=request.compliance_area,
        )

        # Extract metrics for requested area
        metrics = []
        if request.compliance_area:
            area_map = {
                ComplianceArea.GOVERNANCE: full_report.governance_metrics,
                ComplianceArea.RISK_MANAGEMENT: full_report.risk_management_metrics,
                ComplianceArea.DATA_MANAGEMENT: full_report.data_management_metrics,
                ComplianceArea.TRANSPARENCY: full_report.transparency_metrics,
                ComplianceArea.HUMAN_OVERSIGHT: full_report.human_oversight_metrics,
                ComplianceArea.SECURITY_PRIVACY: full_report.security_privacy_metrics,
            }
            metrics = area_map.get(request.compliance_area, [])
        else:
            # All metrics
            metrics = (
                full_report.governance_metrics
                + full_report.risk_management_metrics
                + full_report.data_management_metrics
                + full_report.transparency_metrics
                + full_report.human_oversight_metrics
                + full_report.security_privacy_metrics
            )

        # Calculate area scores
        area_scores = {}
        for area in ComplianceArea:
            area_metrics = [m for m in metrics if m.compliance_area == area]
            if area_metrics:
                compliant = sum(
                    1 for m in area_metrics if m.status.value == "compliant"
                )
                area_scores[area.value] = compliant / len(area_metrics) * 100

        return GetComplianceMetricsResponse(
            metrics=metrics,
            area_scores=area_scores,
            overall_score=full_report.overall_compliance_score,
            message=f"Retrieved {len(metrics)} compliance metrics",
        )

    except Exception as e:
        logger.error(
            "compliance_metrics_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get compliance metrics: {str(e)}"
        ) from e


@router.post(
    "/compliance/risks",
    response_model=GetRiskRegisterResponse,
    summary="Get Risk Register Data",
)
async def get_risk_register(
    request: GetRiskRegisterRequest,
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get risk register data with optional filtering.

    Returns active risks from the risk register with filtering options for:
    - Risk level (critical, high, medium, low)
    - Status (open, mitigated, accepted, closed)
    - Option to include closed risks
    """
    try:
        # Get active risks
        risks = await compliance_service._get_active_risks(
            tenant_id=request.tenant_id, project_id=request.project_id
        )

        # Apply filters
        if request.risk_level:
            risks = [r for r in risks if r.risk_level == request.risk_level]

        if request.status:
            risks = [r for r in risks if r.status == request.status]

        if not request.include_closed:
            risks = [r for r in risks if r.status != "closed"]

        # Calculate risk summary
        risk_summary = {}
        for level in RiskLevel:
            risk_summary[level.value] = sum(1 for r in risks if r.risk_level == level)

        high_priority_count = sum(
            1 for r in risks if r.risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]
        )

        logger.info(
            "risk_register_retrieved",
            tenant_id=request.tenant_id,
            total_risks=len(risks),
            high_priority=high_priority_count,
        )

        return GetRiskRegisterResponse(
            risks=risks,
            risk_summary=risk_summary,
            high_priority_count=high_priority_count,
            message=f"Retrieved {len(risks)} risks from risk register",
        )

    except Exception as e:
        logger.error(
            "risk_register_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get risk register: {str(e)}"
        ) from e


@router.post(
    "/compliance/audit-trail",
    response_model=GetAuditTrailResponse,
    summary="Get Audit Trail Entries",
)
async def get_audit_trail(
    request: GetAuditTrailRequest,
):
    """
    Get audit trail entries for compliance verification.

    Returns audit log entries with filtering by:
    - Time range
    - Event types
    - Actor types

    Includes pagination support via limit/offset parameters.
    """
    try:
        # Placeholder - would query audit_trail_log table
        # For now, return empty result
        entries: List[Dict[str, Any]] = []
        total_count = 0
        completeness = 85.0  # Placeholder

        logger.info(
            "audit_trail_retrieved",
            tenant_id=request.tenant_id,
            entry_count=len(entries),
        )

        return GetAuditTrailResponse(
            entries=entries,
            total_count=total_count,
            completeness_percentage=completeness,
            message=f"Retrieved {len(entries)} audit trail entries",
        )

    except Exception as e:
        logger.error(
            "audit_trail_failed",
            tenant_id=request.tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get audit trail: {str(e)}"
        ) from e


@router.get(
    "/compliance/rls-status",
    summary="Get RLS Verification Status",
)
async def get_rls_status(
    tenant_id: str = Query(..., description="Tenant ID"),
    compliance_service: ComplianceService = Depends(get_compliance_service),
):
    """
    Get Row-Level Security verification status.

    Verifies that:
    - RLS is enabled on all critical tables
    - Policies are active
    - No security gaps exist

    This is a critical security check for tenant isolation compliance.
    """
    try:
        rls_status = await compliance_service.verify_rls_status(tenant_id=tenant_id)

        logger.info(
            "rls_status_checked",
            tenant_id=tenant_id,
            verification_passed=rls_status.verification_passed,
            rls_percentage=rls_status.rls_enabled_percentage,
        )

        return {
            "tenant_id": tenant_id,
            "rls_status": rls_status,
            "message": (
                "RLS verification passed"
                if rls_status.verification_passed
                else "RLS verification failed - see issues"
            ),
        }

    except Exception as e:
        logger.error(
            "rls_status_check_failed",
            tenant_id=tenant_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to verify RLS status: {str(e)}"
        ) from e
