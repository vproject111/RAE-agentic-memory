from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from rae_core.interfaces.llm import ILLMProvider
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.reflection.engine import ReflectionEngine


@pytest.fixture
def mock_storage():
    storage = Mock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock(return_value=uuid4())
    storage.list_memories = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def mock_llm():
    llm = Mock(spec=ILLMProvider)
    return llm


@pytest.fixture
def reflection_engine(mock_storage, mock_llm):
    # Patch sub-components to test orchestration logic independently
    with (
        patch("rae_core.reflection.engine.Actor") as MockActor,
        patch("rae_core.reflection.engine.Evaluator") as MockEvaluator,
        patch("rae_core.reflection.engine.Reflector") as MockReflector,
    ):
        engine = ReflectionEngine(memory_storage=mock_storage, llm_provider=mock_llm)

        # Setup mocks on the instance
        engine.actor = MockActor.return_value  # type: ignore[method-assign]
        engine.evaluator = MockEvaluator.return_value  # type: ignore[method-assign]
        engine.reflector = MockReflector.return_value  # type: ignore[method-assign]

        # Configure async methods
        engine.actor.execute_action = AsyncMock()  # type: ignore[method-assign]
        engine.evaluator.evaluate_action_outcome = AsyncMock()  # type: ignore[method-assign]
        engine.reflector.identify_reflection_candidates = AsyncMock()  # type: ignore[method-assign]
        engine.reflector.generate_reflection = AsyncMock()  # type: ignore[method-assign]

        yield engine


@pytest.mark.asyncio
async def test_run_reflection_cycle_success(reflection_engine):
    # Setup happy path

    # 1. Identify candidates
    reflection_engine.reflector.identify_reflection_candidates.return_value = [
        {"memory_ids": [uuid4(), uuid4()], "type": "group"}
    ]

    # 2. Generate reflection
    reflection_engine.reflector.generate_reflection.return_value = {
        "success": True,
        "reflection_id": str(uuid4()),
    }

    # 3. Execute action
    reflection_engine.actor.execute_action.return_value = {
        "success": True,
        "action_id": "act_1",
    }

    # 4. Evaluate
    reflection_engine.evaluator.evaluate_action_outcome.return_value = {
        "outcome": "success",
        "score": 1.0,
    }

    # Run cycle
    results = await reflection_engine.run_reflection_cycle(tenant_id="t", agent_id="a")

    assert results["success"] is True
    assert results["reflections_generated"] == 1
    assert results["actions_executed"] == 1
    assert results["evaluations_performed"] == 1

    # Verify sequence
    reflection_engine.reflector.identify_reflection_candidates.assert_called_once()
    reflection_engine.reflector.generate_reflection.assert_called_once()
    reflection_engine.actor.execute_action.assert_called_once()
    reflection_engine.evaluator.evaluate_action_outcome.assert_called_once()


@pytest.mark.asyncio
async def test_run_reflection_cycle_no_candidates(reflection_engine):
    reflection_engine.reflector.identify_reflection_candidates.return_value = []

    results = await reflection_engine.run_reflection_cycle(tenant_id="t", agent_id="a")

    assert results["success"] is False
    assert results["reason"] == "No reflection candidates found"

    reflection_engine.reflector.generate_reflection.assert_not_called()


@pytest.mark.asyncio
async def test_run_reflection_cycle_generation_failure(reflection_engine):
    reflection_engine.reflector.identify_reflection_candidates.return_value = [
        {"memory_ids": [uuid4()], "type": "group"}
    ]

    reflection_engine.reflector.generate_reflection.return_value = {
        "success": False,
        "error": "LLM error",
    }

    results = await reflection_engine.run_reflection_cycle(tenant_id="t", agent_id="a")

    assert results["reflections_generated"] == 0
    assert results["actions_executed"] == 0

    reflection_engine.actor.execute_action.assert_not_called()
