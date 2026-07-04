"""Coverage tests for Sync Merge and Manager."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.models.sync import SyncHandshake, SyncPeer
from rae_core.sync.manager import SyncManager
from rae_core.sync.merge import (
    ConflictResolutionStrategy,
    ConflictResolver,
    MergeResult,
    apply_merge_results,
    merge_memories,
)


class TestMergeCoverageExtended:
    def test_merge_fields_content_collision(self):
        """Test merging content field (should pass through newer)."""
        resolver = ConflictResolver()
        now = datetime.now(timezone.utc)
        # Make local NEWER so it wins
        local = {"id": str(uuid4()), "content": "local", "modified_at": now}
        remote = {
            "id": local["id"],
            "content": "remote",
            "modified_at": now - timedelta(seconds=1),
        }

        res = resolver._merge_fields(local, remote, ["content"])
        assert res["content"] == "local"

    def test_merge_fields_importance_explicit(self):
        """Explicitly test importance merge."""
        resolver = ConflictResolver()
        now = datetime.now(timezone.utc)
        local = {"id": str(uuid4()), "importance": 0.5, "modified_at": now}
        remote = {"id": local["id"], "importance": 0.9, "modified_at": now}

        res = resolver._merge_fields(local, remote, ["importance"])
        assert res["importance"] == 0.9

    def test_merge_memories_no_conflict(self):
        """Test merging identical memories (no conflict path)."""
        mid = str(uuid4())
        now = datetime.now(timezone.utc)
        mem = {"id": mid, "content": "same", "modified_at": now, "version": 1}

        # Identical memories -> no conflicts -> LAST_WRITE_WINS resolved
        results = merge_memories([mem], [mem])
        assert len(results) == 1
        assert results[0].success
        # Should not have conflicts
        assert not results[0].conflicts_resolved

    @pytest.mark.asyncio
    async def test_apply_merge_results_exception(self):
        """Test exception handling in apply_merge_results."""
        mid = uuid4()
        res = MergeResult(
            memory_id=mid,
            success=True,
            strategy_used=ConflictResolutionStrategy.KEEP_LOCAL,
            merged_memory={"id": mid},
        )

        mock_updater = AsyncMock(side_effect=ValueError("Update failed"))

        summary = await apply_merge_results([res], mock_updater)
        assert summary["failed"] == 1
        assert summary["errors"][0]["error"] == "Update failed"

    @pytest.mark.asyncio
    async def test_apply_merge_results_failure(self):
        """Test apply_merge_results with a failed result."""
        mid = uuid4()
        res = MergeResult(
            memory_id=mid,
            success=False,
            strategy_used=ConflictResolutionStrategy.MANUAL,
            error_message="Manual required",
        )

        summary = await apply_merge_results([res], AsyncMock())
        assert summary["failed"] == 1
        assert summary["errors"][0]["error"] == "Manual required"


class TestSyncManagerCoverage:
    @pytest.mark.asyncio
    async def test_handshake_bad_version(self):
        manager = SyncManager("agent1", "primary", MagicMock())
        handshake = SyncHandshake(
            peer_id="peer1", role="replica", protocol_version="99.9", capabilities=[]
        )
        success = await manager.receive_handshake(handshake)
        assert not success
        assert "peer1" not in manager.peers

    @pytest.mark.asyncio
    async def test_sync_unknown_peer(self):
        manager = SyncManager("agent1", "primary", MagicMock())
        with pytest.raises(ValueError, match="not connected"):
            await manager.sync_with_peer("unknown", "tenant")

    @pytest.mark.asyncio
    async def test_sync_exception(self):
        manager = SyncManager("agent1", "primary", MagicMock())
        # Add peer manually
        manager.peers["peer1"] = SyncPeer(
            peer_id="peer1",
            role="replica",
            protocol_version="1.0",
            last_seen=datetime.now(),
        )

        # Mock protocol to raise
        manager.protocol.pull = AsyncMock(side_effect=RuntimeError("Protocol error"))  # type: ignore

        log = await manager.sync_with_peer("peer1", "tenant")
        assert log.status == "failed"
        assert "Protocol error" in log.metadata["error"]
