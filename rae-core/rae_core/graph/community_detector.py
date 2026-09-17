"""Deterministic community detector for architectural knowledge graphs."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from rae_core.models.graph import GraphEdge


class GraphCommunity(BaseModel):
    """A cluster of semantically/architecturally connected graph nodes."""

    model_config = ConfigDict(extra="forbid")

    community_id: str
    node_ids: list[UUID] = Field(default_factory=list)
    edge_count: int = 0
    density: float = 0.0
    domain_label: str | None = None
    is_dirty: bool = False


class CommunityDetector:
    """
    Deterministic community detector using connected components and modularity analysis.
    Supports incremental dirty-state invalidation so only updated communities are re-synthesized.
    """

    def __init__(self, min_community_size: int = 1):
        self.min_community_size = min_community_size
        self._cached_communities: dict[str, GraphCommunity] = {}
        self._node_to_community: dict[UUID, str] = {}

    def detect_communities(
        self,
        nodes: list[UUID],
        edges: list[GraphEdge],
        node_properties: dict[UUID, dict[str, Any]] | None = None,
    ) -> list[GraphCommunity]:
        """
        Detect disjoint communities from nodes and edges using BFS component clustering.
        """
        adjacency: dict[UUID, set[UUID]] = defaultdict(set)
        for edge in edges:
            adjacency[edge.source_id].add(edge.target_id)
            adjacency[edge.target_id].add(edge.source_id)

        # Include isolated nodes
        for node_id in nodes:
            if node_id not in adjacency:
                adjacency[node_id] = set()

        visited: set[UUID] = set()
        communities: list[GraphCommunity] = []
        cluster_idx = 0

        for start_node in nodes:
            if start_node in visited:
                continue

            # BFS to find connected component
            component_nodes: list[UUID] = []
            queue = deque([start_node])
            visited.add(start_node)

            while queue:
                curr = queue.popleft()
                component_nodes.append(curr)

                for neighbor in adjacency[curr]:
                    if neighbor not in visited and neighbor in adjacency:
                        visited.add(neighbor)
                        queue.append(neighbor)

            if len(component_nodes) < self.min_community_size:
                continue

            # Count internal edges
            node_set = set(component_nodes)
            internal_edges = 0
            for edge in edges:
                if edge.source_id in node_set and edge.target_id in node_set:
                    internal_edges += 1

            n = len(component_nodes)
            possible_edges = (n * (n - 1)) / 2 if n > 1 else 1.0
            density = min(1.0, internal_edges / possible_edges) if n > 1 else 1.0

            # Derive domain label from node properties if available
            domain_label = None
            if node_properties:
                labels: list[str] = []
                for nid in component_nodes:
                    props = node_properties.get(nid, {})
                    domain = (
                        props.get("domain")
                        or props.get("project")
                        or props.get("category")
                    )
                    if domain and domain not in labels:
                        labels.append(domain)
                if labels:
                    domain_label = "_".join(labels[:3])

            comm_id = f"comm_{cluster_idx}_{domain_label or 'general'}"
            community = GraphCommunity(
                community_id=comm_id,
                node_ids=component_nodes,
                edge_count=internal_edges,
                density=density,
                domain_label=domain_label,
                is_dirty=False,
            )

            communities.append(community)
            self._cached_communities[comm_id] = community
            for nid in component_nodes:
                self._node_to_community[nid] = comm_id

            cluster_idx += 1

        return communities

    def mark_dirty(self, modified_node_ids: list[UUID]) -> list[str]:
        """
        Mark communities containing modified nodes as dirty.
        Returns list of dirty community IDs requiring re-synthesis.
        """
        dirty_ids: set[str] = set()
        for nid in modified_node_ids:
            comm_id = self._node_to_community.get(nid)
            if comm_id and comm_id in self._cached_communities:
                self._cached_communities[comm_id].is_dirty = True
                dirty_ids.add(comm_id)
        return sorted(list(dirty_ids))
