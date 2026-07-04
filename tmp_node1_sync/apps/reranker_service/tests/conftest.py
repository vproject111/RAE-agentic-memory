import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_reranker_dependencies(monkeypatch):
    """
    Mock heavy dependencies for reranker service.
    """
    mock_st = MagicMock()
    mock_cross_encoder = MagicMock()
    mock_st.CrossEncoder = mock_cross_encoder

    # Patch sys.modules
    monkeypatch.setitem(sys.modules, "sentence_transformers", mock_st)
