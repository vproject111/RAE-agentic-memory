"""
Additional coverage tests for graph_operator.py to hit edge cases.
"""

from unittest.mock import patch

import pytest

from apps.memory_api.core.graph_operator import (
    GraphActionType,
    GraphEdge,
    GraphNode,
    GraphUpdateOperator,
    KnowledgeGraph,
)


@pytest.fixture
def graph_operator():
    return GraphUpdateOperator()


@pytest.fixture
def empty_graph():
    return KnowledgeGraph(tenant_id="test", project_id="test")


@pytest.mark.unit
def test_add_node_missing_data(graph_operator, empty_graph):
    # Line 352: if not node_data
    new_graph = graph_operator.apply(
        graph=empty_graph,
        action_type=GraphActionType.ADD_NODE,
        observation={},
        parameters={},
    )
    assert len(new_graph.nodes) == 0


@pytest.mark.unit
def test_add_edge_missing_data(graph_operator, empty_graph):
    # Lines 442-443: if not edge_data
    new_graph = graph_operator.apply(
        graph=empty_graph,
        action_type=GraphActionType.ADD_EDGE,
        observation={},
        parameters={},
    )
    assert len(new_graph.edges) == 0


@pytest.mark.unit
def test_merge_nodes_missing_ids(graph_operator, empty_graph):
    # Lines 578-579: if not node1_id or not node2_id
    new_graph = graph_operator.apply(
        graph=empty_graph,
        action_type=GraphActionType.MERGE_NODES,
        observation={},
        parameters={"node1_id": "n1"},  # missing node2_id
    )
    # Should return graph unchanged (nodes and edges same)
    # Note: apply() updates last_updated, so direct object comparison fails
    assert new_graph.nodes == empty_graph.nodes
    assert new_graph.edges == empty_graph.edges


@pytest.mark.unit
def test_merge_nodes_edge_redirect_and_cleanup(graph_operator, empty_graph):
    # Lines 609-611: Edge ID update and cleanup

    # Setup graph: N1, N2, N3. Edge N2->N3.
    # Merge N2 into N1. Edge becomes N1->N3.

    n1 = GraphNode(id="n1", label="Node 1", node_type="entity")
    n2 = GraphNode(id="n2", label="Node 2", node_type="entity")
    n3 = GraphNode(id="n3", label="Node 3", node_type="entity")

    e_2_3 = GraphEdge(
        id="n2_rel_n3", source_id="n2", target_id="n3", relation="rel", weight=0.5
    )

    graph = empty_graph
    graph.nodes = {"n1": n1, "n2": n2, "n3": n3}
    graph.edges = {"n2_rel_n3": e_2_3}

    new_graph = graph_operator.apply(
        graph=graph,
        action_type=GraphActionType.MERGE_NODES,
        observation={},
        parameters={"node1_id": "n1", "node2_id": "n2"},
    )

    # N2 should be gone
    assert "n2" not in new_graph.nodes

    # Edge should be redirected: n1_rel_n3
    assert "n1_rel_n3" in new_graph.edges
    assert new_graph.edges["n1_rel_n3"].source_id == "n1"

    # Old edge ID should be gone (Line 611 check)
    assert "n2_rel_n3" not in new_graph.edges


@pytest.mark.unit
def test_analyze_convergence_exception_handling(graph_operator):
    # Lines 800-802: Exception handling in spectral gap

    g1 = KnowledgeGraph()
    n1 = GraphNode(id="n1", label="n1", node_type="e")
    n2 = GraphNode(id="n2", label="n2", node_type="e")
    g1.nodes = {"n1": n1, "n2": n2}  # Needs >1 node

    with patch("numpy.linalg.eigvals", side_effect=Exception("Math error")):
        result = graph_operator.analyze_convergence([g1, g1])  # Need >= 2 history

        # Should catch exception and set spectral_gap = 0.0
        assert result["spectral_gap"] == 0.0
