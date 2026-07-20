"""Service for managing Mesh Federation (Peer-to-Peer Trust)."""

import base64
import hashlib
import json
import secrets
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
import structlog
from pydantic import BaseModel
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

logger = structlog.get_logger(__name__)


class PeerInfo(BaseModel):
    peer_id: str
    name: str
    url: str
    token: str  # The token we use to call them
    created_at: float
    status: str = "active"
    consent_grant_id: Optional[str] = None
    transport_type: str = "http"


class MeshInvite(BaseModel):
    code: str
    expires_at: float
    host_url: str
    tenant_id: str


from uuid import UUID, uuid4

def parse_uuid(val: Any) -> UUID:
    if isinstance(val, UUID):
        return val
    if isinstance(val, str) and val:
        try:
            return UUID(val)
        except ValueError:
            pass
    return uuid4()

def parse_datetime(val: Any) -> Optional[datetime]:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val:
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            pass
    return None


class MeshService:
    """
    Manages the 'Trust Handshake' protocol.
    Stores trusted peers and active invite codes.
    """

    def __init__(self, pool: Any = None, redis_client: Any = None, secret_key: str = "mesh-secret-change-me"):
        self.pool = pool
        self.redis_client = redis_client
        self.secret_key = secret_key
        # In-memory fallback storage for peers and active invites
        self._peers: Dict[str, PeerInfo] = {}
        self._fallback_pubkeys: Dict[str, str] = {}
        self._active_invites: Dict[str, dict] = {}
        self._used_jtis: Dict[str, float] = {}
        self._key_cache: Dict[str, tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]] = {}
        self._lock = threading.RLock()

    def _get_encryption_key(self) -> bytes:
        """Derive a 256-bit AES key from secret_key."""
        return hashlib.sha256(self.secret_key.encode("utf-8")).digest()

    def encrypt_auth_data(self, token: str, public_key: Optional[str]) -> str:
        """Encrypts token and public_key using AES-GCM with a key derived from SECRET_KEY."""
        data = {
            "token": token,
            "public_key": public_key
        }
        json_data = json.dumps(data)
        
        key = self._get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = secrets.token_bytes(12)
        ciphertext = aesgcm.encrypt(nonce, json_data.encode("utf-8"), None)
        # Prepend nonce to ciphertext and base64-encode
        return base64.b64encode(nonce + ciphertext).decode("utf-8")

    def decrypt_auth_data(self, encrypted_b64: str) -> tuple[str, Optional[str]]:
        """Decrypts and returns (token, public_key)."""
        key = self._get_encryption_key()
        aesgcm = AESGCM(key)
        raw_data = base64.b64decode(encrypted_b64.encode("utf-8"))
        if len(raw_data) < 12:
            raise ValueError("Ciphertext too short")
        nonce = raw_data[:12]
        ciphertext = raw_data[12:]
        decrypted_json = aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
        data = json.loads(decrypted_json)
        return data.get("token", ""), data.get("public_key")

    def derive_key_pair(self, peer_id: str) -> tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Derive an Ed25519 key pair deterministically from SECRET_KEY using HKDF, a salt, and caching."""
        with self._lock:
            if peer_id in self._key_cache:
                return self._key_cache[peer_id]
            hkdf = HKDF(
                algorithm=hashes.SHA512(),
                length=32,
                salt=b"rae-mesh-key-derivation-salt",
                info=peer_id.encode("utf-8")
            )
            seed = hkdf.derive(self.secret_key.encode("utf-8"))
            private_key = ed25519.Ed25519PrivateKey.from_private_bytes(seed)
            result = (private_key, private_key.public_key())
            self._key_cache[peer_id] = result
            return result

    def generate_challenge(self, my_peer_id: str) -> dict[str, Any]:
        """Generate a challenge and host public key, signed by host's private key."""
        nonce = secrets.token_hex(16)
        timestamp = int(time.time())
        challenge = {
            "nonce": nonce,
            "timestamp": timestamp
        }
        private_key, public_key = self.derive_key_pair(my_peer_id)
        challenge_bytes = json.dumps(challenge, sort_keys=True).encode("utf-8")
        signature = private_key.sign(challenge_bytes)
        
        return {
            "challenge": challenge,
            "host_public_key": public_key.public_bytes_raw().hex(),
            "challenge_signature": signature.hex()
        }

    def verify_challenge_signature(self, public_key_hex: str, challenge: dict[str, Any], signature_hex: str) -> None:
        """Verify that the challenge has a valid signature and is fresh (within 5 minutes)."""
        timestamp = challenge.get("timestamp", 0)
        if abs(time.time() - timestamp) > 300:
            raise ValueError("Challenge has expired or is in the future")
            
        try:
            pub_key = ed25519.Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
            challenge_bytes = json.dumps(challenge, sort_keys=True).encode("utf-8")
            pub_key.verify(bytes.fromhex(signature_hex), challenge_bytes)
        except Exception as e:
            raise ValueError(f"Invalid challenge signature: {e}")

    def sign_challenge(self, challenge: dict[str, Any], my_peer_id: str) -> str:
        """Sign a challenge using own private key."""
        private_key, _ = self.derive_key_pair(my_peer_id)
        challenge_bytes = json.dumps(challenge, sort_keys=True).encode("utf-8")
        return private_key.sign(challenge_bytes).hex()

    def create_invite(
        self, host_url: str, tenant_id: str, duration_minutes: int = 5
    ) -> str:
        """Generate a signed invite code."""
        nonce = secrets.token_hex(8)
        now = int(time.time())
        exp = now + duration_minutes * 60
        payload = {
            "iss": "rae-mesh-host",
            "aud": "rae-mesh-peers",
            "iat": now,
            "exp": exp,
            "host": host_url,
            "tenant": tenant_id,
            "nonce": nonce,
        }

        # Sign JWT with typ header
        code = jwt.encode(
            payload,
            self.secret_key,
            algorithm="HS256",
            headers={"typ": "mesh-invite-v1"}
        )

        # Store for validation (nonce check)
        self._active_invites[nonce] = {
            "tenant": tenant_id,
            "expires": exp,
        }

        logger.info("mesh_invite_created", nonce=nonce, tenant=tenant_id)
        return code

    def validate_invite(self, code: str) -> dict[str, Any]:
        """Verify an invite code is valid and active."""
        try:
            # 1. Enforce signature algorithm check by getting the unverified header first
            header = jwt.get_unverified_header(code)
            alg = header.get("alg")
            if alg != "HS256":
                raise ValueError(f"Algorithm {alg} is not allowed (only HS256)")

            if header.get("typ") != "mesh-invite-v1":
                raise ValueError("Token typ must be 'mesh-invite-v1'")

            # 2. Decode and verify signature & claims
            payload = jwt.decode(
                code,
                self.secret_key,
                audience="rae-mesh-peers",
                algorithms=["HS256"],
                options={
                    "require": ["exp", "iat", "aud", "iss"],
                    "verify_signature": True,
                }
            )

            nonce = payload.get("nonce")
            if nonce not in self._active_invites:
                raise ValueError("Invalid or expired invite (nonce not found)")

            stored = self._active_invites[nonce]
            if time.time() > stored["expires"]:
                if nonce in self._active_invites:
                    del self._active_invites[nonce]
                raise ValueError("Invite expired")

            return payload

        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid token: {e}")

    async def register_peer(
        self, 
        peer_id: str, 
        name: str, 
        url: str, 
        token: str, 
        public_key: Optional[str] = None, 
        consent_grant_id: Optional[str] = None,
        status: str = "active",
        transport_type: str = "http"
    ) -> None:
        """Register a trusted peer after successful handshake."""
        encrypted_token = self.encrypt_auth_data(token, public_key)
        
        if self.pool is not None:
            try:
                await self.pool.execute(
                    """
                    INSERT INTO mesh_peers (
                        peer_id, name, transport_type, endpoint_url, encrypted_auth_token, consent_grant_id, status, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ON CONFLICT (peer_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        transport_type = EXCLUDED.transport_type,
                        endpoint_url = EXCLUDED.endpoint_url,
                        encrypted_auth_token = EXCLUDED.encrypted_auth_token,
                        consent_grant_id = EXCLUDED.consent_grant_id,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    """,
                    peer_id,
                    name,
                    transport_type,
                    url,
                    encrypted_token,
                    consent_grant_id,
                    status
                )
            except Exception as e:
                logger.error("failed_to_register_peer_in_db", error=str(e), peer_id=peer_id)
                raise
        else:
            self._peers[peer_id] = PeerInfo(
                peer_id=peer_id,
                name=name,
                url=url,
                token=token,
                created_at=time.time(),
                status=status,
                consent_grant_id=consent_grant_id,
                transport_type=transport_type
            )
            self._fallback_pubkeys[peer_id] = public_key

        logger.info("mesh_peer_registered", peer_id=peer_id, name=name)

    async def get_peer(self, peer_id: str) -> Optional[PeerInfo]:
        if self.pool is not None:
            try:
                row = await self.pool.fetchrow(
                    """
                    SELECT peer_id, name, transport_type, endpoint_url, encrypted_auth_token, consent_grant_id, status, created_at
                    FROM mesh_peers
                    WHERE peer_id = $1
                    """,
                    peer_id
                )
                if not row:
                    return None
                
                encrypted_token = row["encrypted_auth_token"]
                token = ""
                if encrypted_token:
                    try:
                        token, _ = self.decrypt_auth_data(encrypted_token)
                    except Exception as e:
                        logger.error("token_decryption_failed", error=str(e), peer_id=peer_id)
                
                return PeerInfo(
                    peer_id=row["peer_id"],
                    name=row["name"],
                    url=row["endpoint_url"],
                    token=token,
                    created_at=row["created_at"].timestamp(),
                    status=row["status"],
                    consent_grant_id=row["consent_grant_id"],
                    transport_type=row.get("transport_type", "http")
                )
            except Exception as e:
                logger.error("failed_to_get_peer_from_db", error=str(e), peer_id=peer_id)
                return None
        else:
            return self._peers.get(peer_id)

    async def get_peer_public_key(self, peer_id: str) -> Optional[str]:
        if self.pool is not None:
            try:
                val = await self.pool.fetchval(
                    "SELECT encrypted_auth_token FROM mesh_peers WHERE peer_id = $1",
                    peer_id
                )
                if val:
                    _, public_key = self.decrypt_auth_data(val)
                    return public_key
            except Exception:
                pass
            return None
        else:
            return self._fallback_pubkeys.get(peer_id)

    async def list_peers(self) -> List[PeerInfo]:
        if self.pool is not None:
            try:
                rows = await self.pool.fetch(
                    """
                    SELECT peer_id, name, transport_type, endpoint_url, encrypted_auth_token, consent_grant_id, status, created_at
                    FROM mesh_peers
                    """
                )
                peers = []
                for row in rows:
                    encrypted_token = row["encrypted_auth_token"]
                    token = ""
                    if encrypted_token:
                        try:
                            token, _ = self.decrypt_auth_data(encrypted_token)
                        except Exception:
                            pass
                    peers.append(
                        PeerInfo(
                            peer_id=row["peer_id"],
                            name=row["name"],
                            url=row["endpoint_url"],
                            token=token,
                            created_at=row["created_at"].timestamp(),
                            status=row["status"],
                            consent_grant_id=row["consent_grant_id"],
                            transport_type=row.get("transport_type", "http")
                        )
                    )
                return peers
            except Exception as e:
                logger.error("failed_to_list_peers_from_db", error=str(e))
                return []
        else:
            return list(self._peers.values())

    async def revoke_peer(self, peer_id: str) -> None:
        if self.pool is not None:
            try:
                await self.pool.execute(
                    "DELETE FROM mesh_peers WHERE peer_id = $1",
                    peer_id
                )
            except Exception as e:
                logger.error("failed_to_revoke_peer_in_db", error=str(e), peer_id=peer_id)
                raise
        else:
            if peer_id in self._peers:
                del self._peers[peer_id]
                if peer_id in self._fallback_pubkeys:
                    del self._fallback_pubkeys[peer_id]
        logger.info("mesh_peer_revoked", peer_id=peer_id)

    async def save_sync_log(self, peer_id: str, memory_id: str, content_hash: str, status: str) -> None:
        if self.pool is not None:
            try:
                from uuid import UUID
                await self.pool.execute(
                    """
                    INSERT INTO mesh_sync_log (peer_id, memory_id, content_hash, status, synced_at)
                    VALUES ($1, $2, $3, $4, NOW())
                    ON CONFLICT (peer_id, memory_id, status) 
                    DO UPDATE SET content_hash = EXCLUDED.content_hash, synced_at = NOW()
                    """,
                    peer_id,
                    UUID(memory_id) if isinstance(memory_id, str) else memory_id,
                    content_hash,
                    status
                )
            except Exception as e:
                logger.error("failed_to_save_sync_log", error=str(e), peer_id=peer_id, memory_id=str(memory_id))

    def generate_consent_token(self, sender_id: str, receiver_id: str, consent_grant_id: str) -> str:
        """Generate a short-lived (<= 5 minutes) consent token containing a jti claim."""
        now = int(time.time())
        payload = {
            "iss": sender_id,
            "aud": receiver_id,
            "iat": now,
            "exp": now + 300,  # 5 minutes
            "consent_grant_id": consent_grant_id,
            "jti": secrets.token_hex(16),
            "typ": "mesh-consent-v1",
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    async def verify_consent_token(self, token: str, expected_sender: str, expected_receiver: str) -> dict[str, Any]:
        """Verify the consent token is active, valid, has TTL <= 5 minutes, and prevents replay attacks using jti."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                audience=expected_receiver,
                algorithms=["HS256"],
                options={
                    "require": ["exp", "iat", "aud", "iss"],
                    "verify_signature": True,
                }
            )
            if payload.get("typ") != "mesh-consent-v1":
                raise ValueError("Invalid consent token typ")
                
            iat = payload.get("iat", 0)
            exp = payload.get("exp", 0)
            if time.time() > exp:
                raise ValueError("Consent token has expired")
            if exp - iat > 300:
                raise ValueError("Consent token TTL exceeds 5 minutes limit")
                
            # Timing attack prevention using compare_digest
            if not secrets.compare_digest(payload.get("iss", ""), expected_sender):
                raise ValueError("Consent token issuer does not match sender")
            if not secrets.compare_digest(payload.get("aud", ""), expected_receiver):
                raise ValueError("Consent token audience does not match receiver")
                
            jti = payload.get("jti")
            if not jti:
                raise ValueError("Consent token is missing jti claim")
                
            # Track used nonces to prevent replay attacks
            jti_key = f"rae:mesh:jti:{jti}"
            if self.redis_client is not None:
                is_new = await self.redis_client.set(jti_key, "1", ex=300, nx=True)
                if not is_new:
                    raise ValueError("Replay attack detected: token has already been used")
            else:
                with self._lock:
                    now = time.time()
                    # Clean up expired JTIs
                    self._used_jtis = {k: v for k, v in self._used_jtis.items() if v > now}
                    if jti in self._used_jtis:
                        raise ValueError("Replay attack detected: token has already been used")
                    self._used_jtis[jti] = float(exp)
                
            return payload
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid consent token: {e}")

    async def prepare_sync_payload(self, peer_id: str, memories: List[Dict[str, Any]], sender_id: str = "rae-host") -> Dict[str, Any]:
        """
        Filter memories by classification before transmission.
        Embeds a short-lived consent token if a valid ConsentGrant exists.
        """
        peer = await self.get_peer(peer_id)
        if not peer:
            raise ValueError(f"Peer {peer_id} is not registered")
            
        consent_grant_id = peer.consent_grant_id
        filtered_memories = []
        
        for m in memories:
            info_class = str(m.get("info_class", "")).lower()
            if info_class == "restricted":
                if consent_grant_id:
                    filtered_memories.append(m)
                else:
                    logger.debug("filtering_restricted_memory_no_consent", memory_id=m.get("id"))
            else:
                filtered_memories.append(m)
                
        consent_token = None
        if consent_grant_id and filtered_memories:
            consent_token = self.generate_consent_token(
                sender_id=sender_id,
                receiver_id=peer_id,
                consent_grant_id=consent_grant_id
            )
            
        return {
            "sender_id": sender_id,
            "receiver_id": peer_id,
            "consent_token": consent_token,
            "memories": filtered_memories
        }

    async def push_memories_to_peer(self, peer_id: str) -> int:
        """Package unsynced memories, compute SHA-256 hashes, sign data, and send payloads to the peer sync endpoint."""
        import httpx
        from apps.memory_api.config import settings
        from urllib.parse import urlparse
        
        peer = await self.get_peer(peer_id)
        if not peer:
            raise ValueError(f"Peer {peer_id} is not registered")
            
        memories = []
        if self.pool is not None:
            try:
                async with self.pool.acquire() as conn:
                    # Get the watermark (created_at of the last successfully synced memory)
                    watermark_row = await conn.fetchrow(
                        """
                        SELECT MAX(m.created_at) as max_created
                        FROM mesh_sync_log l
                        JOIN memories m ON l.memory_id = m.id
                        WHERE l.peer_id = $1 AND l.status = 'success'
                        """,
                        peer_id
                    )
                    watermark = watermark_row["max_created"] if watermark_row and watermark_row["max_created"] else datetime.fromtimestamp(0, tz=timezone.utc)

                    rows = await conn.fetch(
                        """
                        SELECT id, content, layer, tenant_id, agent_id, tags, metadata, importance, created_at, last_accessed_at, expires_at, project, session_id, memory_type, source, info_class
                        FROM memories
                        WHERE created_at >= $1
                          AND id NOT IN (
                              SELECT memory_id FROM mesh_sync_log WHERE peer_id = $2 AND status = 'success'
                          )
                        ORDER BY created_at ASC
                        """,
                        watermark,
                        peer_id
                    )
                    
                    for row in rows:
                        memories.append({
                            "id": str(parse_uuid(row["id"])),
                            "content": row["content"],
                            "layer": row["layer"],
                            "tenant_id": row["tenant_id"],
                            "agent_id": row["agent_id"],
                            "tags": list(row["tags"]) if row["tags"] else [],
                            "metadata": json.loads(row["metadata"]) if isinstance(row["metadata"], str) else (row["metadata"] or {}),
                            "importance": float(row["importance"]) if row["importance"] is not None else 0.5,
                            "created_at": parse_datetime(row["created_at"]).isoformat() if parse_datetime(row["created_at"]) else None,
                            "last_accessed_at": parse_datetime(row["last_accessed_at"]).isoformat() if parse_datetime(row["last_accessed_at"]) else None,
                            "expires_at": parse_datetime(row["expires_at"]).isoformat() if parse_datetime(row["expires_at"]) else None,
                            "project": row["project"],
                            "session_id": row["session_id"],
                            "memory_type": row["memory_type"],
                            "source": row["source"],
                            "info_class": row["info_class"] if "info_class" in row else "internal"
                        })
            except Exception as e:
                logger.error("failed_to_fetch_unsynced_memories", error=str(e), peer_id=peer_id)
                return 0
        else:
            # Fallback (in-memory) mode
            return 0
            
        if not memories:
            return 0
            
        # Filter memories using prepare_sync_payload
        payload = await self.prepare_sync_payload(peer_id, memories, sender_id=settings.RAE_PEER_ID)
        
        if not payload.get("memories"):
            return 0
            
        # Compute SHA-256 hashes of memories
        memories_bytes = json.dumps(payload["memories"], sort_keys=True).encode("utf-8")
        payload_hash = hashlib.sha256(memories_bytes).hexdigest()
        
        # Sign the hash using Ed25519 sender private key
        private_key, _ = self.derive_key_pair(settings.RAE_PEER_ID)
        signature = private_key.sign(memories_bytes).hex()
        
        payload["payload_hash"] = payload_hash
        payload["signature"] = signature
        
        # Determine transport routing
        success = False
        transport = peer.transport_type.lower() if peer.transport_type else "http"
        
        # 1. Tor Hidden Services (starts with .onion or transport == tor)
        if transport == "tor" or ".onion" in peer.url:
            proxy = "socks5h://127.0.0.1:9050"
            async with httpx.AsyncClient(proxy=proxy) as client:
                try:
                    resp = await client.post(
                        f"{peer.url}/v2/mesh/sync/receive",
                        json=payload,
                        headers={"Authorization": f"Bearer {peer.token}"},
                        timeout=30.0
                    )
                    if resp.status_code == 200 and resp.json().get("status") == "accepted":
                        success = True
                except Exception as e:
                    logger.error("tor_sync_failed", error=str(e), url=peer.url)
                    
        # 2. Relay Broker (nats or matrix)
        elif transport in ("nats", "matrix", "relay"):
            from apps.memory_api.services.relay_broker import MatrixRelay, NATSRelay
            if "matrix" in peer.url or transport == "matrix":
                # Matrix relay
                relay = MatrixRelay(
                    homeserver_url=peer.url,
                    access_token=peer.token,
                    room_id="default-room",
                    secret_key=self.secret_key
                )
                success = await relay.publish(payload)
            else:
                # NATS relay
                parsed_url = urlparse(peer.url)
                host = parsed_url.hostname or "127.0.0.1"
                port = parsed_url.port or 4222
                relay = NATSRelay(
                    nats_host=host,
                    nats_port=port,
                    subject="rae.mesh.sync",
                    secret_key=self.secret_key
                )
                success = await relay.publish(payload)
                
        # 3. Direct/Tailscale/VPN
        else:
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.post(
                        f"{peer.url}/v2/mesh/sync/receive",
                        json=payload,
                        headers={"Authorization": f"Bearer {peer.token}"},
                        timeout=30.0
                    )
                    if resp.status_code == 200 and resp.json().get("status") == "accepted":
                        success = True
                except Exception as e:
                    logger.error("direct_sync_failed", error=str(e), url=peer.url)
                    
        if success:
            # Mark successfully synced in database
            for m in payload["memories"]:
                await self.save_sync_log(
                    peer_id=peer_id,
                    memory_id=m["id"],
                    content_hash=hashlib.sha256(m["content"].encode('utf-8')).hexdigest(),
                    status="success"
                )
            return len(payload["memories"])
            
        return 0
