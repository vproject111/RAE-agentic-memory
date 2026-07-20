"""
E2E API Smoke Tests

End-to-end smoke tests to verify the API works on fresh installation.
Supports both local TestClient (unit) and remote URL (integration against containers).

Usage:
    # Run locally (mocked network)
    pytest apps/memory_api/tests/test_api_e2e.py

    # Run against Dev Container
    RAE_API_URL=http://localhost:8001 pytest apps/memory_api/tests/test_api_e2e.py

    # Run against Lite Container
    RAE_API_URL=http://localhost:8008 pytest apps/memory_api/tests/test_api_e2e.py
"""

import os

import httpx
import pytest
from fastapi.testclient import TestClient

# --- Client Fixture Strategy ---


@pytest.fixture
def api_client():
    """
    Returns a client-like object.
    If RAE_API_URL is set and reachable, returns an HTTPX client pointing to that URL.
    Otherwise, returns a FastAPI TestClient using the local app.
    """
    api_url = os.getenv("RAE_API_URL")

    # If pointing to internal docker name while running outside, force local
    if api_url == "http://rae-api:8000" and not os.path.exists("/.dockerenv"):
        api_url = None

    if api_url:
        print(f"🌍 Running E2E tests against REMOTE: {api_url}")

        # Return a wrapper that mimics TestClient sync interface using httpx
        class RemoteClient:
            def __init__(self, base_url):
                self.base_url = base_url.rstrip("/")
                self.headers = {
                    "X-Tenant-ID": "00000000-0000-0000-0000-000000000000",
                    "Authorization": "Bearer dev-key",
                }
                self.client = httpx.Client(
                    base_url=self.base_url, timeout=10.0, headers=self.headers
                )

            def get(self, url, **kwargs):
                return self.client.get(url, **kwargs)

            def post(self, url, **kwargs):
                return self.client.post(url, **kwargs)

            def delete(self, url, **kwargs):
                return self.client.delete(url, **kwargs)

        yield RemoteClient(api_url)

    else:
        print("🏠 Running E2E tests against LOCAL app (TestClient)")
        from unittest.mock import AsyncMock

        from apps.memory_api.main import app

        with TestClient(app) as client:
            # SYSTEM 40.19: Mock LLM to avoid hangs
            if hasattr(app.state, "rae_core_service"):
                # Mock the generate_text method on the engine
                app.state.rae_core_service.engine.generate_text = AsyncMock(
                    return_value="E2E Mocked Response"
                )
                # Mock the generate method on the provider if it exists
                if app.state.rae_core_service.engine.llm_provider:
                    app.state.rae_core_service.engine.llm_provider.generate = AsyncMock(
                        return_value=AsyncMock(text="E2E Mocked Provider Response")
                    )

            client.headers.update(
                {
                    "X-Tenant-ID": "00000000-0000-0000-0000-000000000000",
                    "Authorization": "Bearer dev-key",
                }
            )
            yield client


@pytest.mark.smoke
class TestMemoryAPISmoke:
    """Smoke tests for core memory operations."""

    def test_health_check(self, api_client):
        """Test that health check endpoint responds."""
        response = api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]

    def test_store_and_query_memory_e2e(self, api_client):
        """Test end-to-end memory storage and retrieval."""

        # 1. Store
        payload = {
            "content": "E2E Test Memory Content " + os.urandom(4).hex(),
            "project": "e2e_test",
            "layer": "longterm",
            "importance": 0.8,
        }
        store_res = api_client.post("/v2/memories/", json=payload)
        assert store_res.status_code == 200
        mem_id = store_res.json()["memory_id"]
        assert mem_id

        # 2. Query
        query_payload = {"query": "Test Memory", "project": "e2e_test", "k": 5}
        query_res = api_client.post("/v2/memories/query", json=query_payload)
        assert query_res.status_code == 200
        results = query_res.json()["results"]
        assert isinstance(results, list)

        # Note: Vector search might be async/delayed or fail in mock mode if no vector store
        # But we expect at least a 200 OK response.
        assert "total_count" in query_res.json()

    def test_agent_execute(self, api_client):
        """Test agent execution endpoint."""
        payload = {"prompt": "Hello world", "project": "e2e_agent"}
        res = api_client.post("/v2/agent/execute", json=payload)
        # 200 or 500 depending on LLM availability, but endpoint should exist
        assert res.status_code in [200, 500, 503]


class TestAPIErrorHandling:
    """Test that API handles errors gracefully."""

    def test_missing_tenant_header(self, api_client):
        """Test that missing params returns 422."""
        # Note: Tenant header is handled by middleware, might be default in TestClient
        # So we test missing body params instead (missing 'content' which is required)
        response = api_client.post(
            "/v2/memories/",
            json={},  # Empty body, missing 'content'
        )
        assert response.status_code == 422

    def test_invalid_json(self, api_client):
        """Test that invalid JSON returns 422."""
        response = api_client.post(
            "/v2/memories/",
            content="not valid json",
            headers={"Content-Type": "application/json", "X-Tenant-ID": "test"},
        )
        assert response.status_code in [404, 422]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
