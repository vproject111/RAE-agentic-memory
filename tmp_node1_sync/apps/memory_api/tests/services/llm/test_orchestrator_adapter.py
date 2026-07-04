from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from apps.llm.models import LLMResponse, TokenUsage
from apps.memory_api.services.llm.orchestrator_adapter import OrchestratorAdapter


class MockResponseModel(BaseModel):
    answer: str
    confidence: float


@pytest.fixture
def mock_orchestrator():
    orch = MagicMock()
    orch.generate = AsyncMock()
    orch.strategies_config = {}
    return orch


@pytest.fixture
def adapter(mock_orchestrator):
    return OrchestratorAdapter(mock_orchestrator)


@pytest.mark.asyncio
async def test_generate_calls_orchestrator(adapter, mock_orchestrator):
    mock_orchestrator.generate.return_value = LLMResponse(
        text="Hello",
        usage=TokenUsage(10, 10, 20),
        finish_reason="stop",
        raw={},
        model_name="gpt-4",
    )

    result = await adapter.generate(system="sys", prompt="user", model="gpt-4")

    assert result.text == "Hello"
    assert result.model_name == "gpt-4"

    mock_orchestrator.generate.assert_awaited_once()
    request = mock_orchestrator.generate.call_args[0][0]
    assert request.model == "gpt-4"
    assert request.messages[0].role == "system"
    assert request.messages[1].role == "user"


@pytest.mark.asyncio
async def test_generate_structured_parses_json(adapter, mock_orchestrator):
    mock_orchestrator.generate.return_value = LLMResponse(
        text='{"answer": "Yes", "confidence": 0.9}',
        usage=TokenUsage(10, 10, 20),
        finish_reason="stop",
        raw={},
        model_name="gpt-4",
    )

    result = await adapter.generate_structured(
        system="sys", prompt="user", model="gpt-4", response_model=MockResponseModel
    )

    assert isinstance(result, MockResponseModel)
    assert result.answer == "Yes"
    assert result.confidence == 0.9

    request = mock_orchestrator.generate.call_args[0][0]
    assert request.json_mode is True
    # Check if json instruction was added
    assert "Respond strictly with valid JSON" in request.messages[0].content
