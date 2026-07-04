"""Unit tests for SyncProtocol to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rae_core.sync.protocol import SyncProtocol


class TestSyncProtocolCoverage:
    """Test suite for SyncProtocol coverage gaps."""

    @pytest.fixture
    def mock_provider(self):
        p = MagicMock()
        p.pull_memories = AsyncMock()
        p.sync_memories = AsyncMock()
        p.get_sync_status = AsyncMock()
        p.handshake = AsyncMock()
        return p

    @pytest.fixture
    def protocol(self, mock_provider):
        return SyncProtocol(sync_provider=mock_provider)

    @pytest.mark.asyncio
    async def test_pull_exception(self, protocol, mock_provider):
        """Test pull handling an exception."""
        mock_provider.pull_memories.side_effect = Exception("Pull failed")
        res = await protocol.pull("t1", "a1")
        assert res.success is False
        assert res.error_message == "Pull failed"
        assert res.metadata.sync_type == "pull"

    @pytest.mark.asyncio
    async def test_sync_exception(self, protocol, mock_provider):
        """Test sync handling an exception."""
        mock_provider.sync_memories.side_effect = Exception("Sync failed")
        res = await protocol.sync("t1", "a1")
        assert res.success is False
        assert res.error_message == "Sync failed"
        assert res.metadata.sync_type == "sync"

    @pytest.mark.asyncio
    async def test_get_sync_status(self, protocol, mock_provider):
        """Test get_sync_status."""
        mock_provider.get_sync_status.return_value = {"status": "completed"}
        res = await protocol.get_sync_status("t1", "a1", "s1")
        assert res == {"status": "completed"}
        mock_provider.get_sync_status.assert_called_once_with(
            tenant_id="t1", agent_id="a1", sync_id="s1"
        )

    @pytest.mark.asyncio
    async def test_handshake(self, protocol, mock_provider):
        """Test handshake."""
        mock_provider.handshake.return_value = {"session": "123"}
        res = await protocol.handshake("t1", "a1", {"cap": "sync"})
        assert res == {"session": "123"}
        mock_provider.handshake.assert_called_once_with(
            tenant_id="t1", agent_id="a1", capabilities={"cap": "sync"}
        )
