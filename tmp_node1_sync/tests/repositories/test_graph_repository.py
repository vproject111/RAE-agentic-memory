"""
Tests for GraphRepository - Data Access Layer for Knowledge Graph.

Tests verify that repository methods correctly interact with the database
and follow the Repository/DAO pattern.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.memory_api.repositories.graph_repository import GraphRepository


@pytest.fixture
def mock_pool():
    """Create mock database connection pool."""
    pool = MagicMock()
    conn = AsyncMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__.return_value = conn
    acquire_cm.__aexit__.return_value = None
    pool.acquire.return_value = acquire_cm
    return pool, conn


@pytest.mark.asyncio
async def test_get_all_nodes(mock_pool):
    """Test retrieving all nodes for a project."""
    pool, conn = mock_pool
    conn.fetch.return_value = [
        {"id": 1, "node_id": "node1", "label": "Label1", "properties": {}},
        {"id": 2, "node_id": "node2", "label": "Label2", "properties": {}},
    ]

    repo = GraphRepository(pool)
    nodes = await repo.get_all_nodes(tenant_id="tenant1", project_id="project1")

    assert len(nodes) == 2
    assert nodes[0]["node_id"] == "node1"
    assert nodes[1]["node_id"] == "node2"
    conn.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_edges(mock_pool):
    """Test retrieving all edges for a project."""
    pool, conn = mock_pool
    conn.fetch.return_value = [
        {
            "source_node_id": 1,
            "target_node_id": 2,
            "relation": "RELATED_TO",
            "properties": {},
        },
        {
            "source_node_id": 2,
            "target_node_id": 3,
            "relation": "LINKED_TO",
            "properties": {},
        },
    ]

    repo = GraphRepository(pool)
    edges = await repo.get_all_edges(tenant_id="tenant1", project_id="project1")

    assert len(edges) == 2
    assert edges[0]["relation"] == "RELATED_TO"
    assert edges[1]["relation"] == "LINKED_TO"
    conn.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_update_node_label(mock_pool):
    """Test updating a node's label."""
    pool, conn = mock_pool
    conn.execute.return_value = "UPDATE 1"

    repo = GraphRepository(pool)
    result = await repo.update_node_label(node_internal_id=1, new_label="NewLabel")

    assert result is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_merge_node_edges(mock_pool):
    """Test merging edges from source to target node."""
    pool, conn = mock_pool

    # Mock transaction context - return context manager directly
    class TransactionContext:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *args):
            return None

    conn.transaction = MagicMock(return_value=TransactionContext())

    # Mock execute results
    conn.execute.side_effect = ["UPDATE 3", "UPDATE 2"]

    repo = GraphRepository(pool)
    result = await repo.merge_node_edges(source_node_id=1, target_node_id=2)

    assert result["outgoing_updated"] == 3
    assert result["incoming_updated"] == 2
    assert conn.execute.call_count == 2


@pytest.mark.asyncio
async def test_delete_node_edges(mock_pool):
    """Test deleting all edges connected to a node."""
    pool, conn = mock_pool
    conn.execute.return_value = "DELETE 5"

    repo = GraphRepository(pool)
    count = await repo.delete_node_edges(node_internal_id=1)

    assert count == 5
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_node(mock_pool):
    """Test deleting a node."""
    pool, conn = mock_pool
    conn.execute.return_value = "DELETE 1"

    repo = GraphRepository(pool)
    result = await repo.delete_node(node_internal_id=1)

    assert result is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_delete_node_not_found(mock_pool):
    """Test deleting a non-existent node."""
    pool, conn = mock_pool
    conn.execute.return_value = "DELETE 0"

    repo = GraphRepository(pool)
    result = await repo.delete_node(node_internal_id=999)

    assert result is False
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_node_insert(mock_pool):
    """Test upserting a new node (insert case)."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"id": 123}

    repo = GraphRepository(pool)
    internal_id = await repo.upsert_node(
        tenant_id="tenant1",
        project_id="project1",
        node_id="node1",
        label="Label1",
        properties={"key": "value"},
    )

    assert internal_id == 123
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_node_update(mock_pool):
    """Test upserting an existing node (update case)."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"id": 456}

    repo = GraphRepository(pool)
    internal_id = await repo.upsert_node(
        tenant_id="tenant1",
        project_id="project1",
        node_id="existing_node",
        label="UpdatedLabel",
        properties={"updated": True},
    )

    assert internal_id == 456
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_create_node(mock_pool):
    """Test creating a new node."""
    pool, conn = mock_pool
    conn.execute.return_value = "INSERT 0 1"

    repo = GraphRepository(pool)
    result = await repo.create_node(
        tenant_id="tenant1",
        project_id="project1",
        node_id="node1",
        label="Label1",
        properties={},
    )

    assert result is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_edge(mock_pool):
    """Test creating a new edge."""
    pool, conn = mock_pool
    conn.execute.return_value = "INSERT 0 1"

    repo = GraphRepository(pool)
    result = await repo.create_edge(
        tenant_id="tenant1",
        project_id="project1",
        source_node_internal_id=1,
        target_node_internal_id=2,
        relation="RELATED_TO",
        properties={},
    )

    assert result is True
    conn.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_node_internal_id(mock_pool):
    """Test getting internal ID for a node."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = {"id": 789}

    repo = GraphRepository(pool)
    internal_id = await repo.get_node_internal_id(
        tenant_id="tenant1", project_id="project1", node_id="node1"
    )

    assert internal_id == 789
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_get_node_internal_id_not_found(mock_pool):
    """Test getting internal ID for non-existent node."""
    pool, conn = mock_pool
    conn.fetchrow.return_value = None

    repo = GraphRepository(pool)
    internal_id = await repo.get_node_internal_id(
        tenant_id="tenant1", project_id="project1", node_id="nonexistent"
    )

    assert internal_id is None
    conn.fetchrow.assert_called_once()


@pytest.mark.asyncio
async def test_store_graph_triples(mock_pool):
    """Test storing multiple triples in batch."""
    pool, conn = mock_pool

    # Mock transaction context - return context manager directly
    class TransactionContext:
        async def __aenter__(self):
            return None

        async def __aexit__(self, *args):
            return None

    conn.transaction = MagicMock(return_value=TransactionContext())

    # Mock node creation and ID retrieval
    conn.execute.return_value = "INSERT 0 1"
    conn.fetchrow.side_effect = [
        {"id": 1},  # source node ID
        {"id": 2},  # target node ID
    ]

    repo = GraphRepository(pool)

    # Mock create_node and create_edge to avoid actual calls
    repo.create_node = AsyncMock(return_value=True)
    repo.create_edge = AsyncMock(return_value=True)
    repo.get_node_internal_id = AsyncMock(side_effect=[1, 2])

    triples = [
        {
            "source": "node1",
            "target": "node2",
            "relation": "RELATED_TO",
            "confidence": 0.9,
            "metadata": {},
        }
    ]

    stats = await repo.store_graph_triples(
        triples=triples, tenant_id="tenant1", project_id="project1"
    )

    assert "nodes_created" in stats
    assert "edges_created" in stats
