"""
Enhanced Graph Repository - Enterprise Knowledge Graph Data Access Layer

This repository provides comprehensive data access operations for the enhanced
knowledge graph with temporal, weighted, and versioned features including:
- Weighted edges with confidence scores
- Temporal graph queries (valid_from/valid_to)
- Cycle detection with DFS
- Graph snapshots and restoration
- Advanced traversal algorithms (BFS, DFS, Dijkstra)
- Node metrics and analytics
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID

import asyncpg
import structlog

from apps.memory_api.models.graph_enhanced_models import (
    CycleDetectionResult,
    EnhancedGraphEdge,
    EnhancedGraphNode,
    GraphPath,
    GraphSnapshot,
    GraphStatistics,
    NodeDegreeMetrics,
    TraversalAlgorithm,
)
from rae_adapters.postgres_db import PostgresDatabaseProvider
from rae_core.interfaces.database import IDatabaseProvider

logger = structlog.get_logger(__name__)


# ============================================================================
# Enhanced Graph Repository
# ============================================================================


class EnhancedGraphRepository:
    """
    Enterprise-grade repository for knowledge graph operations.

    Features:
    - Temporal graph queries with time-based filtering
    - Weighted shortest path algorithms
    - Cycle detection with path tracking
    - Graph snapshots for versioning
    - Node metrics and analytics
    - Batch operations for performance
    """

    def __init__(self, pool: asyncpg.Pool | IDatabaseProvider):
        """
        Initialize enhanced graph repository.

        Args:
            pool: AsyncPG connection pool or IDatabaseProvider
        """
        self.db: IDatabaseProvider
        if isinstance(pool, (asyncpg.Pool, asyncpg.Connection)):
            self.db = PostgresDatabaseProvider(pool)
        else:
            self.db = pool
        # Maintain backward compatibility for properties if needed, but methods should use self.db

    # ========================================================================
    # Node Operations
    # ========================================================================

    async def create_node(
        self,
        tenant_id: str,
        project_id: str,
        node_id: str,
        label: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> EnhancedGraphNode:
        """
        Create a knowledge graph node.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            node_id: Unique node identifier
            label: Human-readable label
            properties: Node properties

        Returns:
            Created EnhancedGraphNode

        Raises:
            Exception if node with same node_id already exists
        """
        properties = properties or {}

        record = await self.db.fetchrow(
            """
            INSERT INTO knowledge_graph_nodes (
                tenant_id, project_id, node_id, label, properties
            ) VALUES ($1, $2, $3, $4, $5)
            RETURNING *
            """,
            tenant_id,
            project_id,
            node_id,
            label,
            properties,
        )

        logger.info("graph_node_created", node_id=node_id, label=label)

        return self._record_to_node(record)

    async def get_node_by_id(
        self, tenant_id: str, project_id: str, node_id: UUID
    ) -> Optional[EnhancedGraphNode]:
        """Get node by UUID"""
        record = await self.db.fetchrow(
            """
            SELECT * FROM knowledge_graph_nodes
            WHERE tenant_id = $1 AND project_id = $2 AND id = $3
            """,
            tenant_id,
            project_id,
            node_id,
        )

        if not record:
            return None

        return self._record_to_node(record)

    async def get_node_by_node_id(
        self, tenant_id: str, project_id: str, node_id: str
    ) -> Optional[EnhancedGraphNode]:
        """Get node by string node_id"""
        record = await self.db.fetchrow(
            """
            SELECT * FROM knowledge_graph_nodes
            WHERE tenant_id = $1 AND project_id = $2 AND node_id = $3
            """,
            tenant_id,
            project_id,
            node_id,
        )

        if not record:
            return None

        return self._record_to_node(record)

    async def get_node_metrics(
        self, tenant_id: str, project_id: str, node_id: UUID
    ) -> NodeDegreeMetrics:
        """
        Calculate connectivity metrics for a node.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            node_id: Node UUID

        Returns:
            NodeDegreeMetrics with in/out/total degree
        """
        record = await self.db.fetchrow(
            "SELECT * FROM calculate_node_degree($1, $2, $3)",
            tenant_id,
            project_id,
            node_id,
        )

        # Calculate weighted degrees
        weighted_record = await self.db.fetchrow(
            """
            SELECT
                COALESCE(SUM(edge_weight) FILTER (WHERE target_node_id = $3), 0) as weighted_in,
                COALESCE(SUM(edge_weight) FILTER (WHERE source_node_id = $3), 0) as weighted_out
            FROM knowledge_graph_edges
            WHERE tenant_id = $1 AND project_id = $2 AND is_active = TRUE
                AND (source_node_id = $3 OR target_node_id = $3)
            """,
            tenant_id,
            project_id,
            node_id,
        )

        if not record or not weighted_record:
            raise RuntimeError(f"Failed to retrieve metrics for node {node_id}")

        return NodeDegreeMetrics(
            node_id=node_id,
            in_degree=record["in_degree"],
            out_degree=record["out_degree"],
            total_degree=record["total_degree"],
            weighted_in_degree=float(weighted_record["weighted_in"]),
            weighted_out_degree=float(weighted_record["weighted_out"]),
        )

    async def find_connected_nodes(
        self, tenant_id: str, project_id: str, node_id: UUID, max_depth: int = 5
    ) -> List[Tuple[UUID, int]]:
        """
        Find all nodes connected to given node.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            node_id: Starting node UUID
            max_depth: Maximum distance

        Returns:
            List of (node_id, distance) tuples
        """
        records = await self.db.fetch(
            "SELECT * FROM find_connected_nodes($1, $2, $3, $4)",
            tenant_id,
            project_id,
            node_id,
            max_depth,
        )

        return [(record["connected_node_id"], record["distance"]) for record in records]

    # ========================================================================
    # Edge Operations
    # ========================================================================

    async def create_edge(
        self,
        tenant_id: str,
        project_id: str,
        source_node_id: UUID,
        target_node_id: UUID,
        relation: str,
        edge_weight: float = 1.0,
        confidence: float = 0.8,
        bidirectional: bool = False,
        properties: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
    ) -> EnhancedGraphEdge:
        """
        Create a weighted, temporal knowledge graph edge.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            source_node_id: Source node UUID
            target_node_id: Target node UUID
            relation: Relationship type
            edge_weight: Edge strength (0-1)
            confidence: Confidence in relationship (0-1)
            bidirectional: Whether edge is symmetric
            properties: Edge properties
            metadata: Additional metadata
            valid_from: Start of temporal validity
            valid_to: End of temporal validity

        Returns:
            Created EnhancedGraphEdge

        Raises:
            Exception if edge would create a cycle (if validation enabled)
        """
        properties = properties or {}
        metadata = metadata or {}
        valid_from = valid_from or datetime.now(timezone.utc)

        record = await self.db.fetchrow(
            """
            INSERT INTO knowledge_graph_edges (
                tenant_id, project_id,
                source_node_id, target_node_id, relation,
                edge_weight, confidence, bidirectional,
                properties, metadata,
                valid_from, valid_to, is_active
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, TRUE)
            RETURNING *
            """,
            tenant_id,
            project_id,
            source_node_id,
            target_node_id,
            relation,
            edge_weight,
            confidence,
            bidirectional,
            properties,
            metadata,
            valid_from,
            valid_to,
        )

        logger.info(
            "graph_edge_created",
            source=source_node_id,
            target=target_node_id,
            relation=relation,
            weight=edge_weight,
        )

        return self._record_to_edge(record)

    async def update_edge_weight(
        self, edge_id: UUID, new_weight: float, new_confidence: Optional[float] = None
    ) -> EnhancedGraphEdge:
        """Update edge weight and confidence"""
        if new_confidence is not None:
            record = await self.db.fetchrow(
                """
                UPDATE knowledge_graph_edges
                SET edge_weight = $2, confidence = $3
                WHERE id = $1
                RETURNING *
                """,
                edge_id,
                new_weight,
                new_confidence,
            )
        else:
            record = await self.db.fetchrow(
                """
                UPDATE knowledge_graph_edges
                SET edge_weight = $2
                WHERE id = $1
                RETURNING *
                """,
                edge_id,
                new_weight,
            )

        logger.info("edge_weight_updated", edge_id=edge_id, new_weight=new_weight)

        return self._record_to_edge(record)

    async def deactivate_edge(
        self, edge_id: UUID, reason: Optional[str] = None
    ) -> EnhancedGraphEdge:
        """Soft delete edge by setting is_active to False"""
        metadata_update = {"deactivation_reason": reason} if reason else {}

        record = await self.db.fetchrow(
            """
            UPDATE knowledge_graph_edges
            SET is_active = FALSE, metadata = metadata || $2::jsonb
            WHERE id = $1
            RETURNING *
            """,
            edge_id,
            metadata_update,
        )

        logger.info("edge_deactivated", edge_id=edge_id, reason=reason)

        return self._record_to_edge(record)

    async def activate_edge(self, edge_id: UUID) -> EnhancedGraphEdge:
        """Reactivate a deactivated edge"""
        record = await self.db.fetchrow(
            """
            UPDATE knowledge_graph_edges
            SET is_active = TRUE
            WHERE id = $1
            RETURNING *
            """,
            edge_id,
        )

        logger.info("edge_activated", edge_id=edge_id)

        return self._record_to_edge(record)

    async def set_edge_temporal_validity(
        self, edge_id: UUID, valid_from: datetime, valid_to: Optional[datetime] = None
    ) -> EnhancedGraphEdge:
        """Set temporal validity window for edge"""
        record = await self.db.fetchrow(
            """
            UPDATE knowledge_graph_edges
            SET valid_from = $2, valid_to = $3
            WHERE id = $1
            RETURNING *
            """,
            edge_id,
            valid_from,
            valid_to,
        )

        logger.info("edge_temporal_validity_set", edge_id=edge_id)

        return self._record_to_edge(record)

    # ========================================================================
    # Cycle Detection
    # ========================================================================

    async def detect_cycle(
        self,
        tenant_id: str,
        project_id: str,
        source_node_id: UUID,
        target_node_id: UUID,
        max_depth: int = 50,
    ) -> CycleDetectionResult:
        """
        Detect if adding an edge would create a cycle using DFS.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            source_node_id: Proposed edge source
            target_node_id: Proposed edge target
            max_depth: Maximum search depth

        Returns:
            CycleDetectionResult with cycle information
        """
        record = await self.db.fetchrow(
            "SELECT * FROM detect_graph_cycle_dfs($1, $2, $3, $4, $5)",
            tenant_id,
            project_id,
            source_node_id,
            target_node_id,
            max_depth,
        )

        if not record:
            return CycleDetectionResult(
                has_cycle=False,
                cycle_path=[],
                cycle_length=0,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
            )

        result = CycleDetectionResult(
            has_cycle=record["has_cycle"],
            cycle_path=record["cycle_path"] or [],
            cycle_length=record["cycle_length"] or 0,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
        )

        logger.info(
            "cycle_detection_complete",
            has_cycle=result.has_cycle,
            cycle_length=result.cycle_length,
        )

        return result

    # ========================================================================
    # Temporal Graph Traversal
    # ========================================================================

    async def traverse_temporal(
        self,
        tenant_id: str,
        project_id: str,
        start_node_id: UUID,
        algorithm: TraversalAlgorithm = TraversalAlgorithm.BFS,
        max_depth: int = 3,
        at_timestamp: Optional[datetime] = None,
        relation_filter: Optional[List[str]] = None,
        min_weight: float = 0.0,
        min_confidence: float = 0.0,
    ) -> Tuple[List[EnhancedGraphNode], List[EnhancedGraphEdge]]:
        """
        Perform temporal graph traversal with time-based filtering.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            start_node_id: Starting node UUID
            algorithm: BFS or DFS
            max_depth: Maximum traversal depth
            at_timestamp: Point in time for temporal query
            relation_filter: Filter by relation types
            min_weight: Minimum edge weight
            min_confidence: Minimum edge confidence

        Returns:
            Tuple of (nodes, edges) discovered in traversal
        """
        at_timestamp = at_timestamp or datetime.now(timezone.utc)

        # Call temporal traversal function
        records = await self.db.fetch(
            "SELECT * FROM traverse_graph_temporal($1, $2, $3, $4, $5, $6, $7, $8)",
            tenant_id,
            project_id,
            start_node_id,
            at_timestamp,
            max_depth,
            relation_filter,
            min_weight,
            algorithm.value,
        )

        # Extract unique node IDs from traversal
        node_ids = list(set(record["node_id"] for record in records))

        # Fetch full node data
        nodes = []
        if node_ids:
            node_records = await self.db.fetch(
                """
                SELECT * FROM knowledge_graph_nodes
                WHERE tenant_id = $1 AND project_id = $2 AND id = ANY($3)
                """,
                tenant_id,
                project_id,
                node_ids,
            )
            nodes = [self._record_to_node(r) for r in node_records]

        # Fetch edges between discovered nodes
        edges = []
        if len(node_ids) > 1:
            edge_records = await self.db.fetch(
                """
                SELECT * FROM knowledge_graph_edges
                WHERE tenant_id = $1 AND project_id = $2
                    AND source_node_id = ANY($3)
                    AND target_node_id = ANY($3)
                    AND is_active = TRUE
                    AND valid_from <= $4
                    AND (valid_to IS NULL OR valid_to >= $4)
                    AND edge_weight >= $5
                    AND confidence >= $6
                """,
                tenant_id,
                project_id,
                node_ids,
                at_timestamp,
                min_weight,
                min_confidence,
            )
            edges = [self._record_to_edge(r) for r in edge_records]

        logger.info(
            "temporal_traversal_complete",
            algorithm=algorithm.value,
            nodes_found=len(nodes),
            edges_found=len(edges),
        )

        return nodes, edges

    # ========================================================================
    # Path Finding
    # ========================================================================

    async def find_shortest_path(
        self,
        tenant_id: str,
        project_id: str,
        start_node_id: UUID,
        end_node_id: UUID,
        at_timestamp: Optional[datetime] = None,
        max_depth: int = 10,
    ) -> Optional[GraphPath]:
        """
        Find weighted shortest path using Dijkstra algorithm.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            start_node_id: Start node UUID
            end_node_id: End node UUID
            at_timestamp: Point in time for temporal query
            max_depth: Maximum path length

        Returns:
            GraphPath if found, None otherwise
        """
        at_timestamp = at_timestamp or datetime.now(timezone.utc)

        record = await self.db.fetchrow(
            "SELECT * FROM find_shortest_path_weighted($1, $2, $3, $4, $5, $6)",
            tenant_id,
            project_id,
            start_node_id,
            end_node_id,
            at_timestamp,
            max_depth,
        )

        if not record or not record["path_nodes"]:
            logger.info("no_path_found", start=start_node_id, end=end_node_id)
            return None

        path = GraphPath(
            nodes=record["path_nodes"],
            node_labels=record["path_labels"],
            edges=[],  # Could fetch edge IDs if needed
            length=record["edge_count"],
            total_weight=float(record["total_distance"]),
            avg_confidence=0.0,  # Could calculate if needed
            algorithm_used=TraversalAlgorithm.DIJKSTRA,
        )

        logger.info("shortest_path_found", length=path.length, weight=path.total_weight)

        return path

    # ========================================================================
    # Graph Snapshots
    # ========================================================================

    async def create_snapshot(
        self,
        tenant_id: str,
        project_id: str,
        snapshot_name: str,
        description: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> UUID:
        """
        Create a snapshot of current graph state.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            snapshot_name: Name for snapshot
            description: Optional description
            created_by: User who created snapshot

        Returns:
            Snapshot UUID
        """
        snapshot_id = await self.db.fetchval(
            "SELECT create_graph_snapshot($1, $2, $3, $4, $5)",
            tenant_id,
            project_id,
            snapshot_name,
            description,
            created_by,
        )

        logger.info(
            "snapshot_created", snapshot_id=snapshot_id, snapshot_name=snapshot_name
        )

        return cast(UUID, snapshot_id)

    async def get_snapshot(self, snapshot_id: UUID) -> Optional[GraphSnapshot]:
        """Get snapshot by ID"""
        record = await self.db.fetchrow(
            "SELECT * FROM knowledge_graph_snapshots WHERE id = $1", snapshot_id
        )

        if not record:
            return None

        return self._record_to_snapshot(record)

    async def list_snapshots(
        self, tenant_id: str, project_id: str, limit: int = 10
    ) -> List[GraphSnapshot]:
        """List recent snapshots"""
        records = await self.db.fetch(
            """
            SELECT * FROM knowledge_graph_snapshots
            WHERE tenant_id = $1 AND project_id = $2
            ORDER BY created_at DESC
            LIMIT $3
            """,
            tenant_id,
            project_id,
            limit,
        )

        return [self._record_to_snapshot(r) for r in records]

    async def restore_snapshot(
        self, snapshot_id: UUID, clear_existing: bool = False
    ) -> Tuple[int, int]:
        """
        Restore graph from snapshot.

        Args:
            snapshot_id: Snapshot UUID
            clear_existing: Whether to clear existing graph first

        Returns:
            Tuple of (nodes_restored, edges_restored)
        """
        record = await self.db.fetchrow(
            "SELECT * FROM restore_graph_snapshot($1, $2)", snapshot_id, clear_existing
        )

        if not record:
            return 0, 0

        nodes_restored = record["nodes_restored"]
        edges_restored = record["edges_restored"]

        logger.info(
            "snapshot_restored",
            snapshot_id=snapshot_id,
            nodes=nodes_restored,
            edges=edges_restored,
        )

        return nodes_restored, edges_restored

    # ========================================================================
    # Analytics and Statistics
    # ========================================================================

    async def get_graph_statistics(
        self, tenant_id: str, project_id: str
    ) -> GraphStatistics:
        """
        Get aggregated graph statistics.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier

        Returns:
            GraphStatistics with comprehensive metrics
        """
        record = await self.db.fetchrow(
            """
            SELECT * FROM knowledge_graph_statistics
            WHERE tenant_id = $1 AND project_id = $2
            """,
            tenant_id,
            project_id,
        )

        if not record:
            # Return empty statistics if no graph exists
            return GraphStatistics(tenant_id=tenant_id, project_id=project_id)

        # Get snapshot count
        snapshot_count = await self.db.fetchval(
            """
            SELECT COUNT(*) FROM knowledge_graph_snapshots
            WHERE tenant_id = $1 AND project_id = $2
            """,
            tenant_id,
            project_id,
        )

        latest_snapshot = await self.db.fetchval(
            """
            SELECT MAX(created_at) FROM knowledge_graph_snapshots
            WHERE tenant_id = $1 AND project_id = $2
            """,
            tenant_id,
            project_id,
        )

        return GraphStatistics(
            tenant_id=tenant_id,
            project_id=project_id,
            total_nodes=record["total_nodes"],
            total_edges=record["total_edges"],
            active_edges=record["active_edges"],
            unique_relations=record["unique_relations"],
            bidirectional_edges=record["bidirectional_edges"],
            avg_edge_weight=(
                float(record["avg_edge_weight"]) if record["avg_edge_weight"] else None
            ),
            avg_confidence=(
                float(record["avg_confidence"]) if record["avg_confidence"] else None
            ),
            latest_node_created=record["latest_node_created"],
            latest_edge_created=record["latest_edge_created"],
            snapshot_count=snapshot_count or 0,
            latest_snapshot=latest_snapshot,
        )

    # ========================================================================
    # Batch Operations
    # ========================================================================

    async def batch_create_nodes(
        self, tenant_id: str, project_id: str, nodes: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """
        Create multiple nodes in batch.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            nodes: List of node dictionaries

        Returns:
            Tuple of (successful_count, error_messages)
        """
        successful = 0
        errors = []

        async with self.db.acquire() as conn:
            async with conn.transaction():
                for node_data in nodes:
                    try:
                        await self.create_node(
                            tenant_id=tenant_id,
                            project_id=project_id,
                            node_id=node_data["node_id"],
                            label=node_data["label"],
                            properties=node_data.get("properties", {}),
                        )
                        successful += 1
                    except Exception as e:
                        errors.append(f"Node {node_data.get('node_id')}: {str(e)}")

        logger.info(
            "batch_create_nodes_complete", successful=successful, failed=len(errors)
        )

        return successful, errors

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _record_to_node(self, record) -> EnhancedGraphNode:
        """Convert database record to EnhancedGraphNode"""
        return EnhancedGraphNode(
            id=record["id"],
            tenant_id=record["tenant_id"],
            project_id=record["project_id"],
            node_id=record["node_id"],
            label=record["label"],
            properties=record.get("properties", {}),
            created_at=record["created_at"],
        )

    def _record_to_edge(self, record) -> EnhancedGraphEdge:
        """Convert database record to EnhancedGraphEdge"""
        return EnhancedGraphEdge(
            id=record["id"],
            tenant_id=record["tenant_id"],
            project_id=record["project_id"],
            source_node_id=record["source_node_id"],
            target_node_id=record["target_node_id"],
            relation=record["relation"],
            edge_weight=float(record.get("edge_weight", 1.0)),
            confidence=float(record.get("confidence", 0.8)),
            valid_from=record.get("valid_from"),
            valid_to=record.get("valid_to"),
            is_active=record.get("is_active", True),
            properties=record.get("properties", {}),
            bidirectional=record.get("bidirectional", False),
            metadata=record.get("metadata", {}),
            created_at=record["created_at"],
            updated_at=record.get("updated_at", record["created_at"]),
        )

    def _record_to_snapshot(self, record) -> GraphSnapshot:
        """Convert database record to GraphSnapshot"""
        return GraphSnapshot(
            id=record["id"],
            tenant_id=record["tenant_id"],
            project_id=record["project_id"],
            snapshot_name=record["snapshot_name"],
            description=record.get("description"),
            node_count=record["node_count"],
            edge_count=record["edge_count"],
            snapshot_size_bytes=record.get("snapshot_size_bytes"),
            nodes_snapshot=record.get("nodes_snapshot", []),
            edges_snapshot=record.get("edges_snapshot", []),
            statistics=record.get("statistics", {}),
            tags=record.get("tags", []),
            metadata=record.get("metadata", {}),
            created_at=record["created_at"],
            created_by=record.get("created_by"),
        )
