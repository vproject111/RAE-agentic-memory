from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.sync.merge import (
    ConflictResolutionStrategy,
    ConflictResolver,
    MergeResult,
    apply_merge_results,
    merge_memories,
)


class TestMergeCoverage:
    """Test suite for merge.py coverage gaps."""

    @pytest.fixture
    def resolver(self):
        return ConflictResolver()

    def test_resolve_keep_local(self, resolver):
        local = {"id": str(uuid4()), "content": "local"}
        remote = {"id": local["id"], "content": "remote"}
        res = resolver.resolve(
            local, remote, ["content"], strategy=ConflictResolutionStrategy.KEEP_LOCAL
        )
        assert res.success
        assert res.merged_memory["content"] == "local"

    def test_resolve_keep_remote(self, resolver):
        local = {"id": str(uuid4()), "content": "local"}
        remote = {"id": local["id"], "content": "remote"}
        res = resolver.resolve(
            local, remote, ["content"], strategy=ConflictResolutionStrategy.KEEP_REMOTE
        )
        assert res.success
        assert res.merged_memory["content"] == "remote"

    def test_resolve_manual_strategy(self, resolver):
        local = {"id": str(uuid4()), "content": "local"}
        remote = {"id": local["id"], "content": "remote"}
        res = resolver.resolve(
            local, remote, ["content"], strategy=ConflictResolutionStrategy.MANUAL
        )
        assert not res.success
        assert res.error_message == "Manual resolution required"

    def test_resolve_exception(self, resolver):
        # The code tries memory_id = UUID(local["id"])
        # In resolve(), this is wrapped in a try-except that returns a MergeResult with success=False
        # But wait, the previous run showed it DID NOT catch ValueError?
        # Let's re-read merge.py
        res = resolver.resolve({"id": "not-a-uuid"}, {}, [])
        assert not res.success
        assert "badly formed hexadecimal UUID string" in res.error_message

    def test_last_write_wins_same_timestamp(self, resolver):
        now = datetime.now(timezone.utc)
        local = {"id": str(uuid4()), "modified_at": now, "version": 2}
        remote = {"id": local["id"], "modified_at": now, "version": 1}
        # Local wins due to higher version
        res = resolver._last_write_wins(local, remote, [])
        assert res["version"] == 2

        remote["version"] = 3
        # Remote wins
        res = resolver._last_write_wins(local, remote, [])
        assert res["version"] == 3

    def test_merge_fields_logic(self, resolver):
        local = {
            "id": str(uuid4()),
            "tags": ["t1"],
            "metadata": {"a": 1},
            "importance": 0.5,
            "modified_at": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        remote = {
            "id": local["id"],
            "tags": ["t2"],
            "metadata": {"b": 2},
            "importance": 0.8,
            "modified_at": datetime.now(timezone.utc),
        }

        # Merge tags, metadata, importance
        res = resolver._merge_fields(local, remote, ["tags", "metadata", "importance"])
        assert set(res["tags"]) == {"t1", "t2"}
        assert res["metadata"] == {"a": 1, "b": 2}
        assert res["importance"] == 0.8
        assert res["version"] == 2  # max(1,1) + 1

    def test_merge_memories_flow(self):
        mid1 = uuid4()
        mid2 = uuid4()
        mid3 = uuid4()

        local: list[dict[str, Any]] = [
            {"id": str(mid1), "content": "only local"},
            {
                "id": str(mid3),
                "content": "local conflict",
                "modified_at": datetime.now(timezone.utc),
            },
        ]
        remote: list[dict[str, Any]] = [
            {"id": str(mid2), "content": "only remote"},
            {
                "id": str(mid3),
                "content": "remote conflict",
                "modified_at": datetime.now(timezone.utc) + timedelta(minutes=1),
            },
        ]

        results = merge_memories(local, remote)
        assert len(results) == 3

        result_ids = {r.memory_id for r in results}
        assert result_ids == {mid1, mid2, mid3}

    @pytest.mark.asyncio
    async def test_apply_merge_results_success(self):
        mid = uuid4()
        res = MergeResult(
            memory_id=mid,
            success=True,
            strategy_used=ConflictResolutionStrategy.KEEP_LOCAL,
            merged_memory={"id": mid, "content": "c"},
        )
        summary = await apply_merge_results([res], AsyncMock())
        assert summary["successful"] == 1
