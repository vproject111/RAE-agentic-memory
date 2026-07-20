import json
import time
import pytest
import asyncio
import hashlib
import threading
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from apps.memory_api.services.mesh_service import MeshService, PeerInfo
from apps.memory_api.services.ssh_tunnel import SSHTunnelManager
from apps.memory_api.services.relay_broker import (
    encrypt_payload,
    decrypt_payload,
    MatrixRelay,
    NATSRelay,
)
from apps.memory_api.api.v2.mesh import receive_sync_data, safe_hash


def make_mock_request(payload: dict) -> MagicMock:
    mock_req = MagicMock()
    body_data = json.dumps(payload).encode("utf-8")
    mock_req.headers = {"content-length": str(len(body_data))}
    mock_req.body = AsyncMock(return_value=body_data)
    mock_req.app.state.pool = None
    mock_req.app.state.rae_core_service = None
    return mock_req


@pytest.fixture
def mesh_service():
    return MeshService(secret_key="my-test-secret-key-that-is-long-enough-32-chars")


@pytest.mark.asyncio
async def test_normalization_and_sanitization_in_sync(mesh_service):
    # Register peer
    sender_id = "sender-peer"
    await mesh_service.register_peer(sender_id, "Sender", "http://sender", "token-abc")

    # Content with HTML tags and unicode accents/ligatures (unnormalized)
    raw_content = "<p>Hello 𝔲𝔫𝔦𝔠𝔬𝔡𝔢 <script>alert(1)</script></p>"
    
    payload = {
        "sender_id": sender_id,
        "receiver_id": "rae-host",
        "memories": [
            {
                "id": str(uuid4()),
                "content": raw_content,
                "layer": "episodic",
                "info_class": "public"
            }
        ]
    }

    mock_req = make_mock_request(payload)
    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock()
    mock_conn = AsyncMock()
    # Mock database select showing no existing entry to trigger INSERT
    mock_conn.fetchval = AsyncMock(return_value=None)
    mock_conn.execute = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_req.app.state.pool = mock_pool

    resp = await receive_sync_data(mock_req, mesh_service)
    assert resp["processed"] == 1

    # Check the sanitized insert values
    insert_call = mock_conn.execute.call_args_list[0]
    sql_args = insert_call[0]
    
    sanitized_content = sql_args[2]  # content is the third argument in execute (after query and UUID)
    assert "<script>" not in sanitized_content
    assert "</p>" in sanitized_content  # nh3 keeps safe tags like <p> but strips unsafe
    assert "unicode" in sanitized_content


@pytest.mark.asyncio
async def test_signature_and_provenance_verification_success(mesh_service):
    sender_id = "sender-peer"
    # Deriving keys to generate valid signatures
    private_key, public_key = mesh_service.derive_key_pair(sender_id)
    public_key_hex = public_key.public_bytes_raw().hex()

    await mesh_service.register_peer(
        sender_id, "Sender", "http://sender", "token-abc", public_key=public_key_hex
    )

    memories = [
        {
            "id": str(uuid4()),
            "content": "Secret information",
            "layer": "episodic",
            "info_class": "public"
        }
    ]

    memories_bytes = json.dumps(memories, sort_keys=True).encode("utf-8")
    payload_hash = hashlib.sha256(memories_bytes).hexdigest()
    signature = private_key.sign(memories_bytes).hex()

    payload = {
        "sender_id": sender_id,
        "receiver_id": "rae-host",
        "payload_hash": payload_hash,
        "signature": signature,
        "memories": memories
    }

    mock_req = make_mock_request(payload)
    resp = await receive_sync_data(mock_req, mesh_service)
    assert resp["processed"] == 1


@pytest.mark.asyncio
async def test_signature_verification_failure_altered_payload(mesh_service):
    sender_id = "sender-peer"
    private_key, public_key = mesh_service.derive_key_pair(sender_id)
    public_key_hex = public_key.public_bytes_raw().hex()

    await mesh_service.register_peer(
        sender_id, "Sender", "http://sender", "token-abc", public_key=public_key_hex
    )

    memories = [
        {
            "id": str(uuid4()),
            "content": "Secret information",
            "layer": "episodic",
            "info_class": "public"
        }
    ]

    memories_bytes = json.dumps(memories, sort_keys=True).encode("utf-8")
    signature = private_key.sign(memories_bytes).hex()

    # Alter memory content after signature generation
    altered_memories = [
        {
            "id": memories[0]["id"],
            "content": "Altered secret information",
            "layer": "episodic",
            "info_class": "public"
        }
    ]

    payload = {
        "sender_id": sender_id,
        "receiver_id": "rae-host",
        "signature": signature,
        "memories": altered_memories
    }

    from fastapi import HTTPException
    mock_req = make_mock_request(payload)
    with pytest.raises(HTTPException) as exc:
        await receive_sync_data(mock_req, mesh_service)
    assert exc.value.status_code == 403
    assert "Invalid payload signature" in exc.value.detail


def test_ssh_tunnel_manager_exponential_backoff():
    manager = SSHTunnelManager(
        local_port=8080,
        remote_port=8081,
        ssh_host="example.com",
        ssh_user="operator",
        base_backoff=0.1
    )

    mock_popen = MagicMock()
    # Mock process immediately exiting (e.g. port clash)
    mock_popen.poll.side_effect = [1, 1, 1, None]
    mock_popen.communicate.return_value = ("", "Port clash/already in use")

    with patch("subprocess.Popen", return_value=mock_popen) as mock_spawn:
        # Start tunnel monitor
        manager.start()
        time.sleep(0.5)
        manager.stop()

        # subprocess should have been called multiple times
        assert mock_spawn.call_count >= 2


def test_relay_broker_aes_gcm_encryption_decryption():
    secret_key = "a-very-long-and-secure-test-secret-key-32"
    payload = {
        "sender_id": "peer-a",
        "receiver_id": "peer-b",
        "memories": [{"content": "hello relay!"}]
    }

    encrypted = encrypt_payload(payload, secret_key)
    assert encrypted != json.dumps(payload)

    decrypted = decrypt_payload(encrypted, secret_key)
    assert decrypted["sender_id"] == "peer-a"
    assert decrypted["memories"][0]["content"] == "hello relay!"


@pytest.mark.asyncio
async def test_matrix_relay_publish_consume():
    secret = "my-matrix-relay-shared-secret-1234"
    relay = MatrixRelay(
        homeserver_url="https://matrix.org",
        access_token="syt_token",
        room_id="!room:matrix.org",
        secret_key=secret
    )

    # Mock publish post request
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200, json=lambda: {"event_id": "123"})
        success = await relay.publish({"data": "test"})
        assert success is True
        mock_post.assert_called_once()

    # Mock consume get request
    with patch("httpx.AsyncClient.get") as mock_get:
        payload = {"data": "test"}
        encrypted = encrypt_payload(payload, secret)
        
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "next_batch": "batch_2",
                "rooms": {
                    "join": {
                        "!room:matrix.org": {
                            "timeline": {
                                "events": [
                                    {
                                        "type": "m.room.message",
                                        "content": {
                                            "rae_encrypted": True,
                                            "body": encrypted
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        )
        
        consumed = await relay.consume()
        assert len(consumed) == 1
        assert consumed[0]["data"] == "test"


@pytest.mark.asyncio
async def test_nats_relay_publish_consume():
    secret = "my-nats-relay-shared-secret-1234"
    relay = NATSRelay(
        nats_host="127.0.0.1",
        nats_port=4222,
        subject="rae.mesh.sync",
        secret_key=secret
    )

    mock_reader = AsyncMock()
    mock_reader.readline.return_value = b"INFO {}\r\n"
    mock_writer = AsyncMock()

    # Test publish
    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)) as mock_conn:
        success = await relay.publish({"data": "nats-test"})
        assert success is True
        mock_conn.assert_called_once_with("127.0.0.1", 4222)
        mock_writer.write.assert_called()

    # Test consume_one
    payload = {"data": "nats-test"}
    encrypted = encrypt_payload(payload, secret)
    encrypted_bytes = encrypted.encode("utf-8")
    
    mock_reader.readline.side_effect = [
        b"INFO {}\r\n",
        f"MSG rae.mesh.sync 1 {len(encrypted_bytes)}\r\n".encode("utf-8"),
        b"\r\n"
    ]
    mock_reader.readexactly.return_value = encrypted_bytes

    with patch("asyncio.open_connection", return_value=(mock_reader, mock_writer)) as mock_conn:
        msg = await relay.consume_one()
        assert msg is not None
        assert msg["data"] == "nats-test"
