"""Unit tests for Evaluator and SanityChecker to achieve 100% coverage."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.reflection.evaluator import Evaluator, SanityChecker


class TestEvaluatorCoverage:
    """Test suite for Evaluator coverage gaps."""

    @pytest.fixture
    def mock_storage(self):
        storage = MagicMock()
        storage.get_memory = AsyncMock()
        return storage

    @pytest.mark.asyncio
    async def test_evaluate_memory_quality_not_found(self, mock_storage):
        evaluator = Evaluator(mock_storage)
        mock_storage.get_memory.return_value = None
        res = await evaluator.evaluate_memory_quality(uuid4(), "t")
        assert res == {"error": 1.0}

    @pytest.mark.asyncio
    async def test_evaluate_action_outcomes(self, mock_storage):
        evaluator = Evaluator(mock_storage)

        # update_importance
        res_imp = {"success": True, "updated_count": 2, "total": 2}
        out_imp = await evaluator.evaluate_action_outcome(
            "update_importance", res_imp, {}
        )
        assert out_imp["score"] == 1.0

        # update_importance zero total
        res_imp0 = {"success": True, "updated_count": 0, "total": 0}
        out_imp0 = await evaluator.evaluate_action_outcome(
            "update_importance", res_imp0, {}
        )
        assert out_imp0["score"] == 0.0

        # create_semantic_link
        res_link = {"success": True, "link": {"type": "refers_to"}}
        out_link = await evaluator.evaluate_action_outcome(
            "create_semantic_link", res_link, {}
        )
        assert out_link["score"] == 0.8

        # prune_duplicates
        res_prune = {"success": True, "pruned_count": 1, "total": 4}
        out_prune = await evaluator.evaluate_action_outcome(
            "prune_duplicates", res_prune, {}
        )
        assert out_prune["score"] == 0.25

        # prune zero
        res_prune0 = {"success": True, "pruned_count": 0, "total": 0}
        out_prune0 = await evaluator.evaluate_action_outcome(
            "prune_duplicates", res_prune0, {}
        )
        assert out_prune0["score"] == 0.0

        # Unknown action
        res_unk = {"success": True}
        out_unk = await evaluator.evaluate_action_outcome("unknown", res_unk, {})
        assert out_unk["outcome"] == "success"
        assert out_unk["score"] == 0.5

    @pytest.mark.asyncio
    async def test_evaluate_memory_batch_with_errors(self, mock_storage):
        evaluator = Evaluator(mock_storage)
        mids = [uuid4(), uuid4()]
        # First succeeds, second not found (error)
        mock_storage.get_memory.side_effect = [{"content": "c"}, None]

        res = await evaluator.evaluate_memory_batch(mids, "t")
        assert res["evaluated_count"] == 1
        assert res["total"] == 2


class TestSanityCheckerCoverage:
    def test_contradictions(self):
        checker = SanityChecker()

        # Direct negation
        s1 = "The sky is blue"
        s2 = "not The sky is blue"
        sane, issues = checker.check_for_contradictions([s1, s2])
        assert sane is False
        assert len(issues) == 1

        # Pattern "is X" vs "is not X"
        s3 = "Alice is happy"
        s4 = "Alice is not happy"
        sane, issues = checker.check_for_contradictions([s3, s4])
        assert sane is False

        # Reverse pattern
        sane, issues = checker.check_for_contradictions([s4, s3])
        assert sane is False

        # No contradictions
        sane, issues = checker.check_for_contradictions(["A is B", "C is D"])
        assert sane is True
