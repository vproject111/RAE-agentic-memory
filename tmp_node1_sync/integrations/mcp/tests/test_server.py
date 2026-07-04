"""
Enterprise-grade tests for RAE MCP Server

These tests validate:
- MCP Tools functionality
- MCP Resources functionality
- MCP Prompts functionality
- Error handling
- RAEMemoryClient operations
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

from rae_mcp.server import (
    RAEMemoryClient,
    handle_call_tool,
    handle_get_prompt,
    handle_list_prompts,
    handle_list_resources,
    handle_list_tools,
    handle_read_resource,
    rae_client,
    server,
)


class TestRAEMemoryClient:
    """Test the RAEMemoryClient class"""

    @pytest.mark.asyncio
    async def test_store_memory_success(self):
        """Test successful memory storage"""
        client = RAEMemoryClient(
            api_url="http://test:8000", api_key="test-key", tenant_id="test-tenant"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "mem-123", "message": "Success"}
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            result = await client.store_memory(
                content="Test content",
                source="test-source",
                layer="episodic",
                tags=["test"],
            )

            assert result["id"] == "mem-123"
            assert result["message"] == "Success"

    @pytest.mark.asyncio
    async def test_search_memory_success(self):
        """Test successful memory search"""
        client = RAEMemoryClient(
            api_url="http://test:8000", api_key="test-key", tenant_id="test-tenant"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"content": "Result 1", "score": 0.95},
                {"content": "Result 2", "score": 0.85},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            results = await client.search_memory(query="test query", top_k=5)

            assert len(results) == 2
            assert results[0]["content"] == "Result 1"
            assert results[0]["score"] == 0.95

    @pytest.mark.asyncio
    async def test_get_file_context(self):
        """Test getting file context"""
        client = RAEMemoryClient(
            api_url="http://test:8000", api_key="test-key", tenant_id="test-tenant"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{"content": "File change 1", "source": "/path/to/file.py"}]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )

            results = await client.get_file_context(
                file_path="/path/to/file.py", top_k=10
            )

            assert len(results) == 1
            assert results[0]["source"] == "/path/to/file.py"


class TestMCPTools:
    """Test MCP Tools functionality"""

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test listing available tools"""
        tools = await handle_list_tools()

        assert len(tools) == 7
        tool_names = [t.name for t in tools]
        assert "save_memory" in tool_names
        assert "search_memory" in tool_names
        assert "get_related_context" in tool_names
        assert "request_approval" in tool_names
        assert "check_approval_status" in tool_names
        assert "get_circuit_breakers" in tool_names
        assert "list_policies" in tool_names

    @pytest.mark.asyncio
    async def test_save_memory_tool(self):
        """Test save_memory tool invocation"""
        with patch.object(
            rae_client, "store_memory", new_callable=AsyncMock
        ) as mock_store:
            mock_store.return_value = {"id": "mem-456"}

            result = await handle_call_tool(
                name="save_memory",
                arguments={
                    "content": "Test memory",
                    "source": "test",
                    "tags": ["test"],
                    "layer": "episodic",
                },
            )

            assert len(result) == 1
            assert result[0].type == "text"
            assert "mem-456" in result[0].text
            assert "✓" in result[0].text

    @pytest.mark.asyncio
    async def test_save_memory_missing_content(self):
        """Test save_memory with missing content"""
        result = await handle_call_tool(
            name="save_memory", arguments={"source": "test"}
        )

        assert len(result) == 1
        assert "Error" in result[0].text
        assert "content" in result[0].text

    @pytest.mark.asyncio
    async def test_search_memory_tool(self):
        """Test search_memory tool invocation"""
        with patch.object(
            rae_client, "search_memory", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = [
                {
                    "content": "Result 1",
                    "score": 0.9,
                    "source": "test",
                    "tags": ["tag1"],
                },
                {"content": "Result 2", "score": 0.8, "source": "test", "tags": []},
            ]

            result = await handle_call_tool(
                name="search_memory", arguments={"query": "test query", "top_k": 5}
            )

            assert len(result) == 1
            assert result[0].type == "text"
            assert "Found 2 relevant memories" in result[0].text
            assert "Result 1" in result[0].text

    @pytest.mark.asyncio
    async def test_search_memory_no_results(self):
        """Test search_memory with no results"""
        with patch.object(
            rae_client, "search_memory", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = []

            result = await handle_call_tool(
                name="search_memory", arguments={"query": "nonexistent"}
            )

            assert len(result) == 1
            assert "No memories found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_related_context_tool(self):
        """Test get_related_context tool invocation"""
        with patch.object(
            rae_client, "get_file_context", new_callable=AsyncMock
        ) as mock_context:
            mock_context.return_value = [
                {"content": "Change 1", "timestamp": "2025-01-01"},
                {"content": "Change 2", "timestamp": "2025-01-02"},
            ]

            result = await handle_call_tool(
                name="get_related_context",
                arguments={"file_path": "/test/file.py", "include_count": 10},
            )

            assert len(result) == 1
            assert "/test/file.py" in result[0].text
            assert "Found 2 related items" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling unknown tool"""
        result = await handle_call_tool(name="unknown_tool", arguments={})

        assert len(result) == 1
        assert "Unknown tool" in result[0].text


class TestMCPResources:
    """Test MCP Resources functionality"""

    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test listing available resources"""
        resources = await handle_list_resources()

        assert len(resources) == 2
        uris = [str(r.uri) for r in resources]
        assert "rae://project/reflection" in uris
        assert "rae://project/guidelines" in uris

    @pytest.mark.asyncio
    async def test_read_reflection_resource(self):
        """Test reading reflection resource"""
        with patch.object(
            rae_client, "get_latest_reflection", new_callable=AsyncMock
        ) as mock_ref:
            mock_ref.return_value = "Test reflection summary"

            content = await handle_read_resource("rae://project/reflection")

            assert content == "Test reflection summary"

    @pytest.mark.asyncio
    async def test_read_guidelines_resource(self):
        """Test reading guidelines resource"""
        with patch.object(
            rae_client, "get_project_guidelines", new_callable=AsyncMock
        ) as mock_guide:
            mock_guide.return_value = [
                {"content": "Guideline 1"},
                {"content": "Guideline 2"},
            ]

            content = await handle_read_resource("rae://project/guidelines")

            assert "PROJECT GUIDELINES" in content
            assert "Guideline 1" in content
            assert "Guideline 2" in content

    @pytest.mark.asyncio
    async def test_read_unknown_resource(self):
        """Test reading unknown resource"""
        content = await handle_read_resource("rae://unknown/resource")

        assert "Error" in content
        assert "Unknown resource" in content


class TestMCPPrompts:
    """Test MCP Prompts functionality"""

    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test listing available prompts"""
        prompts = await handle_list_prompts()

        assert len(prompts) == 2
        prompt_names = [p.name for p in prompts]
        assert "project-guidelines" in prompt_names
        assert "recent-context" in prompt_names

    @pytest.mark.asyncio
    async def test_get_guidelines_prompt(self):
        """Test getting project guidelines prompt"""
        with patch.object(
            rae_client, "get_project_guidelines", new_callable=AsyncMock
        ) as mock_guide:
            mock_guide.return_value = [
                {"content": "Use Python 3.10+"},
                {"content": "Follow PEP 8"},
            ]

            result = await handle_get_prompt(name="project-guidelines", arguments={})

            assert len(result.messages) == 1
            assert result.messages[0].role == "user"
            content_text = result.messages[0].content.text
            assert "PROJECT GUIDELINES" in content_text
            assert "Use Python 3.10+" in content_text

    @pytest.mark.asyncio
    async def test_get_recent_context_prompt(self):
        """Test getting recent context prompt"""
        with patch.object(
            rae_client, "search_memory", new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = [
                {"content": "Recent change 1", "timestamp": "2025-01-01"},
                {"content": "Recent change 2", "timestamp": "2025-01-02"},
            ]

            result = await handle_get_prompt(name="recent-context", arguments={})

            assert len(result.messages) == 1
            content_text = result.messages[0].content.text
            assert "RECENT PROJECT CONTEXT" in content_text
            assert "Recent change 1" in content_text

    @pytest.mark.asyncio
    async def test_get_unknown_prompt(self):
        """Test getting unknown prompt"""
        result = await handle_get_prompt(name="unknown-prompt", arguments={})

        assert len(result.messages) == 1
        assert "Error" in result.messages[0].content.text


# =============================================================================
# Test Configuration
# =============================================================================


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("RAE_API_URL", "http://test:8000")
    monkeypatch.setenv("RAE_API_KEY", "test-key")
    monkeypatch.setenv("RAE_PROJECT_ID", "test-project")
    monkeypatch.setenv("RAE_TENANT_ID", "test-tenant")


def test_server_initialization():
    """Test that server is properly initialized"""
    assert server is not None
    assert server.name == "rae-memory"


def test_rae_client_initialization():
    """Test that RAE client is initialized"""
    assert rae_client is not None
    assert isinstance(rae_client, RAEMemoryClient)
