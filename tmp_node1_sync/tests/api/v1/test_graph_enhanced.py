from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from apps.memory_api.models.graph_enhanced_models import (
    ActivateEdgeRequest,
    BatchCreateEdgesRequest,
    BatchCreateNodesRequest,
    CreateGraphEdgeRequest,
    CreateGraphNodeRequest,
    CreateSnapshotRequest,
    CycleDetectionResult,
    DeactivateEdgeRequest,
    DetectCycleRequest,
    EnhancedGraphEdge,
    EnhancedGraphNode,
    FindPathRequest,
    GetGraphStatisticsRequest,
    GraphPath,
    GraphSnapshot,
    GraphStatistics,
    NodeDegreeMetrics,
    RestoreSnapshotRequest,
    SetEdgeTemporalValidityRequest,
    TraversalAlgorithm,
    TraverseGraphRequest,
    UpdateEdgeWeightRequest,
)
from apps.memory_api.routes.graph_enhanced import (
    activate_edge,
    batch_create_edges,
    batch_create_nodes,
    create_edge,
    create_node,
    create_snapshot,
    deactivate_edge,
    detect_cycle,
    find_shortest_path,
    get_graph_statistics,
    get_node_metrics,
    get_snapshot,
    health_check,
    list_snapshots,
    restore_snapshot,
    set_edge_temporal_validity,
    traverse_graph,
    update_edge_weight,
)

# --- Fixtures ---


@pytest.fixture
def mock_repo():
    return AsyncMock()


@pytest.fixture
def mock_rae_service(mock_repo):
    service = MagicMock()
    service.postgres_pool = AsyncMock()
    service.enhanced_graph_repo = mock_repo
    return service


# --- Node Operations Tests ---


@pytest.mark.asyncio
async def test_create_node(mock_repo, mock_rae_service):
    node_uuid = uuid4()
    req = CreateGraphNodeRequest(
        tenant_id="t1",
        project_id="p1",
        node_id=str(node_uuid),
        label="Test Node",
        properties={"key": "value"},
    )

    mock_node = EnhancedGraphNode(
        id=node_uuid,
        tenant_id="t1",
        project_id="p1",
        node_id=str(node_uuid),
        label="Test Node",
        created_at=datetime.now(timezone.utc),
    )
    mock_repo.create_node.return_value = mock_node

    response = await create_node(req, mock_rae_service)

    assert str(response.id) == str(node_uuid)
    assert response.label == "Test Node"
    mock_repo.create_node.assert_called_once()


@pytest.mark.asyncio
async def test_get_node_metrics(mock_repo, mock_rae_service):
    node_id = uuid4()
    mock_metrics = NodeDegreeMetrics(
        node_id=node_id, in_degree=2, out_degree=3, total_degree=5
    )
    mock_repo.get_node_metrics.return_value = mock_metrics

    response = await get_node_metrics("t1", "p1", str(node_id), mock_rae_service)

    assert response.metrics.total_degree == 5
    assert str(response.node_id) == str(node_id)


# --- Edge Operations Tests ---


@pytest.mark.asyncio
async def test_create_edge_success(mock_repo, mock_rae_service):
    req = CreateGraphEdgeRequest(
        tenant_id="t1",
        project_id="p1",
        source_node_id=str(uuid4()),
        target_node_id=str(uuid4()),
        relation="RELATES_TO",
    )

    mock_repo.detect_cycle.return_value = MagicMock(has_cycle=False)

    mock_edge = EnhancedGraphEdge(
        id=uuid4(),
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="RELATES_TO",
        valid_from=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_repo.create_edge.return_value = mock_edge

    response = await create_edge(req, mock_rae_service)

    assert response.relation == "RELATES_TO"
    mock_repo.create_edge.assert_called_once()


@pytest.mark.asyncio
async def test_create_edge_failure(mock_repo, mock_rae_service):
    req = CreateGraphEdgeRequest(
        tenant_id="t1",
        project_id="p1",
        source_node_id=str(uuid4()),
        target_node_id=str(uuid4()),
        relation="RELATES_TO",
    )
    mock_repo.detect_cycle.side_effect = Exception("DB Error")
    with pytest.raises(HTTPException) as exc:
        await create_edge(req, mock_rae_service)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_edge_weight(mock_repo, mock_rae_service):
    edge_id = uuid4()
    req = UpdateEdgeWeightRequest(edge_id=edge_id, new_weight=0.8, new_confidence=0.9)

    mock_repo.update_edge_weight.return_value = EnhancedGraphEdge(
        id=edge_id,
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="rel",
        edge_weight=0.8,
        confidence=0.9,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
    )

    response = await update_edge_weight(str(edge_id), req, mock_rae_service)
    assert response.edge_weight == 0.8
    assert response.confidence == 0.9


@pytest.mark.asyncio
async def test_deactivate_edge(mock_repo, mock_rae_service):
    edge_id = uuid4()
    req = DeactivateEdgeRequest(edge_id=edge_id, reason="Outdated")

    mock_repo.deactivate_edge.return_value = EnhancedGraphEdge(
        id=edge_id,
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="rel",
        is_active=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
    )

    response = await deactivate_edge(str(edge_id), req, mock_rae_service)
    assert response.is_active is False


@pytest.mark.asyncio
async def test_activate_edge(mock_repo, mock_rae_service):
    edge_id = uuid4()
    req = ActivateEdgeRequest(edge_id=edge_id)

    mock_repo.activate_edge.return_value = EnhancedGraphEdge(
        id=edge_id,
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="rel",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
    )

    response = await activate_edge(str(edge_id), req, mock_rae_service)
    assert response.is_active is True


@pytest.mark.asyncio
async def test_set_edge_temporal_validity(mock_repo, mock_rae_service):
    edge_id = uuid4()
    start = datetime.now(timezone.utc)
    req = SetEdgeTemporalValidityRequest(edge_id=edge_id, valid_from=start)

    mock_repo.set_edge_temporal_validity.return_value = EnhancedGraphEdge(
        id=edge_id,
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="rel",
        valid_from=start,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    response = await set_edge_temporal_validity(str(edge_id), req, mock_rae_service)
    assert response.valid_from == start


# --- Traversal & Analysis Tests ---


@pytest.mark.asyncio
async def test_traverse_graph(mock_repo, mock_rae_service):
    req = TraverseGraphRequest(
        tenant_id="t1",
        project_id="p1",
        start_node_id=uuid4(),
        algorithm=TraversalAlgorithm.BFS,
        max_depth=2,
    )

    mock_repo.traverse_temporal.return_value = ([], [])
    response = await traverse_graph(req, mock_rae_service)
    assert response.total_nodes == 0


@pytest.mark.asyncio
async def test_detect_cycle(mock_repo, mock_rae_service):
    source_id = uuid4()
    target_id = uuid4()
    req = DetectCycleRequest(
        tenant_id="t1",
        project_id="p1",
        source_node_id=source_id,
        target_node_id=target_id,
    )
    mock_repo.detect_cycle.return_value = CycleDetectionResult(
        has_cycle=True,
        cycle_length=3,
        source_node_id=source_id,
        target_node_id=target_id,
    )

    response = await detect_cycle(req, mock_rae_service)
    assert response.result.has_cycle is True


@pytest.mark.asyncio
async def test_find_shortest_path(mock_repo, mock_rae_service):
    req = FindPathRequest(
        tenant_id="t1", project_id="p1", start_node_id=uuid4(), end_node_id=uuid4()
    )
    mock_repo.find_shortest_path.return_value = GraphPath(
        nodes=[], length=0, total_weight=0
    )

    response = await find_shortest_path(req, mock_rae_service)
    assert response.path_found is True


@pytest.mark.asyncio
async def test_get_graph_statistics(mock_repo, mock_rae_service):
    req = GetGraphStatisticsRequest(tenant_id="t1", project_id="p1")
    mock_repo.get_graph_statistics.return_value = GraphStatistics(
        tenant_id="t1",
        project_id="p1",
        total_nodes=100,
        total_edges=200,
        avg_degree=4.0,
        snapshot_count=2,
        last_snapshot_at=None,
    )

    response = await get_graph_statistics(req, mock_rae_service)
    assert response.statistics.total_nodes == 100


# --- Snapshot Tests ---


@pytest.mark.asyncio
async def test_create_snapshot(mock_repo, mock_rae_service):
    req = CreateSnapshotRequest(tenant_id="t1", project_id="p1", snapshot_name="Snap1")
    snap_id = uuid4()
    mock_repo.create_snapshot.return_value = snap_id
    mock_repo.get_snapshot.return_value = GraphSnapshot(
        id=snap_id,
        tenant_id="t1",
        project_id="p1",
        snapshot_name="Snap1",
        node_count=10,
        edge_count=10,
        snapshot_size_bytes=100,
        created_at=datetime.now(timezone.utc),
    )

    response = await create_snapshot(req, mock_rae_service)
    assert response.snapshot_id == snap_id


@pytest.mark.asyncio
async def test_get_snapshot(mock_repo, mock_rae_service):
    snap_id = uuid4()
    mock_repo.get_snapshot.return_value = GraphSnapshot(
        id=snap_id,
        tenant_id="t1",
        project_id="p1",
        snapshot_name="Snap1",
        node_count=10,
        edge_count=10,
        snapshot_size_bytes=100,
        created_at=datetime.now(timezone.utc),
    )

    response = await get_snapshot(str(snap_id), mock_rae_service)
    assert response.id == snap_id


@pytest.mark.asyncio
async def test_get_snapshot_not_found(mock_repo, mock_rae_service):
    mock_repo.get_snapshot.return_value = None
    with pytest.raises(HTTPException) as exc:
        await get_snapshot(str(uuid4()), mock_rae_service)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_snapshots(mock_repo, mock_rae_service):
    mock_repo.list_snapshots.return_value = []
    response = await list_snapshots("t1", "p1", 10, mock_rae_service)
    assert response == []


@pytest.mark.asyncio
async def test_restore_snapshot(mock_repo, mock_rae_service):
    snap_id = uuid4()
    req = RestoreSnapshotRequest(snapshot_id=snap_id, clear_existing=True)
    mock_repo.restore_snapshot.return_value = (10, 20)

    response = await restore_snapshot(str(snap_id), req, mock_rae_service)
    assert response.nodes_restored == 10
    assert response.edges_restored == 20


# --- Batch Operations Tests ---


@pytest.mark.asyncio
async def test_batch_create_nodes(mock_repo, mock_rae_service):
    req = BatchCreateNodesRequest(
        tenant_id="t1", project_id="p1", nodes=[{"node_id": "n1", "label": "l1"}]
    )
    mock_repo.batch_create_nodes.return_value = (5, ["Error 1"])

    response = await batch_create_nodes(req, mock_rae_service)
    assert response.successful == 5
    assert response.failed == 1
    assert len(response.errors) == 1


@pytest.mark.asyncio
async def test_batch_create_edges(mock_repo, mock_rae_service):
    edge_req = CreateGraphEdgeRequest(
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="r",
    )
    req = BatchCreateEdgesRequest(tenant_id="t1", project_id="p1", edges=[edge_req])

    # Successful creation
    mock_edge = EnhancedGraphEdge(
        id=uuid4(),
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="r",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
    )
    mock_repo.create_edge.return_value = mock_edge

    response = await batch_create_edges(req, mock_rae_service)
    assert response.successful == 1
    assert response.failed == 0


@pytest.mark.asyncio
async def test_batch_create_edges_partial_failure(mock_repo, mock_rae_service):
    edge_req1 = CreateGraphEdgeRequest(
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="r",
    )
    edge_req2 = CreateGraphEdgeRequest(
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="r",
    )
    req = BatchCreateEdgesRequest(
        tenant_id="t1", project_id="p1", edges=[edge_req1, edge_req2]
    )

    # First succeeds, second fails
    mock_edge = EnhancedGraphEdge(
        id=uuid4(),
        tenant_id="t1",
        project_id="p1",
        source_node_id=uuid4(),
        target_node_id=uuid4(),
        relation="r",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        valid_from=datetime.now(timezone.utc),
    )
    mock_repo.create_edge.side_effect = [mock_edge, Exception("Cycle detected")]

    response = await batch_create_edges(req, mock_rae_service)
    assert response.successful == 1
    assert response.failed == 1
    assert len(response.errors) == 1


@pytest.mark.asyncio
async def test_health_check():
    response = await health_check()
    assert response["status"] == "healthy"
    assert response["service"] == "enhanced_graph_api"
