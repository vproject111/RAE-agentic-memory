"""
Enhanced Graph API Routes - Enterprise Knowledge Graph Endpoints

This module provides FastAPI routes for enhanced graph operations including:
- Temporal graph traversal
- Weighted shortest path finding
- Cycle detection
- Graph snapshots and restoration
- Node metrics and analytics
- Batch operations
"""

from typing import List

import structlog
from fastapi import APIRouter, Depends, HTTPException

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.models.graph_enhanced_models import (  # Request/Response models; Data models
    ActivateEdgeRequest,
    BatchCreateEdgesRequest,
    BatchCreateNodesRequest,
    BatchOperationResponse,
    CreateGraphEdgeRequest,
    CreateGraphNodeRequest,
    CreateSnapshotRequest,
    CreateSnapshotResponse,
    DeactivateEdgeRequest,
    DetectCycleRequest,
    DetectCycleResponse,
    EnhancedGraphEdge,
    EnhancedGraphNode,
    FindConnectedNodesRequest,
    FindConnectedNodesResponse,
    FindPathRequest,
    FindPathResponse,
    GetGraphStatisticsRequest,
    GetGraphStatisticsResponse,
    GetNodeMetricsResponse,
    GraphSnapshot,
    RestoreSnapshotRequest,
    RestoreSnapshotResponse,
    SetEdgeTemporalValidityRequest,
    TraverseGraphRequest,
    TraverseGraphResponse,
    UpdateEdgeWeightRequest,
)
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/graph-management", tags=["Graph Management"])


# ============================================================================
# Node Operations
# ============================================================================


@router.post("/nodes", response_model=EnhancedGraphNode, status_code=201)
async def create_node(
    request: CreateGraphNodeRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Create a knowledge graph node.

    Creates a new node with the specified properties. Node IDs must be unique
    within a tenant/project scope.
    """
    try:
        repo = rae_service.enhanced_graph_repo
        node = await repo.create_node(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            node_id=request.node_id,
            label=request.label,
            properties=request.properties,
        )

        logger.info("node_created_via_api", node_id=request.node_id)
        return node

    except Exception as e:
        logger.error("node_creation_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/nodes/{node_id}/metrics", response_model=GetNodeMetricsResponse)
async def get_node_metrics(
    tenant_id: str,
    project_id: str,
    node_id: str,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Get connectivity metrics for a node.

    Returns in-degree, out-degree, total degree, and weighted metrics.
    """
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        node_uuid = UUID(node_id)
        metrics = await repo.get_node_metrics(tenant_id, project_id, node_uuid)

        return GetNodeMetricsResponse(
            node_id=node_uuid,
            metrics=metrics,
            message="Node metrics retrieved successfully",
        )

    except Exception as e:
        logger.error("get_node_metrics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/nodes/connected", response_model=FindConnectedNodesResponse)
async def find_connected_nodes(
    request: FindConnectedNodesRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Find all nodes connected to a given node.

    Returns nodes within max_depth distance with their distance values.
    """
    try:
        repo = rae_service.enhanced_graph_repo
        connected = await repo.find_connected_nodes(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            node_id=request.node_id,
            max_depth=request.max_depth,
        )

        return FindConnectedNodesResponse(
            node_id=request.node_id,
            connected_nodes=connected,
            total_connected=len(connected),
        )

    except Exception as e:
        logger.error("find_connected_nodes_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Edge Operations
# ============================================================================


@router.post("/edges", response_model=EnhancedGraphEdge, status_code=201)
async def create_edge(
    request: CreateGraphEdgeRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Create a weighted, temporal knowledge graph edge.

    Creates an edge with optional weight, confidence, temporal validity,
    and bidirectionality.
    """
    try:
        repo = rae_service.enhanced_graph_repo

        # Optional: Check for cycles before creating edge
        cycle_result = await repo.detect_cycle(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            source_node_id=request.source_node_id,
            target_node_id=request.target_node_id,
        )

        if cycle_result.has_cycle:
            logger.warning("cycle_detected", cycle_length=cycle_result.cycle_length)
            # Optionally raise error or just log warning
            # raise HTTPException(status_code=400, detail="Edge would create a cycle")

        edge = await repo.create_edge(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            source_node_id=request.source_node_id,
            target_node_id=request.target_node_id,
            relation=request.relation,
            edge_weight=request.edge_weight,
            confidence=request.confidence,
            bidirectional=request.bidirectional,
            properties=request.properties,
            metadata=request.metadata,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
        )

        logger.info("edge_created_via_api", edge_id=edge.id)
        return edge

    except Exception as e:
        logger.error("edge_creation_failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.put("/edges/{edge_id}/weight", response_model=EnhancedGraphEdge)
async def update_edge_weight(
    edge_id: str,
    request: UpdateEdgeWeightRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Update edge weight and optionally confidence"""
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        edge = await repo.update_edge_weight(
            edge_id=UUID(edge_id),
            new_weight=request.new_weight,
            new_confidence=request.new_confidence,
        )

        return edge

    except Exception as e:
        logger.error("update_edge_weight_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/edges/{edge_id}/deactivate", response_model=EnhancedGraphEdge)
async def deactivate_edge(
    edge_id: str,
    request: DeactivateEdgeRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Deactivate an edge (soft delete)"""
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        edge = await repo.deactivate_edge(edge_id=UUID(edge_id), reason=request.reason)

        return edge

    except Exception as e:
        logger.error("deactivate_edge_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/edges/{edge_id}/activate", response_model=EnhancedGraphEdge)
async def activate_edge(
    edge_id: str,
    request: ActivateEdgeRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Reactivate a deactivated edge"""
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        edge = await repo.activate_edge(edge_id=UUID(edge_id))

        return edge

    except Exception as e:
        logger.error("activate_edge_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/edges/{edge_id}/temporal", response_model=EnhancedGraphEdge)
async def set_edge_temporal_validity(
    edge_id: str,
    request: SetEdgeTemporalValidityRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Set temporal validity window for an edge"""
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        edge = await repo.set_edge_temporal_validity(
            edge_id=UUID(edge_id),
            valid_from=request.valid_from,
            valid_to=request.valid_to,
        )

        return edge

    except Exception as e:
        logger.error("set_temporal_validity_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Graph Traversal
# ============================================================================


@router.post("/traverse", response_model=TraverseGraphResponse)
async def traverse_graph(
    request: TraverseGraphRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Perform temporal graph traversal with BFS or DFS.

    Supports:
    - Temporal filtering (at_timestamp)
    - Edge weight filtering (min_weight)
    - Relation type filtering
    - Confidence filtering
    """
    try:
        import time

        start_time = time.time()

        repo = rae_service.enhanced_graph_repo

        nodes, edges = await repo.traverse_temporal(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            start_node_id=request.start_node_id,
            algorithm=request.algorithm,
            max_depth=request.max_depth,
            at_timestamp=request.at_timestamp,
            relation_filter=request.relation_filter,
            min_weight=request.min_weight,
            min_confidence=request.min_confidence,
        )

        execution_time = int((time.time() - start_time) * 1000)

        # Calculate max depth reached
        max_depth_reached = 0
        if nodes:
            # Would need to track depth during traversal for accurate result
            max_depth_reached = min(request.max_depth, len(nodes))

        logger.info(
            "graph_traversal_complete",
            algorithm=request.algorithm.value,
            nodes=len(nodes),
            edges=len(edges),
            time_ms=execution_time,
        )

        return TraverseGraphResponse(
            nodes=nodes,
            edges=edges,
            total_nodes=len(nodes),
            total_edges=len(edges),
            max_depth_reached=max_depth_reached,
            execution_time_ms=execution_time,
            algorithm_used=request.algorithm,
            filters_applied={
                "at_timestamp": (
                    str(request.at_timestamp) if request.at_timestamp else None
                ),
                "relation_filter": request.relation_filter,
                "min_weight": request.min_weight,
                "min_confidence": request.min_confidence,
            },
        )

    except Exception as e:
        logger.error("graph_traversal_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Path Finding
# ============================================================================


@router.post("/path/shortest", response_model=FindPathResponse)
async def find_shortest_path(
    request: FindPathRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Find weighted shortest path between two nodes using Dijkstra.

    Returns the path with lowest total weight considering edge weights.
    """
    try:
        import time

        start_time = time.time()

        repo = rae_service.enhanced_graph_repo

        path = await repo.find_shortest_path(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            start_node_id=request.start_node_id,
            end_node_id=request.end_node_id,
            at_timestamp=request.at_timestamp,
            max_depth=request.max_depth,
        )

        execution_time = int((time.time() - start_time) * 1000)

        if not path:
            return FindPathResponse(
                path_found=False,
                algorithm_used=request.algorithm,
                execution_time_ms=execution_time,
            )

        logger.info(
            "shortest_path_found",
            length=path.length,
            weight=path.total_weight,
            time_ms=execution_time,
        )

        return FindPathResponse(
            path_found=True,
            path=path,
            algorithm_used=request.algorithm,
            execution_time_ms=execution_time,
        )

    except Exception as e:
        logger.error("find_shortest_path_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Cycle Detection
# ============================================================================


@router.post("/cycles/detect", response_model=DetectCycleResponse)
async def detect_cycle(
    request: DetectCycleRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Detect if adding an edge would create a cycle.

    Uses DFS to check if there's a path from target back to source.
    """
    try:
        repo = rae_service.enhanced_graph_repo

        result = await repo.detect_cycle(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            source_node_id=request.source_node_id,
            target_node_id=request.target_node_id,
            max_depth=request.max_depth,
        )

        message = f"Cycle {'detected' if result.has_cycle else 'not detected'}"
        if result.has_cycle:
            message += f" (length: {result.cycle_length})"

        logger.info(
            "cycle_detection_complete",
            has_cycle=result.has_cycle,
            cycle_length=result.cycle_length,
        )

        return DetectCycleResponse(result=result, message=message)

    except Exception as e:
        logger.error("cycle_detection_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Graph Snapshots
# ============================================================================


@router.post("/snapshots", response_model=CreateSnapshotResponse, status_code=201)
async def create_snapshot(
    request: CreateSnapshotRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Create a versioned snapshot of the graph.

    Captures complete graph topology at current point in time for
    versioning, rollback, and historical analysis.
    """
    try:
        repo = rae_service.enhanced_graph_repo

        snapshot_id = await repo.create_snapshot(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            snapshot_name=request.snapshot_name,
            description=request.description,
            created_by=request.created_by,
        )

        # Get snapshot details
        snapshot = await repo.get_snapshot(snapshot_id)

        logger.info(
            "snapshot_created",
            snapshot_id=snapshot_id,
            nodes=snapshot.node_count if snapshot else 0,
            edges=snapshot.edge_count if snapshot else 0,
        )

        return CreateSnapshotResponse(
            snapshot_id=snapshot_id,
            node_count=snapshot.node_count if snapshot else 0,
            edge_count=snapshot.edge_count if snapshot else 0,
            snapshot_size_bytes=snapshot.snapshot_size_bytes if snapshot else None,
            message="Snapshot created successfully",
        )

    except Exception as e:
        logger.error("snapshot_creation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/snapshots/{snapshot_id}", response_model=GraphSnapshot)
async def get_snapshot(
    snapshot_id: str,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Get snapshot details by ID"""
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        snapshot = await repo.get_snapshot(UUID(snapshot_id))

        if not snapshot:
            raise HTTPException(status_code=404, detail="Snapshot not found")

        return snapshot

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_snapshot_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/snapshots", response_model=List[GraphSnapshot])
async def list_snapshots(
    tenant_id: str,
    project_id: str,
    limit: int = 10,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """List recent snapshots"""
    try:
        repo = rae_service.enhanced_graph_repo

        snapshots = await repo.list_snapshots(
            tenant_id=tenant_id, project_id=project_id, limit=limit
        )

        return snapshots

    except Exception as e:
        logger.error("list_snapshots_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/snapshots/{snapshot_id}/restore", response_model=RestoreSnapshotResponse)
async def restore_snapshot(
    snapshot_id: str,
    request: RestoreSnapshotRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Restore graph from snapshot.

    Optionally clears existing graph before restoring.
    """
    try:
        from uuid import UUID

        repo = rae_service.enhanced_graph_repo

        nodes_restored, edges_restored = await repo.restore_snapshot(
            snapshot_id=UUID(snapshot_id), clear_existing=request.clear_existing
        )

        logger.info(
            "snapshot_restored",
            snapshot_id=snapshot_id,
            nodes=nodes_restored,
            edges=edges_restored,
        )

        return RestoreSnapshotResponse(
            nodes_restored=nodes_restored,
            edges_restored=edges_restored,
            message=f"Snapshot restored successfully ({nodes_restored} nodes, {edges_restored} edges)",
        )

    except Exception as e:
        logger.error("snapshot_restoration_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Analytics and Statistics
# ============================================================================


@router.post("/statistics", response_model=GetGraphStatisticsResponse)
async def get_graph_statistics(
    request: GetGraphStatisticsRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Get comprehensive graph statistics.

    Returns node count, edge count, connectivity metrics, and snapshot info.
    """
    try:
        repo = rae_service.enhanced_graph_repo

        statistics = await repo.get_graph_statistics(
            tenant_id=request.tenant_id, project_id=request.project_id
        )

        logger.info(
            "statistics_retrieved",
            nodes=statistics.total_nodes,
            edges=statistics.total_edges,
        )

        return GetGraphStatisticsResponse(
            statistics=statistics, message="Graph statistics retrieved successfully"
        )

    except Exception as e:
        logger.error("get_statistics_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Batch Operations
# ============================================================================


@router.post("/nodes/batch", response_model=BatchOperationResponse, status_code=201)
async def batch_create_nodes(
    request: BatchCreateNodesRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Create multiple nodes in batch.

    More efficient than individual create calls for bulk operations.
    """
    try:
        repo = rae_service.enhanced_graph_repo

        successful, errors = await repo.batch_create_nodes(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            nodes=request.nodes,
        )

        logger.info(
            "batch_create_nodes_complete", successful=successful, failed=len(errors)
        )

        return BatchOperationResponse(
            successful=successful,
            failed=len(errors),
            errors=errors,
            message=f"Batch operation completed: {successful} successful, {len(errors)} failed",
        )

    except Exception as e:
        logger.error("batch_create_nodes_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/edges/batch", response_model=BatchOperationResponse, status_code=201)
async def batch_create_edges(
    request: BatchCreateEdgesRequest,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Create multiple edges in batch.

    More efficient than individual create calls for bulk operations.
    """
    try:
        repo = rae_service.enhanced_graph_repo

        successful = 0
        failed = 0
        errors = []
        created_ids = []

        for edge_req in request.edges:
            try:
                edge = await repo.create_edge(
                    tenant_id=request.tenant_id,
                    project_id=request.project_id,
                    source_node_id=edge_req.source_node_id,
                    target_node_id=edge_req.target_node_id,
                    relation=edge_req.relation,
                    edge_weight=edge_req.edge_weight,
                    confidence=edge_req.confidence,
                    bidirectional=edge_req.bidirectional,
                    properties=edge_req.properties,
                    metadata=edge_req.metadata,
                    valid_from=edge_req.valid_from,
                    valid_to=edge_req.valid_to,
                )
                successful += 1
                created_ids.append(edge.id)
            except Exception as e:
                failed += 1
                errors.append(str(e))

        logger.info("batch_create_edges_complete", successful=successful, failed=failed)

        return BatchOperationResponse(
            successful=successful,
            failed=failed,
            errors=errors,
            created_ids=created_ids,
            message=f"Batch operation completed: {successful} successful, {failed} failed",
        )

    except Exception as e:
        logger.error("batch_create_edges_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Health Check
# ============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for graph service"""
    return {
        "status": "healthy",
        "service": "enhanced_graph_api",
        "version": "2.0",
        "features": [
            "temporal_traversal",
            "weighted_paths",
            "cycle_detection",
            "graph_snapshots",
            "node_metrics",
            "batch_operations",
        ],
    }
