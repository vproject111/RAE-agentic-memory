"""Unit tests for Reflection Actor and Evaluator."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.reflection.actor import Actor
from rae_core.reflection.evaluator import Evaluator


@pytest.fixture
def mock_storage():
    storage = Mock()
    storage.get_memory = AsyncMock()
    storage.store_memory = AsyncMock()
    storage.update_memory = AsyncMock()
    storage.delete_memory = AsyncMock()
    return storage


class TestActor:
    @pytest.mark.asyncio
    async def test_consolidate_memories(self, mock_storage):
        actor = Actor(memory_storage=mock_storage)
        mem_id1 = str(uuid4())
        mem_id2 = str(uuid4())

        mock_storage.get_memory.side_effect = [
            {"content": "I like cats", "tenant_id": "t1"},
            {"content": "Cats are fuzzy", "tenant_id": "t1"},
        ]
        mock_storage.store_memory.return_value = uuid4()

        context = {"memory_ids": [mem_id1, mem_id2], "agent_id": "a1"}
        result = await actor.execute_action("consolidate_memories", context, "t1")

        assert result["success"] is True
        assert result["consolidated_count"] == 2
        mock_storage.store_memory.assert_called_once()
        assert "cats" in mock_storage.store_memory.call_args.kwargs["content"].lower()

    @pytest.mark.asyncio
    async def test_update_importance(self, mock_storage):
        actor = Actor(memory_storage=mock_storage)
        mem_id = uuid4()
        mock_storage.update_memory.return_value = True

        context = {"updates": [{"memory_id": mem_id, "importance": 0.9}]}
        result = await actor.execute_action("update_importance", context, "t1")

        assert result["success"] is True
        assert result["updated_count"] == 1
        mock_storage.update_memory.assert_called_once_with(
            memory_id=mem_id, tenant_id="t1", updates={"importance": 0.9}
        )

    @pytest.mark.asyncio
    async def test_create_semantic_link(self, mock_storage):
        actor = Actor(memory_storage=mock_storage)
        src_id = uuid4()
        tgt_id = uuid4()
        mock_storage.update_memory.return_value = True

        context = {
            "source_id": src_id,
            "target_id": tgt_id,
            "relation_type": "supports",
        }
        result = await actor.execute_action("create_semantic_link", context, "t1")

        assert result["success"] is True
        mock_storage.update_memory.assert_called_once()
        assert (
            "link_supports"
            in mock_storage.update_memory.call_args.kwargs["updates"]["metadata"]
        )

    @pytest.mark.asyncio
    async def test_prune_duplicates(self, mock_storage):
        actor = Actor(memory_storage=mock_storage)
        mem_id = uuid4()
        mock_storage.delete_memory.return_value = True

        context = {"memory_ids": [mem_id]}
        result = await actor.execute_action("prune_duplicates", context, "t1")

        assert result["success"] is True
        assert result["pruned_count"] == 1
        mock_storage.delete_memory.assert_called_once_with(
            memory_id=mem_id, tenant_id="t1"
        )


class TestEvaluator:
    @pytest.mark.asyncio
    async def test_evaluate_memory_quality(self, mock_storage):
        evaluator = Evaluator(memory_storage=mock_storage)
        mem_id = uuid4()
        mock_storage.get_memory.return_value = {
            "content": "This is a very long and coherent sentence that should score well.",
            "tenant_id": "t1",
            "tags": ["a"],
            "metadata": {"b": 1},
        }

        metrics = await evaluator.evaluate_memory_quality(mem_id, "t1")
        assert "quality" in metrics
        assert "completeness" in metrics
        assert metrics["quality"] > 0

    @pytest.mark.asyncio
    async def test_evaluate_action_outcome(self, mock_storage):
        evaluator = Evaluator(memory_storage=mock_storage)

        # Consolidation outcome
        result = {"success": True, "consolidated_count": 3}
        outcome = await evaluator.evaluate_action_outcome(
            "consolidate_memories", result, {}
        )
        assert outcome["outcome"] == "success"
        assert outcome["score"] == 0.7

        # Failure case
        fail_result = {"success": False, "error": "Disk full"}
        outcome = await evaluator.evaluate_action_outcome(
            "prune_duplicates", fail_result, {}
        )
        assert outcome["outcome"] == "failure"
        assert outcome["score"] == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_memory_batch(self, mock_storage):
        evaluator = Evaluator(memory_storage=mock_storage)
        mem_ids = [uuid4(), uuid4()]
        mock_storage.get_memory.return_value = {"content": "Sample", "tenant_id": "t1"}

        batch_results = await evaluator.evaluate_memory_batch(mem_ids, "t1")
        assert batch_results["evaluated_count"] == 2
        assert "quality" in batch_results["metrics"]
