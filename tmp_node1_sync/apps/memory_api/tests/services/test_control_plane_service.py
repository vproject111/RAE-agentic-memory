from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from apps.memory_api.models.control_plane import (
    ComputeNode,
    DelegatedTask,
    NodeStatus,
    TaskStatus,
)
from apps.memory_api.services.control_plane_service import ControlPlaneService


@pytest.fixture
def mock_node_repo():
    return AsyncMock()


@pytest.fixture
def mock_task_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_node_repo, mock_task_repo):
    return ControlPlaneService(mock_node_repo, mock_task_repo)


@pytest.mark.asyncio
async def test_register_node(service, mock_node_repo):
    node_id = "test-node-1"
    api_key = "secret"
    capabilities = {"gpu": True}
    ip = "100.1.2.3"

    expected_node = ComputeNode(
        id=uuid4(),
        node_id=node_id,
        status=NodeStatus.ONLINE,
        last_heartbeat=datetime.now(),
        capabilities=capabilities,
        ip_address=ip,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    mock_node_repo.register_node.return_value = expected_node

    result = await service.register_node(node_id, api_key, capabilities, ip)

    assert result == expected_node
    mock_node_repo.register_node.assert_called_once()
    # Check if api_key was hashed (simple check that it's not the raw key if we passed it to repo,
    # but service hashes it before calling repo. The mock sees the hash.)
    call_args = mock_node_repo.register_node.call_args
    assert call_args[0][1] != api_key  # Hash should not equal raw key


@pytest.mark.asyncio
async def test_process_heartbeat_success(service, mock_node_repo):
    node_id = "test-node-1"
    expected_node = ComputeNode(
        id=uuid4(),
        node_id=node_id,
        status=NodeStatus.ONLINE,
        last_heartbeat=datetime.now(),
        ip_address="100.1.2.3",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_node_repo.update_heartbeat.return_value = expected_node

    result = await service.process_heartbeat(node_id, NodeStatus.ONLINE)

    assert result == expected_node
    mock_node_repo.update_heartbeat.assert_called_with(node_id, NodeStatus.ONLINE)


@pytest.mark.asyncio
async def test_process_heartbeat_fail(service, mock_node_repo):
    mock_node_repo.update_heartbeat.return_value = None

    with pytest.raises(ValueError):
        await service.process_heartbeat("unknown", NodeStatus.ONLINE)


@pytest.mark.asyncio
async def test_poll_task_success(service, mock_node_repo, mock_task_repo):
    node_id = "test-node-1"
    node_uuid = uuid4()

    mock_node_repo.get_node.return_value = ComputeNode(
        id=node_uuid,
        node_id=node_id,
        status=NodeStatus.ONLINE,
        last_heartbeat=datetime.now(),
        ip_address="100.1.2.3",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    expected_task = DelegatedTask(
        id=uuid4(),
        type="test",
        status=TaskStatus.PROCESSING,
        priority=1,
        payload={},
        assigned_node_id=node_uuid,
        error=None,
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=None,
        result=None,
    )
    mock_task_repo.claim_task.return_value = expected_task

    result = await service.poll_task(node_id)

    assert result == expected_task
    mock_task_repo.claim_task.assert_called_with(node_uuid)
