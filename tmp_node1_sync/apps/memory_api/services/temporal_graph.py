"""
Temporal Graph Service - Track knowledge graph evolution over time
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.graph_algorithms import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
)

logger = structlog.get_logger(__name__)


class ChangeType(str, Enum):
    """Types of graph changes"""

    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    NODE_UPDATED = "node_updated"
    EDGE_ADDED = "edge_added"
    EDGE_REMOVED = "edge_removed"
    EDGE_UPDATED = "edge_updated"


class GraphSnapshot:
    """Snapshot of graph at a specific point in time"""

    def __init__(
        self,
        tenant_id: UUID,
        timestamp: datetime,
        graph: KnowledgeGraph,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.tenant_id = tenant_id
        self.timestamp = timestamp
        self.graph = graph
        self.metadata = metadata or {}

    def __repr__(self):
        return f"GraphSnapshot({self.timestamp}, {self.graph})"


class GraphChange:
    """Represents a change to the graph"""

    def __init__(
        self,
        change_type: ChangeType,
        timestamp: datetime,
        entity_id: str,
        entity_type: str,
        old_value: Optional[Any] = None,
        new_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.change_type = change_type
        self.timestamp = timestamp
        self.entity_id = entity_id
        self.entity_type = entity_type
        self.old_value = old_value
        self.new_value = new_value
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "change_type": self.change_type.value,
            "timestamp": self.timestamp.isoformat(),
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "metadata": self.metadata,
        }

    def __repr__(self):
        return f"GraphChange({self.change_type}, {self.entity_id}, {self.timestamp})"


class TemporalGraphService:
    """Service for temporal graph operations"""

    def __init__(self, graph_repo: Optional[GraphRepository] = None):
        """
        Initialize temporal graph service

        Args:
            graph_repo: Graph repository for persistence
        """
        self.graph_repo = graph_repo

        # In-memory storage for development
        self._snapshots: Dict[UUID, List[GraphSnapshot]] = {}
        self._changes: Dict[UUID, List[GraphChange]] = {}

    async def create_snapshot(
        self,
        tenant_id: UUID,
        graph: KnowledgeGraph,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> GraphSnapshot:
        """
        Create a snapshot of the current graph state

        Args:
            tenant_id: Tenant UUID
            graph: Current knowledge graph
            metadata: Optional metadata about the snapshot

        Returns:
            GraphSnapshot instance
        """
        snapshot = GraphSnapshot(
            tenant_id=tenant_id,
            timestamp=datetime.now(timezone.utc),
            graph=graph,
            metadata=metadata,
        )

        # Store snapshot
        if tenant_id not in self._snapshots:
            self._snapshots[tenant_id] = []
        self._snapshots[tenant_id].append(snapshot)

        logger.info(
            "snapshot_created",
            tenant_id=str(tenant_id),
            timestamp=snapshot.timestamp.isoformat(),
            nodes=graph.node_count(),
            edges=graph.edge_count(),
        )

        return snapshot

    async def get_snapshot_at_time(
        self, tenant_id: UUID, timestamp: datetime
    ) -> Optional[GraphSnapshot]:
        """
        Get graph snapshot at or before specified time

        Args:
            tenant_id: Tenant UUID
            timestamp: Target timestamp

        Returns:
            GraphSnapshot or None if not found
        """
        snapshots = self._snapshots.get(tenant_id, [])

        # Find snapshot at or before timestamp
        valid_snapshots = [s for s in snapshots if s.timestamp <= timestamp]

        if not valid_snapshots:
            return None

        # Return most recent valid snapshot
        return max(valid_snapshots, key=lambda s: s.timestamp)

    async def get_latest_snapshot(self, tenant_id: UUID) -> Optional[GraphSnapshot]:
        """
        Get most recent snapshot

        Args:
            tenant_id: Tenant UUID

        Returns:
            Latest GraphSnapshot or None
        """
        snapshots = self._snapshots.get(tenant_id, [])

        if not snapshots:
            return None

        return max(snapshots, key=lambda s: s.timestamp)

    async def record_change(self, tenant_id: UUID, change: GraphChange):
        """
        Record a graph change

        Args:
            tenant_id: Tenant UUID
            change: GraphChange instance
        """
        if tenant_id not in self._changes:
            self._changes[tenant_id] = []

        self._changes[tenant_id].append(change)

        logger.info(
            "change_recorded",
            tenant_id=str(tenant_id),
            change_type=change.change_type.value,
            entity_id=change.entity_id,
        )

    async def get_changes(
        self,
        tenant_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        change_types: Optional[List[ChangeType]] = None,
        entity_id: Optional[str] = None,
    ) -> List[GraphChange]:
        """
        Get graph changes with optional filters

        Args:
            tenant_id: Tenant UUID
            start_time: Filter changes after this time
            end_time: Filter changes before this time
            change_types: Filter by change types
            entity_id: Filter by specific entity

        Returns:
            List of GraphChange instances
        """
        changes = self._changes.get(tenant_id, [])

        # Apply filters
        filtered = changes

        if start_time:
            filtered = [c for c in filtered if c.timestamp >= start_time]

        if end_time:
            filtered = [c for c in filtered if c.timestamp <= end_time]

        if change_types:
            filtered = [c for c in filtered if c.change_type in change_types]

        if entity_id:
            filtered = [c for c in filtered if c.entity_id == entity_id]

        return sorted(filtered, key=lambda c: c.timestamp)

    async def get_entity_history(
        self, tenant_id: UUID, entity_id: str
    ) -> List[GraphChange]:
        """
        Get complete change history for an entity

        Args:
            tenant_id: Tenant UUID
            entity_id: Entity ID

        Returns:
            List of changes affecting this entity, chronologically ordered
        """
        return await self.get_changes(tenant_id, entity_id=entity_id)

    async def reconstruct_graph_at_time(
        self, tenant_id: UUID, timestamp: datetime
    ) -> Optional[KnowledgeGraph]:
        """
        Reconstruct the knowledge graph as it existed at a specific time

        Args:
            tenant_id: Tenant UUID
            timestamp: Target timestamp

        Returns:
            Reconstructed KnowledgeGraph or None
        """
        # Find latest snapshot before timestamp
        snapshot = await self.get_snapshot_at_time(tenant_id, timestamp)

        if not snapshot:
            # No snapshot available, would need to reconstruct from scratch
            return None

        # Start with snapshot graph
        graph = snapshot.graph

        # Apply changes between snapshot and target time
        changes = await self.get_changes(
            tenant_id, start_time=snapshot.timestamp, end_time=timestamp
        )

        # Apply changes chronologically
        for change in changes:
            graph = self._apply_change(graph, change)

        return graph

    def _apply_change(
        self, graph: KnowledgeGraph, change: GraphChange
    ) -> KnowledgeGraph:
        """
        Apply a change to a graph

        Args:
            graph: Knowledge graph
            change: Change to apply

        Returns:
            Modified graph
        """
        if change.change_type == ChangeType.NODE_ADDED:
            if change.new_value and isinstance(change.new_value, dict):
                node = GraphNode(
                    id=change.entity_id,
                    entity_type=change.new_value.get("entity_type", "unknown"),
                    properties=change.new_value.get("properties", {}),
                )
                graph.add_node(node)

        elif change.change_type == ChangeType.NODE_REMOVED:
            if change.entity_id in graph.nodes:
                del graph.nodes[change.entity_id]

        elif change.change_type == ChangeType.NODE_UPDATED:
            if change.entity_id in graph.nodes and change.new_value:
                node = graph.nodes[change.entity_id]
                if isinstance(change.new_value, dict):
                    node.properties.update(change.new_value.get("properties", {}))

        elif change.change_type == ChangeType.EDGE_ADDED:
            if change.new_value and isinstance(change.new_value, dict):
                edge = GraphEdge(
                    source_id=change.new_value.get("source_id", ""),
                    target_id=change.new_value.get("target_id", ""),
                    relation_type=change.new_value.get("relation_type", "unknown"),
                    weight=change.new_value.get("weight", 1.0),
                    properties=change.new_value.get("properties", {}),
                )
                graph.add_edge(edge)

        elif change.change_type == ChangeType.EDGE_REMOVED:
            # Remove edge from graph.edges list
            graph.edges = [
                e
                for e in graph.edges
                if not (
                    e.source_id == change.entity_id.split("->")[0]
                    and e.target_id == change.entity_id.split("->")[1]
                )
            ]

        return graph

    async def compare_graphs(
        self, graph1: KnowledgeGraph, graph2: KnowledgeGraph
    ) -> Dict[str, Any]:
        """
        Compare two graphs and identify differences

        Args:
            graph1: First graph (older)
            graph2: Second graph (newer)

        Returns:
            Dictionary describing differences
        """
        # Nodes added
        nodes_added = set(graph2.nodes.keys()) - set(graph1.nodes.keys())

        # Nodes removed
        nodes_removed = set(graph1.nodes.keys()) - set(graph2.nodes.keys())

        # Edges added
        edges1 = {(e.source_id, e.target_id, e.relation_type) for e in graph1.edges}
        edges2 = {(e.source_id, e.target_id, e.relation_type) for e in graph2.edges}
        edges_added = edges2 - edges1
        edges_removed = edges1 - edges2

        return {
            "nodes_added": list(nodes_added),
            "nodes_removed": list(nodes_removed),
            "nodes_added_count": len(nodes_added),
            "nodes_removed_count": len(nodes_removed),
            "edges_added": [
                {"source": s, "target": t, "relation": r} for s, t, r in edges_added
            ],
            "edges_removed": [
                {"source": s, "target": t, "relation": r} for s, t, r in edges_removed
            ],
            "edges_added_count": len(edges_added),
            "edges_removed_count": len(edges_removed),
            "total_changes": len(nodes_added)
            + len(nodes_removed)
            + len(edges_added)
            + len(edges_removed),
        }

    async def get_evolution_timeline(
        self,
        tenant_id: UUID,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get timeline of graph evolution

        Args:
            tenant_id: Tenant UUID
            start_time: Start of timeline
            end_time: End of timeline

        Returns:
            List of timeline events with statistics
        """
        changes = await self.get_changes(tenant_id, start_time, end_time)

        # Group changes by time bucket (e.g., hourly)
        timeline = []
        current_bucket = None
        bucket_changes: List[GraphChange] = []

        for change in changes:
            # Create hourly buckets
            bucket_time = change.timestamp.replace(minute=0, second=0, microsecond=0)

            if current_bucket != bucket_time:
                # Save previous bucket
                if current_bucket and bucket_changes:
                    timeline.append(
                        self._summarize_bucket(current_bucket, bucket_changes)
                    )

                current_bucket = bucket_time
                bucket_changes = []

            bucket_changes.append(change)

        # Save last bucket
        if current_bucket and bucket_changes:
            timeline.append(self._summarize_bucket(current_bucket, bucket_changes))

        return timeline

    def _summarize_bucket(
        self, bucket_time: datetime, changes: List[GraphChange]
    ) -> Dict[str, Any]:
        """Summarize changes in a time bucket"""
        change_type_counts: Dict[str, int] = {}
        for change in changes:
            change_type = change.change_type.value
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1

        return {
            "timestamp": bucket_time.isoformat(),
            "total_changes": len(changes),
            "by_type": change_type_counts,
            "entities_affected": len(set(c.entity_id for c in changes)),
        }

    async def get_growth_metrics(
        self, tenant_id: UUID, period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate graph growth metrics over a period

        Args:
            tenant_id: Tenant UUID
            period_days: Number of days to analyze

        Returns:
            Growth metrics including rates and trends
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=period_days)

        # Get snapshots at start and end
        start_graph = await self.reconstruct_graph_at_time(tenant_id, start_time)
        end_graph = await self.reconstruct_graph_at_time(tenant_id, end_time)

        if not start_graph or not end_graph:
            return {"error": "Insufficient data for growth analysis"}

        # Calculate growth
        start_nodes = start_graph.node_count()
        end_nodes = end_graph.node_count()
        start_edges = start_graph.edge_count()
        end_edges = end_graph.edge_count()

        node_growth = end_nodes - start_nodes
        edge_growth = end_edges - start_edges

        return {
            "period_days": period_days,
            "start_date": start_time.isoformat(),
            "end_date": end_time.isoformat(),
            "nodes": {
                "start": start_nodes,
                "end": end_nodes,
                "growth": node_growth,
                "growth_rate": node_growth / start_nodes if start_nodes > 0 else 0,
                "daily_growth": node_growth / period_days,
            },
            "edges": {
                "start": start_edges,
                "end": end_edges,
                "growth": edge_growth,
                "growth_rate": edge_growth / start_edges if start_edges > 0 else 0,
                "daily_growth": edge_growth / period_days,
            },
            "density": {
                "start": await self._calculate_density(start_graph),
                "end": await self._calculate_density(end_graph),
            },
        }

    async def _calculate_density(self, graph: KnowledgeGraph) -> float:
        """Calculate graph density"""
        num_nodes = graph.node_count()
        num_edges = graph.edge_count()

        if num_nodes <= 1:
            return 0.0

        max_edges = num_nodes * (num_nodes - 1) / 2
        return num_edges / max_edges if max_edges > 0 else 0.0

    async def find_emerging_patterns(
        self, tenant_id: UUID, window_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Find emerging patterns in graph evolution

        Identifies:
        - Rapidly growing entities
        - New connection patterns
        - Trending topics

        Args:
            tenant_id: Tenant UUID
            window_days: Analysis window in days

        Returns:
            List of emerging patterns
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=window_days)

        changes = await self.get_changes(tenant_id, start_time, end_time)

        patterns = []

        # Find rapidly growing entities (entities with many new connections)
        entity_connection_count: Dict[str, int] = {}
        for change in changes:
            if change.change_type == ChangeType.EDGE_ADDED:
                if change.new_value and isinstance(change.new_value, dict):
                    source = change.new_value.get("source_id")
                    target = change.new_value.get("target_id")

                    if source:
                        entity_connection_count[source] = (
                            entity_connection_count.get(source, 0) + 1
                        )
                    if target:
                        entity_connection_count[target] = (
                            entity_connection_count.get(target, 0) + 1
                        )

        # Identify top growing entities
        if entity_connection_count:
            sorted_entities = sorted(
                entity_connection_count.items(), key=lambda x: x[1], reverse=True
            )[:10]

            for entity_id, connection_count in sorted_entities:
                patterns.append(
                    {
                        "type": "rapidly_growing_entity",
                        "entity_id": entity_id,
                        "new_connections": connection_count,
                        "confidence": min(connection_count / 10.0, 1.0),
                    }
                )

        return patterns

    async def cleanup_old_snapshots(
        self, tenant_id: UUID, retention_days: int = 90
    ) -> int:
        """
        Clean up old snapshots beyond retention period

        Args:
            tenant_id: Tenant UUID
            retention_days: Number of days to retain

        Returns:
            Number of snapshots deleted
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=retention_days)
        snapshots = self._snapshots.get(tenant_id, [])

        # Keep snapshots after cutoff
        kept_snapshots = [s for s in snapshots if s.timestamp >= cutoff_time]
        removed_count = len(snapshots) - len(kept_snapshots)

        self._snapshots[tenant_id] = kept_snapshots

        logger.info(
            "snapshots_cleaned",
            tenant_id=str(tenant_id),
            removed=removed_count,
            retained=len(kept_snapshots),
        )

        return removed_count
