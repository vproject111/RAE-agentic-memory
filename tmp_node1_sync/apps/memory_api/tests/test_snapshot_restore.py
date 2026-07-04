from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.memory_api.repositories.graph_repository_enhanced import (
    EnhancedGraphRepository,
)


@pytest.mark.asyncio
async def test_restore_snapshot_logic():
    # Mock the database provider
    mock_db = AsyncMock()

    # Setup the repository with the mock DB
    repo = EnhancedGraphRepository(mock_db)

    # Test data
    snapshot_id = uuid4()
    clear_existing = True
    expected_nodes_restored = 10
    expected_edges_restored = 20

    # Mock the database response
    mock_db.fetchrow.return_value = {
        "nodes_restored": expected_nodes_restored,
        "edges_restored": expected_edges_restored,
    }

    # Call the method under test
    nodes, edges = await repo.restore_snapshot(snapshot_id, clear_existing)

    # Verify the results
    assert nodes == expected_nodes_restored
    assert edges == expected_edges_restored

    # Verify the database interaction
    mock_db.fetchrow.assert_called_once_with(
        "SELECT * FROM restore_graph_snapshot($1, $2)", snapshot_id, clear_existing
    )


@pytest.mark.asyncio
async def test_restore_snapshot_not_found():
    # Mock the database provider
    mock_db = AsyncMock()
    repo = EnhancedGraphRepository(mock_db)

    snapshot_id = uuid4()

    # Mock return value as None (snapshot not found or procedure returned null)
    mock_db.fetchrow.return_value = None

    # Call the method
    nodes, edges = await repo.restore_snapshot(snapshot_id)

    # Verify it returns (0, 0) gracefully
    assert nodes == 0
    assert edges == 0
