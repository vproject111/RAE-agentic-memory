from typing import Any, cast

from rae_core.guards.isolation import MemoryIsolationGuard


def test_isolation_guard_object_input():
    guard = MemoryIsolationGuard()

    class MemoryObj:
        def __init__(self):
            self.agent_id = "a1"
            self.tenant_id = "t1"
            self.id = "m1"
            self.session_id = "s1"

    obj = MemoryObj()
    assert (
        guard.validate_single_memory(cast(Any, obj), "a1", expected_tenant_id="t1")
        is True
    )
    assert (
        guard.validate_single_memory(cast(Any, obj), "other", expected_tenant_id="t1")
        is False
    )


def test_isolation_guard_tenant_mismatch():
    guard = MemoryIsolationGuard()
    memory = {"agent_id": "a1", "tenant_id": "other_tenant", "id": "m1"}

    # Validation should fail when tenant_id mismatch
    assert guard.validate_single_memory(memory, "a1", expected_tenant_id="t1") is False


def test_isolation_guard_stats():
    guard = MemoryIsolationGuard()
    assert guard.get_stats()["leak_count"] == 0

    # Detection
    guard.validate_search_results([{"agent_id": "leak"}], "a1")
    stats = guard.get_stats()
    assert stats["leak_count"] == 1
    assert stats["leak_rate"] == 1.0

    # Reset
    guard.reset_stats()
    assert guard.get_stats()["leak_count"] == 0
