"""
Memory Dashboard Models - Real-time Monitoring and Visualization

This module defines models for the interactive dashboard including:
- Real-time metrics and statistics
- Visualization data structures
- WebSocket event messages
- System health indicators
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class DashboardEventType(str, Enum):
    """Types of dashboard events pushed via WebSocket"""

    MEMORY_CREATED = "memory_created"
    MEMORY_UPDATED = "memory_updated"
    MEMORY_DELETED = "memory_deleted"

    REFLECTION_GENERATED = "reflection_generated"
    SEMANTIC_NODE_CREATED = "semantic_node_created"

    SEARCH_EXECUTED = "search_executed"
    QUALITY_ALERT = "quality_alert"
    DRIFT_DETECTED = "drift_detected"

    TRIGGER_FIRED = "trigger_fired"
    ACTION_COMPLETED = "action_completed"

    METRICS_UPDATED = "metrics_updated"
    HEALTH_CHANGED = "health_changed"


class VisualizationType(str, Enum):
    """Types of visualizations"""

    REFLECTION_TREE = "reflection_tree"
    SEMANTIC_GRAPH = "semantic_graph"
    MEMORY_TIMELINE = "memory_timeline"
    QUALITY_TREND = "quality_trend"
    SEARCH_HEATMAP = "search_heatmap"
    CLUSTER_MAP = "cluster_map"


class HealthStatus(str, Enum):
    """System health status levels"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


class MetricPeriod(str, Enum):
    """Time periods for metrics"""

    LAST_HOUR = "last_hour"
    LAST_24H = "last_24h"
    LAST_7D = "last_7d"
    LAST_30D = "last_30d"
    CUSTOM = "custom"


# ============================================================================
# Real-time Metrics Models
# ============================================================================


class SystemMetrics(BaseModel):
    """
    Real-time system metrics for dashboard.

    Provides overview of system activity and health.
    """

    # Memory metrics
    total_memories: int = Field(0, ge=0)
    memories_last_24h: int = Field(0, ge=0)
    avg_memory_importance: float = Field(0.0, ge=0.0, le=1.0)

    # Reflection metrics
    total_reflections: int = Field(0, ge=0)
    reflections_last_24h: int = Field(0, ge=0)
    avg_reflection_score: float = Field(0.0, ge=0.0, le=1.0)

    # Semantic metrics
    total_semantic_nodes: int = Field(0, ge=0)
    semantic_nodes_last_24h: int = Field(0, ge=0)
    degraded_nodes_count: int = Field(0, ge=0)

    # Search metrics
    searches_last_24h: int = Field(0, ge=0)
    avg_search_quality_mrr: float = Field(0.0, ge=0.0, le=1.0)
    avg_search_latency_ms: float = Field(0.0, ge=0.0)

    # Graph metrics
    total_graph_nodes: int = Field(0, ge=0)
    total_graph_edges: int = Field(0, ge=0)
    avg_node_degree: float = Field(0.0, ge=0.0)

    # Trigger metrics
    active_triggers: int = Field(0, ge=0)
    trigger_executions_last_24h: int = Field(0, ge=0)
    trigger_success_rate: float = Field(0.0, ge=0.0, le=1.0)

    # System health
    health_status: HealthStatus = HealthStatus.HEALTHY
    error_rate_last_hour: float = Field(0.0, ge=0.0, le=1.0)

    # Timestamps
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    period: MetricPeriod = MetricPeriod.LAST_24H


class TimeSeriesPoint(BaseModel):
    """Single point in time series data"""

    timestamp: datetime
    value: float
    label: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TimeSeriesMetric(BaseModel):
    """
    Time series metric for trend visualization.

    Used for charts showing metrics over time.
    """

    metric_name: str
    metric_label: str
    unit: Optional[str] = None

    data_points: List[TimeSeriesPoint] = Field(default_factory=list)

    # Statistics
    current_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None

    # Trend
    trend_direction: Optional[str] = Field(
        None, description="'up', 'down', or 'stable'"
    )
    percent_change: Optional[float] = None

    period_start: datetime
    period_end: datetime


class ActivityLog(BaseModel):
    """
    Activity log entry for recent events.

    Displayed in dashboard activity feed.
    """

    log_id: UUID
    event_type: DashboardEventType

    title: str
    description: Optional[str] = None

    # Context
    tenant_id: str
    project_id: str

    # Related entities
    memory_id: Optional[UUID] = None
    reflection_id: Optional[UUID] = None
    semantic_node_id: Optional[UUID] = None
    trigger_id: Optional[UUID] = None

    # Severity for alerts
    severity: Optional[str] = Field(
        None, description="'info', 'warning', 'error', 'critical'"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamp
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Visualization Data Models
# ============================================================================


class ReflectionTreeNode(BaseModel):
    """
    Node in reflection hierarchy tree.

    Used for tree visualization of hierarchical reflections.
    """

    reflection_id: UUID
    content: str
    type: str
    score: float = Field(ge=0.0, le=1.0)
    depth_level: int = Field(ge=0)

    # Parent-child relationships
    parent_id: Optional[UUID] = None
    children: List["ReflectionTreeNode"] = Field(default_factory=list)

    # Metadata for visualization
    cluster_id: Optional[str] = None
    source_memory_count: int = Field(0, ge=0)

    # Display properties
    color: Optional[str] = None
    size: Optional[float] = None

    created_at: datetime


# Allow recursive type
ReflectionTreeNode.model_rebuild()


class SemanticGraphNode(BaseModel):
    """
    Node in semantic knowledge graph.

    Used for graph visualization of semantic relationships.
    """

    node_id: UUID
    label: str
    node_type: str
    canonical_form: str

    # Node properties
    importance_score: float = Field(ge=0.0, le=1.0)
    reinforcement_count: int = Field(0, ge=0)
    is_degraded: bool = False

    # Visualization properties
    x: Optional[float] = None  # Position (if pre-calculated)
    y: Optional[float] = None
    color: Optional[str] = None
    size: float = 10.0


class SemanticGraphEdge(BaseModel):
    """
    Edge in semantic knowledge graph.

    Represents relationship between semantic nodes.
    """

    source_node_id: UUID
    target_node_id: UUID
    relation_type: str

    # Edge properties
    weight: float = Field(1.0, ge=0.0, le=1.0)
    confidence: float = Field(0.8, ge=0.0, le=1.0)

    # Visualization properties
    color: Optional[str] = None
    width: Optional[float] = None
    dashed: bool = False


class SemanticGraph(BaseModel):
    """
    Complete semantic graph for visualization.

    Contains nodes and edges with layout information.
    """

    nodes: List[SemanticGraphNode]
    edges: List[SemanticGraphEdge]

    # Graph statistics
    node_count: int
    edge_count: int
    avg_degree: float

    # Layout algorithm used
    layout_algorithm: Optional[str] = Field(
        None, description="'force', 'hierarchical', 'circular'"
    )

    # Timestamp
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryTimelineEvent(BaseModel):
    """
    Event on memory timeline.

    Represents a memory creation or significant event.
    """

    event_id: UUID
    event_type: str  # 'memory_created', 'reflection_generated', etc.

    title: str
    description: Optional[str] = None

    # Related entities
    memory_id: Optional[UUID] = None
    reflection_id: Optional[UUID] = None

    # Importance for sizing
    importance: float = Field(0.5, ge=0.0, le=1.0)

    # Visualization
    color: Optional[str] = None
    icon: Optional[str] = None

    occurred_at: datetime


class MemoryTimeline(BaseModel):
    """
    Timeline of memory events.

    Displays chronological view of memory creation and processing.
    """

    events: List[MemoryTimelineEvent]

    # Time range
    start_time: datetime
    end_time: datetime

    # Statistics
    total_events: int
    event_density: float = Field(0.0, description="Events per day")


class QualityTrend(BaseModel):
    """
    Quality metrics trend over time.

    Shows how system quality evolves.
    """

    metric_name: str  # 'mrr', 'ndcg', 'precision', etc.

    # Time series
    time_points: List[datetime]
    values: List[float]

    # Trend analysis
    trend_direction: str  # 'improving', 'declining', 'stable'
    percent_change: float

    # Thresholds
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None

    # Current status
    current_value: float
    is_healthy: bool


class SearchHeatmap(BaseModel):
    """
    Heatmap of search activity.

    Shows search patterns by time and query type.
    """

    # Grid data
    time_buckets: List[datetime]  # X-axis
    query_types: List[str]  # Y-axis
    heat_values: List[List[float]]  # 2D array of intensities

    # Statistics
    total_searches: int
    peak_time: datetime
    peak_query_type: str


class ClusterMapNode(BaseModel):
    """
    Node in cluster visualization.

    Represents a cluster of similar memories.
    """

    cluster_id: str
    cluster_label: Optional[str] = None

    # Cluster properties
    member_count: int = Field(ge=0)
    avg_importance: float = Field(ge=0.0, le=1.0)

    # Centroid (for positioning)
    centroid_x: float
    centroid_y: float

    # Visualization
    color: Optional[str] = None
    size: float = 10.0

    # Representative memories
    top_memories: List[UUID] = Field(default_factory=list)


class ClusterMap(BaseModel):
    """
    Map of memory clusters.

    Shows how memories are grouped by similarity.
    """

    clusters: List[ClusterMapNode]

    # Statistics
    total_clusters: int
    total_memories: int
    avg_cluster_size: float

    # Dimensionality reduction method
    reduction_method: str = Field("umap", description="'umap', 'tsne', 'pca'")


# ============================================================================
# WebSocket Message Models
# ============================================================================


class WebSocketMessage(BaseModel):
    """
    Base WebSocket message.

    All WebSocket messages follow this structure.
    """

    message_id: UUID = Field(default_factory=lambda: __import__("uuid").uuid4())
    event_type: DashboardEventType

    # Payload
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Context
    tenant_id: str
    project_id: str

    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MetricsUpdateMessage(WebSocketMessage):
    """
    Metrics update message.

    Pushed when system metrics change significantly.
    """

    event_type: DashboardEventType = DashboardEventType.METRICS_UPDATED
    metrics: SystemMetrics


class HealthChangeMessage(WebSocketMessage):
    """
    Health status change message.

    Pushed when system health status changes.
    """

    event_type: DashboardEventType = DashboardEventType.HEALTH_CHANGED
    old_status: HealthStatus
    new_status: HealthStatus
    reason: str
    details: Optional[Dict[str, Any]] = None


class AlertMessage(WebSocketMessage):
    """
    Alert notification message.

    Pushed for quality degradation, drift detection, etc.
    """

    event_type: DashboardEventType

    alert_id: UUID = Field(default_factory=lambda: __import__("uuid").uuid4())
    severity: str  # 'warning', 'error', 'critical'
    title: str
    description: str

    # Recommended actions
    actions: List[str] = Field(default_factory=list)

    # Related entities
    related_ids: Dict[str, UUID] = Field(default_factory=dict)


# ============================================================================
# System Health Models
# ============================================================================


class ComponentHealth(BaseModel):
    """
    Health status of a system component.
    """

    component_name: str
    status: HealthStatus

    # Metrics
    response_time_ms: Optional[float] = None
    error_rate: Optional[float] = None
    throughput: Optional[float] = None

    # Details
    message: Optional[str] = None
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Sub-components
    sub_components: List["ComponentHealth"] = Field(default_factory=list)


# Allow recursive type
ComponentHealth.model_rebuild()


class SystemHealth(BaseModel):
    """
    Overall system health status.

    Aggregates health from all components.
    """

    overall_status: HealthStatus

    # Component statuses
    components: List[ComponentHealth] = Field(default_factory=list)

    # System metrics
    uptime_seconds: float = Field(0.0, ge=0.0)
    total_requests_last_hour: int = Field(0, ge=0)
    avg_response_time_ms: float = Field(0.0, ge=0.0)
    error_rate: float = Field(0.0, ge=0.0, le=1.0)

    # Resource usage
    cpu_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    memory_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)
    disk_usage_percent: Optional[float] = Field(None, ge=0.0, le=100.0)

    # Database
    db_connection_pool_usage: Optional[float] = Field(None, ge=0.0, le=1.0)
    db_query_avg_ms: Optional[float] = None

    # Active issues
    active_alerts: int = Field(0, ge=0)
    degraded_components: int = Field(0, ge=0)

    # Timestamp
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# ISO/IEC 42001 Compliance Models
# ============================================================================


class ComplianceStatus(str, Enum):
    """ISO 42001 compliance status levels"""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class ComplianceArea(str, Enum):
    """ISO 42001 compliance areas"""

    GOVERNANCE = "governance"
    RISK_MANAGEMENT = "risk_management"
    DATA_MANAGEMENT = "data_management"
    TRANSPARENCY = "transparency"
    HUMAN_OVERSIGHT = "human_oversight"
    SECURITY_PRIVACY = "security_privacy"
    ACCOUNTABILITY = "accountability"
    FAIRNESS = "fairness"
    QUALITY_PERFORMANCE = "quality_performance"


class RiskLevel(str, Enum):
    """Risk severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NEGLIGIBLE = "negligible"


class ISO42001Requirement(BaseModel):
    """
    ISO 42001 requirement definition.

    Maps to specific clauses in ISO/IEC 42001 standard.
    """

    requirement_id: str = Field(..., description="e.g., 'A.5.1', 'A.6.2'")
    requirement_name: str
    requirement_description: str
    compliance_area: ComplianceArea

    # Parent requirement (for hierarchical requirements)
    parent_requirement_id: Optional[str] = None

    # Applicable controls
    control_ids: List[str] = Field(default_factory=list)

    # Evidence required
    evidence_types: List[str] = Field(default_factory=list)


class ISO42001Metric(BaseModel):
    """
    ISO 42001 compliance metric.

    Tracks compliance status for a specific requirement.
    """

    requirement_id: str
    requirement_name: str
    compliance_area: ComplianceArea

    # Current status
    status: ComplianceStatus
    current_value: float = Field(..., ge=0.0, le=100.0, description="Percentage 0-100")
    threshold: float = Field(
        100.0, ge=0.0, le=100.0, description="Required threshold for compliance"
    )

    # Timestamps
    last_check: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_compliant_at: Optional[datetime] = None

    # Evidence and details
    evidence_ids: List[str] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RiskMetric(BaseModel):
    """
    Risk metric from risk register.

    Tracks identified risks and mitigation status.
    """

    risk_id: str
    risk_description: str
    category: str

    # Risk assessment
    probability: float = Field(..., ge=0.0, le=1.0)
    impact: float = Field(..., ge=0.0, le=1.0)
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_level: RiskLevel

    # Current status
    status: str = Field(..., description="e.g., 'open', 'mitigated', 'accepted'")
    mitigation_status: Optional[str] = None

    # Controls
    mitigation_controls: List[str] = Field(default_factory=list)
    effectiveness_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Ownership
    owner: Optional[str] = None
    responsible_party: Optional[str] = None

    # Timestamps
    identified_at: datetime
    last_reviewed_at: datetime
    next_review_due: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditTrailEntry(BaseModel):
    """
    Audit trail entry for compliance tracking.

    Records actions for accountability and transparency.
    """

    entry_id: UUID = Field(default_factory=lambda: __import__("uuid").uuid4())
    tenant_id: str

    # Event classification
    event_type: str = Field(..., description="e.g., 'data_access', 'model_decision'")
    event_category: str = Field(
        ..., description="e.g., 'data_operation', 'ai_decision', 'user_action'"
    )

    # Actor information
    actor_type: str = Field(..., description="'user', 'system', 'api', 'external'")
    actor_id: str
    actor_name: Optional[str] = None

    # Resource information
    resource_type: str = Field(..., description="e.g., 'memory', 'model', 'data'")
    resource_id: str
    resource_name: Optional[str] = None

    # Action details
    action: str = Field(..., description="'create', 'read', 'update', 'delete'")
    action_description: str

    # Result
    result: str = Field(..., description="'success', 'failure', 'partial'")
    result_details: Optional[str] = None

    # Context
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DataRetentionMetric(BaseModel):
    """
    Data retention compliance metric.

    Tracks adherence to data retention policies.
    """

    tenant_id: str
    data_class: str = Field(..., description="e.g., 'episodic_memory', 'audit_logs'")

    # Retention policy
    retention_policy_days: int = Field(..., description="-1 for permanent retention")
    policy_name: str

    # Current status
    total_records: int = Field(0, ge=0)
    expired_records: int = Field(0, ge=0)
    deleted_records_last_30d: int = Field(0, ge=0)

    # Compliance
    compliance_percentage: float = Field(..., ge=0.0, le=100.0)
    overdue_deletions: int = Field(0, ge=0)

    # Last cleanup
    last_cleanup_at: Optional[datetime] = None
    next_cleanup_scheduled: Optional[datetime] = None

    # Timestamp
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceTrustMetric(BaseModel):
    """
    Source trust distribution metric.

    Tracks trust levels of knowledge sources.
    """

    tenant_id: str

    # Trust level distribution
    high_trust_count: int = Field(0, ge=0)
    medium_trust_count: int = Field(0, ge=0)
    low_trust_count: int = Field(0, ge=0)
    unverified_count: int = Field(0, ge=0)

    # Percentages
    high_trust_percentage: float = Field(0.0, ge=0.0, le=100.0)
    verified_percentage: float = Field(0.0, ge=0.0, le=100.0)

    # Verification status
    sources_pending_verification: int = Field(0, ge=0)
    sources_due_for_reverification: int = Field(0, ge=0)

    # Timestamp
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplianceReport(BaseModel):
    """
    ISO 42001 compliance report.

    Comprehensive compliance status across all areas.
    """

    report_id: UUID = Field(default_factory=lambda: __import__("uuid").uuid4())
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Context
    tenant_id: str
    project_id: str
    report_type: str = Field("full", description="'full', 'summary', 'area_specific'")

    # Overall compliance
    overall_compliance_score: float = Field(..., ge=0.0, le=100.0)
    overall_status: ComplianceStatus

    # Area-specific compliance
    governance_metrics: List[ISO42001Metric] = Field(default_factory=list)
    risk_management_metrics: List[ISO42001Metric] = Field(default_factory=list)
    data_management_metrics: List[ISO42001Metric] = Field(default_factory=list)
    transparency_metrics: List[ISO42001Metric] = Field(default_factory=list)
    human_oversight_metrics: List[ISO42001Metric] = Field(default_factory=list)
    security_privacy_metrics: List[ISO42001Metric] = Field(default_factory=list)

    # Risk register
    active_risks: List[RiskMetric] = Field(default_factory=list)
    high_priority_risks: int = Field(0, ge=0)
    mitigated_risks: int = Field(0, ge=0)

    # Data governance
    retention_metrics: List[DataRetentionMetric] = Field(default_factory=list)
    source_trust_metrics: Optional[SourceTrustMetric] = None

    # Audit trail
    audit_trail_completeness: float = Field(
        0.0, ge=0.0, le=100.0, description="Percentage of events with audit trail"
    )
    audit_entries_last_30d: int = Field(0, ge=0)

    # Gaps and recommendations
    critical_gaps: List[str] = Field(default_factory=list)
    non_compliant_requirements: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    action_items: List[Dict[str, Any]] = Field(default_factory=list)

    # Certification status
    certification_ready: bool = False
    next_audit_date: Optional[datetime] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RLSVerificationStatus(BaseModel):
    """
    Row-Level Security verification status.

    Tracks RLS enforcement for tenant isolation.
    """

    tenant_id: str

    # RLS status per table
    tables_with_rls: List[str] = Field(default_factory=list)
    tables_without_rls: List[str] = Field(default_factory=list)

    # RLS policies
    total_policies: int = Field(0, ge=0)
    active_policies: int = Field(0, ge=0)
    disabled_policies: int = Field(0, ge=0)

    # Verification results
    rls_enabled_percentage: float = Field(0.0, ge=0.0, le=100.0)
    all_critical_tables_protected: bool

    # Last verification
    last_verified_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    verification_passed: bool

    # Issues
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# Request/Response Models
# ============================================================================


class GetDashboardMetricsRequest(BaseModel):
    """Request to get dashboard metrics"""

    tenant_id: str
    project_id: str
    period: MetricPeriod = MetricPeriod.LAST_24H
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class GetDashboardMetricsResponse(BaseModel):
    """Response with dashboard metrics"""

    system_metrics: SystemMetrics
    time_series_metrics: List[TimeSeriesMetric] = Field(default_factory=list)
    recent_activity: List[ActivityLog] = Field(default_factory=list)
    message: str = "Dashboard metrics retrieved successfully"


class GetVisualizationRequest(BaseModel):
    """Request to get visualization data"""

    tenant_id: str
    project_id: str
    visualization_type: VisualizationType

    # Type-specific parameters
    root_reflection_id: Optional[UUID] = None  # For reflection tree
    max_depth: int = Field(5, ge=1, le=10)
    limit: int = Field(100, ge=10, le=1000)

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class GetVisualizationResponse(BaseModel):
    """Response with visualization data"""

    visualization_type: VisualizationType

    # Polymorphic data - one of these will be populated
    reflection_tree: Optional[ReflectionTreeNode] = None
    semantic_graph: Optional[SemanticGraph] = None
    memory_timeline: Optional[MemoryTimeline] = None
    quality_trend: Optional[QualityTrend] = None
    search_heatmap: Optional[SearchHeatmap] = None
    cluster_map: Optional[ClusterMap] = None

    # Metadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cache_valid_until: Optional[datetime] = None
    message: str = "Visualization data generated successfully"


class GetSystemHealthRequest(BaseModel):
    """Request to get system health"""

    tenant_id: str
    project_id: str
    include_sub_components: bool = True


class GetSystemHealthResponse(BaseModel):
    """Response with system health"""

    system_health: SystemHealth
    recommendations: List[str] = Field(default_factory=list)
    message: str = "System health retrieved successfully"


class SubscribeWebSocketRequest(BaseModel):
    """Request to subscribe to WebSocket events"""

    tenant_id: str
    project_id: str

    # Event filters
    event_types: List[DashboardEventType] = Field(
        default_factory=lambda: list(DashboardEventType)
    )

    # Update frequency
    metrics_update_interval_seconds: int = Field(5, ge=1, le=60)


class WebSocketSubscription(BaseModel):
    """WebSocket subscription confirmation"""

    subscription_id: UUID = Field(default_factory=lambda: __import__("uuid").uuid4())
    tenant_id: str
    project_id: str

    subscribed_events: List[DashboardEventType]
    update_interval_seconds: int

    connected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None


class GetComplianceReportRequest(BaseModel):
    """Request to get ISO 42001 compliance report"""

    tenant_id: str
    project_id: str
    report_type: str = Field("full", description="'full', 'summary', 'area_specific'")
    compliance_area: Optional[ComplianceArea] = None  # For area_specific reports
    include_audit_trail: bool = True


class GetComplianceReportResponse(BaseModel):
    """Response with ISO 42001 compliance report"""

    compliance_report: ComplianceReport
    rls_status: Optional[RLSVerificationStatus] = None
    message: str = "Compliance report generated successfully"


class GetComplianceMetricsRequest(BaseModel):
    """Request to get compliance metrics by area"""

    tenant_id: str
    project_id: str
    compliance_area: Optional[ComplianceArea] = None
    include_history: bool = False
    period: MetricPeriod = MetricPeriod.LAST_30D


class GetComplianceMetricsResponse(BaseModel):
    """Response with compliance metrics"""

    metrics: List[ISO42001Metric]
    area_scores: Dict[str, float] = Field(
        default_factory=dict, description="Compliance score by area"
    )
    overall_score: float = Field(..., ge=0.0, le=100.0)
    message: str = "Compliance metrics retrieved successfully"


class GetRiskRegisterRequest(BaseModel):
    """Request to get risk register data"""

    tenant_id: str
    project_id: str
    risk_level: Optional[RiskLevel] = None
    status: Optional[str] = None  # 'open', 'mitigated', etc.
    include_closed: bool = False


class GetRiskRegisterResponse(BaseModel):
    """Response with risk register data"""

    risks: List[RiskMetric]
    risk_summary: Dict[str, int] = Field(
        default_factory=dict, description="Count by risk level"
    )
    high_priority_count: int = Field(0, ge=0)
    message: str = "Risk register retrieved successfully"


class GetAuditTrailRequest(BaseModel):
    """Request to get audit trail entries"""

    tenant_id: str
    project_id: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_types: Optional[List[str]] = None
    actor_types: Optional[List[str]] = None
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class GetAuditTrailResponse(BaseModel):
    """Response with audit trail entries"""

    entries: List[AuditTrailEntry]
    total_count: int = Field(0, ge=0)
    completeness_percentage: float = Field(0.0, ge=0.0, le=100.0)
    message: str = "Audit trail retrieved successfully"
