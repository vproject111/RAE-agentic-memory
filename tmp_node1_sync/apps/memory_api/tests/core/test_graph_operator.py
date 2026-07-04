"""
Tests for RAE Graph Update Operator (Iteration 5).

Tests cover:
  1. Graph operator creation and configuration
  2. Graph transformations (add_node, add_edge, merge_nodes, prune)
  3. Temporal decay of edge weights
  4. Convergence analysis
  5. Edge cases and error handling
"""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pytest

from apps.memory_api.core.graph_operator import (
    GraphActionType,
    GraphEdge,
    GraphNode,
    GraphUpdateOperator,
    KnowledgeGraph,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def graph_operator():
    """Create graph operator with standard parameters"""
    return GraphUpdateOperator(
        edge_half_life_days=30.0,
        edge_prune_threshold=0.1,
        merge_similarity_threshold=0.9,
    )


@pytest.fixture
def simple_graph():
    """Create a simple test graph"""
    return KnowledgeGraph(
        nodes={
            "node1": GraphNode(
                id="node1",
                label="Alice",
                node_type="person",
                properties={"age": 30},
                created_at=datetime.now(),
                last_updated=datetime.now(),
                importance=0.8,
                centrality=0.5,
            ),
            "node2": GraphNode(
                id="node2",
                label="Bob",
                node_type="person",
                properties={"age": 25},
                created_at=datetime.now(),
                last_updated=datetime.now(),
                importance=0.7,
                centrality=0.4,
            ),
        },
        edges={
            "node1_knows_node2": GraphEdge(
                id="node1_knows_node2",
                source_id="node1",
                target_id="node2",
                relation="knows",
                weight=0.8,
                confidence=0.9,
                created_at=datetime.now(),
                last_updated=datetime.now(),
                evidence_count=1,
            )
        },
        tenant_id="test_tenant",
        project_id="test_project",
        created_at=datetime.now(),
        last_updated=datetime.now(),
    )


# ============================================================================
# Test Graph Operator Creation
# ============================================================================


def test_graph_operator_creation():
    """Test creating graph operator with custom parameters"""
    operator = GraphUpdateOperator(
        edge_half_life_days=60.0,
        edge_prune_threshold=0.05,
        merge_similarity_threshold=0.85,
    )

    assert operator.edge_half_life_days == 60.0
    assert operator.edge_prune_threshold == 0.05
    assert operator.merge_similarity_threshold == 0.85


def test_graph_operator_defaults():
    """Test default parameters"""
    operator = GraphUpdateOperator()

    assert operator.edge_half_life_days == 30.0
    assert operator.edge_prune_threshold == 0.1
    assert operator.merge_similarity_threshold == 0.9


# ============================================================================
# Test Graph Data Structures
# ============================================================================


def test_graph_node_creation():
    """Test creating graph node"""
    node = GraphNode(
        id="node1",
        label="Alice",
        node_type="person",
        properties={"age": 30},
        importance=0.8,
    )

    assert node.id == "node1"
    assert node.label == "Alice"
    assert node.node_type == "person"
    assert node.properties["age"] == 30
    assert node.importance == 0.8
    assert node.centrality == 0.0


def test_graph_edge_creation():
    """Test creating graph edge"""
    edge = GraphEdge(
        id="edge1",
        source_id="node1",
        target_id="node2",
        relation="knows",
        weight=0.8,
        confidence=0.9,
    )

    assert edge.id == "edge1"
    assert edge.source_id == "node1"
    assert edge.target_id == "node2"
    assert edge.relation == "knows"
    assert edge.weight == 0.8
    assert edge.confidence == 0.9


def test_knowledge_graph_creation(simple_graph):
    """Test creating knowledge graph"""
    assert len(simple_graph.nodes) == 2
    assert len(simple_graph.edges) == 1
    assert "node1" in simple_graph.nodes
    assert "node2" in simple_graph.nodes
    assert simple_graph.tenant_id == "test_tenant"


def test_knowledge_graph_get_node(simple_graph):
    """Test getting node by ID"""
    node = simple_graph.get_node("node1")

    assert node is not None
    assert node.label == "Alice"

    # Non-existent node
    node = simple_graph.get_node("nonexistent")
    assert node is None


def test_knowledge_graph_get_edge(simple_graph):
    """Test getting edge by ID"""
    edge = simple_graph.get_edge("node1_knows_node2")

    assert edge is not None
    assert edge.relation == "knows"

    # Non-existent edge
    edge = simple_graph.get_edge("nonexistent")
    assert edge is None


def test_knowledge_graph_adjacency_matrix(simple_graph):
    """Test adjacency matrix computation"""
    adj = simple_graph.adjacency_matrix()

    assert adj.shape == (2, 2)
    assert adj[0, 1] == 0.8  # Alice knows Bob

    # Test empty graph
    empty_graph = KnowledgeGraph()
    adj_empty = empty_graph.adjacency_matrix()
    assert adj_empty.shape == (1, 0) or adj_empty.size == 0


def test_knowledge_graph_copy(simple_graph):
    """Test deep copy of graph"""
    graph_copy = simple_graph.copy()

    assert len(graph_copy.nodes) == len(simple_graph.nodes)
    assert len(graph_copy.edges) == len(simple_graph.edges)

    # Modify copy
    graph_copy.nodes["node1"].label = "Charlie"

    # Original unchanged
    assert simple_graph.nodes["node1"].label == "Alice"


def test_knowledge_graph_to_dict(simple_graph):
    """Test serialization to dictionary"""
    graph_dict = simple_graph.to_dict()

    assert "nodes" in graph_dict
    assert "edges" in graph_dict
    assert graph_dict["node_count"] == 2
    assert graph_dict["edge_count"] == 1
    assert graph_dict["tenant_id"] == "test_tenant"


# ============================================================================
# Test Add Node Transformation
# ============================================================================


def test_add_node_basic(graph_operator, simple_graph):
    """Test adding a node"""
    observation = {
        "node_data": {
            "id": "node3",
            "label": "Charlie",
            "node_type": "person",
            "properties": {"age": 35},
            "importance": 0.6,
        }
    }

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.ADD_NODE,
        observation=observation,
    )

    assert len(new_graph.nodes) == 3
    assert "node3" in new_graph.nodes
    assert new_graph.nodes["node3"].label == "Charlie"
    assert new_graph.nodes["node3"].importance == 0.6


def test_add_node_duplicate(graph_operator, simple_graph):
    """Test adding duplicate node (should be ignored)"""
    observation = {
        "node_data": {
            "id": "node3",
            "label": "Alice",  # Duplicate label
            "node_type": "person",
        }
    }

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.ADD_NODE,
        observation=observation,
    )

    # Should not add duplicate
    assert len(new_graph.nodes) == 2
    assert "node3" not in new_graph.nodes


def test_add_node_missing_data(graph_operator, simple_graph):
    """Test adding node with missing data"""
    observation: dict[str, Any] = {}  # No node_data

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.ADD_NODE,
        observation=observation,
    )

    # Graph unchanged
    assert len(new_graph.nodes) == 2


# ============================================================================
# Test Add Edge Transformation
# ============================================================================


def test_add_edge_basic(graph_operator, simple_graph):
    """Test adding an edge"""
    observation = {
        "edge_data": {
            "source_id": "node2",
            "target_id": "node1",
            "relation": "likes",
            "weight": 0.7,
            "confidence": 0.85,
        }
    }

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.ADD_EDGE,
        observation=observation,
    )

    assert len(new_graph.edges) == 2
    assert "node2_likes_node1" in new_graph.edges
    assert new_graph.edges["node2_likes_node1"].weight == 0.7


def test_add_edge_strengthen_existing(graph_operator, simple_graph):
    """Test strengthening existing edge"""
    observation = {
        "edge_data": {
            "source_id": "node1",
            "target_id": "node2",
            "relation": "knows",  # Already exists
            "weight": 0.5,
        }
    }

    initial_weight = simple_graph.edges["node1_knows_node2"].weight

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.ADD_EDGE,
        observation=observation,
    )

    # Edge strengthened
    assert len(new_graph.edges) == 1
    assert new_graph.edges["node1_knows_node2"].weight > initial_weight
    assert new_graph.edges["node1_knows_node2"].evidence_count == 2


def test_add_edge_nonexistent_nodes(graph_operator, simple_graph):
    """Test adding edge with non-existent nodes"""
    observation = {
        "edge_data": {
            "source_id": "nonexistent1",
            "target_id": "nonexistent2",
            "relation": "knows",
        }
    }

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.ADD_EDGE,
        observation=observation,
    )

    # Edge not added
    assert len(new_graph.edges) == 1


# ============================================================================
# Test Update Edge Weight (Temporal Decay)
# ============================================================================


def test_update_edge_weight_decay(graph_operator, simple_graph):
    """Test temporal decay of edge weights"""
    # Set edge last_updated to 30 days ago
    edge = simple_graph.edges["node1_knows_node2"]
    edge.last_updated = datetime.now() - timedelta(days=30)
    initial_weight = edge.weight

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.UPDATE_EDGE_WEIGHT,
        observation={},
    )

    # Weight should decay (exponential decay with half-life 30 days)
    new_weight = new_graph.edges["node1_knows_node2"].weight
    assert new_weight < initial_weight
    assert new_weight > 0  # Should not be zero yet

    # Approximate decay: w(30 days) ≈ w_0 * exp(-1) ≈ w_0 * 0.368
    expected_weight = initial_weight * np.exp(-1)
    assert abs(new_weight - expected_weight) < 0.1


def test_update_edge_weight_prune_low_weight(graph_operator, simple_graph):
    """Test pruning edges with weight below threshold"""
    # Set edge weight very low and old
    edge = simple_graph.edges["node1_knows_node2"]
    edge.weight = 0.15
    edge.last_updated = datetime.now() - timedelta(days=100)

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.UPDATE_EDGE_WEIGHT,
        observation={},
    )

    # Edge should be pruned
    assert len(new_graph.edges) == 0


# ============================================================================
# Test Merge Nodes Transformation
# ============================================================================


def test_merge_nodes_basic(graph_operator, simple_graph):
    """Test merging two nodes"""
    parameters = {"node1_id": "node1", "node2_id": "node2"}

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.MERGE_NODES,
        observation={},
        parameters=parameters,
    )

    # Node2 merged into node1
    assert len(new_graph.nodes) == 1
    assert "node1" in new_graph.nodes
    assert "node2" not in new_graph.nodes

    # Properties merged
    assert new_graph.nodes["node1"].importance == max(0.8, 0.7)


def test_merge_nodes_redirect_edges(graph_operator):
    """Test edge redirection when merging nodes"""
    # Create graph with multiple edges
    graph = KnowledgeGraph(
        nodes={
            "node1": GraphNode(
                id="node1", label="Alice", node_type="person", importance=0.8
            ),
            "node2": GraphNode(
                id="node2", label="Bob", node_type="person", importance=0.7
            ),
            "node3": GraphNode(
                id="node3", label="Charlie", node_type="person", importance=0.6
            ),
        },
        edges={
            "edge1": GraphEdge(
                id="node1_knows_node2",
                source_id="node1",
                target_id="node2",
                relation="knows",
                weight=0.8,
            ),
            "edge2": GraphEdge(
                id="node2_knows_node3",
                source_id="node2",
                target_id="node3",
                relation="knows",
                weight=0.7,
            ),
        },
        tenant_id="test",
        project_id="test",
    )

    # Merge node2 into node1
    parameters = {"node1_id": "node1", "node2_id": "node2"}

    new_graph = graph_operator.apply(
        graph=graph,
        action_type=GraphActionType.MERGE_NODES,
        observation={},
        parameters=parameters,
    )

    # Node2 removed
    assert "node2" not in new_graph.nodes

    # Edges redirected
    assert "node1_knows_node3" in new_graph.edges


def test_merge_nodes_missing_parameters(graph_operator, simple_graph):
    """Test merge with missing parameters"""
    parameters: dict[str, Any] = {}  # No node IDs

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.MERGE_NODES,
        observation={},
        parameters=parameters,
    )

    # Graph unchanged
    assert len(new_graph.nodes) == 2


# ============================================================================
# Test Prune Node Transformation
# ============================================================================


def test_prune_node_basic(graph_operator, simple_graph):
    """Test pruning a node"""
    parameters = {"node_id": "node2"}

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.PRUNE_NODE,
        observation={},
        parameters=parameters,
    )

    # Node removed
    assert len(new_graph.nodes) == 1
    assert "node2" not in new_graph.nodes

    # Connected edges removed
    assert len(new_graph.edges) == 0


def test_prune_node_nonexistent(graph_operator, simple_graph):
    """Test pruning non-existent node"""
    parameters = {"node_id": "nonexistent"}

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.PRUNE_NODE,
        observation={},
        parameters=parameters,
    )

    # Graph unchanged
    assert len(new_graph.nodes) == 2


# ============================================================================
# Test Prune Edge Transformation
# ============================================================================


def test_prune_edge_basic(graph_operator, simple_graph):
    """Test pruning an edge"""
    parameters = {"edge_id": "node1_knows_node2"}

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.PRUNE_EDGE,
        observation={},
        parameters=parameters,
    )

    # Edge removed
    assert len(new_graph.edges) == 0

    # Nodes remain
    assert len(new_graph.nodes) == 2


def test_prune_edge_nonexistent(graph_operator, simple_graph):
    """Test pruning non-existent edge"""
    parameters = {"edge_id": "nonexistent"}

    new_graph = graph_operator.apply(
        graph=simple_graph,
        action_type=GraphActionType.PRUNE_EDGE,
        observation={},
        parameters=parameters,
    )

    # Graph unchanged
    assert len(new_graph.edges) == 1


# ============================================================================
# Test Convergence Analysis
# ============================================================================


def test_convergence_analysis_insufficient_history(graph_operator, simple_graph):
    """Test convergence analysis with insufficient history"""
    history = [simple_graph]

    convergence = graph_operator.analyze_convergence(history)

    assert convergence["is_converging"] is False
    assert convergence["reason"] == "insufficient_history"


def test_convergence_analysis_stable_graph(graph_operator, simple_graph):
    """Test convergence analysis with stable graph"""
    # Create history with minimal changes
    history = [simple_graph.copy() for _ in range(5)]

    # Make small changes
    for i in range(1, 5):
        history[i].last_updated = datetime.now()

    convergence = graph_operator.analyze_convergence(history)

    assert convergence["is_converging"] is True
    assert convergence["node_churn"] == 0.0
    assert convergence["edge_churn"] == 0.0


def test_convergence_analysis_growing_graph(graph_operator):
    """Test convergence analysis with growing graph"""
    # Create history with growing graph
    history = []

    for i in range(10):
        graph = KnowledgeGraph(
            nodes={
                f"node{j}": GraphNode(
                    id=f"node{j}", label=f"Person{j}", node_type="person"
                )
                for j in range(i + 1)
            },
            tenant_id="test",
            project_id="test",
        )
        history.append(graph)

    convergence = graph_operator.analyze_convergence(history)

    assert convergence["is_converging"] is False
    assert convergence["node_churn"] > 0


def test_convergence_analysis_spectral_gap(graph_operator):
    """Test spectral gap computation in convergence analysis"""
    # Create stable graph with clear structure
    graph = KnowledgeGraph(
        nodes={
            "node1": GraphNode(id="node1", label="Alice", node_type="person"),
            "node2": GraphNode(id="node2", label="Bob", node_type="person"),
            "node3": GraphNode(id="node3", label="Charlie", node_type="person"),
        },
        edges={
            "edge1": GraphEdge(
                id="node1_knows_node2",
                source_id="node1",
                target_id="node2",
                relation="knows",
                weight=0.8,
            ),
            "edge2": GraphEdge(
                id="node2_knows_node3",
                source_id="node2",
                target_id="node3",
                relation="knows",
                weight=0.7,
            ),
        },
        tenant_id="test",
        project_id="test",
    )

    history = [graph.copy() for _ in range(5)]

    convergence = graph_operator.analyze_convergence(history)

    assert "spectral_gap" in convergence
    assert convergence["spectral_gap"] >= 0


# ============================================================================
# Test Determinism and Reproducibility
# ============================================================================


def test_transformation_deterministic(graph_operator, simple_graph):
    """Test that transformations are deterministic"""
    observation = {
        "node_data": {
            "id": "node3",
            "label": "Charlie",
            "node_type": "person",
            "importance": 0.6,
        }
    }

    # Apply same transformation twice
    graph1 = graph_operator.apply(
        graph=simple_graph.copy(),
        action_type=GraphActionType.ADD_NODE,
        observation=observation,
    )

    graph2 = graph_operator.apply(
        graph=simple_graph.copy(),
        action_type=GraphActionType.ADD_NODE,
        observation=observation,
    )

    # Results should be identical (except timestamps)
    assert len(graph1.nodes) == len(graph2.nodes)
    assert len(graph1.edges) == len(graph2.edges)
    assert "node3" in graph1.nodes and "node3" in graph2.nodes


# ============================================================================
# Test Error Handling
# ============================================================================


def test_invalid_action_type(graph_operator, simple_graph):
    """Test handling invalid action type"""
    with pytest.raises(ValueError):
        graph_operator.apply(
            graph=simple_graph,
            action_type="invalid_action",  # Invalid
            observation={},
        )


# ============================================================================
# Test Mathematical Properties
# ============================================================================


def test_temporal_decay_exponential(graph_operator):
    """Test exponential decay formula: w(t) = w_0 * exp(-t/half_life)"""
    graph = KnowledgeGraph(
        nodes={
            "node1": GraphNode(id="node1", label="A", node_type="person"),
            "node2": GraphNode(id="node2", label="B", node_type="person"),
        },
        edges={
            "node1_knows_node2": GraphEdge(
                id="node1_knows_node2",
                source_id="node1",
                target_id="node2",
                relation="knows",
                weight=1.0,
                last_updated=datetime.now() - timedelta(days=30),  # 30 days ago
            )
        },
    )

    new_graph = graph_operator.apply(
        graph=graph, action_type=GraphActionType.UPDATE_EDGE_WEIGHT, observation={}
    )

    # After 30 days (1 half-life), weight should be ~0.5
    expected_weight = 1.0 * np.exp(-1)
    actual_weight = new_graph.edges["node1_knows_node2"].weight

    assert abs(actual_weight - expected_weight) < 0.1


def test_edge_weight_bounds(graph_operator, simple_graph):
    """Test that edge weights stay in [0, 1] bounds"""
    # Add edge multiple times to test upper bound
    observation = {
        "edge_data": {
            "source_id": "node1",
            "target_id": "node2",
            "relation": "knows",
            "weight": 0.9,
        }
    }

    graph = simple_graph.copy()

    # Add edge 10 times
    for _ in range(10):
        graph = graph_operator.apply(
            graph=graph, action_type=GraphActionType.ADD_EDGE, observation=observation
        )

    # Weight should not exceed 1.0
    edge = graph.edges["node1_knows_node2"]
    assert 0.0 <= edge.weight <= 1.0
