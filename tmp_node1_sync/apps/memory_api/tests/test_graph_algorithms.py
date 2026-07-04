from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.graph_algorithms import (
    GraphAlgorithmsService,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
)


@pytest.mark.asyncio
async def test_graph_node():
    node = GraphNode("n1", "Person", {"name": "Alice"})
    assert node.id == "n1"
    assert node.entity_type == "Person"
    assert node.properties["name"] == "Alice"
    assert node.get_neighbors() == []

    edge = GraphEdge("n1", "n2", "knows")
    node.add_edge(edge)
    assert node.get_neighbors() == ["n2"]


@pytest.mark.asyncio
async def test_graph_edge():
    edge = GraphEdge("n1", "n2", "knows", 0.5, {"since": 2020})
    assert edge.source_id == "n1"
    assert edge.target_id == "n2"
    assert edge.relation_type == "knows"
    assert edge.weight == 0.5
    assert edge.properties["since"] == 2020


@pytest.mark.asyncio
async def test_knowledge_graph():
    graph = KnowledgeGraph()
    node1 = GraphNode("n1", "Person")
    node2 = GraphNode("n2", "Person")
    edge = GraphEdge("n1", "n2", "knows")

    graph.add_node(node1)
    graph.add_node(node2)
    graph.add_edge(edge)

    assert graph.node_count() == 2
    assert graph.edge_count() == 1
    assert graph.get_node("n1") == node1
    assert graph.get_neighbors("n1") == ["n2"]
    assert graph.get_neighbors("n3") == []


@pytest.fixture
def mock_graph_repo():
    return AsyncMock(spec=GraphRepository)


@pytest.mark.asyncio
async def test_service_load_tenant_graph(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Mock Repo response
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": "n1", "node_id": "n1", "label": "Person", "properties": {}},
        {"id": "n2", "node_id": "n2", "label": "Person", "properties": {}},
    ]
    mock_graph_repo.get_all_edges.return_value = [
        {
            "source_node_id": "n1",
            "target_node_id": "n2",
            "relation": "knows",
            "properties": {},
        }
    ]

    graph = await service.load_tenant_graph(tenant_id)

    assert graph.node_count() == 2
    assert graph.edge_count() == 1

    # Verify Repo calls
    mock_graph_repo.get_all_nodes.assert_called_once()
    mock_graph_repo.get_all_edges.assert_called_once()


@pytest.mark.asyncio
async def test_pagerank(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Mock Repo loading a graph: n1 -> n2
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": "n1", "node_id": "n1", "label": "A", "properties": {}},
        {"id": "n2", "node_id": "n2", "label": "B", "properties": {}},
    ]
    mock_graph_repo.get_all_edges.return_value = [
        {
            "source_node_id": "n1",
            "target_node_id": "n2",
            "relation": "link",
            "properties": {},
        }
    ]

    scores = await service.pagerank(tenant_id)

    assert len(scores) == 2
    assert "n1" in scores
    assert "n2" in scores
    # n2 should have higher score because it has an incoming link
    assert scores["n2"] > scores["n1"]


@pytest.mark.asyncio
async def test_shortest_path(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Graph: n1 -> n2 -> n3
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": "n1", "node_id": "n1", "label": "A", "properties": {}},
        {"id": "n2", "node_id": "n2", "label": "A", "properties": {}},
        {"id": "n3", "node_id": "n3", "label": "A", "properties": {}},
    ]
    mock_graph_repo.get_all_edges.return_value = [
        {
            "source_node_id": "n1",
            "target_node_id": "n2",
            "relation": "link",
            "properties": {},
        },
        {
            "source_node_id": "n2",
            "target_node_id": "n3",
            "relation": "link",
            "properties": {},
        },
    ]

    path = await service.shortest_path(tenant_id, "n1", "n3")
    assert path == ["n1", "n2", "n3"]


@pytest.mark.asyncio
async def test_find_all_paths(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Graph: n1 -> n2 -> n3
    #          n1 -> n3
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": "n1", "node_id": "n1", "label": "A", "properties": {}},
        {"id": "n2", "node_id": "n2", "label": "A", "properties": {}},
        {"id": "n3", "node_id": "n3", "label": "A", "properties": {}},
    ]
    mock_graph_repo.get_all_edges.return_value = [
        {
            "source_node_id": "n1",
            "target_node_id": "n2",
            "relation": "link",
            "properties": {},
        },
        {
            "source_node_id": "n2",
            "target_node_id": "n3",
            "relation": "link",
            "properties": {},
        },
        {
            "source_node_id": "n1",
            "target_node_id": "n3",
            "relation": "direct",
            "properties": {},
        },
    ]

    paths = await service.find_all_paths(tenant_id, "n1", "n3")
    assert len(paths) == 2
    # paths could be in any order
    assert ["n1", "n3"] in paths
    assert ["n1", "n2", "n3"] in paths


@pytest.mark.asyncio
async def test_find_related_entities(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Graph: n1 -> n2 (dist 1) -> n3 (dist 2)
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": "n1", "node_id": "n1", "label": "A", "properties": {}},
        {"id": "n2", "node_id": "n2", "label": "B", "properties": {}},
        {"id": "n3", "node_id": "n3", "label": "C", "properties": {}},
    ]
    mock_graph_repo.get_all_edges.return_value = [
        {
            "source_node_id": "n1",
            "target_node_id": "n2",
            "relation": "r1",
            "properties": {},
        },
        {
            "source_node_id": "n2",
            "target_node_id": "n3",
            "relation": "r2",
            "properties": {},
        },
    ]

    related = await service.find_related_entities(tenant_id, "n1", max_distance=2)
    assert len(related) == 2
    # n2 (distance 1) and n3 (distance 2)

    # Sort by entity_id to check
    related.sort(key=lambda x: x["entity_id"])
    assert related[0]["entity_id"] == "n2"
    assert related[0]["distance"] == 1
    assert related[1]["entity_id"] == "n3"
    assert related[1]["distance"] == 2


@pytest.mark.asyncio
async def test_graph_summary(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Use a constructed graph mock to avoid multiple Repo calls
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("n1", "Person"))
    graph.add_node(GraphNode("n2", "Place"))
    graph.add_edge(GraphEdge("n1", "n2", "visits"))

    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        summary = await service.graph_summary(tenant_id)

    assert summary["num_nodes"] == 2
    assert summary["num_edges"] == 1
    assert summary["node_types"] == {"Person": 1, "Place": 1}
    assert summary["relation_types"] == {"visits": 1}
    assert summary["density"] == 1.0  # 2 nodes, 1 possible edge, 1 actual edge
    assert summary["is_connected"] is True


@pytest.mark.asyncio
async def test_community_detection(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    graph = KnowledgeGraph()
    graph.add_node(GraphNode("n1", "A"))
    graph.add_node(GraphNode("n2", "A"))

    # Louvain
    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        communities = await service.community_detection(tenant_id, algorithm="louvain")
        assert "n1" in communities
        assert "n2" in communities

    # Label Propagation
    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        communities = await service.community_detection(
            tenant_id, algorithm="label_propagation"
        )
        assert "n1" in communities
        assert "n2" in communities

    # Invalid algorithm
    with pytest.raises(ValueError):
        await service.community_detection(tenant_id, algorithm="invalid")


@pytest.mark.asyncio
async def test_calculate_centrality(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    graph = KnowledgeGraph()
    n1 = GraphNode("n1", "A")
    n2 = GraphNode("n2", "A")
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(GraphEdge("n1", "n2", "link"))

    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        # Degree
        cent = await service.calculate_centrality(tenant_id, "degree")
        assert cent["n1"] == 1.0
        assert cent["n2"] == 0.0

        # Betweenness
        cent = await service.calculate_centrality(tenant_id, "betweenness")
        assert cent["n1"] == 0.0

        # Closeness
        cent = await service.calculate_centrality(tenant_id, "closeness")
        assert cent["n1"] == 1.0
        assert cent["n2"] == 0.0

        # Eigenvector (calls pagerank)
        with patch.object(
            service, "pagerank", new=AsyncMock(return_value={"n1": 0.5})
        ) as mock_pagerank:
            cent = await service.calculate_centrality(tenant_id, "eigenvector")
            assert cent["n1"] == 0.5
            mock_pagerank.assert_called_once()

        # Invalid
        with pytest.raises(ValueError):
            await service.calculate_centrality(tenant_id, "invalid")


@pytest.mark.asyncio
async def test_graph_density(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    graph = KnowledgeGraph()
    graph.add_node(GraphNode("n1", "A"))
    graph.add_node(GraphNode("n2", "A"))
    graph.add_edge(GraphEdge("n1", "n2", "link"))

    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        density = await service.graph_density(tenant_id)
        # 2 nodes, max edges = 2*1/2 = 1. Actual edges = 1. Density = 1.0
        assert density == 1.0

    graph_empty = KnowledgeGraph()
    with patch.object(
        service, "load_tenant_graph", new=AsyncMock(return_value=graph_empty)
    ):
        density = await service.graph_density(tenant_id)
        assert density == 0.0


@pytest.mark.asyncio
async def test_subgraph_extraction(mock_graph_repo):
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    graph = KnowledgeGraph()
    graph.add_node(GraphNode("n1", "A"))
    graph.add_node(GraphNode("n2", "A"))
    graph.add_node(GraphNode("n3", "A"))
    graph.add_edge(GraphEdge("n1", "n2", "link"))
    graph.add_edge(GraphEdge("n2", "n3", "link"))

    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        subgraph = await service.subgraph_extraction(tenant_id, ["n1", "n2"])

        assert subgraph.node_count() == 2
        assert "n1" in subgraph.nodes
        assert "n2" in subgraph.nodes
        assert "n3" not in subgraph.nodes
        assert subgraph.edge_count() == 1


@pytest.mark.asyncio
async def test_repr_methods():
    """Test __repr__ methods for graph objects"""
    node = GraphNode("n1", "Person")
    assert repr(node) == "Node(n1, Person)"

    edge = GraphEdge("n1", "n2", "knows")
    assert repr(edge) == "Edge(n1 --[knows]--> n2)"

    graph = KnowledgeGraph()
    graph.add_node(node)
    graph.add_edge(edge)
    assert repr(graph) == "KnowledgeGraph(nodes=1, edges=1)"


@pytest.mark.asyncio
async def test_load_tenant_graph_no_db():
    """Test loading graph without Repo"""
    from typing import cast

    service = GraphAlgorithmsService(graph_repo=cast(GraphRepository, None))
    graph = await service.load_tenant_graph(uuid4())
    assert graph.node_count() == 0


@pytest.mark.asyncio
async def test_load_tenant_graph_with_project_id(mock_graph_repo):
    """Test loading graph with project_id filter"""
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()
    project_id = "proj-123"

    mock_graph_repo.get_all_nodes.return_value = []
    mock_graph_repo.get_all_edges.return_value = []

    await service.load_tenant_graph(tenant_id, project_id=project_id)

    # Verify Repo calls contained project_id
    mock_graph_repo.get_all_nodes.assert_called_once_with(str(tenant_id), project_id)


@pytest.mark.asyncio
async def test_load_tenant_graph_exception(mock_graph_repo):
    """Test exception handling during graph load"""
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    mock_graph_repo.get_all_nodes.side_effect = Exception("Repo Error")

    with pytest.raises(Exception):
        await service.load_tenant_graph(uuid4())


@pytest.mark.asyncio
async def test_empty_graph_algorithms(mock_graph_repo):
    """Test algorithms on empty graph"""
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()
    empty_graph = KnowledgeGraph()

    with patch.object(
        service, "load_tenant_graph", new=AsyncMock(return_value=empty_graph)
    ):
        assert await service.pagerank(tenant_id) == {}
        assert await service.community_detection(tenant_id, "louvain") == {}
        assert await service.community_detection(tenant_id, "label_propagation") == {}
        assert await service.calculate_centrality(tenant_id, "degree") == {}
        assert await service.calculate_centrality(tenant_id, "betweenness") == {}
        assert await service.calculate_centrality(tenant_id, "closeness") == {}


@pytest.mark.asyncio
async def test_find_all_paths_edge_cases(mock_graph_repo):
    """Test find_all_paths edge cases"""
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    graph = KnowledgeGraph()
    graph.add_node(GraphNode("n1", "A"))

    with patch.object(service, "load_tenant_graph", new=AsyncMock(return_value=graph)):
        # Target not in graph
        assert await service.find_all_paths(tenant_id, "n1", "n2") == []

        # Source not in graph
        assert await service.find_all_paths(tenant_id, "n2", "n1") == []


@pytest.mark.asyncio
async def test_find_bridges_and_articulation_points(mock_graph_repo):
    """Test bridge and articulation point placeholders"""
    service = GraphAlgorithmsService(graph_repo=mock_graph_repo)
    tenant_id = uuid4()

    # Just verify they run without error for now as they are placeholders
    assert await service.find_bridges(tenant_id) == []
    assert await service.find_articulation_points(tenant_id) == []
