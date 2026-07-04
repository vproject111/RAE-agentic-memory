"""
Graph Transformation Logic.
Extracted from graph_operator.py to reduce file size.
"""

from datetime import datetime
from typing import Any, Dict

import numpy as np
import structlog

from apps.memory_api.core.graph_operator import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
)

logger = structlog.get_logger(__name__)


def add_node(
    graph: KnowledgeGraph,
    observation: Dict[str, Any],
    parameters: Dict[str, Any],
    find_duplicate_fn: Any,
) -> KnowledgeGraph:
    """
    Add new node to graph.
    """
    node_data = observation.get("node_data") or parameters.get("node_data")

    if not node_data:
        logger.warning("add_node_missing_data")
        return graph

    # Check for duplicates
    existing = find_duplicate_fn(graph, node_data["label"])
    if existing:
        logger.info("node_already_exists", node_id=existing.id, label=existing.label)
        return graph

    # Create new node
    node = GraphNode(
        id=node_data.get("id", f"node_{len(graph.nodes)}"),
        label=node_data["label"],
        node_type=node_data.get("node_type", "entity"),
        properties=node_data.get("properties", {}),
        created_at=datetime.now(),
        last_updated=datetime.now(),
        importance=node_data.get("importance", 0.5),
        centrality=0.0,  # Will be computed later
    )

    graph.nodes[node.id] = node

    logger.debug("node_added", node_id=node.id, label=node.label)

    return graph


def add_edge(
    graph: KnowledgeGraph,
    observation: Dict[str, Any],
    parameters: Dict[str, Any],
) -> KnowledgeGraph:
    """
    Add or strengthen edge.
    """
    edge_data = observation.get("edge_data") or parameters.get("edge_data")

    if not edge_data:
        logger.warning("add_edge_missing_data")
        return graph

    source_id = edge_data["source_id"]
    target_id = edge_data["target_id"]
    relation = edge_data["relation"]

    # Check nodes exist
    if source_id not in graph.nodes or target_id not in graph.nodes:
        logger.warning("edge_nodes_not_found", source=source_id, target=target_id)
        return graph

    # Check if edge already exists
    edge_id = f"{source_id}_{relation}_{target_id}"
    existing_edge = graph.edges.get(edge_id)

    if existing_edge:
        # Strengthen existing edge
        existing_edge.weight = min(1.0, existing_edge.weight + 0.1)
        existing_edge.evidence_count += 1
        existing_edge.last_updated = datetime.now()

        logger.debug(
            "edge_strengthened",
            edge_id=edge_id,
            new_weight=existing_edge.weight,
            evidence_count=existing_edge.evidence_count,
        )
    else:
        # Create new edge
        edge = GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=edge_data.get("weight", 0.7),
            confidence=edge_data.get("confidence", 0.8),
            created_at=datetime.now(),
            last_updated=datetime.now(),
            evidence_count=1,
        )

        graph.edges[edge_id] = edge

        logger.debug("edge_added", edge_id=edge_id, weight=edge.weight)

    return graph


def update_edge_weight(
    graph: KnowledgeGraph,
    edge_half_life_days: float,
    edge_prune_threshold: float,
) -> KnowledgeGraph:
    """
    Update edge weights with temporal decay.
    """
    now = datetime.now()

    edges_to_remove = []

    for edge_id, edge in graph.edges.items():
        # Temporal decay: w(t) = w(t_0) * exp(-Δt / half_life)
        time_delta_days = (now - edge.last_updated).total_seconds() / 86400
        decay = np.exp(-time_delta_days / edge_half_life_days)

        # Apply decay
        edge.weight = edge.weight * decay

        # Mark for pruning if below threshold
        if edge.weight < edge_prune_threshold:
            edges_to_remove.append(edge_id)

    # Remove pruned edges
    for edge_id in edges_to_remove:
        del graph.edges[edge_id]
        logger.debug("edge_pruned_by_decay", edge_id=edge_id)

    logger.info(
        "edge_weights_updated",
        edges_total=len(graph.edges),
        edges_pruned=len(edges_to_remove),
    )

    return graph


def merge_nodes(
    graph: KnowledgeGraph,
    parameters: Dict[str, Any],
) -> KnowledgeGraph:
    """
    Merge duplicate nodes.
    """
    node1_id = parameters.get("node1_id")
    node2_id = parameters.get("node2_id")

    if not node1_id or not node2_id:
        logger.warning("merge_nodes_missing_ids")
        return graph

    node1 = graph.nodes.get(node1_id)
    node2 = graph.nodes.get(node2_id)

    if not node1 or not node2:
        logger.warning("merge_nodes_not_found")
        return graph

    # Create merged node (keep node1, merge properties)
    node1.properties.update(node2.properties)
    node1.importance = max(node1.importance, node2.importance)
    node1.last_updated = datetime.now()

    # Remove node2
    del graph.nodes[node2_id]

    # Redirect all edges from node2 to node1
    edges_to_update = []
    for edge_id, edge in graph.edges.items():
        if edge.source_id == node2_id:
            edges_to_update.append((edge_id, "source"))
        elif edge.target_id == node2_id:
            edges_to_update.append((edge_id, "target"))

    for edge_id, direction in edges_to_update:
        edge = graph.edges[edge_id]

        # Create new edge ID
        if direction == "source":
            new_edge_id = f"{node1_id}_{edge.relation}_{edge.target_id}"
        else:
            new_edge_id = f"{edge.source_id}_{edge.relation}_{node1_id}"

        # Check if edge already exists
        if new_edge_id in graph.edges:
            # Merge weights
            existing = graph.edges[new_edge_id]
            existing.weight = min(1.0, existing.weight + edge.weight)
            existing.evidence_count += edge.evidence_count
        else:
            # Update edge
            if direction == "source":
                edge.source_id = node1_id
            else:
                edge.target_id = node1_id

            edge.id = new_edge_id
            graph.edges[new_edge_id] = edge

        # Remove old edge
        if edge_id != new_edge_id:
            del graph.edges[edge_id]

    logger.info(
        "nodes_merged",
        node1=node1_id,
        node2=node2_id,
        edges_redirected=len(edges_to_update),
    )

    return graph


def prune_node(
    graph: KnowledgeGraph,
    parameters: Dict[str, Any],
) -> KnowledgeGraph:
    """
    Remove low-value node.
    """
    node_id = parameters.get("node_id")

    if not node_id or node_id not in graph.nodes:
        logger.warning("prune_node_not_found", node_id=node_id)
        return graph

    # Remove node
    del graph.nodes[node_id]

    # Remove all edges connected to this node
    edges_to_remove = [
        edge_id
        for edge_id, edge in graph.edges.items()
        if edge.source_id == node_id or edge.target_id == node_id
    ]

    for edge_id in edges_to_remove:
        del graph.edges[edge_id]

    logger.info(
        "node_pruned",
        node_id=node_id,
        edges_removed=len(edges_to_remove),
    )

    return graph


def prune_edge(
    graph: KnowledgeGraph,
    parameters: Dict[str, Any],
) -> KnowledgeGraph:
    """
    Remove specific edge.
    """
    edge_id = parameters.get("edge_id")

    if not edge_id or edge_id not in graph.edges:
        logger.warning("prune_edge_not_found", edge_id=edge_id)
        return graph

    del graph.edges[edge_id]

    logger.debug("edge_pruned", edge_id=edge_id)

    return graph
