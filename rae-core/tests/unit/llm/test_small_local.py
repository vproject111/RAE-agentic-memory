from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rae_core.llm.small_local import SmallLocalLLMProvider


@pytest.fixture
def provider():
    return SmallLocalLLMProvider(
        onnx_model_path=None, ollama_url="http://localhost:11434"
    )


@pytest.mark.asyncio
async def test_generate_onnx_success():
    mock_onnx = MagicMock()
    mock_onnx.generate = AsyncMock(return_value="ONNX Response")

    with patch("rae_core.llm.small_local.LocalOnnxLLMProvider", return_value=mock_onnx):
        provider = SmallLocalLLMProvider(onnx_model_path="/path/to/model")
        res = await provider.generate("test prompt")
        assert res == "ONNX Response"
        mock_onnx.generate.assert_called_once()


@pytest.mark.asyncio
async def test_generate_ollama_success(provider):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "Ollama Response"}

    with patch.object(provider.client, "post", AsyncMock(return_value=mock_response)):
        res = await provider.generate("test prompt", system_prompt="sys prompt")
        assert res == "Ollama Response"


@pytest.mark.asyncio
async def test_generate_ollama_failure_fallback(provider):
    with patch.object(
        provider.client, "post", AsyncMock(side_effect=Exception("Connection Error"))
    ):
        res = await provider.generate("Krok 1: Test step", system_prompt="sys prompt")
        assert "ORDER ENTRY ASSISTANT" in res
        assert "Krok 1: Test step" in res


@pytest.mark.asyncio
async def test_generate_with_context(provider):
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hello"},
    ]
    with patch.object(
        provider, "generate", AsyncMock(return_value="Response")
    ) as mock_gen:
        res = await provider.generate_with_context(messages)
        assert res == "Response"
        mock_gen.assert_called_once()


@pytest.mark.asyncio
async def test_sync_methods(provider):
    assert await provider.count_tokens("hello world") == 2
    assert provider.supports_function_calling() is False


@pytest.mark.asyncio
async def test_async_stubs(provider):
    assert await provider.extract_entities("text") == []
    res = await provider.summarize(
        "This is a long text that needs summarization", max_length=10
    )
    assert res == "This is a ..."


def test_procedural_fallback_logic(provider):
    # Test regex matches
    prompt = "Step 1: Do this\n1. Do that\nKolejno: Third\nKrok 4: Fourth"
    context = "Some context"
    res = provider._generate_procedural_fallback(prompt, context)
    assert "Step 1: Do this" in res
    assert "1. Do that" in res
    assert "Kolejno: Third" in res
    assert "Krok 4: Fourth" in res

    # Test keywords
    prompt = "Należy kliknąć przycisk\nMusisz zapisać\nPowinieneś sprawdzić\nWymagane jest hasło\nInstrukcja obsługi"
    res = provider._generate_procedural_fallback(prompt, "")
    assert "- Należy kliknąć przycisk" in res
    assert "- Musisz zapisać" in res
    assert "- Powinieneś sprawdzić" in res
    assert "- Wymagane jest hasło" in res
    assert "- Instrukcja obsługi" in res

    # Test skip headers
    prompt = "# This is a header with należy"
    res = provider._generate_procedural_fallback(prompt, "")
    assert "# This is a header" not in res

    # Test duplicate and short lines
    prompt = "Step 1: Long enough line\nStep 1: Long enough line\nShort"
    res = provider._generate_procedural_fallback(prompt, "")
    assert res.count("Step 1: Long enough line") == 1
    assert "Short" not in res

    # Test no steps
    res = provider._generate_procedural_fallback("Nothing here", "")
    assert "STABILITY MODE" in res
