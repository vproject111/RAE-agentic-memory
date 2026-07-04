from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import pytest

from apps.memory_api.services.graph_algorithms import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
)
from apps.memory_api.services.temporal_graph import (
    ChangeType,
    GraphChange,
    GraphSnapshot,
    TemporalGraphService,
)


@pytest.fixture
def temporal_service():
    return TemporalGraphService()


@pytest.fixture
def sample_graph():
    graph = KnowledgeGraph()
    graph.add_node(GraphNode("n1", "Person"))
    graph.add_node(GraphNode("n2", "Place"))
    graph.add_edge(GraphEdge("n1", "n2", "visits"))
    return graph


@pytest.mark.asyncio
async def test_create_snapshot(temporal_service, sample_graph):
    tenant_id = uuid4()

    snapshot = await temporal_service.create_snapshot(tenant_id, sample_graph)

    assert isinstance(snapshot, GraphSnapshot)
    assert snapshot.tenant_id == tenant_id
    assert snapshot.graph == sample_graph
    assert len(temporal_service._snapshots[tenant_id]) == 1


@pytest.mark.asyncio
async def test_get_snapshot_at_time(temporal_service, sample_graph):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # Create snapshots at different times
    s1 = GraphSnapshot(tenant_id, now - timedelta(hours=2), sample_graph)
    s2 = GraphSnapshot(tenant_id, now - timedelta(hours=1), sample_graph)

    temporal_service._snapshots[tenant_id] = [s1, s2]

    # Get snapshot between s1 and s2
    result = await temporal_service.get_snapshot_at_time(
        tenant_id, now - timedelta(minutes=90)
    )
    assert result == s1

    # Get snapshot after s2
    result = await temporal_service.get_snapshot_at_time(tenant_id, now)
    assert result == s2

    # Get snapshot before s1
    result = await temporal_service.get_snapshot_at_time(
        tenant_id, now - timedelta(hours=3)
    )
    assert result is None


@pytest.mark.asyncio
async def test_get_latest_snapshot(temporal_service, sample_graph):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    s1 = GraphSnapshot(tenant_id, now - timedelta(hours=2), sample_graph)
    s2 = GraphSnapshot(tenant_id, now - timedelta(hours=1), sample_graph)

    temporal_service._snapshots[tenant_id] = [s1, s2]

    latest = await temporal_service.get_latest_snapshot(tenant_id)
    assert latest == s2


@pytest.mark.asyncio
async def test_record_change(temporal_service):
    tenant_id = uuid4()
    change = GraphChange(
        ChangeType.NODE_ADDED,
        datetime.now(timezone.utc),
        "n1",
        "Person",
        new_value={"properties": {"name": "Alice"}},
    )

    await temporal_service.record_change(tenant_id, change)

    assert len(temporal_service._changes[tenant_id]) == 1
    assert temporal_service._changes[tenant_id][0] == change


@pytest.mark.asyncio
async def test_get_changes_filters(temporal_service):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    c1 = GraphChange(ChangeType.NODE_ADDED, now - timedelta(hours=2), "n1", "Person")
    c2 = GraphChange(
        ChangeType.EDGE_ADDED, now - timedelta(hours=1), "n1->n2", "Relation"
    )
    c3 = GraphChange(ChangeType.NODE_REMOVED, now, "n3", "Person")

    temporal_service._changes[tenant_id] = [c1, c2, c3]

    # Filter by time
    changes = await temporal_service.get_changes(
        tenant_id,
        start_time=now - timedelta(minutes=90),
        end_time=now - timedelta(minutes=30),
    )
    assert len(changes) == 1
    assert changes[0] == c2

    # Filter by type
    changes = await temporal_service.get_changes(
        tenant_id, change_types=[ChangeType.NODE_ADDED]
    )
    assert len(changes) == 1
    assert changes[0] == c1

    # Filter by entity_id
    changes = await temporal_service.get_changes(tenant_id, entity_id="n3")
    assert len(changes) == 1
    assert changes[0] == c3


@pytest.mark.asyncio
async def test_get_entity_history(temporal_service):
    tenant_id = uuid4()
    c1 = GraphChange(ChangeType.NODE_ADDED, datetime.now(timezone.utc), "n1", "Person")
    c2 = GraphChange(
        ChangeType.NODE_UPDATED, datetime.now(timezone.utc), "n1", "Person"
    )
    temporal_service._changes[tenant_id] = [c1, c2]

    history = await temporal_service.get_entity_history(tenant_id, "n1")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_reconstruct_graph_at_time(temporal_service, sample_graph):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # Snapshot at T-2h
    snapshot = GraphSnapshot(tenant_id, now - timedelta(hours=2), sample_graph)
    temporal_service._snapshots[tenant_id] = [snapshot]

    # Changes at T-1h
    # Add node n3
    c1 = GraphChange(
        ChangeType.NODE_ADDED,
        now - timedelta(hours=1),
        "n3",
        "Person",
        new_value={"entity_type": "Person", "properties": {}},
    )
    # Add edge n2->n3
    c2 = GraphChange(
        ChangeType.EDGE_ADDED,
        now - timedelta(minutes=50),
        "n2->n3",
        "knows",
        new_value={"source_id": "n2", "target_id": "n3", "relation_type": "knows"},
    )

    temporal_service._changes[tenant_id] = [c1, c2]

    # Reconstruct at now
    graph = await temporal_service.reconstruct_graph_at_time(tenant_id, now)

    assert graph.node_count() == 3  # n1, n2 + n3
    assert graph.edge_count() == 2  # n1->n2 + n2->n3
    assert "n3" in graph.nodes
    assert "n2" in graph.nodes
    neighbors = graph.get_neighbors("n2")
    assert "n3" in neighbors


@pytest.mark.asyncio
async def test_apply_change_logic(temporal_service):
    graph = KnowledgeGraph()

    # Add node
    c1 = GraphChange(
        ChangeType.NODE_ADDED,
        datetime.now(timezone.utc),
        "n1",
        "Person",
        new_value={"entity_type": "Person", "properties": {"a": 1}},
    )
    graph = temporal_service._apply_change(graph, c1)
    assert "n1" in graph.nodes
    assert graph.nodes["n1"].properties["a"] == 1

    # Update node
    c2 = GraphChange(
        ChangeType.NODE_UPDATED,
        datetime.now(timezone.utc),
        "n1",
        "Person",
        new_value={"properties": {"b": 2}},
    )
    graph = temporal_service._apply_change(graph, c2)
    assert graph.nodes["n1"].properties["a"] == 1
    assert graph.nodes["n1"].properties["b"] == 2

    # Remove node
    c3 = GraphChange(
        ChangeType.NODE_REMOVED, datetime.now(timezone.utc), "n1", "Person"
    )
    graph = temporal_service._apply_change(graph, c3)
    assert "n1" not in graph.nodes


@pytest.mark.asyncio
async def test_compare_graphs(temporal_service):
    g1 = KnowledgeGraph()
    g1.add_node(GraphNode("n1", "Person"))

    g2 = KnowledgeGraph()
    g2.add_node(GraphNode("n1", "Person"))
    g2.add_node(GraphNode("n2", "Person"))  # Added
    g2.add_edge(GraphEdge("n1", "n2", "knows"))  # Added

    diff = await temporal_service.compare_graphs(g1, g2)

    assert diff["nodes_added"] == ["n2"]
    assert diff["nodes_removed"] == []
    assert len(diff["edges_added"]) == 1
    assert diff["edges_added"][0]["source"] == "n1"
    assert diff["edges_added"][0]["target"] == "n2"


@pytest.mark.asyncio
async def test_get_evolution_timeline(temporal_service):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # 3 changes in same hour
    c1 = GraphChange(ChangeType.NODE_ADDED, now.replace(minute=10), "n1", "A")
    c2 = GraphChange(ChangeType.NODE_ADDED, now.replace(minute=20), "n2", "A")
    c3 = GraphChange(ChangeType.EDGE_ADDED, now.replace(minute=30), "n1->n2", "R")

    temporal_service._changes[tenant_id] = [c1, c2, c3]

    timeline = await temporal_service.get_evolution_timeline(tenant_id)

    assert len(timeline) == 1
    assert timeline[0]["total_changes"] == 3
    assert timeline[0]["by_type"][ChangeType.NODE_ADDED.value] == 2


@pytest.mark.asyncio
async def test_get_growth_metrics(temporal_service, sample_graph):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # Start: empty graph
    GraphSnapshot(tenant_id, now - timedelta(days=30), KnowledgeGraph())

    # End: sample graph (2 nodes, 1 edge)
    # Actually, reconstruct_graph_at_time uses get_changes logic if snapshot is old.
    # To test growth metrics, we need snapshots covering the period or changes.
    # Let's mock reconstruct_graph_at_time to return specific graphs

    g_start = KnowledgeGraph()
    g_start.add_node(GraphNode("n1", "A"))  # 1 node

    g_end = KnowledgeGraph()
    g_end.add_node(GraphNode("n1", "A"))
    g_end.add_node(GraphNode("n2", "A"))  # 2 nodes
    g_end.add_edge(GraphEdge("n1", "n2", "L"))  # 1 edge

    with patch.object(
        temporal_service, "reconstruct_graph_at_time", side_effect=[g_start, g_end]
    ):
        metrics = await temporal_service.get_growth_metrics(tenant_id, period_days=30)

        assert metrics["nodes"]["start"] == 1
        assert metrics["nodes"]["end"] == 2
        assert metrics["nodes"]["growth"] == 1
        assert metrics["edges"]["end"] == 1


@pytest.mark.asyncio
async def test_find_emerging_patterns(temporal_service):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # n1 gets many new edges
    changes = []
    for i in range(5):
        changes.append(
            GraphChange(
                ChangeType.EDGE_ADDED,
                now - timedelta(days=1),
                f"n1->m{i}",
                "rel",
                new_value={"source_id": "n1", "target_id": f"m{i}"},
            )
        )

    temporal_service._changes[tenant_id] = changes

    patterns = await temporal_service.find_emerging_patterns(tenant_id)

    assert len(patterns) >= 1
    p = patterns[0]
    assert p["type"] == "rapidly_growing_entity"
    assert p["entity_id"] == "n1"
    assert p["new_connections"] == 5


@pytest.mark.asyncio
async def test_cleanup_old_snapshots(temporal_service, sample_graph):
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # Old snapshot
    s1 = GraphSnapshot(tenant_id, now - timedelta(days=100), sample_graph)
    # New snapshot
    s2 = GraphSnapshot(tenant_id, now - timedelta(days=10), sample_graph)

    temporal_service._snapshots[tenant_id] = [s1, s2]

    deleted = await temporal_service.cleanup_old_snapshots(tenant_id, retention_days=90)

    assert deleted == 1
    assert len(temporal_service._snapshots[tenant_id]) == 1
    assert temporal_service._snapshots[tenant_id][0] == s2
