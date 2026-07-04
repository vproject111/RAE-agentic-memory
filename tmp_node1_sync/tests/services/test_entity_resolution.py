"""
Tests for EntityResolutionService - Entity deduplication and merging.

Tests verify that the service correctly uses GraphRepository for all database operations.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.memory_api.services.entity_resolution import (
    EntityResolutionService,
    MergeDecision,
)


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for EntityResolutionService."""
    mock_rae_service = MagicMock()
    mock_rae_service.postgres_pool = MagicMock()
    mock_graph_repo = AsyncMock()
    mock_ml_client = AsyncMock()

    return mock_rae_service, mock_graph_repo, mock_ml_client


@pytest.mark.asyncio
async def test_fetch_nodes_uses_repository(mock_dependencies):
    """Test that _fetch_nodes uses GraphRepository."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    # Mock repository response
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "node_id": "node1", "label": "Entity1"},
        {"id": 2, "node_id": "node2", "label": "Entity2"},
    ]

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    nodes = await service._fetch_nodes(project_id="project1", tenant_id="tenant1")

    assert len(nodes) == 2
    assert nodes[0]["label"] == "Entity1"
    mock_graph_repo.get_all_nodes.assert_called_once_with(
        tenant_id="tenant1", project_id="project1"
    )


@pytest.mark.asyncio
async def test_merge_nodes_with_canonical_name(mock_dependencies):
    """Test merging nodes with canonical name using repository."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    # Mock repository methods
    mock_graph_repo.update_node_label.return_value = True
    mock_graph_repo.merge_node_edges.return_value = {
        "outgoing_updated": 2,
        "incoming_updated": 1,
    }
    mock_graph_repo.delete_node_edges.return_value = 3
    mock_graph_repo.delete_node.return_value = True

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    nodes = [{"id": 1, "label": "Apple Inc"}, {"id": 2, "label": "Apple Company"}]

    await service._merge_nodes(
        nodes=nodes,
        project_id="project1",
        tenant_id="tenant1",
        canonical_name="Apple Inc.",
    )

    # Verify repository methods were called
    mock_graph_repo.update_node_label.assert_called_once_with(
        node_internal_id=1, new_label="Apple Inc."
    )
    mock_graph_repo.merge_node_edges.assert_called_once()
    mock_graph_repo.delete_node_edges.assert_called_once()
    mock_graph_repo.delete_node.assert_called_once()


@pytest.mark.asyncio
async def test_merge_nodes_without_canonical_name(mock_dependencies):
    """Test merging nodes without canonical name (longest label heuristic)."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    # Mock repository methods
    mock_graph_repo.merge_node_edges.return_value = {
        "outgoing_updated": 1,
        "incoming_updated": 1,
    }
    mock_graph_repo.delete_node_edges.return_value = 2
    mock_graph_repo.delete_node.return_value = True

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    nodes = [{"id": 1, "label": "Short"}, {"id": 2, "label": "Much Longer Label"}]

    await service._merge_nodes(
        nodes=nodes, project_id="project1", tenant_id="tenant1", canonical_name=None
    )

    # Should pick node with longest label (id=2)
    # Should merge node 1 into node 2
    mock_graph_repo.merge_node_edges.assert_called_once_with(
        source_node_id=1, target_node_id=2
    )
    mock_graph_repo.delete_node.assert_called_once_with(node_internal_id=1)


@pytest.mark.asyncio
async def test_merge_nodes_empty_list(mock_dependencies):
    """Test merging with empty node list."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    # Should handle empty list gracefully
    await service._merge_nodes(
        nodes=[], project_id="project1", tenant_id="tenant1", canonical_name="Test"
    )

    # No repository methods should be called
    mock_graph_repo.update_node_label.assert_not_called()
    mock_graph_repo.merge_node_edges.assert_not_called()


@pytest.mark.asyncio
async def test_run_clustering_with_insufficient_nodes(mock_dependencies):
    """Test that clustering skips when less than 2 nodes."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    # Mock single node
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "node_id": "node1", "label": "OnlyNode"}
    ]

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    await service.run_clustering_and_merging(project_id="project1", tenant_id="tenant1")

    # ML service should not be called
    mock_ml_client.resolve_entities.assert_not_called()


@pytest.mark.asyncio
async def test_process_group_with_merge_approval(mock_dependencies):
    """Test processing a group when Janitor Agent approves merge."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    # Mock LLM provider
    service.llm_provider = MagicMock()
    service.llm_provider.generate_structured = AsyncMock(
        return_value=MergeDecision(
            should_merge=True,
            canonical_name="Python Programming Language",
            reasoning="Both refer to the same programming language",
        )
    )

    # Mock merge operation
    service._merge_nodes = AsyncMock()

    nodes = [{"id": 1, "label": "Python"}, {"id": 2, "label": "Python Language"}]

    await service._process_group(
        nodes=nodes, project_id="project1", tenant_id="tenant1"
    )

    # Verify merge was called with canonical name
    service._merge_nodes.assert_called_once_with(
        nodes, "project1", "tenant1", canonical_name="Python Programming Language"
    )


@pytest.mark.asyncio
async def test_process_group_with_merge_rejection(mock_dependencies):
    """Test processing a group when Janitor Agent rejects merge."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    # Mock LLM provider to reject merge
    service.llm_provider = MagicMock()
    service.llm_provider.generate_structured = AsyncMock(
        return_value=MergeDecision(
            should_merge=False,
            canonical_name="",
            reasoning="Java (island) and Java (programming language) are different concepts",
        )
    )

    # Mock merge operation
    service._merge_nodes = AsyncMock()

    nodes = [{"id": 1, "label": "Java"}, {"id": 2, "label": "Java Island"}]

    await service._process_group(
        nodes=nodes, project_id="project1", tenant_id="tenant1"
    )

    # Verify merge was NOT called
    service._merge_nodes.assert_not_called()


@pytest.mark.asyncio
async def test_run_clustering_success(mock_dependencies):
    """Test full clustering workflow success."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    # Mock nodes
    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "label": "A"},
        {"id": 2, "label": "A Inc"},
        {"id": 3, "label": "B"},
    ]

    # Mock ML response
    mock_ml_client.resolve_entities.return_value = {
        "merge_groups": [["1", "2"]],
        "statistics": {},
    }

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    # Mock process group to avoid complex interactions
    service._process_group = AsyncMock()

    await service.run_clustering_and_merging("p1", "t1")

    # Verify ML called
    mock_ml_client.resolve_entities.assert_called_once()

    # Verify process group called for the group
    service._process_group.assert_called_once()
    # Check args: group nodes should have ids 1 and 2
    call_args = service._process_group.call_args
    group_nodes = call_args[0][0]
    assert len(group_nodes) == 2
    assert group_nodes[0]["id"] == 1
    assert group_nodes[1]["id"] == 2


@pytest.mark.asyncio
async def test_run_clustering_ml_failure(mock_dependencies):
    """Test handling of ML service failure."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    mock_graph_repo.get_all_nodes.return_value = [
        {"id": 1, "label": "A"},
        {"id": 2, "label": "B"},
    ]

    mock_ml_client.resolve_entities.side_effect = Exception("ML Down")

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    await service.run_clustering_and_merging("p1", "t1")

    # Should not crash
    mock_ml_client.resolve_entities.assert_called_once()


@pytest.mark.asyncio
async def test_ask_janitor_failure(mock_dependencies):
    """Test handling of Janitor LLM failure."""
    mock_rae_service, mock_graph_repo, mock_ml_client = mock_dependencies

    service = EntityResolutionService(
        rae_service=mock_rae_service,
        ml_client=mock_ml_client,
        graph_repository=mock_graph_repo,
    )

    service.llm_provider = MagicMock()
    service.llm_provider.generate_structured = AsyncMock(
        side_effect=Exception("LLM Error")
    )

    decision = await service._ask_janitor(["A", "B"])

    # Should return default False decision
    assert decision.should_merge is False
    assert decision.reasoning == "Error"
