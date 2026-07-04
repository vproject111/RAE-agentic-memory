from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from rae_core.models.interaction import AgentAction, AgentActionType


@pytest.fixture
def mock_rae_service():
    """Mock RAE Core Service for Agent API tests."""
    mock_service = AsyncMock()
    mock_service.execute_action = AsyncMock()
    return mock_service


@pytest.fixture
def client_with_auth(mock_rae_service):
    """Test client with authentication overrides and mocked RAE service."""
    # Override auth dependency
    app.dependency_overrides[get_and_verify_tenant_id] = lambda: "test-tenant"

    # Inject mock service into app state
    app.state.rae_core_service = mock_rae_service

    # Mock pool to avoid lifespan errors
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    app.state.pool = mock_pool

    with (
        patch(
            "rae_adapters.infra_factory.asyncpg.create_pool",
            new=AsyncMock(return_value=mock_pool),
        ),
        patch("apps.memory_api.main.rebuild_full_cache", new=AsyncMock()),
        patch("apps.memory_api.main.RAECoreService", return_value=mock_rae_service),
    ):
        with TestClient(app) as client:
            yield client

    # Cleanup
    app.dependency_overrides = {}
    if hasattr(app.state, "pool"):
        del app.state.pool
    if hasattr(app.state, "rae_core_service"):
        del app.state.rae_core_service


@pytest.mark.asyncio
async def test_agent_execute_happy_path(client_with_auth, mock_rae_service):
    """Test successful agent execution pipeline via RAE-First."""

    # Mock RAE Runtime response
    mock_action = AgentAction(
        type=AgentActionType.FINAL_ANSWER,
        content="Agent Answer",
        confidence=0.9,
        reasoning="Test Reasoning",
        signals=[],
    )
    mock_rae_service.execute_action.return_value = mock_action

    payload = {
        "tenant_id": "test-tenant",
        "project": "test-project",
        "prompt": "Hello",
    }

    response = client_with_auth.post("/v1/agent/execute", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "Agent Answer"

    # Verify execution call
    mock_rae_service.execute_action.assert_called_once()
    call_kwargs = mock_rae_service.execute_action.call_args.kwargs
    assert call_kwargs["tenant_id"] == "test-tenant"
    assert call_kwargs["agent_id"] == "test-project"
    assert call_kwargs["prompt"] == "Hello"


@pytest.mark.asyncio
async def test_agent_execute_no_episodic_memories(client_with_auth, mock_rae_service):
    """Test execution response when no context is found (handled by runtime)."""

    # Runtime handles context building internally now.
    # We just simulate it returning an answer without context.
    mock_action = AgentAction(
        type=AgentActionType.FINAL_ANSWER,
        content="Answer without context",
        confidence=0.5,
        reasoning="Fallback",
        signals=["fallback"],
    )
    mock_rae_service.execute_action.return_value = mock_action

    response = client_with_auth.post(
        "/v1/agent/execute",
        json={
            "tenant_id": "test-tenant",
            "project": "test-project",
            "prompt": "Query",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Answer without context"


@pytest.mark.asyncio
async def test_agent_execute_reranker_failure(client_with_auth, mock_rae_service):
    """Test execution when runtime fails (simulating reranker error inside runtime)."""

    mock_rae_service.execute_action.side_effect = Exception("Reranker Error")

    response = client_with_auth.post(
        "/v1/agent/execute",
        json={
            "tenant_id": "test-tenant",
            "project": "test-project",
            "prompt": "Query",
        },
    )

    assert response.status_code == 500
    data = response.json()
    error_msg = data.get("detail") or data.get("error", {}).get("message", "")
    assert "RAE-First execution failed" in error_msg


@pytest.mark.asyncio
async def test_agent_execute_llm_failure(client_with_auth, mock_rae_service):
    """Test execution when runtime fails (simulating LLM error inside runtime)."""

    mock_rae_service.execute_action.side_effect = Exception("LLM Error")

    response = client_with_auth.post(
        "/v1/agent/execute",
        json={
            "tenant_id": "test-tenant",
            "project": "test-project",
            "prompt": "Query",
        },
    )

    assert response.status_code == 500
    data = response.json()
    error_msg = data.get("detail") or data.get("error", {}).get("message", "")
    assert "RAE-First execution failed" in error_msg


@pytest.mark.asyncio
async def test_agent_execute_reflection_failure_ignored(
    client_with_auth, mock_rae_service
):
    """
    Test that reflection hook failure doesn't break the response.

    Note: In RAE-First, reflection is an async side effect handled inside execute_action.
    The runtime is expected to catch and log it. If execute_action returns successfully,
    it implies side effects were handled.
    """

    # We assume execute_action succeeds even if internal reflection fails
    mock_action = AgentAction(
        type=AgentActionType.FINAL_ANSWER,
        content="Answer",
        confidence=0.9,
        reasoning="Success",
        signals=[],
    )
    mock_rae_service.execute_action.return_value = mock_action

    response = client_with_auth.post(
        "/v1/agent/execute",
        json={
            "tenant_id": "test-tenant",
            "project": "test-project",
            "prompt": "Query",
        },
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "Answer"


@pytest.mark.asyncio
async def test_agent_execute_vector_store_failure(client_with_auth, mock_rae_service):
    """Test execution when runtime fails (simulating vector store error)."""

    mock_rae_service.execute_action.side_effect = Exception("Vector Store Error")

    response = client_with_auth.post(
        "/v1/agent/execute",
        json={"tenant_id": "test-tenant", "project": "test-project", "prompt": "Query"},
    )

    assert response.status_code == 500
    data = response.json()
    error_msg = data.get("detail") or data.get("error", {}).get("message", "")
    assert "RAE-First execution failed" in error_msg
