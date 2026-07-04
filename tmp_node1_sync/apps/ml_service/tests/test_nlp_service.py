import sys
from unittest.mock import MagicMock, patch

import pytest

from apps.ml_service.services.nlp_service import NLPService


# Fixture to mock spacy.load and spacy.blank by patching sys.modules
@pytest.fixture
def mock_spacy_module():
    # Create a mock for the spacy module itself
    mock_spacy = MagicMock()

    # Create a mock for the loaded NLP model instance that spacy.load() returns
    mock_nlp_model = MagicMock()
    mock_spacy.load.return_value = mock_nlp_model
    mock_spacy.blank.return_value = (
        mock_nlp_model  # Also mock blank to return same model
    )

    # Configure mock_nlp_model for doc processing
    mock_doc = MagicMock()
    mock_nlp_model.return_value = (
        mock_doc  # When mock_nlp_model is called with text (e.g., nlp(text))
    )

    # Configure doc.ents for extract_entities and extract_keywords
    mock_ent1 = MagicMock(text="Apple Inc.", label_="ORG", start_char=0, end_char=10)
    mock_ent2 = MagicMock(text="California", label_="GPE", start_char=28, end_char=38)
    mock_doc.ents = [mock_ent1, mock_ent2]

    # Configure doc.noun_chunks for extract_keywords
    mock_noun_chunk1 = MagicMock(
        text="new AI features", root=MagicMock(text="features", pos_="NOUN")
    )
    mock_noun_chunk2 = MagicMock(
        text="Apple Inc.", root=MagicMock(text="Inc.", pos_="PROPN")
    )
    mock_doc.noun_chunks = [mock_noun_chunk1, mock_noun_chunk2]

    # Configure doc tokens for extract_keywords
    # Need to mock the token objects and their attributes used in nlp_service.py
    # and ensure __iter__ works on the doc object
    mock_token_announced = MagicMock(
        text="announced", pos_="VERB", is_stop=False, is_punct=False, is_space=False
    )
    mock_token_the = MagicMock(
        text="the", pos_="DET", is_stop=True, is_punct=False, is_space=False
    )
    mock_token_ai = MagicMock(
        text="AI", pos_="PROPN", is_stop=False, is_punct=False, is_space=False
    )
    mock_token_features = MagicMock(
        text="features", pos_="NOUN", is_stop=False, is_punct=False, is_space=False
    )  # for noun chunk root
    mock_token_great = MagicMock(
        text="great", pos_="ADJ", is_stop=False, is_punct=False, is_space=False
    )
    mock_doc.__iter__.return_value = iter(
        [
            mock_token_announced,
            mock_token_the,
            mock_token_ai,
            mock_token_features,
            mock_token_great,
        ]
    )

    # Patch sys.modules to inject our mock spacy module
    with patch.dict(sys.modules, {"spacy": mock_spacy}):
        yield mock_spacy, mock_nlp_model


@pytest.fixture
def nlp_service_instance(mock_spacy_module):
    # Reset singleton for NLPService to ensure fresh instance per test
    NLPService._instance = None
    NLPService._nlp = None
    service = NLPService(language="en")
    yield service
    NLPService._instance = None
    NLPService._nlp = None


def test_nlp_service_init_loads_model(nlp_service_instance, mock_spacy_module):
    """Test that spaCy model is loaded on initialization, trying preferred models."""
    mock_spacy, mock_nlp_model = mock_spacy_module

    # Check if spacy.load was called with 'en_core_web_lg' or one of its fallbacks
    # Since mock.load is configured, it means a call happened
    assert mock_spacy.load.called
    assert nlp_service_instance._nlp is mock_nlp_model


def test_nlp_service_init_falls_back_to_blank(mock_spacy_module):
    """Test that if no specific model is found, it falls back to spacy.blank."""
    mock_spacy, mock_nlp_model = mock_spacy_module
    # Simulate OSError for all load attempts
    mock_spacy.load.side_effect = OSError("Model not found")

    # Reset the singleton to force re-initialization
    NLPService._instance = None
    NLPService._nlp = None

    service = NLPService(language="fr")
    mock_spacy.load.assert_called_with("fr_core_news_sm")  # The last attempted model
    mock_spacy.blank.assert_called_once_with("fr")
    assert service._nlp is mock_nlp_model


def test_nlp_service_init_import_error(mock_spacy_module):
    """Test that ImportError for spacy raises RuntimeError."""
    mock_spacy, _ = mock_spacy_module  # Get the mock spacy module from the fixture

    # Configure mock_spacy.load to raise ImportError when called
    mock_spacy.load.side_effect = ImportError("Mocked spacy import error (from load)")

    # Reset the singleton to force re-initialization
    NLPService._instance = None
    NLPService._nlp = None

    with pytest.raises(RuntimeError, match="spaCy is not installed"):
        NLPService(language="en")

    # Ensure spacy.load was called during the attempt
    mock_spacy.load.assert_called()


def test_nlp_service_singleton_behavior(mock_spacy_module):
    """Test that only one instance of NLPService is created (singleton)."""
    mock_spacy, mock_nlp_model = mock_spacy_module

    # Clear any previous call records on mocks for this specific test
    mock_spacy.load.reset_mock()
    mock_spacy.blank.reset_mock()

    NLPService._instance = None
    NLPService._nlp = None
    service1 = NLPService(language="en")

    # Do NOT reset NLPService._instance = None here, as it breaks singleton

    service2 = NLPService(language="fr")  # Should reuse the first instance

    assert service1 is service2
    # The SentenceTransformer should only be initialized once during the first service creation.
    # The exact call count on mock_spacy.load might depend on internal details of the mock setup and spaCy's
    # loading mechanism, but the key is that service1 and service2 should be the same object due to the singleton.


def test_extract_keywords_empty_text(nlp_service_instance, mock_spacy_module):
    """Test keyword extraction with empty text."""
    mock_spacy, mock_nlp_model = mock_spacy_module
    mock_nlp_model.return_value = MagicMock(
        ents=[], noun_chunks=[], __iter__=lambda: iter([])
    )  # Empty doc
    keywords = nlp_service_instance.extract_keywords("")
    assert keywords == []
    # The internal nlp model should not be called with empty text
    mock_nlp_model.assert_not_called()


def test_extract_keywords_basic_text(nlp_service_instance, mock_spacy_module):
    """Test keyword extraction with basic text containing entities, noun chunks, and tokens."""
    mock_spacy, mock_nlp_model = mock_spacy_module
    text = "Apple Inc. announced new AI features in California."

    keywords = nlp_service_instance.extract_keywords(text)

    mock_nlp_model.assert_called_once_with(text)

    extracted_texts = [kw["text"] for kw in keywords]
    assert "Apple Inc." in extracted_texts
    assert "California" in extracted_texts
    assert "new AI features" in extracted_texts
    assert "AI" in extracted_texts  # It should be picked up as a PROPN
    assert "great" in extracted_texts

    # Check that scores are roughly as expected
    for kw in keywords:
        if kw["text"] in ["Apple Inc.", "California"]:
            assert kw["type"] == "entity"
            assert kw["score"] == 1.0
        elif kw["text"] == "new AI features":
            assert kw["type"] == "noun_phrase"
            assert kw["score"] == 0.7
        elif kw["text"] in ["AI", "great"]:
            assert kw["type"] == "token"
            assert kw["score"] == 0.5


def test_extract_keywords_max_keywords_limit(nlp_service_instance, mock_spacy_module):
    """Test that max_keywords limits the number of returned keywords."""
    mock_spacy, mock_nlp_model = mock_spacy_module
    text = "This is a very long text with many potential keywords, entities, and noun phrases."

    # Populate mock_doc with more keywords than max_keywords (using individual mocks to control order/score)
    mock_ent1 = MagicMock(text="Entity 1", label_="ENT", score=1.0)
    mock_ent2 = MagicMock(text="Entity 2", label_="ENT", score=1.0)
    mock_noun_chunk1 = MagicMock(
        text="Noun Chunk 1", root=MagicMock(text="Chunk", pos_="NOUN"), score=0.7
    )
    mock_noun_chunk2 = MagicMock(
        text="Noun Chunk 2", root=MagicMock(text="Chunk", pos_="NOUN"), score=0.7
    )
    mock_token1 = MagicMock(
        text="Word 1",
        pos_="NOUN",
        is_stop=False,
        is_punct=False,
        is_space=False,
        score=0.5,
    )
    mock_token2 = MagicMock(
        text="Word 2",
        pos_="NOUN",
        is_stop=False,
        is_punct=False,
        is_space=False,
        score=0.5,
    )

    mock_doc_for_limit = MagicMock()
    mock_doc_for_limit.ents = [mock_ent1, mock_ent2]
    mock_doc_for_limit.noun_chunks = [mock_noun_chunk1, mock_noun_chunk2]
    mock_doc_for_limit.__iter__.return_value = iter([mock_token1, mock_token2])
    mock_nlp_model.return_value = mock_doc_for_limit  # Configure for this specific call

    keywords = nlp_service_instance.extract_keywords(text, max_keywords=3)
    assert len(keywords) == 3
    # Check that the top 3 (by score) are returned
    assert [kw["text"] for kw in keywords] == ["Entity 1", "Entity 2", "Noun Chunk 1"]


def test_extract_entities_empty_text(nlp_service_instance, mock_spacy_module):
    """Test entity extraction with empty text."""
    mock_spacy, mock_nlp_model = mock_spacy_module
    mock_nlp_model.return_value = MagicMock(ents=[])
    entities = nlp_service_instance.extract_entities("")
    assert entities == []
    mock_nlp_model.assert_not_called()


def test_extract_entities_basic_text(nlp_service_instance, mock_spacy_module):
    """Test entity extraction with text containing named entities."""
    mock_spacy, mock_nlp_model = mock_spacy_module
    text = "Apple Inc. announced new AI features in California."

    entities = nlp_service_instance.extract_entities(text)

    mock_nlp_model.assert_called_once_with(text)
    assert len(entities) == 2
    assert entities[0]["text"] == "Apple Inc."
    assert entities[0]["label"] == "ORG"
    assert entities[1]["text"] == "California"
    assert entities[1]["label"] == "GPE"
