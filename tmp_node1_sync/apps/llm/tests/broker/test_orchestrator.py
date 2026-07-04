from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.llm.broker.orchestrator import LLMOrchestrator
from apps.llm.models import LLMRequest, LLMResponse, TokenUsage


@pytest.fixture
def mock_router():
    router = MagicMock()
    router.providers = {}
    router.complete = AsyncMock()
    return router


@pytest.fixture
def mock_llm_request():
    return LLMRequest(model="default-model", messages=[])


@pytest.fixture
def mock_llm_response():
    return LLMResponse(
        text="Response",
        usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
        finish_reason="stop",
        raw={},
    )


@pytest.fixture
def orchestrator(mock_router):
    # Mock config directly to avoid file I/O
    config = {
        "default_strategy": "test_single",
        "models": [
            {
                "id": "model_a",
                "provider": "provider_a",
                "model_name": "real_model_a",
                "enabled": True,
            },
            {
                "id": "model_b",
                "provider": "provider_b",
                "model_name": "real_model_b",
                "enabled": True,
            },
        ],
        "strategies": {
            "test_single": {"mode": "single", "primary": "model_a"},
            "test_fallback": {
                "mode": "fallback",
                "primary": "model_a",
                "fallback": "model_b",
            },
        },
    }

    # Setup router providers
    provider_a = MagicMock()
    provider_a.complete = AsyncMock()
    provider_b = MagicMock()
    provider_b.complete = AsyncMock()

    mock_router.providers = {"provider_a": provider_a, "provider_b": provider_b}

    with patch(
        "apps.llm.broker.orchestrator.LLMOrchestrator._load_config", return_value=config
    ):
        orch = LLMOrchestrator(router=mock_router)
        return orch


@pytest.mark.asyncio
async def test_generate_single_strategy(
    orchestrator, mock_llm_request, mock_llm_response
):
    mock_llm_request.strategy = "test_single"

    # Mock provider response
    provider_a = orchestrator.router.providers["provider_a"]
    provider_a.complete.return_value = mock_llm_response

    response = await orchestrator.generate(mock_llm_request)

    assert response == mock_llm_response

    # Verify provider was called with correct model name
    call_args = provider_a.complete.call_args
    assert call_args is not None
    called_req = call_args[0][0]
    assert called_req.model == "real_model_a"


@pytest.mark.asyncio
async def test_generate_fallback_success(
    orchestrator, mock_llm_request, mock_llm_response
):
    mock_llm_request.strategy = "test_fallback"

    # Primary succeeds
    provider_a = orchestrator.router.providers["provider_a"]
    provider_a.complete.return_value = mock_llm_response

    response = await orchestrator.generate(mock_llm_request)

    assert response == mock_llm_response
    provider_a.complete.assert_awaited_once()
    orchestrator.router.providers["provider_b"].complete.assert_not_awaited()


@pytest.mark.asyncio
async def test_generate_fallback_triggered(
    orchestrator, mock_llm_request, mock_llm_response
):
    mock_llm_request.strategy = "test_fallback"

    # Primary fails
    provider_a = orchestrator.router.providers["provider_a"]
    provider_a.complete.side_effect = Exception("Primary failed")

    # Fallback succeeds
    provider_b = orchestrator.router.providers["provider_b"]
    provider_b.complete.return_value = mock_llm_response

    response = await orchestrator.generate(mock_llm_request)

    assert response == mock_llm_response
    provider_a.complete.assert_awaited_once()
    provider_b.complete.assert_awaited_once()

    # Verify fallback called with correct model
    call_args = provider_b.complete.call_args
    called_req = call_args[0][0]
    assert called_req.model == "real_model_b"


@pytest.mark.asyncio
async def test_generate_unknown_strategy_uses_default(
    orchestrator, mock_llm_request, mock_llm_response
):
    mock_llm_request.strategy = "non_existent"
    # Default is test_single -> model_a

    provider_a = orchestrator.router.providers["provider_a"]
    provider_a.complete.return_value = mock_llm_response

    await orchestrator.generate(mock_llm_request)

    provider_a.complete.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_direct_model_bypass(orchestrator, mock_llm_request):
    # If we request a model ID that isn't in config, it should go to router directly
    mock_llm_request.strategy = "test_single"

    # Hack: Modify config to point to unknown model
    orchestrator.strategies_config["test_single"]["primary"] = "unknown_model_id"

    orchestrator.router.complete.return_value = "Direct Response"

    await orchestrator.generate(mock_llm_request)

    # Router.complete should be called with "unknown_model_id"
    call_args = orchestrator.router.complete.call_args
    called_req = call_args[0][0]
    assert called_req.model == "unknown_model_id"
