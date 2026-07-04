from datetime import datetime
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from rae_core.reflection.actor import Actor
from rae_core.reflection.engine import ReflectionEngine
from rae_core.reflection.evaluator import Evaluator
from rae_core.reflection.reflector import Reflector


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.get_memory = AsyncMock()
    storage.delete_memory = AsyncMock(return_value=True)
    storage.list_memories = AsyncMock(return_value=[])
    storage.store_memory = AsyncMock(return_value=uuid4())
    return storage


@pytest.mark.asyncio
async def test_actor_extra(mock_storage):
    actor = Actor(mock_storage)

    # Unknown action (58)
    res = await actor.execute_action("unknown", {}, "t1")
    assert res["success"] is False
    assert "Unknown action" in res["error"]

    # Consolidate no memories (76)
    res = await actor._consolidate_memories({}, "t1")
    assert res["success"] is False
    assert "No memories provided" in res["error"]

    # Consolidate invalid memories (89)
    mock_storage.get_memory.return_value = None
    res = await actor._consolidate_memories({"memory_ids": [uuid4()]}, "t1")
    assert res["success"] is False
    assert "No valid memories found" in res["error"]

    # Create semantic link missing IDs (172)
    res = await actor._create_semantic_link({}, "t1")
    assert res["success"] is False
    assert "Missing source or target ID" in res["error"]


@pytest.mark.asyncio
async def test_reflection_engine_find_low_quality_string_id(mock_storage):
    engine = ReflectionEngine(mock_storage)

    # Mock evaluator to return low quality

    with patch.object(
        engine.evaluator,
        "evaluate_memory_quality",
        AsyncMock(return_value={"quality": 0.1}),
    ):
        # Mock storage to return memory with string ID

        mock_storage.list_memories.return_value = [
            {"id": str(uuid4()), "content": "test"}
        ]

        results = await engine.prune_low_quality_memories(
            "t1", "a1", quality_threshold=0.5
        )

        assert results["success"] is True

        assert results["pruned_count"] == 1


@pytest.mark.asyncio
async def test_reflection_evaluator_extra(mock_storage):
    evaluator = Evaluator(mock_storage)

    # Line 70: context provided
    memory = {"content": "test", "id": uuid4(), "created_at": datetime.now()}
    mock_storage.get_memory.return_value = memory

    # We need to mock scorer.evaluate
    with patch.object(
        evaluator.scorer, "evaluate", return_value=MagicMock()
    ) as mock_evaluate:
        await evaluator.evaluate_memory_quality(
            cast(UUID, memory["id"]), tenant_id="t1", context="query"
        )
        assert mock_evaluate.call_args[0][1]["query"] == "query"

    # Consolidation scores (142, 146)
    res_low = evaluator._evaluate_consolidation({"consolidated_count": 1}, {})
    assert res_low["score"] == 0.3

    res_high = evaluator._evaluate_consolidation({"consolidated_count": 10}, {})
    assert res_high["score"] == 1.0


@pytest.mark.asyncio
async def test_reflector_temporal_clustering(mock_storage):
    reflector = Reflector(mock_storage)
    memories = [
        {"id": uuid4(), "content": "c1", "created_at": "2025-01-01T10:00:00"},
        {"id": uuid4(), "content": "c2", "created_at": "2025-01-01T10:05:00"},
        {"id": uuid4(), "content": "c3", "created_at": "2025-01-01T10:10:00"},
    ]
    # This should hit line 147 in reflector.py
    res = await reflector._generate_pattern_reflection(memories, "t1", "a1")
    assert "temporal_clustering" in res["patterns"]
