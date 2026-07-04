import sys
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Import app after mocking dependencies (which is done in conftest.py)
from apps.ml_service.main import app

client = TestClient(app)


def setup_function():
    # Reset singletons
    from apps.ml_service.services.embedding_service import EmbeddingMLService
    from apps.ml_service.services.nlp_service import NLPService
    from apps.ml_service.services.triple_extraction import TripleExtractionService

    EmbeddingMLService._instance = None
    NLPService._instance = None
    TripleExtractionService._instance = None

    # Reset mocks
    if "spacy" in sys.modules and isinstance(sys.modules["spacy"], MagicMock):
        sys.modules["spacy"].reset_mock()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "ml-service"}


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "RAE ML Service"


@patch("apps.ml_service.services.embedding_service.SentenceTransformer")
def test_generate_embeddings(mock_st):
    # Setup mock
    mock_model = MagicMock()
    # encode returns a list of numpy arrays (which have tolist method)
    # We mock this by returning objects with tolist method
    mock_array1 = MagicMock()
    mock_array1.tolist.return_value = [0.1, 0.2]
    mock_array2 = MagicMock()
    mock_array2.tolist.return_value = [0.3, 0.4]

    mock_model.encode.return_value = [mock_array1, mock_array2]
    mock_model.get_sentence_embedding_dimension.return_value = 2
    mock_st.return_value = mock_model

    response = client.post(
        "/embeddings", json={"texts": ["hello", "world"], "model": "test-model"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "embeddings" in data
    assert len(data["embeddings"]) == 2
    assert data["embeddings"][0] == [0.1, 0.2]
    assert data["embeddings"][1] == [0.3, 0.4]
    assert data["model"] == "test-model"
    assert data["dimension"] == 2


@patch("apps.ml_service.services.entity_resolution.SentenceTransformer")
@patch("apps.ml_service.services.entity_resolution.AgglomerativeClustering")
def test_resolve_entities(mock_clustering, mock_st):
    # Setup mocks
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1], [0.2], [0.3]]
    mock_st.return_value = mock_model

    mock_cluster_instance = MagicMock()
    mock_cluster_instance.fit_predict.return_value = [0, 0, 1]  # First two in cluster 0
    mock_clustering.return_value = mock_cluster_instance

    # Mock cosine_similarity if needed
    with patch(
        "apps.ml_service.services.entity_resolution.cosine_similarity",
        return_value=[[1.0]],
    ):
        response = client.post(
            "/resolve-entities",
            json={
                "nodes": [
                    {"id": "1", "label": "a"},
                    {"id": "2", "label": "b"},
                    {"id": "3", "label": "c"},
                ],
                "similarity_threshold": 0.85,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "merge_groups" in data
    # We expect one group with id "1" and "2"
    assert len(data["merge_groups"]) == 1
    assert set(data["merge_groups"][0]) == {"1", "2"}


def test_extract_keywords():
    # Setup mock doc using sys.modules["spacy"]
    mock_spacy = sys.modules["spacy"]
    mock_nlp = MagicMock()
    mock_doc = MagicMock()

    # Mock entities
    ent1 = MagicMock()
    ent1.text = "Apple"
    ent1.label_ = "ORG"
    ent1.start_char = 0
    ent1.end_char = 5

    mock_doc.ents = [ent1]
    mock_doc.noun_chunks = []
    mock_doc.__iter__.return_value = []  # No tokens

    mock_nlp.return_value = mock_doc
    mock_spacy.load.return_value = mock_nlp
    # Also mock blank for fallback
    mock_spacy.blank.return_value = mock_nlp

    response = client.post(
        "/extract-keywords", json={"text": "Apple is great.", "max_keywords": 5}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["keywords"]) > 0
    assert data["keywords"][0]["text"] == "Apple"


def test_extract_triples_simple():
    # For simple extraction, we need entities and verbs
    mock_spacy = sys.modules["spacy"]
    mock_nlp = MagicMock()
    mock_doc = MagicMock()

    # Setup sentence
    mock_sent = MagicMock()

    # Entities
    ent1 = MagicMock()
    ent1.text = "Bob"
    ent1.start = 0
    ent1.end = 1

    ent2 = MagicMock()
    ent2.text = "Alice"
    ent2.start = 2
    ent2.end = 3

    mock_sent.ents = [ent1, ent2]

    # Verb
    verb = MagicMock()
    verb.pos_ = "VERB"
    verb.lemma_ = "love"
    verb.i = 1  # Between 0 and 2

    mock_sent.__iter__.return_value = [verb]

    mock_doc.sents = [mock_sent]
    mock_nlp.return_value = mock_doc
    mock_spacy.load.return_value = mock_nlp
    mock_spacy.blank.return_value = mock_nlp

    response = client.post(
        "/extract-triples", json={"text": "Bob loves Alice", "method": "simple"}
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["triples"]) == 1
    assert data["triples"][0]["subject"] == "Bob"
    assert data["triples"][0]["predicate"] == "love"
    assert data["triples"][0]["object"] == "Alice"
