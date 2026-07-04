from fastapi.testclient import TestClient

from apps.memory_api.main import app

client = TestClient(app)


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "RAE Memory API"
    # OpenAPI spec doesn't require top-level tags to list all tags used in paths
    # We verify the path exists and has the correct tag in operation
    assert "/v1/memory/store" in schema["paths"]
    assert "Memory Operations" in schema["paths"]["/v1/memory/store"]["post"]["tags"]
