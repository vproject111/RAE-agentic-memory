import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# We need to ensure main is imported AFTER mocks are set up.
# The mocks are set up in conftest.py (if using fixtures) or we can do it here.
# Since we want to test the main module which runs code at import time,
# we should mock explicitly if conftest fixture hasn't run yet.
# However, fixtures run at test time.


@pytest.fixture
def client(mock_reranker_dependencies):
    # Import app inside fixture to ensure mocks are active
    current_file = Path(__file__).resolve()
    service_dir = current_file.parent.parent
    sys.path.insert(0, str(service_dir))

    # Reset module if it was already imported (e.g. by another test)
    if "main" in sys.modules:
        del sys.modules["main"]
    if "apps.reranker_service.main" in sys.modules:
        del sys.modules["apps.reranker_service.main"]

    # Now import
    try:
        from apps.reranker_service import main as reranker_main
    except ImportError:
        # Try local import if package structure is different
        import main as reranker_main  # type: ignore

    return TestClient(reranker_main.app)


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_rerank(client):
    # Mock the model's predict method
    # We need to get the model instance from the imported main module
    # OR rely on the mock setup in conftest/fixture.

    # The mock_reranker_dependencies fixture in conftest.py sets up sys.modules["sentence_transformers"].
    # So when main imports it, it gets the mock.
    import sys

    mock_st = sys.modules["sentence_transformers"]
    mock_model = mock_st.CrossEncoder.return_value

    # Configure mock to return scores
    mock_model.predict.return_value = [0.9, 0.1]

    response = client.post(
        "/rerank",
        json={
            "query": "test query",
            "items": [
                {"id": "1", "text": "relevant text"},
                {"id": "2", "text": "irrelevant text"},
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["items"][0]["id"] == "1"
    assert data["items"][0]["score"] == 0.9
    assert data["items"][1]["id"] == "2"
    assert data["items"][1]["score"] == 0.1


def test_rerank_empty(client):
    response = client.post("/rerank", json={"query": "test", "items": []})
    assert response.status_code == 200
    assert response.json()["items"] == []
