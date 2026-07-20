import time
import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from cryptography.hazmat.primitives.asymmetric import ed25519

from apps.memory_api.services.mesh_service import MeshService, PeerInfo
from apps.memory_api.api.v2.mesh import receive_sync_data, get_handshake_challenge, receive_handshake

@pytest.fixture
def mesh_service():
    return MeshService(secret_key="my-test-secret-key-that-is-long-enough-32-chars")

def make_mock_request(payload: dict) -> MagicMock:
    mock_req = MagicMock()
    body_data = json.dumps(payload).encode("utf-8")
    mock_req.headers = {"content-length": str(len(body_data))}
    mock_req.body = AsyncMock(return_value=body_data)
    return mock_req

def test_aes_gcm_token_encryption(mesh_service):
    token = "some-secure-uuid-token"
    public_key = "some-hex-pub-key"
    
    # Encrypt
    encrypted = mesh_service.encrypt_auth_data(token, public_key)
    assert encrypted != token
    
    # Decrypt
    decrypted_token, decrypted_pub_key = mesh_service.decrypt_auth_data(encrypted)
    assert decrypted_token == token
    assert decrypted_pub_key == public_key

def test_key_pair_derivation_and_challenge_signing(mesh_service):
    priv, pub = mesh_service.derive_key_pair("peer-a")
    assert isinstance(priv, ed25519.Ed25519PrivateKey)
    assert isinstance(pub, ed25519.Ed25519PublicKey)
    
    # Generate and verify challenge
    challenge_data = mesh_service.generate_challenge("peer-a")
    assert "challenge" in challenge_data
    assert "host_public_key" in challenge_data
    assert "challenge_signature" in challenge_data
    
    challenge = challenge_data["challenge"]
    pub_key_hex = challenge_data["host_public_key"]
    sig_hex = challenge_data["challenge_signature"]
    
    # Should verify successfully
    mesh_service.verify_challenge_signature(pub_key_hex, challenge, sig_hex)
    
    # Replay protection: invalid timestamp should fail
    expired_challenge = challenge.copy()
    expired_challenge["timestamp"] = int(time.time()) - 400
    with pytest.raises(ValueError, match="expired"):
        mesh_service.verify_challenge_signature(pub_key_hex, expired_challenge, sig_hex)

def test_signed_invite_jwt_validation(mesh_service):
    host_url = "http://localhost:8000"
    tenant_id = "test-tenant"
    
    # Create invite
    code = mesh_service.create_invite(host_url, tenant_id)
    
    # Validate invite (claims: exp, iat, aud, iss, typ)
    payload = mesh_service.validate_invite(code)
    assert payload["host"] == host_url
    assert payload["tenant"] == tenant_id
    assert payload["iss"] == "rae-mesh-host"
    assert payload["aud"] == "rae-mesh-peers"
    
    # Try using invalid/altered token
    import jwt
    untrusted_code = jwt.encode(
        {"host": host_url, "tenant": tenant_id, "nonce": "xyz", "iss": "bad-iss", "aud": "rae-mesh-peers", "iat": int(time.time()), "exp": int(time.time()) + 300},
        "wrong-secret",
        algorithm="HS256",
        headers={"typ": "mesh-invite-v1"}
    )
    with pytest.raises(ValueError):
        mesh_service.validate_invite(untrusted_code)

@pytest.mark.asyncio
async def test_consent_token_generation_and_validation(mesh_service):
    sender = "peer-a"
    receiver = "peer-b"
    grant_id = "grant-123"
    
    token = mesh_service.generate_consent_token(sender, receiver, grant_id)
    
    # Verify valid token
    payload = await mesh_service.verify_consent_token(token, sender, receiver)
    assert payload["consent_grant_id"] == grant_id
    assert payload["iss"] == sender
    assert payload["aud"] == receiver
    
    # Verify validation fails for incorrect receiver
    with pytest.raises(ValueError, match="Audience doesn't match"):
        await mesh_service.verify_consent_token(token, sender, "peer-c")
        
    # Verify validation fails for expired/exceeded TTL token
    # (Mocking time so that token appears expired)
    with patch("time.time", return_value=time.time() + 600):
        with pytest.raises(ValueError):
            await mesh_service.verify_consent_token(token, sender, receiver)

    # Verify replay protection via jti
    token2 = mesh_service.generate_consent_token(sender, receiver, "grant-456")
    await mesh_service.verify_consent_token(token2, sender, receiver)
    with pytest.raises(ValueError, match="Replay attack detected"):
        await mesh_service.verify_consent_token(token2, sender, receiver)

@pytest.mark.asyncio
async def test_data_classification_filtering_before_transmission(mesh_service):
    # Register peer first with no consent
    peer_id = "peer-no-consent"
    await mesh_service.register_peer(peer_id, "No Consent Peer", "http://peer-nc", "token-123")
    
    memories = [
        {"id": "1", "content": "public memory", "info_class": "public"},
        {"id": "2", "content": "internal memory", "info_class": "internal"},
        {"id": "3", "content": "confidential memory", "info_class": "confidential"},
        {"id": "4", "content": "restricted memory", "info_class": "restricted"},
    ]
    
    # Prepare payload with no consent
    payload = await mesh_service.prepare_sync_payload(peer_id, memories)
    assert payload["consent_token"] is None
    filtered_ids = [m["id"] for m in payload["memories"]]
    assert "4" not in filtered_ids  # Restricted memory should be filtered out
    assert "1" in filtered_ids
    assert "2" in filtered_ids
    assert "3" in filtered_ids
    
    # Register peer with consent
    peer_consent_id = "peer-with-consent"
    grant_id = "grant-abc"
    await mesh_service.register_peer(peer_consent_id, "Consent Peer", "http://peer-c", "token-456", consent_grant_id=grant_id)
    
    # Prepare payload with consent
    payload_consent = await mesh_service.prepare_sync_payload(peer_consent_id, memories)
    assert payload_consent["consent_token"] is not None
    filtered_ids_consent = [m["id"] for m in payload_consent["memories"]]
    assert "4" in filtered_ids_consent  # Restricted memory should be allowed since consent grant exists

@pytest.mark.asyncio
async def test_receiver_sync_handling_classification_guards(mesh_service):
    # Register sender peer with consent
    sender_id = "sender-peer"
    grant_id = "grant-xyz"
    await mesh_service.register_peer(sender_id, "Sender Peer", "http://sender", "token-abc", consent_grant_id=grant_id)
    
    # Case 1: Send unrestricted memories (no consent token required)
    payload_unrestricted = {
        "sender_id": sender_id,
        "receiver_id": "rae-host",
        "memories": [{"id": "1", "content": "some public info", "info_class": "public"}]
    }
    resp = await receive_sync_data(make_mock_request(payload_unrestricted), mesh_service)
    assert resp["processed"] == 1
    
    # Case 2: Send restricted memories without consent token (should be blocked)
    payload_restricted_no_token = {
        "sender_id": sender_id,
        "receiver_id": "rae-host",
        "memories": [{"id": "2", "content": "secret email content", "info_class": "restricted"}]
    }
    with pytest.raises(HTTPException) as excinfo:
        await receive_sync_data(make_mock_request(payload_restricted_no_token), mesh_service)
    assert excinfo.value.status_code == 403
    assert "no consent token was provided" in excinfo.value.detail
    
    # Case 3: Send restricted memories with valid consent token
    consent_token = mesh_service.generate_consent_token(sender_id, "rae-host", grant_id)
    payload_restricted_with_token = {
        "sender_id": sender_id,
        "receiver_id": "rae-host",
        "consent_token": consent_token,
        "memories": [{"id": "2", "content": "secret email content", "info_class": "restricted"}]
    }
    resp_ok = await receive_sync_data(make_mock_request(payload_restricted_with_token), mesh_service)
    assert resp_ok["processed"] == 1

@pytest.mark.asyncio
async def test_receive_sync_payload_too_large(mesh_service):
    # Test body size > 10MB fails with 413
    mock_req = MagicMock()
    mock_req.headers = {"content-length": str(11 * 1024 * 1024)} # 11MB
    mock_req.body = AsyncMock(return_value=b"a" * (11 * 1024 * 1024))
    
    with pytest.raises(HTTPException) as excinfo:
        await receive_sync_data(mock_req, mesh_service)
    assert excinfo.value.status_code == 413

@pytest.mark.asyncio
async def test_db_persistence_calls():
    # Test that MeshService interacts correctly with asyncpg Pool
    mock_pool = MagicMock()
    mock_pool.execute = AsyncMock()
    mock_pool.fetchrow = AsyncMock(return_value={
        "peer_id": "peer-1",
        "name": "DB Peer",
        "endpoint_url": "http://db-peer",
        "encrypted_auth_token": "some-token-b64",
        "consent_grant_id": "grant-123",
        "status": "active",
        "created_at": datetime.now()
    })
    mock_pool.fetch = AsyncMock(return_value=[])
    
    service_db = MeshService(pool=mock_pool, secret_key="my-test-secret-key-that-is-long-enough-32-chars")
    
    # Mock decrypt_auth_data to bypass actual decryption in db retrieval test
    with patch.object(service_db, "decrypt_auth_data", return_value=("token-abc", "pubkey-xyz")):
        peer = await service_db.get_peer("peer-1")
        assert peer is not None
        assert peer.peer_id == "peer-1"
        assert peer.token == "token-abc"
        assert peer.consent_grant_id == "grant-123"
        mock_pool.fetchrow.assert_called_once()
        
        # Test register_peer DB call
        await service_db.register_peer("peer-2", "New Peer", "http://peer-2", "token-2", "pubkey-2", "grant-456")
        mock_pool.execute.assert_called()
