from unittest.mock import MagicMock

import pytest

from apps.memory_api.core.actions import ActionType, ConsolidateEpisodicToWorkingAction
from apps.memory_api.core.reward import RewardFunction
from apps.memory_api.core.state import (
    BudgetState,
    GraphState,
    MemoryState,
    RAEState,
    WorkingContext,
)


@pytest.fixture
def real_state():
    return RAEState(
        tenant_id="test_tenant",
        project_id="test_project",
        budget_state=BudgetState(),
        memory_state=MemoryState(),
        graph_state=GraphState(),
        working_context=WorkingContext(),
    )


def test_evaluate_quality_default_fallback(real_state):
    """Test that unhandled action types return default quality 0.5 (Line 210)"""
    reward_fn = RewardFunction()
    action = ConsolidateEpisodicToWorkingAction(
        action_type=ActionType.CONSOLIDATE_EPISODIC_TO_WORKING, parameters={}
    )

    quality = reward_fn._evaluate_quality(real_state, action, real_state, {})
    assert quality == 0.5


def test_evaluate_retrieval_quality_zero_memories():
    """Test retrieval quality with zero memories (Line 227)"""
    reward_fn = RewardFunction()
    execution_result = {"memories_retrieved": 0}
    quality = reward_fn._evaluate_retrieval_quality(execution_result)
    assert quality == 0.0


def test_evaluate_llm_quality_no_result():
    """Test LLM quality with missing result (Line 250)"""
    reward_fn = RewardFunction()
    execution_result = {"status": "failed"}  # Non-empty but no llm_result
    quality = reward_fn._evaluate_llm_quality(execution_result)
    assert quality == 0.0


def test_evaluate_llm_quality_short_output():
    """Test LLM quality with short output (Line 261)"""
    reward_fn = RewardFunction()
    mock_result = MagicMock()
    mock_result.text = "Short text"
    execution_result = {"llm_result": mock_result}

    quality = reward_fn._evaluate_llm_quality(execution_result)
    assert quality == 0.4


def test_evaluate_reflection_quality_no_scoring():
    """Test reflection quality when scoring is missing (Line 293)"""
    reward_fn = RewardFunction()
    # Reflection object without scoring
    mock_reflection = MagicMock()
    mock_reflection.scoring = None

    execution_result = {"reflections": [mock_reflection]}

    quality = reward_fn._evaluate_reflection_quality(execution_result)
    assert quality == 0.6
