"""
API Contract Tests for V2 (RAE-Core)

These tests ensure that the new V2 API endpoints maintain their contract.
"""

from typing import Any, Dict, List
from unittest.mock import patch, MagicMock
import pytest

try:
    from apps.memory_api.api.v2.memory import (
        StoreMemoryResponseV2,
        QueryMemoryResponseV2,
        MemoryResult
    )
    HAS_V2_MODELS = True
except ImportError:
    HAS_V2_MODELS = False

# Check if test infrastructure is available
try:
    from apps.memory_api.services.rae_core_service import RAECoreService
    HAS_TEST_INFRASTRUCTURE = True
except ImportError:
    HAS_TEST_INFRASTRUCTURE = False


def assert_v2_schema(data: Dict[str, Any], expected_schema: Dict[str, type]):
    """Helper to assert schema matching."""
    for field, expected_type in expected_schema.items():
        assert field in data, f"Missing required field: {field}"
        value = data[field]
        if value is None:
            continue
        if expected_type is list:
            assert isinstance(value, list), f"{field} should be list"
        elif expected_type is dict:
            assert isinstance(value, dict), f"{field} should be dict"
        else:
            assert isinstance(value, expected_type), f"{field} should be {expected_type}"


@pytest.mark.contract
@pytest.mark.skipif(not HAS_TEST_INFRASTRUCTURE, reason="Test infrastructure not available")
class TestMemoryStoreContractV2:
    """Contract tests for /v2/memories/ endpoint"""

    def test_store_memory_v2_response_schema(self, client_with_overrides):
        """Ensure V2 store memory returns correct schema"""
        payload = {
            "content": "Test memory content v2",
            "source": "test-contract",
            "layer": "working",
            "importance": 0.9,
            "project": "test-project-v2",
            "tags": ["contract", "v2"],
            "metadata": {"test": True}
        }

        response = client_with_overrides.post(
            "/v2/memories/", 
            json=payload, 
            headers={"X-Tenant-Id": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()

        expected_schema = {
            "memory_id": str,
            "message": str
        }
        assert_v2_schema(data, expected_schema)
        assert data["message"] == "Memory stored in RAE-Core"


@pytest.mark.contract
@pytest.mark.skipif(not HAS_TEST_INFRASTRUCTURE, reason="Test infrastructure not available")
class TestMemoryQueryContractV2:
    """Contract tests for /v2/memories/query endpoint"""

    def test_query_memory_v2_response_schema(self, client_with_overrides, mock_rae_service):
        """Ensure V2 query memory returns correct schema"""
        # Configure mock to return valid search response
        mock_result = MagicMock()
        mock_result.id = "test-1"
        mock_result.content = "found content"
        mock_result.score = 0.95
        mock_result.layer = "working"
        mock_result.importance = 0.8
        mock_result.tags = ["tag1"]
        mock_result.metadata = {"key": "val"}

        mock_query_response = MagicMock()
        mock_query_response.results = [mock_result]
        mock_query_response.synthesized_context = "Summary"
        
        mock_rae_service.query_memories.return_value = mock_query_response

        payload = {
            "query": "test query v2",
            "project": "test-project-v2",
            "k": 5,
            "layers": ["working", "longterm"],
            "filters": {"source": "test"}
        }

        response = client_with_overrides.post(
            "/v2/memories/query", 
            json=payload, 
            headers={"X-Tenant-Id": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()

        # Top level fields
        expected_top_schema = {
            "results": list,
            "total_count": int,
        }
        
        assert "results" in data
        assert "total_count" in data
        assert isinstance(data["results"], list)
        assert isinstance(data["total_count"], int)
        if data.get("synthesized_context") is not None:
            assert isinstance(data["synthesized_context"], str)

        # Result item fields
        if data["results"]:
            result = data["results"][0]
            assert "id" in result
            assert "content" in result
            assert "score" in result
            assert "layer" in result


@pytest.mark.contract
@pytest.mark.skipif(not HAS_TEST_INFRASTRUCTURE, reason="Test infrastructure not available")
class TestMemoryDeleteContractV2:
    """Contract tests for /v2/memories/{id} endpoint"""

    def test_delete_memory_v2_response_schema(self, client_with_overrides, mock_rae_service):
        """Ensure V2 delete memory returns correct schema"""
        mock_rae_service.delete_memory.return_value = True
        memory_id = "00000000-0000-0000-0000-000000000001"

        response = client_with_overrides.delete(
            f"/v2/memories/{memory_id}",
            headers={"X-Tenant-Id": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()

        expected_schema = {
            "message": str,
            "memory_id": str
        }
        assert_v2_schema(data, expected_schema)
        assert data["memory_id"] == memory_id


@pytest.mark.contract
@pytest.mark.skipif(not HAS_TEST_INFRASTRUCTURE, reason="Test infrastructure not available")
class TestMemoryConsolidateContractV2:
    """Contract tests for /v2/memories/consolidate endpoint"""

    def test_consolidate_memories_response_schema(self, client_with_overrides, mock_rae_service):
        """Ensure consolidate endpoint returns correct schema"""
        mock_rae_service.consolidate_memories.return_value = {"processed": 10, "moved": 5}
        
        response = client_with_overrides.post(
            "/v2/memories/consolidate?project=test-project",
            headers={"X-Tenant-Id": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "results" in data
        assert isinstance(data["results"], dict)


@pytest.mark.contract
@pytest.mark.skipif(not HAS_TEST_INFRASTRUCTURE, reason="Test infrastructure not available")
class TestMemoryReflectionsContractV2:
    """Contract tests for /v2/memories/reflections endpoint"""

    def test_generate_reflections_response_schema(self, client_with_overrides, mock_rae_service):
        """Ensure reflections generation returns correct schema"""
        # Mock return list of objects with id, content, etc.
        MockReflection = MagicMock()
        MockReflection.id = "ref-1"
        MockReflection.content = "Insight"
        MockReflection.importance = 0.8
        MockReflection.tags = ["tag"]
        
        mock_rae_service.generate_reflections.return_value = [MockReflection]

        response = client_with_overrides.post(
            "/v2/memories/reflections?project=test-project",
            headers={"X-Tenant-Id": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "count" in data
        assert "reflections" in data
        assert isinstance(data["reflections"], list)
        if data["reflections"]:
            ref = data["reflections"][0]
            assert "id" in ref
            assert "content" in ref
            assert "importance" in ref


@pytest.mark.contract
@pytest.mark.skipif(not HAS_TEST_INFRASTRUCTURE, reason="Test infrastructure not available")
class TestMemoryStatsContractV2:
    """Contract tests for /v2/memories/stats endpoint"""

    def test_get_statistics_response_schema(self, client_with_overrides, mock_rae_service):
        """Ensure statistics endpoint returns correct schema"""
        mock_rae_service.get_statistics.return_value = {
            "total_count": 100,
            "layers": {"sensory": 10, "working": 20}
        }

        response = client_with_overrides.get(
            "/v2/memories/stats?project=test-project",
            headers={"X-Tenant-Id": "test-tenant"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "statistics" in data
        stats = data["statistics"]
        assert "total_count" in stats
