import os
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from rae_core.llm import CapabilityMatrix, ModelDescriptor, resolve_llm_runtime
from rae_core.llm.providers import (
    BridgeLLMProvider,
    LightweightOpenAIProvider,
    LightweightAnthropicProvider,
    LightweightGoogleProvider
)
from rae_core.llm.small_local import SmallLocalLLMProvider

def test_model_descriptor_and_capabilities():
    matrix = CapabilityMatrix(
        chat=True,
        json_schema=True,
        tools=True,
        vision=False,
        embeddings=False,
        streaming=True,
        reasoning=True
    )
    descriptor = ModelDescriptor(
        id="gpt-5.5",
        name="GPT-5.5",
        provider="openai",
        context_window=1000000,
        max_tokens=16384,
        capabilities=matrix,
        cost={"input": 2.0, "output": 10.0, "cacheRead": 0.2, "cacheWrite": 0.0}
    )
    assert descriptor.id == "gpt-5.5"
    assert descriptor.capabilities.json_schema is True
    assert descriptor.capabilities.vision is False
    assert descriptor.cost["input"] == 2.0

@pytest.mark.asyncio
async def test_resolve_llm_runtime_local_openai(monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    
    runtime = await resolve_llm_runtime()
    assert isinstance(runtime, LightweightOpenAIProvider)
    assert runtime.api_key == "test-openai-key"

@pytest.mark.asyncio
async def test_resolve_llm_runtime_local_anthropic(monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    
    runtime = await resolve_llm_runtime()
    assert isinstance(runtime, LightweightAnthropicProvider)
    assert runtime.api_key == "test-anthropic-key"

@pytest.mark.asyncio
async def test_resolve_llm_runtime_local_google(monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    
    runtime = await resolve_llm_runtime()
    assert isinstance(runtime, LightweightGoogleProvider)
    assert runtime.api_key == "test-gemini-key"

@pytest.mark.asyncio
async def test_resolve_llm_runtime_local_fallback(monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "local")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    
    runtime = await resolve_llm_runtime()
    assert isinstance(runtime, SmallLocalLLMProvider)

@pytest.mark.asyncio
async def test_resolve_llm_runtime_with_requirements(monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "local")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-deepseek-key")
    
    runtime = await resolve_llm_runtime(requirements={"requires_reasoning": True})
    assert isinstance(runtime, LightweightOpenAIProvider)
    assert runtime.model == "deepseek-reasoner"
    assert runtime.api_key == "test-deepseek-key"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_resolve_llm_runtime_remote_success(mock_get, monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "remote")
    monkeypatch.setenv("RAE_API_URL", "http://test-bridge:8000")
    
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = lambda: None
    mock_get.return_value = mock_resp
    
    runtime = await resolve_llm_runtime()
    assert isinstance(runtime, BridgeLLMProvider)
    assert runtime.api_url == "http://test-bridge:8000"

@pytest.mark.asyncio
@patch("httpx.AsyncClient.get")
async def test_resolve_llm_runtime_remote_failure(mock_get, monkeypatch):
    monkeypatch.setenv("RAE_LLM_MODE", "remote")
    monkeypatch.setenv("RAE_API_URL", "http://test-bridge:8000")
    
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    
    with pytest.raises(RuntimeError) as exc_info:
        await resolve_llm_runtime()
    assert "RAE Bridge is unavailable" in str(exc_info.value)
