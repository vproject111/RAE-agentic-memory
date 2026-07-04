"""
Enhanced Graph Models - Enterprise Knowledge Graph with Temporal and Weighted Features

This module defines comprehensive Pydantic models for the enhanced knowledge graph including:
- Weighted edges with confidence scores
- Temporal validity (valid_from/valid_to)
- Graph snapshots for versioning
- Traversal metadata and analytics
- Cycle detection results
- Path finding results
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Enums
# ============================================================================


class TraversalAlgorithm(str, Enum):
    """Graph traversal algorithms"""

    BFS = "BFS"  # Breadth-First Search
    DFS = "DFS"  # Depth-First Search
    DIJKSTRA = "DIJKSTRA"  # Dijkstra's shortest path
    A_STAR = "A_STAR"  # A* search algorithm


class EdgeDirection(str, Enum):
    """Edge directionality"""

    FORWARD = "forward"  # Follow edges forward (source → target)
    BACKWARD = "backward"  # Follow edges backward (target → source)
    BOTH = "both"  # Follow edges in both directions


# ============================================================================
# Core Enhanced Models
# ============================================================================


class EnhancedGraphNode(BaseModel):
    """
    Enhanced knowledge graph node with full metadata.

    Extends basic node with connectivity metrics and temporal info.
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Core identification
    node_id: str = Field(..., max_length=255, description="Canonical node identifier")
    label: str = Field(..., max_length=255, description="Human-readable label")

    # Properties
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Flexible node properties"
    )

    # Connectivity metrics (calculated on demand)
    in_degree: Optional[int] = Field(None, description="Number of incoming edges")
    out_degree: Optional[int] = Field(None, description="Number of outgoing edges")
    total_degree: Optional[int] = Field(None, description="Total connectivity")

    # Timestamps
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnhancedGraphEdge(BaseModel):
    """
    Enhanced knowledge graph edge with weights, confidence, and temporal validity.

    Supports:
    - Weighted edges for relationship strength
    - Confidence scores for uncertain relationships
    - Temporal validity windows
    - Bidirectional edges
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Core relationship
    source_node_id: UUID
    target_node_id: UUID
    relation: str = Field(..., max_length=255, description="Relationship type")

    # Weights and confidence
    edge_weight: float = Field(1.0, ge=0.0, le=1.0, description="Edge strength/weight")
    confidence: float = Field(
        0.8, ge=0.0, le=1.0, description="Confidence in relationship"
    )

    # Temporal validity
    valid_from: datetime = Field(..., description="Start of validity period")
    valid_to: Optional[datetime] = Field(
        None, description="End of validity (NULL = ongoing)"
    )
    is_active: bool = Field(True, description="Whether edge is currently active")

    # Properties
    properties: Dict[str, Any] = Field(default_factory=dict)
    bidirectional: bool = Field(False, description="True if relationship is symmetric")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GraphPath(BaseModel):
    """
    A path through the graph from source to target.

    Represents a sequence of nodes connected by edges.
    """

    nodes: List[UUID] = Field(..., description="Ordered list of node IDs in path")
    node_labels: List[str] = Field(
        default_factory=list, description="Labels for readability"
    )
    edges: List[UUID] = Field(
        default_factory=list, description="Ordered list of edge IDs"
    )

    # Path metrics
    length: int = Field(..., description="Number of edges in path")
    total_weight: float = Field(0.0, description="Sum of edge weights")
    avg_confidence: float = Field(
        0.0, ge=0.0, le=1.0, description="Average edge confidence"
    )

    # Metadata
    algorithm_used: Optional[TraversalAlgorithm] = None
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CycleDetectionResult(BaseModel):
    """
    Result of cycle detection algorithm.

    Indicates whether a cycle exists and provides the cycle path.
    """

    has_cycle: bool = Field(..., description="True if cycle detected")
    cycle_path: List[UUID] = Field(
        default_factory=list, description="Node IDs forming the cycle"
    )
    cycle_length: int = Field(0, description="Number of nodes in cycle")

    # Context
    source_node_id: UUID
    target_node_id: UUID
    detection_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class GraphSnapshot(BaseModel):
    """
    Versioned snapshot of graph state.

    Captures complete graph topology at a point in time for versioning,
    rollback, and historical analysis.
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Snapshot metadata
    snapshot_name: str = Field(..., max_length=255)
    description: Optional[str] = None

    # Counts
    node_count: int = Field(0, ge=0)
    edge_count: int = Field(0, ge=0)
    snapshot_size_bytes: Optional[int] = None

    # Snapshot data (full graph serialized)
    nodes_snapshot: List[Dict[str, Any]] = Field(default_factory=list)
    edges_snapshot: List[Dict[str, Any]] = Field(default_factory=list)

    # Statistics at snapshot time
    statistics: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    created_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GraphTraversal(BaseModel):
    """
    Metadata and results from a graph traversal operation.

    Logs traversal operations for analytics and debugging.
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Traversal parameters
    start_node_id: UUID
    algorithm: TraversalAlgorithm
    max_depth: Optional[int] = None

    # Filters applied
    relation_filter: List[str] = Field(default_factory=list)
    temporal_filter: Optional[Tuple[datetime, datetime]] = None
    min_weight: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Results
    nodes_visited: List[UUID] = Field(default_factory=list)
    edges_traversed: List[UUID] = Field(default_factory=list)
    path_found: Optional[GraphPath] = None

    # Performance metrics
    execution_time_ms: Optional[int] = None
    nodes_count: int = Field(0, ge=0)
    edges_count: int = Field(0, ge=0)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NodeDegreeMetrics(BaseModel):
    """
    Connectivity metrics for a graph node.

    Provides in-degree, out-degree, and total connectivity.
    """

    node_id: UUID
    in_degree: int = Field(0, ge=0, description="Number of incoming edges")
    out_degree: int = Field(0, ge=0, description="Number of outgoing edges")
    total_degree: int = Field(0, ge=0, description="Total connectivity")

    # Weighted metrics
    weighted_in_degree: Optional[float] = Field(
        None, description="Sum of incoming edge weights"
    )
    weighted_out_degree: Optional[float] = Field(
        None, description="Sum of outgoing edge weights"
    )


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateGraphNodeRequest(BaseModel):
    """Request to create a graph node"""

    tenant_id: str
    project_id: str
    node_id: str = Field(..., max_length=255)
    label: str = Field(..., max_length=255)
    properties: Dict[str, Any] = Field(default_factory=dict)


class CreateGraphEdgeRequest(BaseModel):
    """Request to create a graph edge"""

    tenant_id: str
    project_id: str
    source_node_id: UUID
    target_node_id: UUID
    relation: str = Field(..., max_length=255)

    # Optional enhanced features
    edge_weight: float = Field(1.0, ge=0.0, le=1.0)
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    bidirectional: bool = Field(False)
    properties: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Temporal validity
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None


class TraverseGraphRequest(BaseModel):
    """Request for temporal graph traversal"""

    tenant_id: str
    project_id: str
    start_node_id: UUID

    # Traversal parameters
    algorithm: TraversalAlgorithm = Field(TraversalAlgorithm.BFS)
    max_depth: int = Field(3, gt=0, le=10)

    # Temporal filter
    at_timestamp: Optional[datetime] = Field(
        None, description="Point in time for temporal query"
    )

    # Edge filters
    relation_filter: Optional[List[str]] = Field(
        None, description="Filter by relation types"
    )
    min_weight: float = Field(0.0, ge=0.0, le=1.0, description="Minimum edge weight")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Minimum confidence")

    # Direction
    direction: EdgeDirection = Field(EdgeDirection.FORWARD)


class TraverseGraphResponse(BaseModel):
    """Response from graph traversal"""

    nodes: List[EnhancedGraphNode] = Field(default_factory=list)
    edges: List[EnhancedGraphEdge] = Field(default_factory=list)

    # Statistics
    total_nodes: int = Field(0)
    total_edges: int = Field(0)
    max_depth_reached: int = Field(0)

    # Performance
    execution_time_ms: Optional[int] = None

    # Metadata
    algorithm_used: TraversalAlgorithm
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class FindPathRequest(BaseModel):
    """Request to find path between two nodes"""

    tenant_id: str
    project_id: str
    start_node_id: UUID
    end_node_id: UUID

    # Path finding parameters
    algorithm: TraversalAlgorithm = Field(TraversalAlgorithm.DIJKSTRA)
    max_depth: int = Field(10, gt=0, le=20)

    # Temporal filter
    at_timestamp: Optional[datetime] = None

    # Filters
    relation_filter: Optional[List[str]] = None
    min_weight: float = Field(0.0, ge=0.0, le=1.0)


class FindPathResponse(BaseModel):
    """Response with found path"""

    path_found: bool
    path: Optional[GraphPath] = None

    # Alternative paths (if requested)
    alternative_paths: List[GraphPath] = Field(default_factory=list)

    # Statistics
    nodes_explored: int = Field(0)
    algorithm_used: TraversalAlgorithm
    execution_time_ms: Optional[int] = None


class DetectCycleRequest(BaseModel):
    """Request to detect cycle"""

    tenant_id: str
    project_id: str
    source_node_id: UUID
    target_node_id: UUID
    max_depth: int = Field(50, gt=0, le=100)


class DetectCycleResponse(BaseModel):
    """Response from cycle detection"""

    result: CycleDetectionResult
    message: str = "Cycle detection completed"


class CreateSnapshotRequest(BaseModel):
    """Request to create graph snapshot"""

    tenant_id: str
    project_id: str
    snapshot_name: str = Field(..., max_length=255)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    created_by: Optional[str] = None


class CreateSnapshotResponse(BaseModel):
    """Response from snapshot creation"""

    snapshot_id: UUID
    node_count: int
    edge_count: int
    snapshot_size_bytes: Optional[int] = None
    message: str = "Snapshot created successfully"


class RestoreSnapshotRequest(BaseModel):
    """Request to restore graph from snapshot"""

    snapshot_id: UUID
    clear_existing: bool = Field(
        False, description="Clear existing graph before restore"
    )


class RestoreSnapshotResponse(BaseModel):
    """Response from snapshot restoration"""

    nodes_restored: int
    edges_restored: int
    message: str = "Snapshot restored successfully"


class GetNodeMetricsRequest(BaseModel):
    """Request to get node metrics"""

    tenant_id: str
    project_id: str
    node_id: UUID


class GetNodeMetricsResponse(BaseModel):
    """Response with node metrics"""

    node_id: UUID
    metrics: NodeDegreeMetrics
    connected_nodes: List[UUID] = Field(default_factory=list)
    message: str = "Node metrics retrieved"


class FindConnectedNodesRequest(BaseModel):
    """Request to find nodes connected to a given node"""

    tenant_id: str
    project_id: str
    node_id: UUID
    max_depth: int = Field(5, gt=0, le=10)


class FindConnectedNodesResponse(BaseModel):
    """Response with connected nodes"""

    node_id: UUID
    connected_nodes: List[Tuple[UUID, int]] = Field(
        default_factory=list, description="List of (node_id, distance) tuples"
    )
    total_connected: int = Field(0)


class GraphStatistics(BaseModel):
    """Aggregated statistics for a knowledge graph"""

    tenant_id: str
    project_id: str

    # Counts
    total_nodes: int = Field(0, ge=0)
    total_edges: int = Field(0, ge=0)
    active_edges: int = Field(0, ge=0)
    unique_relations: int = Field(0, ge=0)
    bidirectional_edges: int = Field(0, ge=0)

    # Averages
    avg_edge_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    avg_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    avg_node_degree: Optional[float] = None

    # Temporal info
    latest_node_created: Optional[datetime] = None
    latest_edge_created: Optional[datetime] = None

    # Snapshots
    snapshot_count: int = Field(0, ge=0)
    latest_snapshot: Optional[datetime] = None


class GetGraphStatisticsRequest(BaseModel):
    """Request to get graph statistics"""

    tenant_id: str
    project_id: str


class GetGraphStatisticsResponse(BaseModel):
    """Response with graph statistics"""

    statistics: GraphStatistics
    message: str = "Graph statistics retrieved"


class UpdateEdgeWeightRequest(BaseModel):
    """Request to update edge weight"""

    edge_id: UUID
    new_weight: float = Field(..., ge=0.0, le=1.0)
    new_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class DeactivateEdgeRequest(BaseModel):
    """Request to deactivate an edge (soft delete)"""

    edge_id: UUID
    reason: Optional[str] = None


class ActivateEdgeRequest(BaseModel):
    """Request to reactivate a deactivated edge"""

    edge_id: UUID


class SetEdgeTemporalValidityRequest(BaseModel):
    """Request to set temporal validity for an edge"""

    edge_id: UUID
    valid_from: datetime
    valid_to: Optional[datetime] = None


# ============================================================================
# Batch Operations
# ============================================================================


class BatchCreateNodesRequest(BaseModel):
    """Request to create multiple nodes"""

    tenant_id: str
    project_id: str
    nodes: List[Dict[str, Any]] = Field(..., min_length=1, max_length=1000)


class BatchCreateEdgesRequest(BaseModel):
    """Request to create multiple edges"""

    tenant_id: str
    project_id: str
    edges: List[CreateGraphEdgeRequest] = Field(..., min_length=1, max_length=1000)


class BatchOperationResponse(BaseModel):
    """Response from batch operations"""

    successful: int = Field(0, ge=0)
    failed: int = Field(0, ge=0)
    errors: List[str] = Field(default_factory=list)
    created_ids: List[UUID] = Field(default_factory=list)
    message: str = "Batch operation completed"
