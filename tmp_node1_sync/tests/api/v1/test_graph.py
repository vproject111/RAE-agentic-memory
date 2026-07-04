from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.main import app
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.graph_extraction import GraphExtractionResult
from apps.memory_api.services.rae_core_service import RAECoreService


# Mock data models
class MockNode:
    def __init__(self, id):
        self.id = id


class MockEdge:
    def __init__(self, source_id, target_id):
        self.source_id = source_id
        self.target_id = target_id


@pytest.fixture
def mock_reflection_engine():
    with patch("apps.memory_api.api.v1.graph.ReflectionEngine") as MockEngine:
        instance = MockEngine.return_value
        instance.extract_knowledge_graph_enhanced = AsyncMock()
        instance.generate_hierarchical_reflection = AsyncMock()
        yield instance


@pytest.fixture
def mock_rae_service():
    service = AsyncMock(spec=RAECoreService)
    # Mock methods used in graph endpoints if any (currently mostly placeholders)
    return service


@pytest.fixture
def mock_db_pool():
    connection = AsyncMock()
    pool = MagicMock()

    # Make close awaitable for lifespan shutdown
    pool.close = AsyncMock()

    # Setup async context manager for acquire
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=connection)
    cm.__aexit__ = AsyncMock(return_value=None)

    pool.acquire.return_value = cm

    app.state.pool = pool
    yield pool, connection
    del app.state.pool


@pytest.fixture
def client_with_auth(mock_rae_service, mock_db_pool):
    pool, _ = mock_db_pool

    tenant_id = str(uuid4())  # Valid UUID for tests

    # Override auth dependency
    app.dependency_overrides[get_and_verify_tenant_id] = lambda: tenant_id
    app.dependency_overrides[get_rae_core_service] = lambda: mock_rae_service

    # Patch asyncpg.create_pool to return our mock pool
    # And patch rebuild_full_cache since it's called in startup
    with (
        patch(
            "rae_adapters.infra_factory.asyncpg.create_pool",
            new=AsyncMock(return_value=pool),
        ),
        patch("apps.memory_api.main.rebuild_full_cache", new=AsyncMock()),
    ):
        with TestClient(app) as client:
            # Store tenant_id on client for tests to access
            client.tenant_id = tenant_id  # type: ignore[attr-defined]
            yield client

    app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_extract_knowledge_graph(client_with_auth, mock_reflection_engine):
    """Test POST /graph/extract"""

    mock_result = GraphExtractionResult(
        triples=[{"source": "A", "relation": "to", "target": "B"}],
        extracted_entities=["A", "B"],
        statistics={"nodes": 2, "edges": 1},
    )
    mock_reflection_engine.extract_knowledge_graph_enhanced.return_value = mock_result

    payload = {
        "project_id": "test-project",
        "limit": 10,
        "min_confidence": 0.7,
        "auto_store": True,
    }

    headers = {"X-Tenant-Id": client_with_auth.tenant_id}

    response = client_with_auth.post("/v1/graph/extract", json=payload, headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["triples"]) == 1
    assert data["extracted_entities"] == ["A", "B"]
    mock_reflection_engine.extract_knowledge_graph_enhanced.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_generate_hierarchical_reflection(
    client_with_auth, mock_reflection_engine, mock_db_pool
):
    """Test POST /graph/reflection/hierarchical"""

    mock_reflection_engine.generate_hierarchical_reflection.return_value = (
        "Summary of episodes"
    )
    pool, conn = mock_db_pool
    conn.fetchval.return_value = 42  # Episode count

    payload = {"project_id": "test-project", "bucket_size": 5}
    headers = {"X-Tenant-Id": client_with_auth.tenant_id}

    response = client_with_auth.post(
        "/v1/graph/reflection/hierarchical", json=payload, headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Summary of episodes"
    assert data["episodes_processed"] == 42

    mock_reflection_engine.generate_hierarchical_reflection.assert_called_once()
    conn.fetchval.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_graph_statistics(client_with_auth, mock_db_pool):
    """Test GET /graph/stats"""
    pool, conn = mock_db_pool

    # Mock sequence of calls: node_count, edge_count, relations
    conn.fetchval.side_effect = [100, 200]  # nodes, edges
    conn.fetch.return_value = [{"relation": "rel1"}, {"relation": "rel2"}]

    headers = {"X-Tenant-Id": client_with_auth.tenant_id}
    response = client_with_auth.get(
        "/v1/graph/stats?project_id=test-project", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_nodes"] == 100
    assert data["total_edges"] == 200
    assert data["unique_relations"] == ["rel1", "rel2"]
    assert data["statistics"]["avg_edges_per_node"] == 2.0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_graph_nodes(client_with_auth, mock_db_pool):
    """Test GET /graph/nodes"""
    pool, conn = mock_db_pool

    mock_node = {
        "id": uuid4(),
        "node_id": "node1",
        "label": "Person",
        "properties": {"name": "Alice"},
        "created_at": "2023-01-01T00:00:00Z",
    }
    conn.fetch.return_value = [mock_node]

    headers = {"X-Tenant-Id": client_with_auth.tenant_id}
    response = client_with_auth.get(
        "/v1/graph/nodes?project_id=test-project&limit=10", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["node_id"] == "node1"
    assert data[0]["label"] == "Person"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_graph_nodes_with_pagerank(client_with_auth, mock_db_pool):
    """Test GET /graph/nodes with PageRank"""
    pool, conn = mock_db_pool

    with patch(
        "apps.memory_api.services.graph_algorithms.GraphAlgorithmsService"
    ) as MockAlgo:
        algo_instance = MockAlgo.return_value
        # Mock PageRank results
        node_uuid = uuid4()
        algo_instance.pagerank = AsyncMock(return_value={str(node_uuid): 0.5})

        mock_node = {
            "id": node_uuid,
            "node_id": "node1",
            "label": "Person",
            "properties": {"name": "Alice"},
            "created_at": "2023-01-01T00:00:00Z",
        }
        conn.fetchrow.return_value = mock_node

        headers = {"X-Tenant-Id": client_with_auth.tenant_id}
        response = client_with_auth.get(
            "/v1/graph/nodes?project_id=test-project&use_pagerank=true&limit=10",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["properties"]["pagerank_score"] == 0.5
        algo_instance.pagerank.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_graph_edges(client_with_auth, mock_db_pool):
    """Test GET /graph/edges"""
    pool, conn = mock_db_pool

    mock_edge = {
        "id": uuid4(),
        "source_node_id": uuid4(),
        "target_node_id": uuid4(),
        "relation": "KNOWS",
        "properties": {},
        "created_at": "2023-01-01T00:00:00Z",
    }
    conn.fetch.return_value = [mock_edge]

    headers = {"X-Tenant-Id": client_with_auth.tenant_id}
    response = client_with_auth.get(
        "/v1/graph/edges?project_id=test-project&relation=KNOWS", headers=headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["relation"] == "KNOWS"


@pytest.mark.asyncio
async def test_query_knowledge_graph(client_with_auth, mock_db_pool):
    """Test POST /graph/query"""
    # Mock HybridSearchService
    with patch("apps.memory_api.api.v1.graph.HybridSearchService") as MockService:
        service_instance = MockService.return_value
        mock_result = MagicMock()
        mock_result.results = []
        mock_result.graph_results_count = 0
        mock_result.model_dump.return_value = {
            "results": [],
            "graph_results_count": 0,
            "total_results": 0,
        }
        service_instance.search = AsyncMock(return_value=mock_result)

        payload = {
            "query": "test query",
            "project_id": "test-project",
            "traversal_strategy": "bfs",
        }
        headers = {"X-Tenant-Id": client_with_auth.tenant_id}

        response = client_with_auth.post(
            "/v1/graph/query", json=payload, headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        service_instance.search.assert_called_once()


@pytest.mark.asyncio
async def test_get_subgraph(client_with_auth, mock_db_pool):
    """Test GET /graph/subgraph"""
    with patch("apps.memory_api.api.v1.graph.EnhancedGraphRepository") as MockRepo:
        repo_instance = MockRepo.return_value

        # Mock node resolution
        node_uuid = uuid4()
        mock_node_obj = MagicMock()
        mock_node_obj.id = node_uuid
        repo_instance.get_node_by_node_id = AsyncMock(return_value=mock_node_obj)

        # Mock traversal
        repo_instance.traverse_temporal = AsyncMock(return_value=([], []))

        node_id = "test-node-id"
        headers = {"X-Tenant-Id": client_with_auth.tenant_id}
        response = client_with_auth.get(
            f"/v1/graph/subgraph?project_id=test-project&node_ids={node_id}&depth=2",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        repo_instance.get_node_by_node_id.assert_called_once()
        repo_instance.traverse_temporal.assert_called_once()


@pytest.mark.asyncio
async def test_error_handling_missing_tenant(client_with_auth):
    """Test error when tenant header is missing"""
    # Do not pass headers with X-Tenant-Id
    response = client_with_auth.get("/v1/graph/stats?project_id=test-project")

    assert response.status_code == 400
    if "detail" in response.json():
        assert "X-Tenant-Id header is required" in response.json()["detail"]
    else:
        # Custom error handling wrapper might trigger
        assert "X-Tenant-Id header is required" in response.json().get("error", {}).get(
            "message", ""
        ) or "X-Tenant-Id header is required" in str(response.json())
