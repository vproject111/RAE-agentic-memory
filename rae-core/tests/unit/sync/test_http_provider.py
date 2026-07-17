from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.sync.http_provider import HttpSyncProvider


@pytest.fixture
async def http_provider():
    provider = HttpSyncProvider(remote_url="http://remote", auth_token="test_token")
    yield provider
    await provider.close()


@pytest.mark.asyncio
async def test_handshake_success(http_provider):
    with patch.object(http_provider.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = await http_provider.handshake("t1", "a1", {})
        assert result["status"] == "connected"
        mock_get.assert_called_once_with("/health")


@pytest.mark.asyncio
async def test_handshake_failure(http_provider):
    with patch.object(http_provider.client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = Exception("Connection failed")

        result = await http_provider.handshake("t1", "a1", {})
        assert result["status"] == "failed"
        assert "Connection failed" in result["error"]


@pytest.mark.asyncio
async def test_pull_memories_success(http_provider):
    with patch.object(
        http_provider.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "memories": [{"id": "mem1", "content": "hello"}],
            "sync_id": "sync123",
        }
        mock_post.return_value = mock_response

        result = await http_provider.pull_memories("t1", "a1", since=datetime.now())
        assert result["success"] is True
        assert result["synced_memory_ids"] == ["mem1"]
        assert result["sync_id"] == "sync123"


@pytest.mark.asyncio
async def test_pull_memories_failure(http_provider):
    with patch.object(
        http_provider.client, "post", new_callable=AsyncMock
    ) as mock_post:
        mock_post.side_effect = Exception("API Error")

        result = await http_provider.pull_memories("t1", "a1")
        assert result["success"] is False
        assert "API Error" in result["error"]


@pytest.mark.asyncio
async def test_get_sync_status(http_provider):
    with patch.object(http_provider.client, "get", new_callable=AsyncMock) as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "completed"}
        mock_get.return_value = mock_response

        result = await http_provider.get_sync_status("t1", "a1", "sync123")
        assert result["status"] == "completed"
        mock_get.assert_called_once_with("/v2/mesh/sync/status/sync123")


@pytest.mark.asyncio
async def test_resolve_conflict_last_write_wins(http_provider):
    local = {"id": "1", "updated_at": "2023-01-01T10:00:00"}
    remote = {"id": "1", "updated_at": "2023-01-01T11:00:00"}

    resolved = await http_provider.resolve_conflict(uuid4(), local, remote)
    assert resolved == remote

    local_newer = {"id": "1", "updated_at": "2023-01-01T12:00:00"}
    resolved = await http_provider.resolve_conflict(uuid4(), local_newer, remote)
    assert resolved == local_newer


@pytest.mark.asyncio
async def test_push_memories_not_implemented(http_provider):
    result = await http_provider.push_memories("t1", "a1")
    assert result["success"] is False
    assert "Not implemented" in result["error"]


@pytest.mark.asyncio
async def test_not_implemented_methods(http_provider):
    with pytest.raises(NotImplementedError):
        await http_provider.push_changes("t1", [])

    with pytest.raises(NotImplementedError):
        await http_provider.pull_changes("t1", "ts")

    with pytest.raises(NotImplementedError):
        await http_provider.sync_memories("t1", "a1")
