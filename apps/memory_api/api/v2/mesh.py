import uuid
import hashlib
import secrets
import threading
from typing import Any, Dict, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from apps.memory_api.services.mesh_service import MeshService, PeerInfo
from apps.memory_api.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["Mesh"], prefix="/v2/mesh")

_mesh_service_lock = threading.Lock()


def safe_hash(content: str, max_size_bytes: int = 10 * 1024 * 1024) -> str:
    """Hash content safely, rejecting content larger than max_size_bytes to prevent DoS."""
    content_bytes = content.encode("utf-8")
    if len(content_bytes) > max_size_bytes:
        raise ValueError("Content size exceeds maximum allowed limit for hashing (10MB)")
    return hashlib.sha256(content_bytes).hexdigest()


# Dependency to get MeshService singleton
def get_mesh_service(request: Request) -> MeshService:
    if not hasattr(request.app.state, "mesh_service"):
        with _mesh_service_lock:
            if not hasattr(request.app.state, "mesh_service"):
                pool = getattr(request.app.state, "pool", None)
                redis_client = getattr(request.app.state, "redis_client", None)
                request.app.state.mesh_service = MeshService(
                    pool=pool, 
                    redis_client=redis_client, 
                    secret_key=settings.SECRET_KEY
                )

    from typing import cast
    return cast(MeshService, request.app.state.mesh_service)


# --- Models ---
class InviteRequest(BaseModel):
    host_url: str
    tenant_id: str = "default"


class InviteResponse(BaseModel):
    invite_code: str
    expires_in_seconds: int


class JoinRequest(BaseModel):
    invite_code: str
    my_peer_id: str
    my_public_url: str
    my_name: str


class JoinResponse(BaseModel):
    status: str
    host_peer_id: str
    host_token: str


class ChallengeResponse(BaseModel):
    challenge: Dict[str, Any]
    host_public_key: str
    challenge_signature: str


class HandshakeRequest(BaseModel):
    invite_code: str
    peer_id: str
    peer_url: str
    peer_name: str
    peer_token: str
    # Security verification
    public_key: str
    challenge: Dict[str, Any]
    signature: str
    joiner_challenge: Dict[str, Any]


# --- Endpoints ---

@router.post("/invite", response_model=InviteResponse)
async def create_invite(
    request: InviteRequest, service: MeshService = Depends(get_mesh_service)
):
    """(Host) Create an invite code for someone to join."""
    code = service.create_invite(request.host_url, request.tenant_id)
    return InviteResponse(invite_code=code, expires_in_seconds=300)


@router.get("/handshake/challenge", response_model=ChallengeResponse)
async def get_handshake_challenge(service: MeshService = Depends(get_mesh_service)):
    """(Host) Retrieve challenge, host public key, and host signature for trust verification."""
    data = service.generate_challenge(settings.RAE_PEER_ID)
    return ChallengeResponse(
        challenge=data["challenge"],
        host_public_key=data["host_public_key"],
        challenge_signature=data["challenge_signature"]
    )


@router.post("/join", response_model=JoinResponse)
async def join_mesh(
    request: JoinRequest, service: MeshService = Depends(get_mesh_service)
):
    """(Joiner) Consume an invite code and connect to a host using signed challenge handshake."""
    try:
        # 1. Decode locally to find Host URL
        import jwt
        payload = jwt.decode(request.invite_code, options={"verify_signature": False})
        host_url = payload.get("host")
        if not host_url:
            raise HTTPException(status_code=400, detail="Invalid invite: missing host")

        # 2. Retrieve challenge from Host
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{host_url}/v2/mesh/handshake/challenge")
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400, detail=f"Failed to fetch challenge from Host: {resp.text}"
                )
            challenge_data = resp.json()

        challenge = challenge_data["challenge"]
        host_pub_key = challenge_data["host_public_key"]
        challenge_sig = challenge_data["challenge_signature"]

        # 3. Verify Host's challenge signature
        try:
            service.verify_challenge_signature(host_pub_key, challenge, challenge_sig)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Host challenge signature verification failed: {e}")

        # 4. Sign Host's challenge using our own private key
        my_signature = service.sign_challenge(challenge, request.my_peer_id)
        _, my_public_key = service.derive_key_pair(request.my_peer_id)
        my_public_key_hex = my_public_key.public_bytes_raw().hex()

        # 5. Generate a challenge for the Host to sign
        import secrets
        import time
        my_challenge = {
            "nonce": secrets.token_hex(16),
            "timestamp": int(time.time())
        }

        # 6. Perform Handshake with Host
        my_token = str(uuid.uuid4())
        async with httpx.AsyncClient() as client:
            hs_payload = {
                "invite_code": request.invite_code,
                "peer_id": request.my_peer_id,
                "peer_url": request.my_public_url,
                "peer_name": request.my_name,
                "peer_token": my_token,
                "public_key": my_public_key_hex,
                "challenge": challenge,
                "signature": my_signature,
                "joiner_challenge": my_challenge
            }
            resp = await client.post(f"{host_url}/v2/mesh/handshake", json=hs_payload)
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400, detail=f"Handshake rejected by Host: {resp.text}"
                )
            data = resp.json()

        # 7. Verify Host's signature of our challenge
        host_id = data["host_id"]
        host_token = data["token"]
        host_signature_of_my_challenge = data["signature"]
        
        try:
            service.verify_challenge_signature(host_pub_key, my_challenge, host_signature_of_my_challenge)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Host signature of our challenge is invalid: {e}")

        # 8. Register Host as a peer locally
        await service.register_peer(
            peer_id=host_id,
            name="Host",
            url=host_url,
            token=host_token,
            public_key=host_pub_key,
            consent_grant_id=data.get("consent_grant_id"),
            status="active"
        )

        return JoinResponse(
            status="connected",
            host_peer_id=host_id,
            host_token=host_token,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("join_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/handshake")
async def receive_handshake(
    request: HandshakeRequest, service: MeshService = Depends(get_mesh_service)
):
    """(Host) Receive a handshake request from a Joiner, validating signed challenge."""
    try:
        # 1. Validate Invite Code
        service.validate_invite(request.invite_code)

        # 2. Verify Joiner's challenge signature
        try:
            service.verify_challenge_signature(request.public_key, request.challenge, request.signature)
        except ValueError as e:
            raise HTTPException(status_code=403, detail=f"Joiner challenge signature verification failed: {e}")

        # 3. Establish Consent Grant ID
        consent_grant_id = f"grant-{uuid.uuid4()}"

        # 4. Register the Joiner as a trusted peer
        await service.register_peer(
            peer_id=request.peer_id,
            name=request.peer_name,
            url=request.peer_url,
            token=request.peer_token,
            public_key=request.public_key,
            consent_grant_id=consent_grant_id,
            status="active"
        )

        # 5. Generate a token for the Joiner to use
        my_token_for_joiner = str(uuid.uuid4())

        # 6. Sign Joiner's challenge
        host_signature = service.sign_challenge(request.joiner_challenge, settings.RAE_PEER_ID)
        
        _, my_public_key = service.derive_key_pair(settings.RAE_PEER_ID)
        my_public_key_hex = my_public_key.public_bytes_raw().hex()

        return {
            "status": "accepted",
            "host_id": settings.RAE_PEER_ID,
            "token": my_token_for_joiner,
            "host_public_key": my_public_key_hex,
            "signature": host_signature,
            "consent_grant_id": consent_grant_id
        }

    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("handshake_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/peers", response_model=List[PeerInfo])
async def list_peers(service: MeshService = Depends(get_mesh_service)):
    """List connected peers."""
    return await service.list_peers()


@router.post("/sync/receive")
async def receive_sync_data(
    payload: Dict[str, Any], 
    service: MeshService = Depends(get_mesh_service)
):
    """Receive pushed memories from a peer, enforcing data classification and consent checks."""
    sender_id = payload.get("sender_id")
    receiver_id = payload.get("receiver_id", settings.RAE_PEER_ID)
    consent_token = payload.get("consent_token")
    memories = payload.get("memories", [])
    
    logger.info("received_sync_push", sender=sender_id, items=len(memories))
    
    if not sender_id:
        raise HTTPException(status_code=400, detail="Missing sender_id in sync payload")
        
    peer = await service.get_peer(sender_id)
    if not peer:
        raise HTTPException(status_code=403, detail=f"Sender peer {sender_id} is not registered")
        
    # Check if there are restricted memories
    has_restricted = any(str(m.get("info_class", "")).lower() == "restricted" for m in memories)
    
    if has_restricted:
        # Require a valid consent token
        if not consent_token:
            raise HTTPException(
                status_code=403, 
                detail="Sync contains RESTRICTED memories but no consent token was provided"
            )
            
        try:
            # Verify consent token (asynchronous)
            token_payload = await service.verify_consent_token(consent_token, sender_id, receiver_id)
            
            # Verify ConsentGrant in DB matches the token's consent_grant_id (prevent timing attacks)
            peer_grant_id = peer.consent_grant_id or ""
            token_grant_id = token_payload.get("consent_grant_id") or ""
            if not peer.consent_grant_id or not secrets.compare_digest(peer_grant_id, token_grant_id):
                raise HTTPException(
                    status_code=403, 
                    detail="ConsentGrant verification failed for sender-receiver pair"
                )
                
            # Verify peer status is active
            if peer.status != "active":
                raise HTTPException(
                    status_code=403, 
                    detail="ConsentGrant is inactive (peer status is not active)"
                )
                
        except ValueError as e:
            raise HTTPException(status_code=403, detail=f"Consent token validation failed: {str(e)}")
            
    # Process and save memories
    processed_count = 0
    for m in memories:
        memory_id = m.get("id")
        content = m.get("content", "")
        try:
            content_hash = safe_hash(content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Save to sync log
        if memory_id:
            await service.save_sync_log(
                peer_id=sender_id,
                memory_id=memory_id,
                content_hash=content_hash,
                status="success"
            )
            processed_count += 1
            
    return {"status": "accepted", "processed": processed_count}
