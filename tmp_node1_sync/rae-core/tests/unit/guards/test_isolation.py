"""Unit tests for MemoryIsolationGuard."""

from uuid import uuid4

import pytest

from rae_core.exceptions.base import RAEError
from rae_core.guards.isolation import MemoryIsolationGuard


class TestMemoryIsolationGuard:
    @pytest.fixture
    def guard(self):
        return MemoryIsolationGuard(strict_mode=False)

    def test_validate_search_results_success(self, guard):
        memories = [
            {"id": uuid4(), "agent_id": "a1", "session_id": "s1", "tenant_id": "t1"},
            {"id": uuid4(), "agent_id": "a1", "session_id": "s1", "tenant_id": "t1"},
        ]

        results = guard.validate_search_results(
            memories,
            expected_agent_id="a1",
            expected_session_id="s1",
            expected_tenant_id="t1",
        )

        assert len(results) == 2
        assert guard.leak_count == 0
        assert guard.validation_count == 1

    def test_filter_wrong_agent(self, guard):
        memories = [
            {"id": uuid4(), "agent_id": "a1", "tenant_id": "t1"},
            {"id": uuid4(), "agent_id": "a2", "tenant_id": "t1"},  # Leak!
        ]

        results = guard.validate_search_results(memories, expected_agent_id="a1")

        assert len(results) == 1
        assert results[0]["agent_id"] == "a1"
        assert guard.leak_count == 1

    def test_raise_on_leak(self, guard):
        memories = [{"agent_id": "bad"}]
        with pytest.raises(RAEError):
            guard.validate_search_results(
                memories, expected_agent_id="good", raise_on_leak=True
            )

    def test_filter_wrong_session(self, guard):
        memories = [
            {"id": uuid4(), "agent_id": "a1", "session_id": "s1"},
            {"id": uuid4(), "agent_id": "a1", "session_id": "s2"},  # Wrong session
        ]

        results = guard.validate_search_results(
            memories, expected_agent_id="a1", expected_session_id="s1"
        )

        assert len(results) == 1
        assert guard.leak_count == 1

    def test_filter_wrong_tenant(self, guard):
        memories = [
            {"id": uuid4(), "agent_id": "a1", "tenant_id": "t1"},
            {"id": uuid4(), "agent_id": "a1", "tenant_id": "t2"},  # Wrong tenant
        ]

        results = guard.validate_search_results(
            memories, expected_agent_id="a1", expected_tenant_id="t1"
        )

        assert len(results) == 1
        assert guard.leak_count == 1

    def test_validate_single_memory(self, guard):
        memory = {"agent_id": "a1", "tenant_id": "t1"}

        assert guard.validate_single_memory(memory, expected_agent_id="a1") is True
        assert guard.validate_single_memory(memory, expected_agent_id="a2") is False

    def test_stats_and_reset(self, guard):
        # Trigger 1 valid, 1 leak
        guard.validate_search_results(
            [{"agent_id": "a1"}, {"agent_id": "bad"}], expected_agent_id="a1"
        )

        stats = guard.get_stats()
        assert stats["leak_count"] == 1
        assert stats["validation_count"] == 1
        assert stats["leak_rate"] == 1.0

        guard.reset_stats()
        assert guard.get_stats()["leak_count"] == 0
