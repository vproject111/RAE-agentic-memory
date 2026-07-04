from unittest.mock import AsyncMock, patch

import pytest


class TestMemoryAPI:
    """
    Test suite for Memory API endpoints.
    """


@pytest.mark.asyncio
async def test_store_memory_success(client_with_overrides, mock_rae_service):
    """Test successful memory storage via RAECoreService."""
    payload = {
        "content": "Test content",
        "source": "cli",
        "layer": "em",
        "tags": ["test"],
        "project": "default",
        "importance": 0.5,
    }

    response = client_with_overrides.post(
        "/v1/memory/store", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == "test-memory-id"

    # Verify RAECoreService was called correctly
    mock_rae_service.store_memory.assert_called_once()
    call_args = mock_rae_service.store_memory.call_args[1]
    assert call_args["content"] == "Test content"
    assert call_args["source"] == "cli"
    assert call_args["project"] == "default"


@pytest.mark.asyncio
async def test_store_memory_failure(client_with_overrides, mock_rae_service):
    """Test handling of storage failure."""
    mock_rae_service.store_memory.side_effect = Exception("Storage Error")

    payload = {
        "content": "Test content",
        "source": "cli",
        "project": "default",
        "importance": 0.5,
    }

    response = client_with_overrides.post(
        "/v1/memory/store", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 500
    assert "Storage error" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_query_memory_vector_only(
    client_with_overrides, mock_vector_store, mock_rae_service
):
    """Test memory query using vector search."""
    # Mock RAECoreService response
    from rae_core.models.search import SearchResponse, SearchResult, SearchStrategy

    mock_result = SearchResult(
        memory_id="mem-1",
        content="Found content",
        score=0.95,
        strategy_used=SearchStrategy.HYBRID,
        metadata={"project": "proj", "source": "src"},
    )

    mock_rae_service.query_memories.return_value = SearchResponse(
        results=[mock_result],
        total_found=1,
        query="test query",
        strategy=SearchStrategy.HYBRID,
        execution_time_ms=10.0,
    )

    payload = {"query_text": "test query", "k": 1}

    response = client_with_overrides.post(
        "/v1/memory/query", json=payload, headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["id"] == "mem-1"

    # Verify stats update called on RAECoreService
    mock_rae_service.update_memory_access_batch.assert_called_once()


@pytest.mark.asyncio
async def test_delete_memory_success(
    client_with_overrides, mock_rae_service, mock_vector_store
):
    """Test successful memory deletion."""
    mock_rae_service.delete_memory.return_value = True

    response = client_with_overrides.delete(
        "/v1/memory/delete?memory_id=mem-1", headers={"X-Tenant-Id": "test-tenant"}
    )

    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    mock_rae_service.delete_memory.assert_called_once_with("mem-1", "test-tenant")
    mock_vector_store.delete.assert_called_once_with("mem-1")


@pytest.mark.asyncio
async def test_delete_memory_not_found(client_with_overrides, mock_rae_service):
    """Test delete memory that doesn't exist."""
    mock_rae_service.delete_memory.return_value = False

    response = client_with_overrides.delete(
        "/v1/memory/delete?memory_id=nonexistent",
        headers={"X-Tenant-Id": "test-tenant"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_reflection_stats(client_with_overrides, mock_rae_service):
    """Test retrieval of reflection statistics."""
    mock_rae_service.count_memories.return_value = 42
    mock_rae_service.get_metric_aggregate.return_value = 0.75

    response = client_with_overrides.get(
        "/v1/memory/reflection-stats?project=test-project",
        headers={"X-Tenant-Id": "test-tenant"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["reflective_memory_count"] == 42
    assert data["average_strength"] == 0.75

    mock_rae_service.count_memories.assert_called_once()
    mock_rae_service.get_metric_aggregate.assert_called_once()


@pytest.mark.asyncio
async def test_hierarchical_reflection_deprecated(
    client_with_overrides, mock_rae_service
):
    """Test deprecated hierarchical reflection endpoint."""
    with patch(
        "apps.memory_api.services.reflection_engine.ReflectionEngine"
    ) as MockEngine:
        mock_engine_instance = AsyncMock()
        MockEngine.return_value = mock_engine_instance
        mock_engine_instance.generate_hierarchical_reflection.return_value = "Summary"

        # Mock stats
        mock_rae_service.count_memories.return_value = 10

        response = client_with_overrides.post(
            "/v1/memory/reflection/hierarchical?project=my-project&bucket_size=15",
            headers={"X-Tenant-Id": "test-tenant"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Summary"
        assert data["statistics"]["episode_count"] == 10
