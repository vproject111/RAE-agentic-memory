"""
Integration tests for GraphExtractionService using Testcontainers.

These tests verify the refactored Repository/DAO pattern implementation:
- GraphExtractionService uses RAECoreService for memory access
- GraphExtractionService uses GraphRepository for graph operations
- Proper JSONB serialization/deserialization
- Complete triple storage workflow (nodes + edges)

Prerequisites:
- Docker running (for testcontainers)
- testcontainers Python package installed
"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

# Skip tests if spacy is not installed (ML dependency)
spacy = pytest.importorskip(
    "spacy",
    reason="Requires spacy – heavy ML dependency, not installed in lightweight CI",
)

# Use noqa: E402 because these imports MUST be after the importorskip check
from apps.memory_api.repositories.graph_repository import GraphRepository  # noqa: E402
from apps.memory_api.services.graph_extraction import (  # noqa: E402
    GraphExtractionService,
    GraphTriple,
)
from apps.memory_api.services.rae_core_service import RAECoreService  # noqa: E402


@pytest.mark.asyncio
async def test_fetch_episodic_memories_uses_service(db_pool):
    """
    Test that GraphExtractionService uses RAECoreService to fetch episodic memories.
    """
    # Arrange: Create test episodic memories
    tenant_id = "test-tenant-extraction"
    project_id = "test-project-extraction"

    mock_memories = [
        {
            "id": "1",
            "content": "User reported bug in auth module",
            "layer": "episodic",
            "tags": ["bug"],
            "source": "tracker",
            "created_at": "2024-01-01T12:00:00",
        },
        {
            "id": "2",
            "content": "Developer fixed the authentication issue",
            "layer": "episodic",
            "tags": ["fix"],
            "source": "git",
            "created_at": "2024-01-02T12:00:00",
        },
    ]

    # Mock RAECoreService
    mock_rae_service = AsyncMock(spec=RAECoreService)
    mock_rae_service.list_memories.return_value = mock_memories

    graph_repo = GraphRepository(db_pool)
    service = GraphExtractionService(mock_rae_service, graph_repo)

    # Act
    memories = await service._fetch_episodic_memories(
        project_id=project_id, tenant_id=tenant_id, limit=10
    )

    # Assert
    assert len(memories) == 2
    assert memories == mock_memories
    mock_rae_service.list_memories.assert_called_once_with(
        tenant_id=tenant_id, layer="episodic", project=project_id, limit=10
    )


@pytest.mark.asyncio
async def test_store_graph_triples_creates_nodes_and_edges(db_pool, use_real_db):
    """
    Test that GraphExtractionService.store_graph_triples properly creates nodes and edges
    using GraphRepository with correct JSONB handling.
    """
    # Arrange
    tenant_id = "test-tenant-triples"
    project_id = "test-project-triples"

    mock_rae_service = AsyncMock(spec=RAECoreService)
    graph_repo = GraphRepository(db_pool)
    service = GraphExtractionService(mock_rae_service, graph_repo)

    # Create test triples
    # Note: Entity names will be normalized (underscores -> spaces)
    triples = [
        GraphTriple(
            source="john",
            target="bug_123",  # Will be normalized to "bug 123"
            relation="REPORTED",
            confidence=0.95,
            metadata={"timestamp": "2024-11-22", "source": "tracker"},
        ),
        GraphTriple(
            source="alice",
            target="bug_123",  # Will be normalized to "bug 123"
            relation="FIXED",
            confidence=0.98,
            metadata={"timestamp": "2024-11-23", "commit": "abc123"},
        ),
        GraphTriple(
            source="auth_service",  # Will be normalized to "auth service"
            target="encryption_service",  # Will be normalized to "encryption service"
            relation="DEPENDS_ON",
            confidence=1.0,
            metadata={"version": "2.0"},
        ),
    ]

    # Act: Store triples
    result = await service.store_graph_triples(
        triples=triples, project_id=project_id, tenant_id=tenant_id
    )

    # Assert: Check statistics
    assert (
        result["nodes_created"] == 5
    )  # john, alice, bug_123, auth_service, encryption_service
    assert result["edges_created"] == 3

    # Verify nodes were created in database
    async with db_pool.acquire() as conn:
        nodes = await conn.fetch(
            """
            SELECT node_id, label, properties
            FROM knowledge_graph_nodes
            WHERE tenant_id = $1 AND project_id = $2
            ORDER BY node_id
            """,
            tenant_id,
            project_id,
        )

        assert len(nodes) == 5
        node_ids = [n["node_id"] for n in nodes]
        assert "john" in node_ids
        assert "bug 123" in node_ids  # Normalized from "bug_123"

        # Verify JSONB properties are properly stored
        john_node = next(n for n in nodes if n["node_id"] == "john")
        assert john_node["properties"] is not None
        # Properties can be dict or JSON string depending on driver
        if isinstance(john_node["properties"], str):
            import json

            props = json.loads(john_node["properties"])
        else:
            props = john_node["properties"]
        assert "timestamp" in props

        # Verify edges were created with correct properties
        edges = await conn.fetch(
            """
            SELECT e.relation, e.properties,
                   src.node_id as source, tgt.node_id as target
            FROM knowledge_graph_edges e
            JOIN knowledge_graph_nodes src ON e.source_node_id = src.id
            JOIN knowledge_graph_nodes tgt ON e.target_node_id = tgt.id
            WHERE e.tenant_id = $1 AND e.project_id = $2
            ORDER BY e.relation
            """,
            tenant_id,
            project_id,
        )

        assert len(edges) == 3

        # Find the DEPENDS_ON edge
        depends_edge = next(e for e in edges if e["relation"] == "DEPENDS_ON")
        assert (
            depends_edge["source"] == "auth service"
        )  # Normalized from "auth_service"
        assert (
            depends_edge["target"] == "encryption service"
        )  # Normalized from "encryption_service"

        # Verify edge properties (including confidence)
        if isinstance(depends_edge["properties"], str):
            import json

            edge_props = json.loads(depends_edge["properties"])
        else:
            edge_props = depends_edge["properties"]

        assert edge_props["confidence"] == 1.0
        assert edge_props["version"] == "2.0"


@pytest.mark.asyncio
async def test_store_triples_handles_duplicates_gracefully(db_pool, use_real_db):
    """
    Test that storing duplicate triples doesn't fail (ON CONFLICT DO NOTHING).
    """
    # Arrange
    tenant_id = "test-tenant-duplicates"
    project_id = "test-project-duplicates"

    mock_rae_service = AsyncMock(spec=RAECoreService)
    graph_repo = GraphRepository(db_pool)
    service = GraphExtractionService(mock_rae_service, graph_repo)

    triple = GraphTriple(
        source="alice",
        target="bob",
        relation="KNOWS",
        confidence=0.9,
        metadata={"since": "2020"},
    )

    # Act: Store the same triple twice
    result1 = await service.store_graph_triples(
        triples=[triple], project_id=project_id, tenant_id=tenant_id
    )

    result2 = await service.store_graph_triples(
        triples=[triple], project_id=project_id, tenant_id=tenant_id
    )

    # Assert: First insert creates nodes and edge, second insert creates nothing
    assert result1["nodes_created"] == 2  # alice, bob
    assert result1["edges_created"] == 1

    assert result2["nodes_created"] == 0  # Already exist
    assert result2["edges_created"] == 0  # Already exists (ON CONFLICT DO NOTHING)


@pytest.mark.asyncio
async def test_graph_repository_jsonb_serialization(db_pool, use_real_db):
    """
    Test that GraphRepository properly handles JSONB serialization for properties.

    This ensures the fix for the JSONB serialization issue is working.
    """
    # Arrange
    tenant_id = "test-tenant-jsonb"
    project_id = "test-project-jsonb"

    repo = GraphRepository(db_pool)

    # Complex nested metadata
    complex_metadata = {
        "nested": {"key": "value", "array": [1, 2, 3]},
        "timestamp": "2024-11-22T10:00:00",
        "tags": ["tag1", "tag2"],
    }

    # Act: Create node with complex properties
    created = await repo.create_node(
        tenant_id=tenant_id,
        project_id=project_id,
        node_id="test_node",
        label="TestEntity",
        properties=complex_metadata,
    )

    assert created is True

    # Retrieve node and verify JSONB was properly stored
    async with db_pool.acquire() as conn:
        node = await conn.fetchrow(
            """
            SELECT properties FROM knowledge_graph_nodes
            WHERE tenant_id = $1 AND project_id = $2 AND node_id = $3
            """,
            tenant_id,
            project_id,
            "test_node",
        )

        # Verify the properties are intact
        if isinstance(node["properties"], str):
            import json

            props = json.loads(node["properties"])
        else:
            props = node["properties"]

        assert props["nested"]["key"] == "value"
        assert props["nested"]["array"] == [1, 2, 3]
        assert props["timestamp"] == "2024-11-22T10:00:00"
        assert len(props["tags"]) == 2


@pytest.mark.asyncio
async def test_graph_repository_get_node_internal_id(db_pool, use_real_db):
    """
    Test GraphRepository.get_node_internal_id method.
    """
    # Arrange
    tenant_id = "test-tenant-internal-id"
    project_id = "test-project-internal-id"

    repo = GraphRepository(db_pool)

    # Create a node
    await repo.create_node(
        tenant_id=tenant_id,
        project_id=project_id,
        node_id="entity_1",
        label="Entity",
        properties={"name": "Test Entity"},
    )

    # Act: Get internal ID
    internal_id = await repo.get_node_internal_id(
        tenant_id=tenant_id, project_id=project_id, node_id="entity_1"
    )

    # Assert
    assert internal_id is not None
    assert isinstance(internal_id, UUID)

    # Try to get non-existent node
    non_existent_id = await repo.get_node_internal_id(
        tenant_id=tenant_id, project_id=project_id, node_id="non_existent"
    )

    assert non_existent_id is None


@pytest.mark.asyncio
async def test_end_to_end_triple_storage_workflow(db_pool, use_real_db):
    """
    End-to-end test of the complete triple storage workflow:
    1. Create memories (MOCKED)
    2. Extract graph (mocked LLM)
    3. Store triples via service
    4. Verify nodes and edges in database
    """
    # Arrange
    tenant_id = "test-tenant-e2e"
    project_id = "test-project-e2e"

    # Mock RAE service returns
    mock_rae_service = AsyncMock(spec=RAECoreService)
    # We don't strictly need it to return anything if we just call store_graph_triples manually with mock triples
    # But if we were calling extract_knowledge_graph, we would need it.
    # The original test populated DB and expected valid fetch.
    # Here we skip the fetch part since we're testing storage workflow primarily in this test block.
    # Wait, the original test "test_end_to_end_triple_storage_workflow":
    # 1. Insert memories
    # 2. Mock triples
    # 3. Store triples
    # It didn't actually call extract_knowledge_graph! It called store_graph_triples directly.
    # So the memory insertion was... redundant? Or maybe just for "realism"?
    # Actually, the original test inserted memories but didn't seem to use them in the Act phase
    # (except maybe assuming store_graph_triples validates them? No, it doesn't seem to).

    # So I can just use the mock service and skip memory insertion if not needed.

    # Mock triples that would be extracted by LLM
    # Note: "auth_bug" will be normalized to "auth bug"
    mock_triples = [
        GraphTriple(
            source="john",
            target="auth_bug",  # Will be normalized to "auth bug"
            relation="REPORTED",
            confidence=0.95,
            metadata={"project": project_id},
        ),
        GraphTriple(
            source="alice",
            target="auth_bug",  # Will be normalized to "auth bug"
            relation="FIXED",
            confidence=0.95,
            metadata={"project": project_id},
        ),
    ]

    # Act: Store triples
    graph_repo = GraphRepository(db_pool)
    service = GraphExtractionService(mock_rae_service, graph_repo)
    result = await service.store_graph_triples(
        triples=mock_triples, project_id=project_id, tenant_id=tenant_id
    )

    # Assert: Verify complete workflow
    assert result["nodes_created"] == 3  # john, alice, auth_bug
    assert result["edges_created"] == 2  # REPORTED, FIXED

    # Verify graph structure
    graph_repo = GraphRepository(db_pool)

    # Verify nodes exist (use normalized names)
    john_id = await graph_repo.get_node_internal_id(tenant_id, project_id, "john")
    alice_id = await graph_repo.get_node_internal_id(tenant_id, project_id, "alice")
    bug_id = await graph_repo.get_node_internal_id(
        tenant_id, project_id, "auth bug"
    )  # Normalized from "auth_bug"

    assert john_id is not None
    assert alice_id is not None
    assert bug_id is not None

    # Verify edges exist with correct relations
    async with db_pool.acquire() as conn:
        edges = await conn.fetch(
            """
            SELECT relation FROM knowledge_graph_edges
            WHERE tenant_id = $1 AND project_id = $2
            ORDER BY relation
            """,
            tenant_id,
            project_id,
        )

        relations = [e["relation"] for e in edges]
        assert "REPORTED" in relations
        assert "FIXED" in relations
