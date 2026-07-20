import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi.testclient import TestClient

from apps.memory_api.main import app
from apps.memory_api.tasks.background_tasks import sync_mesh_peers_task
from apps.memory_api.services.mesh_service import PeerInfo

@pytest.fixture
def test_client():
    with TestClient(app) as client:
        client.headers.update({
            "X-Tenant-ID": "00000000-0000-0000-0000-000000000000",
            "Authorization": "Bearer dev-key"
        })
        yield client

# 1. Test Celery task execution & lexicographical sorting
def test_sync_mesh_peers_task_execution():
    mock_rae_service = AsyncMock()
    mock_rae_service.postgres_pool = AsyncMock()
    mock_rae_service.redis_client = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_rae_service
        
    with patch("apps.memory_api.tasks.background_tasks.rae_context", side_effect=mock_context):
        with patch("apps.memory_api.services.mesh_service.MeshService") as mock_mesh_service_cls:
            mock_mesh_service = MagicMock()
            mock_mesh_service_cls.return_value = mock_mesh_service
            
            peer_a = PeerInfo(
                peer_id="peer-a",
                name="Node A",
                url="http://node-a",
                token="token-a",
                created_at=12345.0,
                transport_type="http"
            )
            peer_b = PeerInfo(
                peer_id="peer-b",
                name="Node B",
                url="http://node-b",
                token="token-b",
                created_at=12346.0,
                transport_type="tor"
            )
            
            # Setup list_peers returns in unsorted order
            mock_mesh_service.list_peers = AsyncMock(return_value=[peer_b, peer_a])
            mock_mesh_service.push_memories_to_peer = AsyncMock(return_value=3)
            
            # Setup Redis lock mocks
            mock_rae_service.redis_client.set = AsyncMock(return_value=True)
            mock_rae_service.redis_client.delete = AsyncMock()
            
            # Trigger task
            result = sync_mesh_peers_task()
            
            # Assertions
            assert result["peers_synced"] == 2
            assert result["details"]["peer-a"] == "success: 3 memories"
            assert result["details"]["peer-b"] == "success: 3 memories"
            
            # Verify lexicographical lock ordering: peer-a (locked first) then peer-b (locked second)
            calls = mock_rae_service.redis_client.set.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == "mesh_sync_peer-a"
            assert calls[1][0][0] == "mesh_sync_peer-b"

# 2. Test lock conflict safety
def test_sync_mesh_peers_task_lock_conflict():
    mock_rae_service = AsyncMock()
    mock_rae_service.postgres_pool = AsyncMock()
    mock_rae_service.redis_client = AsyncMock()
    
    @asynccontextmanager
    async def mock_context():
        yield mock_rae_service
        
    with patch("apps.memory_api.tasks.background_tasks.rae_context", side_effect=mock_context):
        with patch("apps.memory_api.services.mesh_service.MeshService") as mock_mesh_service_cls:
            mock_mesh_service = MagicMock()
            mock_mesh_service_cls.return_value = mock_mesh_service
            
            peer_a = PeerInfo(
                peer_id="peer-a",
                name="Node A",
                url="http://node-a",
                token="token-a",
                created_at=12345.0,
                transport_type="http"
            )
            
            mock_mesh_service.list_peers = AsyncMock(return_value=[peer_a])
            mock_mesh_service.push_memories_to_peer = AsyncMock()
            
            # Redis set returns False (already locked)
            mock_rae_service.redis_client.set = AsyncMock(return_value=False)
            
            result = sync_mesh_peers_task()
            
            assert result["peers_synced"] == 1
            assert result["details"]["peer-a"] == "locked"
            # Verify push_memories_to_peer was not called
            mock_mesh_service.push_memories_to_peer.assert_not_called()

# 3. Test API endpoints
def test_api_register_peer(test_client):
    mock_mesh_service = MagicMock()
    mock_mesh_service.register_peer = AsyncMock()
    app.state.mesh_service = mock_mesh_service
    
    payload = {
        "peer_id": "test-node",
        "name": "Test Node",
        "url": "http://test-node",
        "token": "secret-token",
        "transport_type": "ssh"
    }
    
    response = test_client.post("/v2/mesh/peers", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    mock_mesh_service.register_peer.assert_called_once_with(
        peer_id="test-node",
        name="Test Node",
        url="http://test-node",
        token="secret-token",
        public_key=None,
        consent_grant_id=None,
        status="active",
        transport_type="ssh"
    )

def test_api_revoke_peer(test_client):
    mock_mesh_service = MagicMock()
    mock_mesh_service.revoke_peer = AsyncMock()
    app.state.mesh_service = mock_mesh_service
    
    response = test_client.delete("/v2/mesh/peers/test-node")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    
    mock_mesh_service.revoke_peer.assert_called_once_with("test-node")

def test_api_trigger_peer_sync(test_client):
    mock_mesh_service = MagicMock()
    mock_mesh_service.push_memories_to_peer = AsyncMock(return_value=12)
    mock_mesh_service.redis_client = AsyncMock()
    mock_mesh_service.redis_client.set = AsyncMock(return_value=True)
    mock_mesh_service.redis_client.delete = AsyncMock()
    app.state.mesh_service = mock_mesh_service
    
    response = test_client.post("/v2/mesh/peers/test-node/sync")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["synced_memories"] == 12
    
    mock_mesh_service.redis_client.set.assert_called_once_with("mesh_sync_test-node", "1", ex=300, nx=True)
    mock_mesh_service.push_memories_to_peer.assert_called_once_with("test-node")
    mock_mesh_service.redis_client.delete.assert_called_once_with("mesh_sync_test-node")

def test_api_get_peer_status(test_client):
    mock_mesh_service = MagicMock()
    
    peer = PeerInfo(
        peer_id="test-node",
        name="Test Node",
        url="http://test-node",
        token="secret-token",
        created_at=12345.0,
        transport_type="http"
    )
    
    mock_mesh_service.get_peer = AsyncMock(return_value=peer)
    mock_mesh_service.pool = AsyncMock()
    
    # Mock pool.fetch to return some sync statistics
    stats_data = [
        {"status": "success", "count": 150, "last_sync": datetime(2026, 7, 20, 8, 0, 0)},
        {"status": "failed", "count": 2, "last_sync": datetime(2026, 7, 20, 7, 50, 0)}
    ]
    mock_mesh_service.pool.fetch = AsyncMock(return_value=stats_data)
    app.state.mesh_service = mock_mesh_service
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        
        response = test_client.get("/v2/mesh/peers/test-node/status")
        assert response.status_code == 200
        data = response.json()
        assert data["peer_id"] == "test-node"
        assert data["status"] == "online"
        assert data["latency_ms"] >= 0
        assert data["sync_stats"]["success_count"] == 150
        assert data["sync_stats"]["failed_count"] == 2
        assert "2026-07-20T08:00:00" in data["sync_stats"]["last_synced_at"]
