import pytest

from rae_core.llm.fallback import NoLLMFallback


@pytest.fixture
def fallback():
    return NoLLMFallback()


@pytest.mark.asyncio
async def test_generate_intent_detection(fallback):
    # Test summarization intent in generate
    response = await fallback.generate("Summarize this: Sentence one. Sentence two.")
    assert "Sentence one" in response

    # Test entity extraction intent in generate
    response = await fallback.generate("Extract entities from: John Doe is in London.")
    assert "Entities found" in response
    assert "John" in response

    # Test QA intent
    response = await fallback.generate("What is your name?")
    assert "Based on the question about" in response

    # Test default intent (sentences)
    response = await fallback.generate("Just a normal sentence. Another one.")
    assert "Just a normal sentence" in response
    assert response.endswith("...")


@pytest.mark.asyncio
async def test_generate_with_context(fallback):
    # Test empty messages
    response = await fallback.generate_with_context([])
    assert response == "No input provided."

    # Test messages without user role
    response = await fallback.generate_with_context(
        [{"role": "system", "content": "Hi"}]
    )
    assert response == "No input provided."

    # Test valid user message
    response = await fallback.generate_with_context(
        [{"role": "user", "content": "Summarize this."}]
    )
    assert "Summarize" in response


def test_supports_function_calling(fallback):
    assert fallback.supports_function_calling() is False


@pytest.mark.asyncio
async def test_extract_entities_limits_and_types(fallback):
    # Test many entities
    text = "One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve"
    entities = await fallback.extract_entities(text)
    assert len(entities) <= 10

    # Test numbers
    text = "The year is 2025."
    entities = await fallback.extract_entities(text)
    types = [e["type"] for e in entities]
    assert "NUMBER" in types
    assert "2025" in [e["text"] for e in entities]


@pytest.mark.asyncio
async def test_extractive_summary_edge_cases(fallback):
    # Test very short max_length
    text = "Very long sentence that should be truncated."
    summary = await fallback.summarize(text, max_length=5)
    assert summary.endswith("...")

    # Test empty sentences
    text = "... !!! ???"
    summary = await fallback.summarize(text, max_length=100)
    assert summary.startswith("... !!! ???")
    assert summary.endswith("...")


def test_simple_qa_no_context(fallback):
    # Test question without keyword
    response = fallback._simple_qa("?")
    assert response == "I cannot provide a specific answer with the available context."


def test_extract_entities_rule_based_no_entities(fallback):
    # Test rule based extraction with no capitalized words
    response = fallback._extract_entities_rule_based("no entities here")
    assert response == "No entities found."
