"""
Graph Topology Engine - Deterministic Topological Logic for Knowledge Graph.

This module implements MATH-1: Deterministic Topological Logic.
It uses network analysis algorithms (Dijkstra, Centrality) to "prove" relationships
and paths within the knowledge graph, independent of LLM hallucinations.
"""

from typing import Any, Dict, List

import networkx as nx

from apps.memory_api.models.graph import GraphEdge, GraphNode
from apps.memory_api.repositories.graph_repository import GraphRepository


class GraphTopologyEngine:
    """
    Engine for topological analysis of the knowledge graph.

    Responsibilities:
    1. Subgraph extraction.
    2. Path proving (Shortest Path / Dijkstra).
    3. Centrality analysis (finding key concepts).
    4. Community detection (local).
    """

    def __init__(self, graph_repository: GraphRepository):
        self.graph_repository = graph_repository

    def build_networkx_graph(
        self, nodes: List[GraphNode], edges: List[GraphEdge]
    ) -> nx.DiGraph:
        """
        Convert internal graph models to NetworkX DiGraph.
        """
        G = nx.DiGraph()

        for node in nodes:
            G.add_node(str(node.id), label=node.label, **node.properties)

        for edge in edges:
            # Use 'confidence' or weight from properties if available
            weight = edge.properties.get("confidence", 1.0) if edge.properties else 1.0
            # NetworkX uses 'weight' for Dijkstra (lower is better usually for distance,
            # but here higher confidence is better. So distance = 1/confidence)
            distance = 1.0 / (weight if weight > 0 else 0.001)

            G.add_edge(
                str(edge.source_id),
                str(edge.target_id),
                relation=edge.relation,
                weight=weight,
                distance=distance,
                **edge.properties,
            )

        return G

    async def prove_paths(
        self, start_node_ids: List[str], tenant_id: str, project_id: str, depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find and prove significant paths from start nodes within the subgraph.

        Returns paths that have high cumulative confidence.
        """
        # 1. Fetch Subgraph (BFS)
        nodes, edges = await self.graph_repository.traverse_graph_bfs(
            start_node_ids, tenant_id, project_id, depth
        )

        if not nodes:
            return []

        # 2. Build NetworkX Graph
        G = self.build_networkx_graph(nodes, edges)

        # 3. Analyze Paths
        proven_paths = []

        # Map internal IDs back to GraphNodes for result construction
        node_map = {str(n.id): n for n in nodes}

        # Find paths from start nodes to other significant nodes
        # For simplicity, we calculate centrality to find "significant" nodes in the subgraph
        if len(G) > 1:
            centrality = nx.degree_centrality(G)
            # Filter targets: top 5 central nodes that are NOT start nodes
            sorted_nodes = sorted(centrality.items(), key=lambda x: x[1], reverse=True)

            # We need to map start_node_ids (which might be external 'node_id') to internal 'id'
            # But traverse_graph_bfs takes 'node_id' (external) and returns nodes with internal 'id'.
            # The input start_node_ids are 'node_id'.
            # We need to find which nodes in 'nodes' correspond to 'start_node_ids'.

            internal_start_ids = [
                str(n.id) for n in nodes if n.node_id in start_node_ids
            ]

            targets = [
                n_id for n_id, score in sorted_nodes if n_id not in internal_start_ids
            ][:5]

            for start in internal_start_ids:
                if start not in G:
                    continue

                for target in targets:
                    if target not in G:
                        continue

                    try:
                        # Find shortest path using 'distance' (1/confidence)
                        path_ids = nx.shortest_path(
                            G, source=start, target=target, weight="distance"
                        )

                        # Calculate path confidence (product of edge confidences)
                        confidence = 1.0
                        path_segments = []

                        for i in range(len(path_ids) - 1):
                            u, v = path_ids[i], path_ids[i + 1]
                            edge_data = G.get_edge_data(u, v)
                            confidence *= edge_data.get("weight", 1.0)

                            u_node = node_map[u]
                            v_node = node_map[v]

                            path_segments.append(
                                {
                                    "source": u_node.label,
                                    "target": v_node.label,
                                    "relation": edge_data.get(
                                        "relation", "connected_to"
                                    ),
                                }
                            )

                        proven_paths.append(
                            {
                                "start_node": node_map[start].label,
                                "end_node": node_map[target].label,
                                "path_nodes": [node_map[nid].label for nid in path_ids],
                                "segments": path_segments,
                                "confidence": confidence,
                                "length": len(path_ids),
                            }
                        )

                    except nx.NetworkXNoPath:
                        continue

        return sorted(proven_paths, key=lambda x: x["confidence"], reverse=True)

    async def get_central_concepts(
        self, start_node_ids: List[str], tenant_id: str, project_id: str, depth: int = 2
    ) -> List[GraphNode]:
        """
        Identify central concepts in the subgraph surrounding the start nodes.
        Uses PageRank or Degree Centrality.
        """
        # 1. Fetch Subgraph
        nodes, edges = await self.graph_repository.traverse_graph_bfs(
            start_node_ids, tenant_id, project_id, depth
        )

        if not nodes:
            return []

        # 2. Build Graph
        G = self.build_networkx_graph(nodes, edges)

        # 3. Calculate PageRank
        try:
            pagerank = nx.pagerank(G, weight="weight")
            sorted_nodes = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)

            # Return top 10 nodes
            top_ids = [nid for nid, score in sorted_nodes[:10]]

            node_map = {str(n.id): n for n in nodes}
            return [node_map[nid] for nid in top_ids if nid in node_map]

        except Exception:
            # Fallback to simple list if pagerank fails
            return nodes[:10]
