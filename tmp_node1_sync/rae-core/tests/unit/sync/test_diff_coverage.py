"""Unit tests for diff.py to achieve 100% coverage."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from rae_core.sync.diff import (
    ChangeType,
    DiffResult,
    MemoryChange,
    calculate_memory_diff,
    get_sync_direction,
)


class TestDiffCoverage:
    """Test suite for diff.py coverage gaps."""

    def test_diff_result_properties(self):
        """Test has_conflicts and total_changes properties."""
        mid = uuid4()
        c1 = MemoryChange(memory_id=mid, change_type=ChangeType.CREATED)
        res = DiffResult(tenant_id="t1", agent_id="a1", created=[c1])

        assert res.has_changes is True
        assert res.has_conflicts is False
        assert res.total_changes == 1

        c2 = MemoryChange(
            memory_id=mid, change_type=ChangeType.MODIFIED, conflicts=True
        )
        res.conflicts = [c2]
        assert res.has_conflicts is True

    def test_calculate_diff_unchanged(self):
        """Test calculate_memory_diff with unchanged memories."""
        mid = uuid4()
        local = [{"id": str(mid), "content": "same", "version": 1}]
        remote = [{"id": str(mid), "content": "same", "version": 1}]

        res = calculate_memory_diff(local, remote, "t1", "a1")
        assert len(res.unchanged) == 1
        assert res.unchanged[0].memory_id == mid
        assert res.has_changes is False

    def test_calculate_diff_modified_no_conflict(self):
        """Test modified memory without conflict (e.g. one-sided change)."""
        mid = uuid4()
        now = datetime.now(timezone.utc)
        # Local modified, Remote NOT modified (None timestamp)
        local = [{"id": str(mid), "content": "new", "modified_at": now}]
        remote = [{"id": str(mid), "content": "old", "modified_at": None}]

        res = calculate_memory_diff(local, remote, "t1", "a1")
        assert len(res.modified) == 1
        assert res.modified[0].conflicts is False

    def test_detect_conflicts_close_timestamps(self):
        """Test that very close timestamps do not trigger a conflict."""
        mid = uuid4()
        now = datetime.now(timezone.utc)
        local = [{"id": str(mid), "content": "L", "modified_at": now}]
        remote = [
            {
                "id": str(mid),
                "content": "R",
                "modified_at": now + timedelta(milliseconds=500),
            }
        ]

        res = calculate_memory_diff(local, remote, "t1", "a1")
        assert len(res.modified) == 1
        assert res.modified[0].conflicts is False

    def test_get_sync_direction_modified_timestamps(self):
        """Test get_sync_direction based on timestamps."""
        mid = uuid4()
        now = datetime.now(timezone.utc)

        # Local newer -> Push
        c1 = MemoryChange(
            memory_id=mid,
            change_type=ChangeType.MODIFIED,
            local_modified=now + timedelta(minutes=1),
            remote_modified=now,
        )
        assert get_sync_direction(c1) == "push"

        # Remote newer -> Pull
        c2 = MemoryChange(
            memory_id=mid,
            change_type=ChangeType.MODIFIED,
            local_modified=now,
            remote_modified=now + timedelta(minutes=1),
        )
        assert get_sync_direction(c2) == "pull"

    def test_get_sync_direction_defaults(self):
        """Test default sync directions."""
        mid = uuid4()
        # MODIFIED but missing one timestamp -> Pull
        c = MemoryChange(
            memory_id=mid, change_type=ChangeType.MODIFIED, local_modified=None
        )
        assert get_sync_direction(c) == "pull"

        # UNCHANGED -> Pull (default)
        c2 = MemoryChange(memory_id=mid, change_type=ChangeType.UNCHANGED)
        assert get_sync_direction(c2) == "pull"
