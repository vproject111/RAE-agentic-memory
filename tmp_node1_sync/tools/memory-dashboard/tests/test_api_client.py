"""
Tests for RAE API Client

Tests the enterprise RAE client functionality.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.api_client import RAEClient, get_cached_memories, get_cached_stats


class TestRAEClient:
    """Test suite for RAEClient"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return RAEClient(
            api_url="http://test-api:8000",
            api_key="test-key",
            tenant_id="test-tenant",
            project_id="test-project",
        )

    @pytest.fixture
    def mock_response(self):
        """Create mock httpx response"""
        mock = Mock(spec=httpx.Response)
        mock.status_code = 200
        mock.json.return_value = {"success": True}
        return mock

    def test_client_initialization(self, client):
        """Test client initializes correctly"""
        assert client.api_url == "http://test-api:8000"
        assert client.api_key == "test-key"
        assert client.tenant_id == "test-tenant"
        assert client.project_id == "test-project"
        assert client.headers["X-API-Key"] == "test-key"
        assert client.headers["X-Tenant-Id"] == "test-tenant"

    def test_client_strips_trailing_slash(self):
        """Test API URL trailing slash is removed"""
        client = RAEClient(api_url="http://test-api:8000/")
        assert client.api_url == "http://test-api:8000"

    @patch("httpx.Client.request")
    def test_test_connection_success(self, mock_request, client):
        """Test successful connection test"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        assert client.test_connection() is True
        mock_request.assert_called_once_with("GET", "/health")

    @patch("httpx.Client.request")
    def test_test_connection_failure(self, mock_request, client):
        """Test failed connection test"""
        mock_request.side_effect = httpx.RequestError("Connection failed")

        assert client.test_connection() is False

    @patch("httpx.Client.request")
    def test_get_stats(self, mock_request, client):
        """Test fetching statistics"""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        stats = client.get_stats()

        assert isinstance(stats, dict)
        assert "total" in stats
        assert "episodic" in stats
        assert "working" in stats
        assert "semantic" in stats
        assert "ltm" in stats

    @patch("httpx.Client.request")
    def test_get_memories(self, mock_request, client):
        """Test fetching memories"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "mem1",
                    "content": "Test memory",
                    "layer": "em",
                    "timestamp": "2024-01-01T00:00:00",
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        memories = client.get_memories(layers=["em"], limit=10)

        assert isinstance(memories, list)
        assert len(memories) > 0

    @patch("httpx.Client.request")
    def test_get_memories_with_date_filter(self, mock_request, client):
        """Test fetching memories with date filter"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "id": "mem1",
                    "content": "Test memory",
                    "layer": "em",
                    "timestamp": datetime.now().isoformat(),
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        since = datetime.now() - timedelta(days=7)
        memories = client.get_memories(layers=["em"], since=since, limit=10)

        assert isinstance(memories, list)

    @patch("httpx.Client.request")
    def test_search_memories(self, mock_request, client):
        """Test searching memories"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [{"id": "mem1", "content": "Matching memory", "score": 0.95}]
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        results = client.search_memories(query="test query", top_k=5)

        assert isinstance(results, list)
        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs["json"]["query_text"] == "test query"
        assert call_kwargs["json"]["k"] == 5

    @patch("httpx.Client.request")
    def test_query_memory_with_rerank(self, mock_request, client):
        """Test querying with reranking"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"id": "mem1", "score": 0.8},
                {"id": "mem2", "score": 0.9},
                {"id": "mem3", "score": 0.7},
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        results = client.query_memory(query="test", top_k=10, use_rerank=True)

        # Should be sorted by score descending
        assert results[0]["score"] == 0.9
        assert results[1]["score"] == 0.8
        assert results[2]["score"] == 0.7

    @patch("httpx.Client.request")
    def test_get_knowledge_graph(self, mock_request, client):
        """Test fetching knowledge graph"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "nodes": [{"id": "n1", "label": "Node 1"}],
            "edges": [{"source": "n1", "target": "n2"}],
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        graph = client.get_knowledge_graph()

        assert "nodes" in graph
        assert "edges" in graph

    @patch("httpx.Client.request")
    def test_get_reflection(self, mock_request, client):
        """Test fetching reflection"""
        mock_response = Mock()
        mock_response.json.return_value = {"summary": "Test reflection summary"}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        reflection = client.get_reflection()

        assert isinstance(reflection, str)
        assert len(reflection) > 0

    @patch("httpx.Client.request")
    def test_delete_memory(self, mock_request, client):
        """Test deleting memory"""
        mock_response = Mock()
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        with patch("streamlit.success"):
            result = client.delete_memory("mem123")

        assert result is True

    @patch("httpx.Client.request")
    def test_error_handling_http_error(self, mock_request, client):
        """Test HTTP error handling"""
        mock_request.side_effect = httpx.HTTPStatusError(
            "Not found",
            request=Mock(),
            response=Mock(status_code=404, text="Not found"),
        )

        with patch("streamlit.error"):
            with pytest.raises(httpx.HTTPStatusError):
                client._request("GET", "/test")

    @patch("httpx.Client.request")
    def test_error_handling_request_error(self, mock_request, client):
        """Test request error handling"""
        mock_request.side_effect = httpx.RequestError("Connection failed")

        with patch("streamlit.error"):
            with pytest.raises(httpx.RequestError):
                client._request("GET", "/test")

    def test_context_manager(self):
        """Test client as context manager"""
        with RAEClient() as client:
            assert client is not None
            assert isinstance(client, RAEClient)


class TestCachingFunctions:
    """Test caching helper functions"""

    @pytest.fixture
    def mock_client(self):
        """Create mock client"""
        client = Mock(spec=RAEClient)
        client.get_stats.return_value = {
            "total": 100,
            "episodic": 30,
            "working": 25,
            "semantic": 25,
            "ltm": 20,
        }
        client.get_memories.return_value = [{"id": "mem1", "content": "Test"}]
        return client

    def test_get_cached_stats(self, mock_client):
        """Test cached stats function"""
        stats = get_cached_stats(mock_client)

        assert isinstance(stats, dict)
        assert "total" in stats
        mock_client.get_stats.assert_called_once()

    def test_get_cached_memories(self, mock_client):
        """Test cached memories function"""
        memories = get_cached_memories(mock_client, layers=("em", "wm"), days_back=7)

        assert isinstance(memories, list)
        mock_client.get_memories.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
