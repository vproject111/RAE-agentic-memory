from unittest.mock import AsyncMock

import pytest

from rae_core.reflection.layers.l4_cognitive import L4CognitiveReflection


@pytest.mark.asyncio
async def test_l4_cognitive_no_llm():
    l4 = L4CognitiveReflection(llm_provider=None)
    res = await l4.reflect({"analysis": "test"})
    assert res["status"] == "skipped"
    assert "No LLM provider" in res["reason"]


@pytest.mark.asyncio
async def test_l4_cognitive_success():
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = '{"lesson": "Trust but verify", "confidence": 0.95, "tags": ["trust", "verification"]}'

    l4 = L4CognitiveReflection(llm_provider=mock_llm)
    payload = {
        "analysis": "Agent trusted the user input without checking sources.",
        "retrieved_sources_content": ["Source 1: Always check inputs."],
    }
    res = await l4.reflect(payload)

    assert res["status"] == "success"
    assert res["insight"]["lesson"] == "Trust but verify"
    assert res["model"] == "ollama/qwen3.5:9b"

    mock_llm.generate_text.assert_called_once()
    prompt = mock_llm.generate_text.call_args.kwargs["prompt"]
    assert "AGENT ACTION/ANALYSIS" in prompt
    assert "Source 1: Always check inputs." in prompt


@pytest.mark.asyncio
async def test_l4_cognitive_empty_response():
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = ""

    l4 = L4CognitiveReflection(llm_provider=mock_llm)
    res = await l4.reflect({"analysis": "test"})
    assert res["status"] == "error"
    assert "Empty response" in res["reason"]


@pytest.mark.asyncio
async def test_l4_cognitive_partial_json():
    mock_llm = AsyncMock()
    # LLM might return some text before/after JSON
    mock_llm.generate_text.return_value = 'Here is the insight: {"lesson": "Be careful", "confidence": 0.5, "tags": ["caution"]} Hope this helps.'

    l4 = L4CognitiveReflection(llm_provider=mock_llm)
    res = await l4.reflect({"analysis": "test"})
    assert res["status"] == "success"
    assert res["insight"]["lesson"] == "Be careful"


@pytest.mark.asyncio
async def test_l4_cognitive_invalid_json_fallback():
    mock_llm = AsyncMock()
    mock_llm.generate_text.return_value = "Just some text, no JSON here."

    l4 = L4CognitiveReflection(llm_provider=mock_llm)
    res = await l4.reflect({"analysis": "test"})
    assert res["status"] == "partial"
    assert res["insight"]["lesson"] == "Just some text, no JSON here."


@pytest.mark.asyncio
async def test_l4_cognitive_exception():
    mock_llm = AsyncMock()
    mock_llm.generate_text.side_effect = Exception("Ollama is down")

    l4 = L4CognitiveReflection(llm_provider=mock_llm)
    res = await l4.reflect({"analysis": "test"})
    assert res["status"] == "error"
    assert "Ollama is down" in res["reason"]


@pytest.mark.asyncio
async def test_l4_cognitive_json_parse_error_inside_match():
    mock_llm = AsyncMock()
    # Matches {.*} but invalid JSON
    mock_llm.generate_text.return_value = '{"lesson": "broken", "confidence": }'

    l4 = L4CognitiveReflection(llm_provider=mock_llm)
    res = await l4.reflect({"analysis": "test"})
    # Should fall back to "partial"
    assert res["status"] == "partial"
    assert "Failed to parse JSON" in res["reason"]
