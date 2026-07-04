"""
Tests for CommunityDetectionService - Community detection and summarization.

Tests verify that the service correctly uses GraphRepository for all database operations.
"""

from unittest.mock import AsyncMock, MagicMock

import networkx as nx
import pytest

from apps.memory_api.services.community_detection import (
    CommunityDetectionService,
    CommunitySummary,
)


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for CommunityDetectionService."""
    mock_rae_service = MagicMock()
    mock_rae_service.postgres_pool = MagicMock()
    mock_graph_repo = AsyncMock()

    return mock_rae_service, mock_graph_repo


@pytest.mark.asyncio
async def test_load_graph_uses_repository(mock_dependencies):
    """Test that _load_graph_from_db uses GraphRepository."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    # Mock repository responses
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "node_id": "node1", "label": "Entity1"},
        {"id": 2, "node_id": "node2", "label": "Entity2"},
        {"id": 3, "node_id": "node3", "label": "Entity3"},
    ]

    mock_graph_repo.get_all_edges.return_value = [
        {"source_node_id": 1, "target_node_id": 2, "relation": "RELATED_TO"},
        {"source_node_id": 2, "target_node_id": 3, "relation": "CONNECTED_TO"},
    ]

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    graph = await service._load_graph_from_db(
        project_id="project1", tenant_id="tenant1"
    )

    # Verify graph structure
    assert isinstance(graph, nx.Graph)
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2

    # Verify repository was called
    mock_graph_repo.get_all_nodes.assert_called_once_with(
        tenant_id="tenant1", project_id="project1"
    )
    mock_graph_repo.get_all_edges.assert_called_once_with(
        tenant_id="tenant1", project_id="project1"
    )


@pytest.mark.asyncio
async def test_load_graph_with_disconnected_edges(mock_dependencies):
    """Test loading graph with edges referencing non-existent nodes."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    # Mock nodes and edges where an edge references missing node
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "node_id": "node1", "label": "Entity1"},
        {"id": 2, "node_id": "node2", "label": "Entity2"},
    ]

    mock_graph_repo.get_all_edges.return_value = [
        {"source_node_id": 1, "target_node_id": 2, "relation": "RELATED_TO"},
        {
            "source_node_id": 2,
            "target_node_id": 999,
            "relation": "BROKEN_LINK",
        },  # Node 999 doesn't exist
    ]

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    graph = await service._load_graph_from_db(
        project_id="project1", tenant_id="tenant1"
    )

    # Should only add valid edges
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1  # Only the first edge should be added


@pytest.mark.asyncio
async def test_store_super_node_uses_repository(mock_dependencies):
    """Test that _store_super_node uses GraphRepository."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    # Mock upsert to return internal ID
    mock_graph_repo.upsert_node.return_value = 123

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    summary = CommunitySummary(
        summary="This community discusses Python programming",
        themes=["Python", "Programming", "Development"],
        title="Python Development Community",
    )

    await service._store_super_node(
        community_id=1,
        summary=summary,
        member_node_ids=[1, 2, 3],
        project_id="project1",
        tenant_id="tenant1",
    )

    # Verify repository upsert was called
    mock_graph_repo.upsert_node.assert_called_once()

    # Verify call parameters
    call_args = mock_graph_repo.upsert_node.call_args
    assert call_args.kwargs["tenant_id"] == "tenant1"
    assert call_args.kwargs["project_id"] == "project1"
    assert call_args.kwargs["node_id"] == "community_project1_1"
    assert call_args.kwargs["label"] == "Community: Python Development Community"

    # Verify properties
    properties = call_args.kwargs["properties"]
    assert properties["type"] == "community"
    assert properties["summary"] == summary.summary
    assert properties["themes"] == summary.themes
    assert properties["community_id"] == 1
    assert properties["member_count"] == 3


@pytest.mark.asyncio
async def test_run_community_detection_insufficient_nodes(mock_dependencies):
    """Test that community detection skips for small graphs."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    # Mock small graph (less than 5 nodes)
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "node_id": "node1", "label": "Entity1"},
        {"id": 2, "node_id": "node2", "label": "Entity2"},
    ]
    mock_graph_repo.get_all_edges.return_value = []

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    # Should complete without processing
    await service.run_community_detection_and_summarization(
        project_id="project1", tenant_id="tenant1"
    )

    # Verify upsert was not called (no communities created)
    mock_graph_repo.upsert_node.assert_not_called()


@pytest.mark.asyncio
async def test_generate_summary_llm_integration(mock_dependencies):
    """Test that _generate_summary calls LLM provider."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    # Mock LLM provider
    service.llm_provider = MagicMock()
    service.llm_provider.generate_structured = AsyncMock(
        return_value=CommunitySummary(
            summary="A collection of Python-related entities",
            themes=["Python", "Programming"],
            title="Python Ecosystem",
        )
    )

    description = (
        "Nodes: Python, Django, Flask\nRelationships:\nPython --[RELATED_TO]--> Django"
    )

    summary = await service._generate_summary(description)

    assert isinstance(summary, CommunitySummary)
    assert summary.title == "Python Ecosystem"
    assert "Python" in summary.themes


@pytest.mark.asyncio
async def test_generate_summary_llm_failure(mock_dependencies):
    """Test that _generate_summary handles LLM failures gracefully."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    # Mock LLM provider to raise exception
    service.llm_provider = MagicMock()
    service.llm_provider.generate_structured = AsyncMock(
        side_effect=Exception("LLM Error")
    )

    description = "Test nodes"

    summary = await service._generate_summary(description)

    # Should return default summary on error
    assert isinstance(summary, CommunitySummary)
    assert summary.summary == "Extraction failed"
    assert summary.themes == []
    assert summary.title == "Unknown Community"


@pytest.mark.asyncio
async def test_process_community_workflow(mock_dependencies):
    """Test complete _process_community workflow."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    # Mock LLM provider
    service.llm_provider = MagicMock()
    service.llm_provider.generate_structured = AsyncMock(
        return_value=CommunitySummary(
            summary="Test summary", themes=["Test"], title="Test Community"
        )
    )

    # Mock upsert
    mock_graph_repo.upsert_node.return_value = 456

    # Create test graph
    graph = nx.Graph()
    graph.add_node(1, label="Entity1")
    graph.add_node(2, label="Entity2")
    graph.add_node(3, label="Entity3")
    graph.add_edge(1, 2, relation="RELATED_TO")
    graph.add_edge(2, 3, relation="CONNECTED_TO")

    node_ids = [1, 2, 3]

    await service._process_community(
        community_id=5,
        node_ids=node_ids,
        graph=graph,
        project_id="project1",
        tenant_id="tenant1",
    )

    # Verify LLM was called
    service.llm_provider.generate_structured.assert_called_once()

    # Verify super-node was stored
    mock_graph_repo.upsert_node.assert_called_once()


@pytest.mark.asyncio
async def test_empty_graph_handling(mock_dependencies):
    """Test handling of empty graph."""
    mock_rae_service, mock_graph_repo = mock_dependencies

    mock_graph_repo.get_all_nodes.return_value = []
    mock_graph_repo.get_all_edges.return_value = []

    service = CommunityDetectionService(
        rae_service=mock_rae_service, graph_repository=mock_graph_repo
    )

    graph = await service._load_graph_from_db(
        project_id="project1", tenant_id="tenant1"
    )

    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0
