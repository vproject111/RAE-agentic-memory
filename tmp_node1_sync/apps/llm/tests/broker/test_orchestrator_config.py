import os
from unittest.mock import AsyncMock

import pytest

from apps.llm.broker.orchestrator import LLMOrchestrator


@pytest.fixture
def mock_llm_router():
    """Mock LLMRouter for Orchestrator."""
    router = AsyncMock()
    # Mock the providers attribute if it's accessed
    router.providers = {}  # Ensure providers dict exists
    return router


@pytest.fixture(autouse=True)
def cleanup_env_var():
    """Ensure LLM_MODEL_NAME is clean before and after tests."""
    original_value = os.environ.get("LLM_MODEL_NAME")
    if "LLM_MODEL_NAME" in os.environ:
        del os.environ["LLM_MODEL_NAME"]
    yield
    if original_value is not None:
        os.environ["LLM_MODEL_NAME"] = original_value
    elif "LLM_MODEL_NAME" in os.environ:
        del os.environ["LLM_MODEL_NAME"]


@pytest.mark.asyncio
async def test_llm_model_name_from_env_variable(mock_llm_router, monkeypatch):
    """Test that LLM model name is read from environment variable."""
    expected_model_name = "test-model-from-env"
    monkeypatch.setenv("LLM_MODEL_NAME", expected_model_name)

    orchestrator = LLMOrchestrator(router=mock_llm_router)

    # Find the openai_gpt4o model config
    openai_gpt4o_config = orchestrator.models_config.get("openai_gpt4o")
    assert openai_gpt4o_config is not None
    assert openai_gpt4o_config["model_name"] == expected_model_name


@pytest.mark.asyncio
async def test_llm_model_name_default_when_env_not_set(mock_llm_router):
    """Test that LLM model name defaults to gpt-4o when env variable is not set."""
    # Ensure env var is not set (cleanup_env_var fixture handles this)
    assert "LLM_MODEL_NAME" not in os.environ

    orchestrator = LLMOrchestrator(router=mock_llm_router)

    # Find the openai_gpt4o model config
    openai_gpt4o_config = orchestrator.models_config.get("openai_gpt4o")
    assert openai_gpt4o_config is not None
    assert (
        openai_gpt4o_config["model_name"] == "gpt-4o"
    )  # Expected default from llm_config.yaml
