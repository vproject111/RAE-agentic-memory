"""
Knowledge Graph Update Operator - Iteration 5

Mathematical formulation:
  G_{t+1} = T(G_t, o_t, a_t)

Where:
  G_t = (V_t, E_t) - Graph at time t
  o_t = Observation (new memory, entity extraction result, etc.)
  a_t = Action (add_node, add_edge, merge_nodes, prune, etc.)
  T = Deterministic transformation function

Properties to maintain:
  - Consistency: No duplicate nodes with same entity
  - Connectivity: Graph should remain connected
  - Temporal decay: Edge weights decay over time
  - Convergence: Graph should stabilize over time

Usage:
    operator = GraphUpdateOperator()

    # Load current graph
    G_t = await load_graph(tenant_id, project_id)

    # Observation: new memory with entities
    observation = {
        "memory_id": "mem_123",
        "content": "John met Alice at the conference",
        "entities": ["John", "Alice", "conference"],
        "relations": [("John", "met", "Alice"), ...]
    }

    # Apply transformation
    G_next = operator.apply(
        graph=G_t,
        action_type=GraphActionType.ADD_EDGE,
        observation=observation
    )

    # Analyze convergence
    convergence = operator.analyze_convergence(graph_history)
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import structlog

from apps.memory_api.observability.rae_tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


class GraphActionType(str, Enum):
    """Types of graph transformations"""

    ADD_NODE = "add_node"
    ADD_EDGE = "add_edge"
    UPDATE_EDGE_WEIGHT = "update_edge_weight"
    MERGE_NODES = "merge_nodes"
    PRUNE_NODE = "prune_node"
    PRUNE_EDGE = "prune_edge"
    EXTRACT_SUBGRAPH = "extract_subgraph"


@dataclass
class GraphNode:
    """
    Node in knowledge graph.

    Represents entities, concepts, events in RAE memory.

    Attributes:
        id: Unique node identifier
        label: Human-readable label
        node_type: Type of entity (person, concept, event, etc.)
        properties: Additional metadata
        created_at: Creation timestamp
        last_updated: Last update timestamp
        importance: Importance score [0-1]
        centrality: Graph centrality score [0-1]
    """

    id: str
    label: str
    node_type: str  # entity, concept, event, etc.
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    importance: float = 0.5  # 0-1
    centrality: float = 0.0  # 0-1 (computed from graph structure)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "label": self.label,
            "node_type": self.node_type,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "importance": self.importance,
            "centrality": self.centrality,
        }


@dataclass
class GraphEdge:
    """
    Edge in knowledge graph.

    Represents relationships between entities.

    Attributes:
        id: Unique edge identifier (format: source_relation_target)
        source_id: Source node ID
        target_id: Target node ID
        relation: Relationship type
        weight: Edge weight [0-1]
        confidence: Confidence score [0-1]
        created_at: Creation timestamp
        last_updated: Last update timestamp
        evidence_count: Number of observations supporting this edge
    """

    id: str
    source_id: str
    target_id: str
    relation: str
    weight: float = 0.7  # 0-1
    confidence: float = 0.8  # 0-1
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    evidence_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "weight": self.weight,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "evidence_count": self.evidence_count,
        }


@dataclass
class KnowledgeGraph:
    """
    Complete knowledge graph state.

    Mathematical formulation: G = (V, E)
      V = set of nodes (vertices)
      E = set of edges

    Attributes:
        nodes: Dictionary of node_id -> GraphNode
        edges: Dictionary of edge_id -> GraphEdge
        tenant_id: Tenant identifier
        project_id: Project identifier
        created_at: Graph creation timestamp
        last_updated: Last update timestamp
    """

    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: Dict[str, GraphEdge] = field(default_factory=dict)
    tenant_id: str = ""
    project_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get node by ID"""
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Get edge by ID"""
        return self.edges.get(edge_id)

    def adjacency_matrix(self) -> np.ndarray:
        """
        Get adjacency matrix for graph analysis.

        Returns:
            Adjacency matrix A where A[i,j] = weight of edge from node i to node j
        """
        if not self.nodes:
            return np.array([[]])

        node_ids = list(self.nodes.keys())
        n = len(node_ids)
        adj = np.zeros((n, n))

        node_idx = {node_id: i for i, node_id in enumerate(node_ids)}

        for edge in self.edges.values():
            i = node_idx.get(edge.source_id)
            j = node_idx.get(edge.target_id)

            if i is not None and j is not None:
                adj[i][j] = edge.weight

        return adj

    def copy(self) -> "KnowledgeGraph":
        """Deep copy of graph"""
        import copy

        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": {edge_id: edge.to_dict() for edge_id, edge in self.edges.items()},
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }


class GraphUpdateOperator:
    """
    Implements graph transformation function T.

    Mathematical formulation:
      G_{t+1} = T(G_t, o_t, a_t)

    Where:
      - G_t: Current graph state
      - o_t: Observation (new information)
      - a_t: Action (transformation to apply)
      - T: Deterministic transformation function

    This operator ensures:
      1. Deterministic transformations (reproducible)
      2. Temporal decay of edge weights
      3. Entity resolution (merge duplicates)
      4. Convergence to stable structure

    Usage:
        operator = GraphUpdateOperator(
            edge_half_life_days=30.0,
            edge_prune_threshold=0.1,
            merge_similarity_threshold=0.9
        )

        # Apply transformation
        G_next = operator.apply(
            graph=G_t,
            action_type=GraphActionType.ADD_EDGE,
            observation={"edge_data": {...}},
            parameters={}
        )

        # Analyze convergence
        convergence = operator.analyze_convergence(graph_history)
    """

    def __init__(
        self,
        edge_half_life_days: float = 30.0,
        edge_prune_threshold: float = 0.1,
        merge_similarity_threshold: float = 0.9,
    ):
        """
        Initialize graph operator.

        Args:
            edge_half_life_days: Half-life for edge weight decay (exponential decay)
            edge_prune_threshold: Below this weight, edges are pruned
            merge_similarity_threshold: Above this similarity, nodes are merged
        """
        self.edge_half_life_days = edge_half_life_days
        self.edge_prune_threshold = edge_prune_threshold
        self.merge_similarity_threshold = merge_similarity_threshold

        logger.info(
            "graph_operator_initialized",
            edge_half_life_days=edge_half_life_days,
            edge_prune_threshold=edge_prune_threshold,
            merge_similarity_threshold=merge_similarity_threshold,
        )

    def apply(
        self,
        graph: KnowledgeGraph,
        action_type: GraphActionType,
        observation: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeGraph:
        """
        Apply graph transformation: G_{t+1} = T(G_t, o_t, a_t)

        This is the core transformation function T.

        Args:
            graph: Current graph state G_t
            action_type: Type of transformation (a_t)
            observation: Observation o_t (new data)
            parameters: Optional action parameters

        Returns:
            New graph state G_{t+1}
        """
        with tracer.start_as_current_span("rae.graph.transform") as span:
            # Validate action_type is a GraphActionType enum
            if not isinstance(action_type, GraphActionType):
                raise ValueError(
                    f"action_type must be GraphActionType enum, got {type(action_type)}"
                )

            parameters = parameters or {}

            span.set_attribute("rae.graph.action_type", action_type.value)
            span.set_attribute("rae.tenant_id", graph.tenant_id)
            span.set_attribute("rae.project_id", graph.project_id)
            span.set_attribute("rae.graph.nodes_before", len(graph.nodes))
            span.set_attribute("rae.graph.edges_before", len(graph.edges))

            logger.info(
                "graph_transformation_started",
                action_type=action_type.value,
                nodes_before=len(graph.nodes),
                edges_before=len(graph.edges),
            )

            # Copy graph (immutable transformation)
            G_next = graph.copy()

            # Apply transformation based on action type
            from apps.memory_api.core import graph_transformations as ops

            if action_type == GraphActionType.ADD_NODE:
                G_next = ops.add_node(
                    G_next, observation, parameters, self._find_duplicate_node
                )

            elif action_type == GraphActionType.ADD_EDGE:
                G_next = ops.add_edge(G_next, observation, parameters)

            elif action_type == GraphActionType.UPDATE_EDGE_WEIGHT:
                G_next = ops.update_edge_weight(
                    G_next, self.edge_half_life_days, self.edge_prune_threshold
                )

            elif action_type == GraphActionType.MERGE_NODES:
                G_next = ops.merge_nodes(G_next, parameters)

            elif action_type == GraphActionType.PRUNE_NODE:
                G_next = ops.prune_node(G_next, parameters)

            elif action_type == GraphActionType.PRUNE_EDGE:
                G_next = ops.prune_edge(G_next, parameters)

            else:
                span.set_attribute("rae.outcome.label", "fail")
                raise ValueError(f"Unknown action type: {action_type}")

            # Update timestamp
            G_next.last_updated = datetime.now()

            nodes_delta = len(G_next.nodes) - len(graph.nodes)
            edges_delta = len(G_next.edges) - len(graph.edges)

            span.set_attribute("rae.graph.nodes_after", len(G_next.nodes))
            span.set_attribute("rae.graph.edges_after", len(G_next.edges))
            span.set_attribute("rae.graph.nodes_delta", nodes_delta)
            span.set_attribute("rae.graph.edges_delta", edges_delta)
            span.set_attribute("rae.outcome.label", "success")

            logger.info(
                "graph_transformation_completed",
                action_type=action_type.value,
                nodes_after=len(G_next.nodes),
                edges_after=len(G_next.edges),
                nodes_delta=nodes_delta,
                edges_delta=edges_delta,
            )

            return G_next

    def _find_duplicate_node(
        self,
        graph: KnowledgeGraph,
        label: str,
        similarity_threshold: Optional[float] = None,
    ) -> Optional[GraphNode]:
        """
        Find node with similar label (for duplicate detection).

        Currently uses exact string matching (case-insensitive).
        Future: Use embedding similarity for semantic matching.

        Args:
            graph: Current graph
            label: Node label to search for
            similarity_threshold: Optional similarity threshold (reserved for future use)

        Returns:
            Duplicate node if found, None otherwise
        """
        # Simple exact match for now
        # TODO: Use embedding similarity for semantic matching with similarity_threshold
        for node in graph.nodes.values():
            if node.label.lower() == label.lower():
                return node

        return None

    def analyze_convergence(
        self, graph_history: List[KnowledgeGraph]
    ) -> Dict[str, Any]:
        """
        Analyze whether graph is converging to stable structure.

        Convergence metrics:
          1. Node churn rate: Avg additions/deletions per timestep
          2. Edge churn rate: Avg additions/deletions per timestep
          3. Spectral gap: λ_1 - λ_2 from adjacency matrix eigenvalues
          4. Clustering coefficient variance

        Convergence criteria:
          - Node churn < 5 per timestep
          - Edge churn < 10 per timestep
          - Spectral gap < 0.5

        Args:
            graph_history: List of graph snapshots over time

        Returns:
            Dictionary with convergence metrics and is_converging flag
        """
        with tracer.start_as_current_span("rae.graph.analyze_convergence") as span:
            span.set_attribute("rae.graph.history_length", len(graph_history))

            if len(graph_history) < 2:
                span.set_attribute(
                    "rae.graph.convergence_result", "insufficient_history"
                )
                span.set_attribute("rae.outcome.label", "fail")
                return {
                    "is_converging": False,
                    "reason": "insufficient_history",
                    "history_length": len(graph_history),
                }

            # Node churn
            node_counts = [len(g.nodes) for g in graph_history]
            node_deltas = [
                abs(node_counts[i + 1] - node_counts[i])
                for i in range(len(node_counts) - 1)
            ]
            node_churn = float(np.mean(node_deltas)) if node_deltas else 0.0
            span.set_attribute("rae.graph.node_churn", node_churn)

            # Edge churn
            edge_counts = [len(g.edges) for g in graph_history]
            edge_deltas = [
                abs(edge_counts[i + 1] - edge_counts[i])
                for i in range(len(edge_counts) - 1)
            ]
            edge_churn = float(np.mean(edge_deltas)) if edge_deltas else 0.0
            span.set_attribute("rae.graph.edge_churn", edge_churn)

            # Spectral gap (from latest graph)
            latest_graph = graph_history[-1]
            spectral_gap = 0.0

            span.set_attribute("rae.tenant_id", latest_graph.tenant_id)
            span.set_attribute("rae.project_id", latest_graph.project_id)
            span.set_attribute("rae.graph.node_count", len(latest_graph.nodes))
            span.set_attribute("rae.graph.edge_count", len(latest_graph.edges))

            if len(latest_graph.nodes) > 1:
                adj_matrix = latest_graph.adjacency_matrix()

                if adj_matrix.size > 0:
                    try:
                        eigenvalues = np.linalg.eigvals(adj_matrix)
                        eigenvalues_sorted = np.sort(np.abs(eigenvalues))[::-1]

                        if len(eigenvalues_sorted) >= 2:
                            spectral_gap = float(
                                eigenvalues_sorted[0] - eigenvalues_sorted[1]
                            )
                            span.set_attribute(
                                "rae.graph.eigenvalue_1", float(eigenvalues_sorted[0])
                            )
                            span.set_attribute(
                                "rae.graph.eigenvalue_2", float(eigenvalues_sorted[1])
                            )
                    except Exception as e:
                        logger.warning("spectral_gap_computation_failed", error=str(e))
                        spectral_gap = 0.0

            span.set_attribute("rae.graph.spectral_gap", spectral_gap)

            # Convergence criteria
            # For true convergence, we want very low churn (approaching stability)
            is_converging = (
                node_churn < 1.0  # Less than 1 node added/removed per step
                and edge_churn < 2.0  # Less than 2 edges added/removed per step
                and spectral_gap < 0.5  # Stable eigenvalue spectrum
            )

            span.set_attribute("rae.graph.is_converging", is_converging)
            span.set_attribute(
                "rae.outcome.label", "success" if is_converging else "not_converged"
            )

            return {
                "is_converging": is_converging,
                "node_churn": node_churn,
                "edge_churn": edge_churn,
                "spectral_gap": spectral_gap,
                "node_count": len(latest_graph.nodes),
                "edge_count": len(latest_graph.edges),
                "history_length": len(graph_history),
            }
