import pytest

from rae_core.interfaces.sync import ISyncProvider
from rae_core.models.sync import SyncHandshake
from rae_core.sync.manager import SyncManager


class MockSyncProvider(ISyncProvider):
    async def push_changes(self, tenant_id, changes):
        return True

    async def pull_changes(self, tenant_id, since_timestamp):
        return []

    async def resolve_conflict(self, memory_id, local, remote):
        return local

    async def push_memories(self, tenant_id, agent_id, memory_ids=None, since=None):
        return {"success": True, "synced_memory_ids": ["m1", "m2"], "conflicts": []}

    async def pull_memories(self, tenant_id, agent_id, memory_ids=None, since=None):
        return {"success": True, "synced_memory_ids": ["m3"], "conflicts": []}

    async def sync_memories(self, tenant_id, agent_id, since=None):
        return {"success": True}

    async def get_sync_status(self, tenant_id, agent_id, sync_id):
        return {}

    async def handshake(self, tenant_id, agent_id, capabilities):
        return {"protocol_version": "1.0", "capabilities": capabilities}


@pytest.mark.asyncio
async def test_handshake_flow():
    provider = MockSyncProvider()
    manager = SyncManager(
        agent_id="test-agent-1", role="server", sync_provider=provider
    )

    # Test Initiate
    handshake = await manager.initiate_handshake("peer-2")
    assert handshake.peer_id == "test-agent-1"
    assert handshake.role == "server"

    # Test Receive
    incoming = SyncHandshake(
        peer_id="peer-2", role="mobile", protocol_version="1.0", capabilities=[]
    )
    success = await manager.receive_handshake(incoming)
    assert success is True
    assert "peer-2" in manager.peers


@pytest.mark.asyncio
async def test_sync_execution():
    provider = MockSyncProvider()
    manager = SyncManager(
        agent_id="test-agent-1", role="server", sync_provider=provider
    )

    # Manually add peer
    incoming = SyncHandshake(peer_id="peer-2", role="mobile", protocol_version="1.0")
    await manager.receive_handshake(incoming)

    # Run Sync
    log = await manager.sync_with_peer("peer-2", "tenant-1")

    assert log.status == "success"
    assert log.peer_id == "peer-2"
    assert log.items_synced == 3  # 2 pushed + 1 pulled
