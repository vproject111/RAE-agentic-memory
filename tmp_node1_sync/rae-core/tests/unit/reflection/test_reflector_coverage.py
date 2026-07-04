"""Unit tests for Reflector to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.reflection.reflector import Reflector


class TestReflectorCoverage:
    """Test suite for Reflector coverage gaps."""

    @pytest.fixture
    def mock_deps(self):
        ms = MagicMock()
        ms.get_memory = AsyncMock()
        ms.store_memory = AsyncMock(return_value=uuid4())
        ms.list_memories = AsyncMock()

        llm = MagicMock()
        llm.generate = AsyncMock(return_value="Insight")
        return ms, llm

    @pytest.mark.asyncio
    async def test_generate_reflection_no_memories(self, mock_deps):
        ms, _ = mock_deps
        ms.get_memory.return_value = None
        r = Reflector(ms)
        res = await r.generate_reflection([uuid4()], "t", "a")
        assert res["success"] is False
        assert "No valid memories found" in res["error"]

    @pytest.mark.asyncio
    async def test_generate_reflection_unknown_type(self, mock_deps):
        ms, _ = mock_deps
        ms.get_memory.return_value = {"content": "c"}
        r = Reflector(ms)
        res = await r.generate_reflection(
            [uuid4()], "t", "a", reflection_type="unknown"
        )
        assert res["success"] is False
        assert "Unknown reflection type" in res["error"]

    @pytest.mark.asyncio
    async def test_generate_insight_with_llm(self, mock_deps):
        ms, llm = mock_deps
        ms.get_memory.return_value = {
            "content": "important content",
            "importance": 0.9,
            "layer": "em",
        }
        r = Reflector(ms, llm_provider=llm)
        res = await r.generate_reflection(
            [uuid4()], "t", "a", reflection_type="insight"
        )
        assert res["success"] is True
        assert res["type"] == "insight"
        assert res["content"] == "Insight"
        llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_insight_llm_failure(self, mock_deps):
        ms, llm = mock_deps
        ms.get_memory.return_value = {"content": "c", "importance": 0.5}
        llm.generate.side_effect = Exception("LLM Down")
        r = Reflector(ms, llm_provider=llm)
        res = await r.generate_reflection(
            [uuid4()], "t", "a", reflection_type="insight"
        )
        assert res["success"] is True
        assert "average importance 0.50" in res["content"]

    @pytest.mark.asyncio
    async def test_generate_insight_rule_based(self, mock_deps):
        ms, _ = mock_deps
        ms.get_memory.return_value = {"content": "c", "layer": "working"}
        r = Reflector(ms)
        res = await r.generate_reflection(
            [uuid4()], "t", "a", reflection_type="insight"
        )
        assert res["success"] is True
        assert "across layers: working" in res["content"]

    @pytest.mark.asyncio
    async def test_identify_candidates_too_few(self, mock_deps):
        ms, _ = mock_deps
        ms.list_memories.return_value = [{"id": 1}]  # only 1
        r = Reflector(ms)
        res = await r.identify_reflection_candidates("t", min_memories=5)
        assert res == []
