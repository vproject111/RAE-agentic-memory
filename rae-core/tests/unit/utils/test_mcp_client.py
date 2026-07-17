import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the mcp module before importing RAEMCPClient
mcp_mock = MagicMock()
mcp_client_mock = MagicMock()
mcp_mock.client.stdio = mcp_client_mock
sys.modules["mcp"] = mcp_mock
sys.modules["mcp.client"] = MagicMock()
sys.modules["mcp.client.stdio"] = mcp_client_mock

import pytest

from rae_core.utils.mcp_client import RAEMCPClient


@pytest.mark.asyncio
async def test_mcp_client_init():
    client = RAEMCPClient(command="node", args=["server.js"], env={"KEY": "VAL"})
    assert client.command == "node"
    assert client.args == ["server.js"]
    assert client.env["KEY"] == "VAL"


@pytest.mark.asyncio
async def test_mcp_client_connect_disconnect():
    with (
        patch("rae_core.utils.mcp_client.stdio_client") as mock_stdio,
        patch("rae_core.utils.mcp_client.ClientSession") as mock_session_class,
        patch("rae_core.utils.mcp_client.StdioServerParameters") as mock_params,
    ):

        mock_mgr = AsyncMock()
        mock_read = MagicMock()
        mock_write = MagicMock()
        mock_mgr.__aenter__.return_value = (mock_read, mock_write)
        mock_stdio.return_value = mock_mgr

        mock_session = AsyncMock()
        mock_session_class.return_value = mock_session

        client = RAEMCPClient()
        await client.connect()

        assert client._session == mock_session
        mock_session.initialize.assert_awaited_once()

        # Connect again should do nothing
        await client.connect()
        mock_session.initialize.assert_awaited_once()  # Still once

        await client.disconnect()
        mock_mgr.__aexit__.assert_awaited_once()
        assert client._session is None


@pytest.mark.asyncio
async def test_mcp_client_call_tool_json():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = '{"status": "success"}'
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result

    res = await client.call_tool("my_tool", {"arg1": 1})
    assert res == {"status": "success"}
    mock_session.call_tool.assert_awaited_once_with("my_tool", {"arg1": 1})


@pytest.mark.asyncio
async def test_mcp_client_call_tool_text():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "Just some text"
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result

    res = await client.call_tool("my_tool", {})
    assert res == {"text": "Just some text"}


@pytest.mark.asyncio
async def test_mcp_client_call_tool_json_list():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    mock_content = MagicMock()
    mock_content.text = "[1, 2, 3]"
    mock_result.content = [mock_content]
    mock_session.call_tool.return_value = mock_result

    res = await client.call_tool("my_tool", {})
    assert res == {"result": [1, 2, 3]}


@pytest.mark.asyncio
async def test_mcp_client_call_tool_empty():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    mock_result.content = []
    mock_session.call_tool.return_value = mock_result

    res = await client.call_tool("my_tool", {})
    assert res == {}


@pytest.mark.asyncio
async def test_mcp_client_call_tool_no_content():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    del mock_result.content
    mock_session.call_tool.return_value = mock_result

    res = await client.call_tool("my_tool", {})
    assert res == {}


@pytest.mark.asyncio
async def test_mcp_client_call_tool_auto_connect():
    with patch.object(RAEMCPClient, "connect", new_callable=AsyncMock) as mock_connect:
        client = RAEMCPClient()
        # Mock session to be set after connect
        mock_session = AsyncMock()

        def side_effect():
            client._session = mock_session

        mock_connect.side_effect = side_effect

        mock_result = MagicMock()
        mock_result.content = []
        mock_session.call_tool.return_value = mock_result

        await client.call_tool("test", {})
        mock_connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_client_call_tool_failure():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session
    mock_session.call_tool.side_effect = Exception("error")

    with pytest.raises(Exception, match="error"):
        await client.call_tool("test", {})


@pytest.mark.asyncio
async def test_mcp_client_list_tools():
    client = RAEMCPClient()
    mock_session = AsyncMock()
    client._session = mock_session

    mock_result = MagicMock()
    mock_result.tools = ["tool1", "tool2"]
    mock_session.list_tools.return_value = mock_result

    tools = await client.list_tools()
    assert tools == ["tool1", "tool2"]


@pytest.mark.asyncio
async def test_mcp_client_list_tools_auto_connect():
    with patch.object(RAEMCPClient, "connect", new_callable=AsyncMock) as mock_connect:
        client = RAEMCPClient()
        mock_session = AsyncMock()

        def side_effect():
            client._session = mock_session

        mock_connect.side_effect = side_effect

        mock_result = MagicMock()
        mock_result.tools = []
        mock_session.list_tools.return_value = mock_result

        await client.list_tools()
        mock_connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_mcp_client_list_tools_connect_fail():
    with patch.object(RAEMCPClient, "connect", new_callable=AsyncMock) as mock_connect:
        client = RAEMCPClient()
        # client._session stays None
        tools = await client.list_tools()
        assert tools == []


@pytest.mark.asyncio
async def test_mcp_client_call_tool_connect_fail():
    with patch.object(RAEMCPClient, "connect", new_callable=AsyncMock) as mock_connect:
        client = RAEMCPClient()
        # client._session stays None
        with pytest.raises(RuntimeError, match="Failed to initialize MCP session"):
            await client.call_tool("test", {})
