import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from apps.memory_api.main import app

client = TestClient(app)


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_a2a_bridge_active_routing(mock_post):
    # Mock successful routing response using MagicMock since Response methods are sync
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={"status": "SUCCESS", "code": "fixed_code"})
    mock_post.return_value = mock_resp

    # Make target agent rae-phoenix with refactor intent
    payload = {
        "payload": {
            "intent": "REFACTOR_CODE",
            "project": "dreamsoft",
            "faulty_code": "def old(): pass",
            "tribunal_reasoning": "Unused imports",
            "file_path": "main.py",
        },
        "source_agent": "rae-quality",
        "target_agent": "rae-phoenix",
    }

    # Initialize app.state mock
    app.state.rae_core_service = MagicMock()
    app.state.rae_core_service.engine.store_memory = AsyncMock()

    # We call the FastAPI endpoint sync client
    response = client.post("/v2/bridge/interact", json=payload)

    assert response.status_code == 200
    res_data = response.json()
    assert "routed to rae-phoenix successfully" in res_data["message"]
    assert res_data["target_response"] == {"status": "SUCCESS", "code": "fixed_code"}

    # Verify httpx POST was called with the mapped payload
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://rae-phoenix:8012/v2/phoenix/repair"
    assert kwargs["json"]["project"] == "dreamsoft"
    assert kwargs["json"]["code"] == "def old(): pass"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_a2a_bridge_state_and_journal_propagation(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={"status": "SUCCESS"})
    mock_post.return_value = mock_resp

    payload = {
        "payload": {
            "intent": "REFACTOR_CODE",
            "project": "dreamsoft",
            "faulty_code": "def old(): pass",
            "file_path": "main.py",
        },
        "source_agent": "rae-quality",
        "target_agent": "rae-phoenix",
        "autonomy_state": "DRY_RUN_PASSED",
        "autonomy_journal": ["INIT", "RISK_ASSESSED", "DRY_RUN_PASSED"],
    }

    app.state.rae_core_service = MagicMock()
    store_mock = AsyncMock()
    app.state.rae_core_service.engine.store_memory = store_mock

    response = client.post("/v2/bridge/interact", json=payload)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["autonomy_state"] == "DRY_RUN_PASSED"
    assert res_data["autonomy_journal"] == ["INIT", "RISK_ASSESSED", "DRY_RUN_PASSED"]

    # Verify memory storage metadata includes autonomy state & journal
    store_mock.assert_called_once()
    store_kwargs = store_mock.call_args[1]
    assert store_kwargs["metadata"]["autonomy_state"] == "DRY_RUN_PASSED"
    assert store_kwargs["metadata"]["autonomy_journal"] == [
        "INIT",
        "RISK_ASSESSED",
        "DRY_RUN_PASSED",
    ]

    # Verify headers propagated
    mock_post.assert_called_once()
    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-Autonomy-State"] == "DRY_RUN_PASSED"
    assert json.loads(kwargs["headers"]["X-Autonomy-Journal"]) == [
        "INIT",
        "RISK_ASSESSED",
        "DRY_RUN_PASSED",
    ]
