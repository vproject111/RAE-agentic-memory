"""
End-to-end tests for RAE MCP Server.

These tests verify the complete flow from JSON-RPC requests to RAE API calls.
"""

# Import the server components
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rae_mcp.server import (
    RAEMemoryClient,
    handle_call_tool,
    handle_get_prompt,
    handle_list_prompts,
    handle_list_resources,
    handle_list_tools,
    handle_read_resource,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_rae_api():
    """Mock RAE API responses."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_client.return_value.__aexit__.return_value = None
        yield mock_instance


@pytest.fixture
def rae_client():
    """Create a RAE Memory Client instance for testing."""
    return RAEMemoryClient(
        api_url="http://localhost:8000", api_key="test-api-key", tenant_id="test-tenant"
    )


# =============================================================================
# TOOL TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns all expected tools."""
    tools = await handle_list_tools()

    assert len(tools) == 7
    tool_names = [tool.name for tool in tools]

    assert "save_memory" in tool_names
    assert "search_memory" in tool_names
    assert "get_related_context" in tool_names
    assert "request_approval" in tool_names
    assert "check_approval_status" in tool_names
    assert "get_circuit_breakers" in tool_names
    assert "list_policies" in tool_names

    # Verify save_memory schema
    save_memory_tool = next(t for t in tools if t.name == "save_memory")
    assert "content" in save_memory_tool.inputSchema["properties"]
    assert "source" in save_memory_tool.inputSchema["properties"]
    assert "tags" in save_memory_tool.inputSchema["properties"]
    assert "layer" in save_memory_tool.inputSchema["properties"]
    assert save_memory_tool.inputSchema["required"] == ["content", "source"]


@pytest.mark.asyncio
async def test_save_memory_tool_success(mock_rae_api):
    """Test save_memory tool with successful API response."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "memory-123", "status": "stored"}
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Call tool
    result = await handle_call_tool(
        name="save_memory",
        arguments={
            "content": "Test memory content",
            "source": "test-source",
            "tags": ["test", "e2e"],
            "layer": "episodic",
        },
    )

    # Verify response
    assert len(result) == 1
    assert result[0].type == "text"
    assert "✓ Memory stored successfully" in result[0].text
    assert "memory-123" in result[0].text
    assert "episodic" in result[0].text


@pytest.mark.asyncio
async def test_save_memory_tool_missing_content():
    """Test save_memory tool with missing required content parameter."""
    result = await handle_call_tool(
        name="save_memory", arguments={"source": "test-source"}
    )

    assert len(result) == 1
    assert "Error: 'content' is required" in result[0].text


@pytest.mark.asyncio
async def test_save_memory_tool_missing_source():
    """Test save_memory tool with missing required source parameter."""
    result = await handle_call_tool(
        name="save_memory", arguments={"content": "Test content"}
    )

    assert len(result) == 1
    assert "Error: 'source' is required" in result[0].text


@pytest.mark.asyncio
async def test_search_memory_tool_success(mock_rae_api):
    """Test search_memory tool with successful API response."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "content": "Memory content 1",
                "source": "source-1",
                "score": 0.95,
                "tags": ["tag1"],
            },
            {
                "content": "Memory content 2",
                "source": "source-2",
                "score": 0.85,
                "tags": ["tag2"],
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Call tool
    result = await handle_call_tool(
        name="search_memory", arguments={"query": "test query", "top_k": 5}
    )

    # Verify response
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Found 2 relevant memories" in result[0].text
    assert "Memory content 1" in result[0].text
    assert "Score: 0.950" in result[0].text


@pytest.mark.asyncio
async def test_search_memory_tool_no_results(mock_rae_api):
    """Test search_memory tool with no results."""
    # Mock empty API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": []}
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Call tool
    result = await handle_call_tool(
        name="search_memory", arguments={"query": "nonexistent query"}
    )

    # Verify response
    assert len(result) == 1
    assert "No memories found for query" in result[0].text


@pytest.mark.asyncio
async def test_get_related_context_tool_success(mock_rae_api):
    """Test get_related_context tool with successful API response."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {
                "content": "File modification 1",
                "timestamp": "2025-01-15T10:30:00Z",
                "source": "src/auth.py",
            },
            {
                "content": "File modification 2",
                "timestamp": "2025-01-14T15:20:00Z",
                "source": "src/auth.py",
            },
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Call tool
    result = await handle_call_tool(
        name="get_related_context",
        arguments={"file_path": "src/auth.py", "include_count": 10},
    )

    # Verify response
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Historical context for: src/auth.py" in result[0].text
    assert "Found 2 related items" in result[0].text
    assert "File modification 1" in result[0].text


@pytest.mark.asyncio
async def test_unknown_tool():
    """Test calling an unknown tool."""
    result = await handle_call_tool(name="unknown_tool", arguments={})

    assert len(result) == 1
    assert "Error: Unknown tool 'unknown_tool'" in result[0].text


# =============================================================================
# RESOURCE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_list_resources():
    """Test that list_resources returns all expected resources."""
    resources = await handle_list_resources()

    assert len(resources) == 2
    # Convert AnyUrl to string for comparison
    resource_uris = [str(resource.uri) for resource in resources]

    assert "rae://project/reflection" in resource_uris
    assert "rae://project/guidelines" in resource_uris

    # Verify resource metadata
    reflection_resource = next(
        r for r in resources if str(r.uri) == "rae://project/reflection"
    )
    assert reflection_resource.name == "Project Reflection"
    assert reflection_resource.mimeType == "text/plain"


@pytest.mark.asyncio
async def test_read_reflection_resource(mock_rae_api):
    """Test reading the project reflection resource."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "summary": "This project focuses on authentication improvements..."
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Read resource
    result = await handle_read_resource("rae://project/reflection")

    # Verify response
    assert "This project focuses on authentication improvements" in result


@pytest.mark.asyncio
async def test_read_guidelines_resource(mock_rae_api):
    """Test reading the project guidelines resource."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"content": "Always use type hints in Python code"},
            {"content": "Write tests for all business logic"},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Read resource
    result = await handle_read_resource("rae://project/guidelines")

    # Verify response
    assert "PROJECT GUIDELINES" in result
    assert "Always use type hints in Python code" in result
    assert "Write tests for all business logic" in result


@pytest.mark.asyncio
async def test_read_unknown_resource():
    """Test reading an unknown resource."""
    result = await handle_read_resource("rae://unknown/resource")

    assert "Error reading resource" in result or "Unknown resource URI" in result


# =============================================================================
# PROMPT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_list_prompts():
    """Test that list_prompts returns all expected prompts."""
    prompts = await handle_list_prompts()

    assert len(prompts) == 2
    prompt_names = [prompt.name for prompt in prompts]

    assert "project-guidelines" in prompt_names
    assert "recent-context" in prompt_names


@pytest.mark.asyncio
async def test_get_project_guidelines_prompt(mock_rae_api):
    """Test getting the project-guidelines prompt."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [{"content": "Guideline 1"}, {"content": "Guideline 2"}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Get prompt
    result = await handle_get_prompt("project-guidelines", {})

    # Verify response
    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert "PROJECT GUIDELINES" in result.messages[0].content.text
    assert "Guideline 1" in result.messages[0].content.text


@pytest.mark.asyncio
async def test_get_recent_context_prompt(mock_rae_api):
    """Test getting the recent-context prompt."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"content": "Recent activity 1", "timestamp": "2025-01-15T10:00:00Z"}
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Get prompt
    result = await handle_get_prompt("recent-context", {})

    # Verify response
    assert len(result.messages) == 1
    assert result.messages[0].role == "user"
    assert "RECENT PROJECT CONTEXT" in result.messages[0].content.text


# =============================================================================
# RAE CLIENT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_rae_client_store_memory(mock_rae_api):
    """Test RAEMemoryClient.store_memory method."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": "test-id", "status": "stored"}
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Create client
    client = RAEMemoryClient(
        api_url="http://localhost:8000", api_key="test-key", tenant_id="test-tenant"
    )

    # Store memory
    result = await client.store_memory(
        content="Test content", source="test-source", layer="episodic", tags=["test"]
    )

    # Verify result
    assert result["id"] == "test-id"
    assert result["status"] == "stored"


@pytest.mark.asyncio
async def test_rae_client_search_memory(mock_rae_api):
    """Test RAEMemoryClient.search_memory method."""
    # Mock successful API response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"content": "Result 1", "score": 0.9},
            {"content": "Result 2", "score": 0.8},
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Create client
    client = RAEMemoryClient(
        api_url="http://localhost:8000", api_key="test-key", tenant_id="test-tenant"
    )

    # Search memory
    results = await client.search_memory(query="test query", top_k=5)

    # Verify results
    assert len(results) == 2
    assert results[0]["content"] == "Result 1"
    assert results[1]["score"] == 0.8


@pytest.mark.asyncio
async def test_rae_client_http_error(mock_rae_api):
    """Test RAEMemoryClient handles HTTP errors gracefully."""
    # Mock HTTP error
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Internal Server Error", request=MagicMock(), response=mock_response
    )
    mock_rae_api.post = AsyncMock(return_value=mock_response)

    # Create client
    client = RAEMemoryClient(
        api_url="http://localhost:8000", api_key="test-key", tenant_id="test-tenant"
    )

    # Attempt to store memory (should raise exception)
    with pytest.raises(httpx.HTTPStatusError):
        await client.store_memory(content="Test", source="test")


# =============================================================================
# INTEGRATION TEST (if RAE API is available)
# =============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_mcp_flow():
    """
    Full end-to-end integration test.

    Requires RAE API to be running on localhost:8000.
    Run with: pytest -m integration
    """
    # Create real client
    client = RAEMemoryClient(
        api_url="http://localhost:8000", api_key="test-api-key", tenant_id="test-tenant"
    )

    # 1. Store memory
    store_result = await client.store_memory(
        content="Integration test memory content",
        source="test-e2e",
        layer="episodic",
        tags=["integration", "test"],
    )

    assert "id" in store_result
    store_result["id"]

    # 2. Search memory
    search_results = await client.search_memory(query="integration test", top_k=5)

    assert len(search_results) > 0
    assert any(
        "integration test" in result.get("content", "").lower()
        for result in search_results
    )

    # 3. Get file context (should return empty or existing context)
    context_results = await client.get_file_context(file_path="test-file.py", top_k=10)

    # Results may be empty, but should not error
    assert isinstance(context_results, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
