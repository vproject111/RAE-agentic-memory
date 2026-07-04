"""Unit tests for ReflectionEngine to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.reflection.engine import ReflectionEngine


class TestReflectionEngineCoverage:
    """Test suite for ReflectionEngine coverage gaps."""

    @pytest.fixture
    def mock_deps(self):
        ms = MagicMock()
        ms.get_memory = AsyncMock()
        ms.list_memories = AsyncMock(return_value=[])
        ms.delete_memory = AsyncMock(return_value=True)

        llm = MagicMock()
        llm.generate = AsyncMock(return_value=("reflection", {}))

        return ms, llm

    @pytest.mark.asyncio
    async def test_run_reflection_cycle_no_memories(self, mock_deps):
        ms, llm = mock_deps
        engine = ReflectionEngine(ms, llm)
        # Mocking to skip initial checks
        res = await engine.run_reflection_cycle("t", "a")
        assert res["success"] is False
        assert res["reason"] == "No reflection candidates found"

    @pytest.mark.asyncio
    async def test_execute_action_with_evaluation(self, mock_deps):
        ms, llm = mock_deps
        engine = ReflectionEngine(ms, llm)

        # Use patch.object to avoid method-assign errors in mypy
        with (
            patch.object(
                engine.actor,
                "execute_action",
                AsyncMock(return_value={"success": True, "action": "test"}),
            ),
            patch.object(
                engine.evaluator,
                "evaluate_action_outcome",
                AsyncMock(return_value={"score": 1.0}),
            ),
        ):
            await engine.execute_action("consolidate", {}, "t", evaluate=True)

    @pytest.mark.asyncio
    async def test_evaluate_memory_quality(self, mock_deps):
        ms, llm = mock_deps
        engine = ReflectionEngine(ms, llm)
        with patch.object(
            engine.evaluator,
            "evaluate_memory_quality",
            AsyncMock(return_value={"quality": 0.8}),
        ):
            res = await engine.evaluate_memory_quality(uuid4(), "t")
            assert res["quality"] == 0.8

    @pytest.mark.asyncio
    async def test_identify_low_quality_memories(self, mock_deps):
        ms, llm = mock_deps
        mid1 = uuid4()
        ms.list_memories.return_value = [{"id": mid1}]
        engine = ReflectionEngine(ms, llm)
        with patch.object(
            engine.evaluator,
            "evaluate_memory_quality",
            AsyncMock(return_value={"quality": 0.1}),
        ):
            low = await engine.identify_low_quality_memories("t", quality_threshold=0.4)
            assert len(low) == 1
            assert low[0] == mid1

    @pytest.mark.asyncio
    async def test_prune_low_quality_none_found(self, mock_deps):
        ms, llm = mock_deps
        engine = ReflectionEngine(ms, llm)
        # identify_low_quality_memories uses list_memories which is [] by default
        res = await engine.prune_low_quality_memories("t")
        assert res["success"] is True
        assert res["pruned_count"] == 0

    @pytest.mark.asyncio
    async def test_prune_low_quality_execute(self, mock_deps):
        ms, llm = mock_deps
        mid = uuid4()
        ms.list_memories.return_value = [{"id": mid}]
        engine = ReflectionEngine(ms, llm)

        with (
            patch.object(
                engine.evaluator,
                "evaluate_memory_quality",
                AsyncMock(return_value={"quality": 0.1}),
            ),
            patch.object(
                engine.actor,
                "execute_action",
                AsyncMock(return_value={"success": True, "count": 1}),
            ) as mock_exec,
        ):
            res = await engine.prune_low_quality_memories("t")
            assert res["success"] is True
            mock_exec.assert_called_once()
