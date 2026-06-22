from fastapi.testclient import TestClient

from apps.memory_api.main import app

client = TestClient(app)


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "RAE: Reflective Agentic Engine"
    # OpenAPI spec doesn't require top-level tags to list all tags used in paths
    # We verify the path exists and has the correct tag in operation
    assert "/v2/memories/" in schema["paths"]
    assert "Memory v2 (RAE-Core)" in schema["paths"]["/v2/memories/"]["post"]["tags"]
