import pytest

from rae_core.llm.fallback import NoLLMFallback


@pytest.fixture
def fallback():
    return NoLLMFallback()


@pytest.mark.asyncio
async def test_summarize(fallback):
    long_text = "Sentence one. Sentence two. Sentence three."
    summary = await fallback.summarize(long_text, max_length=20)

    # Simple extractive summary should truncate or take first sentence
    assert len(summary) <= 25  # Allow small margin
    assert "Sentence one" in summary


@pytest.mark.asyncio
async def test_extract_entities(fallback):
    text = "John Doe went to Paris."
    entities = await fallback.extract_entities(text)

    # Rule based should find capitalized words
    entity_texts = [e["text"] for e in entities]
    assert "John" in entity_texts
    assert "Doe" in entity_texts
    assert "Paris" in entity_texts


@pytest.mark.asyncio
async def test_generate_simple_qa(fallback):
    response = await fallback.generate("What is the capital?")
    assert "Based on the question about" in response or "I cannot provide" in response


@pytest.mark.asyncio
async def test_count_tokens(fallback):
    text = "12345678"  # 8 chars -> 2 tokens
    count = await fallback.count_tokens(text)
    assert count == 2
