import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_ml_dependencies(monkeypatch):
    """
    Mock heavy ML dependencies to avoid installing them in the test environment.
    This runs automatically for all tests in this directory.
    """
    # Create mocks
    mock_sentence_transformers = MagicMock()
    mock_sentence_transformer_cls = MagicMock()
    mock_sentence_transformer_cls.return_value.encode.return_value = [[0.1, 0.2, 0.3]]
    mock_sentence_transformer_cls.return_value.get_sentence_embedding_dimension.return_value = (
        384
    )
    mock_sentence_transformers.SentenceTransformer = mock_sentence_transformer_cls

    mock_spacy = MagicMock()
    mock_nlp = MagicMock()
    mock_doc = MagicMock()
    mock_nlp.return_value = mock_doc
    mock_spacy.load.return_value = mock_nlp
    mock_spacy.blank.return_value = mock_nlp

    mock_sklearn = MagicMock()
    mock_cluster = MagicMock()
    mock_pairwise = MagicMock()

    # Mock numpy if not present (it might be present)
    try:
        import numpy  # noqa: F401
    except ImportError:
        mock_numpy = MagicMock()
        mock_numpy.mean.return_value = 0.8
        sys.modules["numpy"] = mock_numpy

    # Patch sys.modules
    monkeypatch.setitem(
        sys.modules, "sentence_transformers", mock_sentence_transformers
    )
    monkeypatch.setitem(sys.modules, "spacy", mock_spacy)
    monkeypatch.setitem(sys.modules, "sklearn", mock_sklearn)
    monkeypatch.setitem(sys.modules, "sklearn.cluster", mock_cluster)
    monkeypatch.setitem(sys.modules, "sklearn.metrics.pairwise", mock_pairwise)

    # Ensure submodules are also mocked
    sys.modules["sklearn.cluster"] = mock_cluster
    sys.modules["sklearn.metrics.pairwise"] = mock_pairwise
