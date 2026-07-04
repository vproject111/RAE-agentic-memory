"""Extended tests for SyncProtocol and Diff calculation."""

from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.sync.diff import ChangeType, calculate_memory_diff, get_sync_direction
from rae_core.sync.protocol import SyncProtocol


class TestSyncProtocol:
    @pytest.fixture
    def mock_provider(self):
        p = Mock()
        p.push_memories = AsyncMock()
        p.pull_memories = AsyncMock()
        p.sync_memories = AsyncMock()
        return p

    @pytest.fixture
    def protocol(self, mock_provider):
        return SyncProtocol(sync_provider=mock_provider)

    @pytest.mark.asyncio
    async def test_push_success(self, protocol, mock_provider):
        mock_provider.push_memories.return_value = {
            "success": True,
            "sync_id": "s1",
            "synced_memory_ids": ["m1"],
        }
        res = await protocol.push("t1", "a1")
        assert res.success is True
        assert res.metadata.sync_type == "push"

    @pytest.mark.asyncio
    async def test_push_failure(self, protocol, mock_provider):
        mock_provider.push_memories.side_effect = Exception("Network error")
        res = await protocol.push("t1", "a1")
        assert res.success is False
        assert "Network error" in res.error_message

    @pytest.mark.asyncio
    async def test_pull_success(self, protocol, mock_provider):
        mock_provider.pull_memories.return_value = {"success": True}
        res = await protocol.pull("t1", "a1")
        assert res.success is True

    @pytest.mark.asyncio
    async def test_sync_success(self, protocol, mock_provider):
        mock_provider.sync_memories.return_value = {"success": True}
        res = await protocol.sync("t1", "a1")
        assert res.success is True


class TestMemoryDiff:
    def test_calculate_diff_created_remote(self):
        id1 = uuid4()
        local: list[dict[str, Any]] = []
        remote: list[dict[str, Any]] = [{"id": id1, "content": "R1", "version": 1}]

        diff = calculate_memory_diff(local, remote, "t1", "a1")
        assert len(diff.created) == 1
        assert diff.created[0].memory_id == id1
        assert diff.has_changes is True

    def test_calculate_diff_deleted_local(self):
        id1 = uuid4()
        local: list[dict[str, Any]] = [{"id": id1, "content": "L1"}]
        remote: list[dict[str, Any]] = []

        diff = calculate_memory_diff(local, remote, "t1", "a1")
        assert len(diff.deleted) == 1
        assert diff.deleted[0].memory_id == id1

    def test_calculate_diff_modified_conflict(self):
        id1 = uuid4()
        now = datetime.now(timezone.utc)
        # Both modified at different times with different content
        local: list[dict[str, Any]] = [
            {"id": id1, "content": "Local", "modified_at": now + timedelta(seconds=10)}
        ]
        remote: list[dict[str, Any]] = [
            {"id": id1, "content": "Remote", "modified_at": now}
        ]

        diff = calculate_memory_diff(local, remote, "t1", "a1")
        assert len(diff.conflicts) == 1
        assert diff.conflicts[0].memory_id == id1
        assert "content" in diff.conflicts[0].conflict_fields

    def test_get_sync_direction(self):
        from rae_core.sync.diff import MemoryChange

        id1 = uuid4()

        # Created -> Pull
        c1 = MemoryChange(memory_id=id1, change_type=ChangeType.CREATED)
        assert get_sync_direction(c1) == "pull"

        # Deleted -> Push
        c2 = MemoryChange(memory_id=id1, change_type=ChangeType.DELETED)
        assert get_sync_direction(c2) == "push"

        # Conflict -> Conflict
        c3 = MemoryChange(
            memory_id=id1, change_type=ChangeType.MODIFIED, conflicts=True
        )
        assert get_sync_direction(c3) == "conflict"
