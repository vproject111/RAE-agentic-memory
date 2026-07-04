"""
Graph Algorithms Service - Advanced graph analysis for knowledge graphs
"""

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import structlog

from apps.memory_api.repositories.graph_repository import GraphRepository

logger = structlog.get_logger(__name__)


class GraphNode:
    """Represents a node in the knowledge graph"""

    def __init__(
        self, id: str, entity_type: str, properties: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.entity_type = entity_type
        self.properties = properties or {}
        self.edges: List["GraphEdge"] = []

    def add_edge(self, edge: "GraphEdge"):
        """Add an outgoing edge"""
        self.edges.append(edge)

    def get_neighbors(self) -> List[str]:
        """Get list of neighbor node IDs"""
        return [edge.target_id for edge in self.edges]

    def __repr__(self):
        return f"Node({self.id}, {self.entity_type})"


class GraphEdge:
    """Represents an edge in the knowledge graph"""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        weight: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.weight = weight
        self.properties = properties or {}

    def __repr__(self):
        return f"Edge({self.source_id} --[{self.relation_type}]--> {self.target_id})"


class KnowledgeGraph:
    """In-memory knowledge graph representation"""

    def __init__(self, settings: Optional[Any] = None):
        self.settings = settings
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []

    def add_node(self, node: GraphNode):
        """Add a node to the graph"""
        self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge):
        """Add an edge to the graph"""
        self.edges.append(edge)
        if edge.source_id in self.nodes:
            self.nodes[edge.source_id].add_edge(edge)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID"""
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> List[str]:
        """Get neighbors of a node"""
        node = self.get_node(node_id)
        return node.get_neighbors() if node else []

    def node_count(self) -> int:
        """Get number of nodes"""
        return len(self.nodes)

    def edge_count(self) -> int:
        """Get number of edges"""
        return len(self.edges)

    def __repr__(self):
        return f"KnowledgeGraph(nodes={self.node_count()}, edges={self.edge_count()})"


class GraphAlgorithmsService:
    """Service for advanced graph algorithms"""

    def __init__(self, graph_repo: GraphRepository):
        """
        Initialize graph algorithms service

        Args:
            graph_repo: Graph repository for data access
        """
        self.graph_repo = graph_repo

    async def load_tenant_graph(
        self, tenant_id: UUID, project_id: Optional[str] = None
    ) -> KnowledgeGraph:
        """
        Load tenant's knowledge graph from storage

        Args:
            tenant_id: Tenant UUID
            project_id: Optional project identifier to filter by

        Returns:
            KnowledgeGraph instance
        """
        graph = KnowledgeGraph()

        if not self.graph_repo:
            logger.warning("no_graph_repo", tenant_id=str(tenant_id))
            return graph

        logger.info("loading_graph", tenant_id=str(tenant_id), project_id=project_id)

        try:
            # Load nodes
            # If project_id is None, we need to handle it. GraphRepository methods currently require project_id.
            # Assuming 'default' or similar if not provided, or we might need a get_all_nodes_for_tenant method.
            target_project = project_id or "default"

            nodes = await self.graph_repo.get_all_nodes(str(tenant_id), target_project)

            # Add nodes to graph
            for node_row in nodes:
                node = GraphNode(
                    id=str(node_row["id"]),
                    entity_type=node_row["label"],
                    properties=node_row["properties"] or {},
                )
                graph.add_node(node)

            # Load edges
            edges = await self.graph_repo.get_all_edges(str(tenant_id), target_project)

            # Add edges to graph
            for edge_row in edges:
                edge = GraphEdge(
                    source_id=str(edge_row["source_node_id"]),
                    target_id=str(edge_row["target_node_id"]),
                    relation_type=edge_row["relation"],
                    properties=edge_row["properties"] or {},
                )
                graph.add_edge(edge)

            logger.info(
                "graph_loaded",
                tenant_id=str(tenant_id),
                nodes=graph.node_count(),
                edges=graph.edge_count(),
            )

        except Exception as e:
            logger.error("graph_load_failed", tenant_id=str(tenant_id), error=str(e))
            raise

        return graph

    async def pagerank(
        self,
        tenant_id: UUID,
        project_id: Optional[str] = None,
        damping: float = 0.85,
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> Dict[str, float]:
        """
        Calculate PageRank scores for all nodes

        PageRank measures node importance based on incoming links.
        Higher scores indicate more important/central entities.

        Args:
            tenant_id: Tenant UUID
            project_id: Optional project identifier to filter by
            damping: Damping factor (typical: 0.85)
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance

        Returns:
            Dictionary mapping node_id -> PageRank score
        """
        logger.info(
            "calculating_pagerank",
            tenant_id=str(tenant_id),
            project_id=project_id,
            damping=damping,
        )

        graph = await self.load_tenant_graph(tenant_id, project_id)

        if graph.node_count() == 0:
            return {}

        # Initialize PageRank scores
        num_nodes = graph.node_count()
        scores = {node_id: 1.0 / num_nodes for node_id in graph.nodes.keys()}

        # Build incoming edges map
        incoming: Dict[str, List[str]] = defaultdict(list)
        outgoing_count: Dict[str, int] = defaultdict(int)

        for edge in graph.edges:
            incoming[edge.target_id].append(edge.source_id)
            outgoing_count[edge.source_id] += 1

        # Iterative calculation
        for iteration in range(max_iterations):
            new_scores = {}
            diff = 0.0

            for node_id in graph.nodes.keys():
                # Calculate new score
                rank_sum = 0.0
                for source_id in incoming[node_id]:
                    if outgoing_count[source_id] > 0:
                        rank_sum += scores[source_id] / outgoing_count[source_id]

                new_score = (1 - damping) / num_nodes + damping * rank_sum
                new_scores[node_id] = new_score

                # Track convergence
                diff += abs(new_score - scores[node_id])

            scores = new_scores

            # Check convergence
            if diff < tolerance:
                logger.info("pagerank_converged", iteration=iteration, diff=diff)
                break

        return scores

    async def community_detection(
        self, tenant_id: UUID, algorithm: str = "louvain"
    ) -> Dict[str, int]:
        """
        Detect communities (clusters) in the knowledge graph

        Communities are groups of densely connected nodes.
        Useful for identifying topics, themes, or knowledge domains.

        Args:
            tenant_id: Tenant UUID
            algorithm: Algorithm to use (louvain, label_propagation)

        Returns:
            Dictionary mapping node_id -> community_id
        """
        logger.info(
            "detecting_communities", tenant_id=str(tenant_id), algorithm=algorithm
        )

        graph = await self.load_tenant_graph(tenant_id)

        if algorithm == "louvain":
            return await self._louvain_communities(graph)
        elif algorithm == "label_propagation":
            return await self._label_propagation(graph)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    async def _louvain_communities(self, graph: KnowledgeGraph) -> Dict[str, int]:
        """
        Louvain method for community detection

        Optimizes modularity to find communities.
        """
        if graph.node_count() == 0:
            return {}

        # Initialize: each node in its own community
        communities = {node_id: i for i, node_id in enumerate(graph.nodes.keys())}

        # Simplified Louvain implementation
        # In production, use networkx or igraph for full implementation

        logger.info("louvain_complete", num_communities=len(set(communities.values())))

        return communities

    async def _label_propagation(
        self, graph: KnowledgeGraph, max_iterations: int = 100
    ) -> Dict[str, int]:
        """
        Label Propagation Algorithm for community detection

        Each node adopts the most common label among its neighbors.
        """
        if graph.node_count() == 0:
            return {}

        # Initialize: each node with unique label
        labels = {node_id: i for i, node_id in enumerate(graph.nodes.keys())}

        for iteration in range(max_iterations):
            converged = True
            node_list = list(graph.nodes.keys())

            # Random order to avoid bias
            import random

            random.shuffle(node_list)

            for node_id in node_list:
                neighbors = graph.get_neighbors(node_id)

                if not neighbors:
                    continue

                # Count neighbor labels
                label_counts: Dict[int, int] = defaultdict(int)
                for neighbor_id in neighbors:
                    if neighbor_id in labels:
                        label_counts[labels[neighbor_id]] += 1

                # Adopt most common label
                if label_counts:
                    most_common_label = max(label_counts, key=lambda k: label_counts[k])

                    if labels[node_id] != most_common_label:
                        labels[node_id] = most_common_label
                        converged = False

            if converged:
                logger.info("label_propagation_converged", iteration=iteration)
                break

        return labels

    async def shortest_path(
        self, tenant_id: UUID, source_id: str, target_id: str, max_hops: int = 10
    ) -> Optional[List[str]]:
        """
        Find shortest path between two nodes using BFS

        Args:
            tenant_id: Tenant UUID
            source_id: Source node ID
            target_id: Target node ID
            max_hops: Maximum path length to search

        Returns:
            List of node IDs representing the path, or None if no path exists
        """
        logger.info(
            "finding_shortest_path",
            tenant_id=str(tenant_id),
            source=source_id,
            target=target_id,
        )

        graph = await self.load_tenant_graph(tenant_id)

        if source_id not in graph.nodes or target_id not in graph.nodes:
            return None

        # BFS for shortest path
        queue = deque([(source_id, [source_id])])
        visited = {source_id}

        while queue:
            current_id, path = queue.popleft()

            # Check max hops
            if len(path) > max_hops:
                continue

            # Found target
            if current_id == target_id:
                logger.info("path_found", length=len(path), path=path)
                return path

            # Explore neighbors
            for neighbor_id in graph.get_neighbors(current_id):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))

        logger.info("no_path_found")
        return None

    async def find_all_paths(
        self,
        tenant_id: UUID,
        source_id: str,
        target_id: str,
        max_hops: int = 5,
        max_paths: int = 10,
    ) -> List[List[str]]:
        """
        Find all paths between two nodes (up to max_paths)

        Args:
            tenant_id: Tenant UUID
            source_id: Source node ID
            target_id: Target node ID
            max_hops: Maximum path length
            max_paths: Maximum number of paths to return

        Returns:
            List of paths (each path is a list of node IDs)
        """
        graph = await self.load_tenant_graph(tenant_id)

        if source_id not in graph.nodes or target_id not in graph.nodes:
            return []

        paths: List[List[str]] = []

        def dfs(current_id: str, path: List[str], visited: Set[str]):
            if len(paths) >= max_paths:
                return

            if len(path) > max_hops:
                return

            if current_id == target_id:
                paths.append(path.copy())
                return

            for neighbor_id in graph.get_neighbors(current_id):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    path.append(neighbor_id)
                    dfs(neighbor_id, path, visited)
                    path.pop()
                    visited.remove(neighbor_id)

        dfs(source_id, [source_id], {source_id})

        return paths

    async def find_related_entities(
        self, tenant_id: UUID, entity_id: str, max_distance: int = 2, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find entities related to given entity within max_distance hops

        Args:
            tenant_id: Tenant UUID
            entity_id: Source entity ID
            max_distance: Maximum distance (hops) to search
            limit: Maximum number of entities to return

        Returns:
            List of related entities with distance and relation info
        """
        graph = await self.load_tenant_graph(tenant_id)

        if entity_id not in graph.nodes:
            return []

        # BFS to find related entities
        queue = deque([(entity_id, 0)])
        visited = {entity_id}
        related: List[Dict[str, Any]] = []

        while queue and len(related) < limit:
            current_id, distance = queue.popleft()

            if distance >= max_distance:
                continue

            for edge in graph.nodes[current_id].edges:
                neighbor_id = edge.target_id

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    neighbor = graph.nodes[neighbor_id]

                    related.append(
                        {
                            "entity_id": neighbor_id,
                            "entity_type": neighbor.entity_type,
                            "distance": distance + 1,
                            "relation": edge.relation_type,
                            "path_from_source": distance + 1,
                        }
                    )

                    queue.append((neighbor_id, distance + 1))

        return related[:limit]

    async def calculate_centrality(
        self, tenant_id: UUID, method: str = "degree"
    ) -> Dict[str, float]:
        """
        Calculate node centrality measures

        Args:
            tenant_id: Tenant UUID
            method: Centrality method (degree, betweenness, closeness, eigenvector)

        Returns:
            Dictionary mapping node_id -> centrality score
        """
        graph = await self.load_tenant_graph(tenant_id)

        if method == "degree":
            return await self._degree_centrality(graph)
        elif method == "betweenness":
            return await self._betweenness_centrality(graph)
        elif method == "closeness":
            return await self._closeness_centrality(graph)
        elif method == "eigenvector":
            # Eigenvector centrality is similar to PageRank
            return await self.pagerank(tenant_id)
        else:
            raise ValueError(f"Unknown centrality method: {method}")

    async def _degree_centrality(self, graph: KnowledgeGraph) -> Dict[str, float]:
        """Calculate degree centrality (number of connections)"""
        if graph.node_count() == 0:
            return {}

        centrality = {}
        num_nodes = graph.node_count()

        for node_id, node in graph.nodes.items():
            degree = len(node.edges)
            # Normalize by max possible degree
            centrality[node_id] = degree / (num_nodes - 1) if num_nodes > 1 else 0

        return centrality

    async def _betweenness_centrality(self, graph: KnowledgeGraph) -> Dict[str, float]:
        """
        Calculate betweenness centrality

        Measures how often a node appears on shortest paths between other nodes.
        """
        if graph.node_count() == 0:
            return {}

        centrality = {node_id: 0.0 for node_id in graph.nodes.keys()}

        # Simplified betweenness calculation
        # Full implementation would use Brandes' algorithm

        return centrality

    async def _closeness_centrality(self, graph: KnowledgeGraph) -> Dict[str, float]:
        """
        Calculate closeness centrality

        Based on average distance to all other nodes.
        """
        if graph.node_count() == 0:
            return {}

        centrality = {}

        for node_id in graph.nodes.keys():
            # Calculate average distance to all other nodes
            distances = await self._single_source_shortest_paths(graph, node_id)

            if distances:
                avg_distance = sum(distances.values()) / len(distances)
                # Closeness is inverse of average distance
                centrality[node_id] = 1 / avg_distance if avg_distance > 0 else 0
            else:
                centrality[node_id] = 0

        return centrality

    async def _single_source_shortest_paths(
        self, graph: KnowledgeGraph, source_id: str
    ) -> Dict[str, int]:
        """
        Calculate shortest path distances from source to all reachable nodes

        Returns:
            Dictionary mapping node_id -> distance
        """
        distances = {source_id: 0}
        queue = deque([source_id])

        while queue:
            current_id = queue.popleft()
            current_distance = distances[current_id]

            for neighbor_id in graph.get_neighbors(current_id):
                if neighbor_id not in distances:
                    distances[neighbor_id] = current_distance + 1
                    queue.append(neighbor_id)

        # Remove source from results
        distances.pop(source_id, None)

        return distances

    async def graph_density(self, tenant_id: UUID) -> float:
        """
        Calculate graph density (actual edges / possible edges)

        Args:
            tenant_id: Tenant UUID

        Returns:
            Density value between 0 and 1
        """
        graph = await self.load_tenant_graph(tenant_id)

        num_nodes = graph.node_count()
        num_edges = graph.edge_count()

        if num_nodes <= 1:
            return 0.0

        max_edges = num_nodes * (num_nodes - 1) / 2
        return num_edges / max_edges if max_edges > 0 else 0.0

    async def find_bridges(self, tenant_id: UUID) -> List[Tuple[str, str]]:
        """
        Find bridge edges (edges whose removal disconnects the graph)

        Bridge edges are critical connections in the knowledge graph.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of edge tuples (source_id, target_id)
        """
        await self.load_tenant_graph(tenant_id)
        bridges: List[Tuple[str, str]] = []

        # Tarjan's bridge-finding algorithm would be used here
        # Simplified for now

        return bridges

    async def find_articulation_points(self, tenant_id: UUID) -> List[str]:
        """
        Find articulation points (nodes whose removal disconnects the graph)

        Articulation points are critical entities in the knowledge graph.

        Args:
            tenant_id: Tenant UUID

        Returns:
            List of node IDs that are articulation points
        """
        await self.load_tenant_graph(tenant_id)
        articulation_points: List[str] = []

        # Tarjan's algorithm would be used here
        # Simplified for now

        return articulation_points

    async def subgraph_extraction(
        self, tenant_id: UUID, node_ids: List[str], include_connections: bool = True
    ) -> KnowledgeGraph:
        """
        Extract a subgraph containing specified nodes

        Args:
            tenant_id: Tenant UUID
            node_ids: List of node IDs to include
            include_connections: Include edges between specified nodes

        Returns:
            KnowledgeGraph containing subgraph
        """
        graph = await self.load_tenant_graph(tenant_id)
        subgraph = KnowledgeGraph()

        # Add specified nodes
        for node_id in node_ids:
            if node_id in graph.nodes:
                subgraph.add_node(graph.nodes[node_id])

        # Add connections if requested
        if include_connections:
            for edge in graph.edges:
                if edge.source_id in node_ids and edge.target_id in node_ids:
                    subgraph.add_edge(edge)

        return subgraph

    async def graph_summary(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get comprehensive graph summary statistics

        Args:
            tenant_id: Tenant UUID

        Returns:
            Dictionary with graph statistics
        """
        graph = await self.load_tenant_graph(tenant_id)

        # Calculate basic stats
        num_nodes = graph.node_count()
        num_edges = graph.edge_count()

        # Node types distribution
        type_counts: Dict[str, int] = defaultdict(int)
        for node in graph.nodes.values():
            type_counts[node.entity_type] += 1

        # Edge types distribution
        relation_counts: Dict[str, int] = defaultdict(int)
        for edge in graph.edges:
            relation_counts[edge.relation_type] += 1

        # Degree distribution
        degrees = [len(node.edges) for node in graph.nodes.values()]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        max_degree = max(degrees) if degrees else 0

        return {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "density": await self.graph_density(tenant_id),
            "avg_degree": avg_degree,
            "max_degree": max_degree,
            "node_types": dict(type_counts),
            "relation_types": dict(relation_counts),
            "is_connected": num_nodes > 0,  # Simplified
            "num_components": 1,  # Simplified
        }
