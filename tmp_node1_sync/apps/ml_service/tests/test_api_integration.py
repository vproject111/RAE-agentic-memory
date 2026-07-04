from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.ml_service.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_embedding_service():
    with patch(
        "apps.ml_service.services.embedding_service.EmbeddingMLService"
    ) as MockService:
        mock_instance = MagicMock()
        MockService.return_value = mock_instance
        mock_instance.generate_embeddings.return_value = [[0.1, 0.2], [0.3, 0.4]]
        mock_instance.get_embedding_dimension.return_value = 2
        yield mock_instance


@pytest.fixture
def mock_entity_resolution_service():
    with patch(
        "apps.ml_service.services.entity_resolution.EntityResolutionMLService"
    ) as MockService:
        mock_instance = MagicMock()
        MockService.return_value = mock_instance
        mock_instance.resolve_entities.return_value = (
            [["node1", "node2"]],
            {"groups_found": 1},
        )
        yield mock_instance


@pytest.fixture
def mock_nlp_service():
    with patch("apps.ml_service.services.nlp_service.NLPService") as MockService:
        mock_instance = MagicMock()
        MockService.return_value = mock_instance
        mock_instance.extract_keywords.return_value = [
            {"text": "keyword1", "score": 0.9},
            {"text": "keyword2", "score": 0.8},
        ]
        yield mock_instance


@pytest.fixture
def mock_triple_extraction_service():
    with patch(
        "apps.ml_service.services.triple_extraction.TripleExtractionService"
    ) as MockService:
        mock_instance = MagicMock()
        MockService.return_value = mock_instance
        mock_instance.extract_triples.return_value = [
            {"subject": "S", "predicate": "P", "object": "O", "confidence": 0.9}
        ]
        mock_instance.extract_simple_triples.return_value = [
            {
                "subject": "S_simple",
                "predicate": "P_simple",
                "object": "O_simple",
                "confidence": 0.6,
            }
        ]
        yield mock_instance


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_generate_embeddings_endpoint(client, mock_embedding_service):
    payload = {"texts": ["text1", "text2"], "model": "test-model"}
    response = client.post("/embeddings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["embeddings"] == [[0.1, 0.2], [0.3, 0.4]]
    assert data["dimension"] == 2
    assert data["model"] == "test-model"
    mock_embedding_service.generate_embeddings.assert_called_once_with(
        ["text1", "text2"]
    )


def test_resolve_entities_endpoint(client, mock_entity_resolution_service):
    payload = {
        "nodes": [
            {"id": "node1", "label": "Label 1"},
            {"id": "node2", "label": "Label 2"},
        ],
        "similarity_threshold": 0.9,
    }
    response = client.post("/resolve-entities", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["merge_groups"] == [["node1", "node2"]]
    assert data["statistics"]["groups_found"] == 1
    mock_entity_resolution_service.resolve_entities.assert_called_once()


def test_extract_keywords_endpoint(client, mock_nlp_service):
    payload = {"text": "This is a test text", "max_keywords": 5, "language": "en"}
    response = client.post("/extract-keywords", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["keywords"]) == 2
    assert data["keywords"][0]["text"] == "keyword1"
    mock_nlp_service.extract_keywords.assert_called_once_with(
        text="This is a test text", max_keywords=5, language="en"
    )


def test_extract_triples_endpoint_dependency(client, mock_triple_extraction_service):
    payload = {"text": "Subject predicate object.", "method": "dependency"}
    response = client.post("/extract-triples", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["triples"]) == 1
    assert data["triples"][0]["subject"] == "S"
    mock_triple_extraction_service.extract_triples.assert_called_once()


def test_extract_triples_endpoint_simple(client, mock_triple_extraction_service):
    payload = {"text": "Subject predicate object.", "method": "simple"}
    response = client.post("/extract-triples", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["triples"]) == 1
    assert data["triples"][0]["subject"] == "S_simple"
    mock_triple_extraction_service.extract_simple_triples.assert_called_once()
