from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from rae_core.interfaces.agent import BaseAgent
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.models.interaction import AgentAction, AgentActionType, RAEInput
from rae_core.runtime import RAERuntime

# --- Mocks ---


class CompliantAgent(BaseAgent):
    async def run(self, input_payload: RAEInput) -> AgentAction:
        return AgentAction(
            type=AgentActionType.FINAL_ANSWER,
            content="I am a compliant agent.",
            confidence=0.99,
            reasoning="I followed the rules.",
        )


class RebelAgent(BaseAgent):
    async def run(self, input_payload: RAEInput) -> AgentAction:
        # Trying to use forbidden methods
        self.print("I will break the rules!")
        return AgentAction(
            type=AgentActionType.FINAL_ANSWER, content="Ignored", confidence=0.0
        )


class IllegalReturnAgent(BaseAgent):
    async def run(
        self, input_payload: RAEInput
    ):  # Missing return type hint intentionally
        return "Just a string"


# --- Tests ---


@pytest.mark.asyncio
async def test_runtime_enforces_memory_hook():
    """Test that RAERuntime automatically stores memory for Final Answers."""
    storage = MagicMock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock()

    agent = CompliantAgent()
    runtime = RAERuntime(storage, agent)

    payload = RAEInput(
        request_id=uuid4(),
        tenant_id="test-tenant",
        content="Hello",
        context={"project": "test-project"},
    )

    result = await runtime.process(payload)

    assert isinstance(result, AgentAction)
    assert result.content == "I am a compliant agent."

    # Verify memory hook triggered
    storage.store_memory.assert_called_once()
    call_args = storage.store_memory.call_args[1]
    assert call_args["content"] == "I am a compliant agent."
    assert call_args["layer"] == "episodic"
    assert call_args["project"] == "test-project"
    assert "rae-first" in call_args["tags"]


@pytest.mark.asyncio
async def test_agent_cannot_use_print():
    """Test that calling print() raises NotImplementedError."""
    agent = RebelAgent()
    payload = RAEInput(request_id=uuid4(), tenant_id="t", content="c")

    with pytest.raises(NotImplementedError) as exc:
        await agent.run(payload)

    assert "VIOLATION" in str(exc.value)


@pytest.mark.asyncio
async def test_runtime_rejects_string_return():
    """Test that returning a raw string raises TypeError."""
    storage = MagicMock(spec=IMemoryStorage)
    agent = IllegalReturnAgent()
    runtime = RAERuntime(storage, agent)
    payload = RAEInput(request_id=uuid4(), tenant_id="t", content="c")

    with pytest.raises(TypeError) as exc:
        await runtime.process(payload)

    assert "Agent returned <class 'str'>" in str(exc.value)
    assert "FORBIDDEN" in str(exc.value)
