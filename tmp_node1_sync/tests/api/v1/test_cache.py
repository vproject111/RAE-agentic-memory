from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.memory_api.main import app

client = TestClient(app)


@patch("apps.memory_api.api.v1.cache.rebuild_cache.delay")
def test_rebuild_cache(mock_task):
    response = client.post("/v1/cache/rebuild", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 202
    mock_task.assert_called_once()
