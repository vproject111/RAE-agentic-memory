import base64
import hashlib
import json
import secrets
import socket
import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)


from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


def _derive_relay_key(secret_key: str) -> bytes:
    """Derive a 256-bit key from secret_key using HKDF with info block."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b"rae-mesh-relay"
    )
    return hkdf.derive(secret_key.encode("utf-8"))


def encrypt_payload(payload: Dict[str, Any], secret_key: str) -> str:
    """Encrypt payload using AES-256-GCM."""
    key = _derive_relay_key(secret_key)
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    plaintext = json.dumps(payload).encode("utf-8")
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    # Prepend nonce to ciphertext and base64-encode
    return base64.b64encode(nonce + ciphertext).decode("utf-8")


def decrypt_payload(encrypted_b64: str, secret_key: str) -> Dict[str, Any]:
    """Decrypt payload using AES-256-GCM."""
    key = _derive_relay_key(secret_key)
    aesgcm = AESGCM(key)
    raw_data = base64.b64decode(encrypted_b64.encode("utf-8"))
    if len(raw_data) < 12:
        raise ValueError("Encrypted payload too short")
    nonce = raw_data[:12]
    ciphertext = raw_data[12:]
    decrypted_bytes = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(decrypted_bytes.decode("utf-8"))


class MatrixRelay:
    """
    Relay client using Matrix CS-API (pure REST HTTP) wrapped in AES-256-GCM.
    """

    def __init__(self, homeserver_url: str, access_token: str, room_id: str, secret_key: str):
        self.homeserver_url = homeserver_url.rstrip("/")
        self.access_token = access_token
        self.room_id = room_id
        self.secret_key = secret_key
        self.next_batch: Optional[str] = None

    async def publish(self, payload: Dict[str, Any]) -> bool:
        """Publish encrypted payload to Matrix room."""
        encrypted_text = encrypt_payload(payload, self.secret_key)
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{self.homeserver_url}/_matrix/client/v3/rooms/{self.room_id}/send/m.room.message"
        body = {
            "msgtype": "m.text",
            "body": encrypted_text,
            "rae_encrypted": True
        }
        
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=body, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    logger.info("Successfully published message to Matrix relay.")
                    return True
                else:
                    logger.error(f"Failed to publish to Matrix: {resp.text}")
                    return False
            except Exception as e:
                logger.error(f"Matrix publish connection error: {e}")
                return False

    async def consume(self) -> List[Dict[str, Any]]:
        """Poll and consume new encrypted events from Matrix room."""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{self.homeserver_url}/_matrix/client/v3/sync"
        params = {"timeout": 1000}
        if self.next_batch:
            params["since"] = self.next_batch

        decrypted_payloads = []
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(url, headers=headers, params=params, timeout=15.0)
                if resp.status_code != 200:
                    logger.error(f"Matrix sync failed: {resp.text}")
                    return []
                
                data = resp.json()
                self.next_batch = data.get("next_batch")
                
                rooms = data.get("rooms", {}).get("join", {})
                if self.room_id in rooms:
                    events = rooms[self.room_id].get("timeline", {}).get("events", [])
                    for ev in events:
                        if ev.get("type") == "m.room.message":
                            content = ev.get("content", {})
                            if content.get("rae_encrypted"):
                                body = content.get("body", "")
                                try:
                                    decrypted = decrypt_payload(body, self.secret_key)
                                    decrypted_payloads.append(decrypted)
                                except Exception as dec_err:
                                    logger.warning(f"Failed to decrypt Matrix message: {dec_err}")
            except Exception as e:
                logger.error(f"Matrix sync error: {e}")
                
        return decrypted_payloads


class NATSRelay:
    """
    Relay client using simple NATS protocol TCP sockets wrapped in AES-256-GCM.
    """

    def __init__(self, nats_host: str, nats_port: int, subject: str, secret_key: str):
        self.nats_host = nats_host
        self.nats_port = nats_port
        self.subject = subject
        self.secret_key = secret_key

    async def publish(self, payload: Dict[str, Any]) -> bool:
        """Connect to NATS and publish the encrypted payload."""
        encrypted_text = encrypt_payload(payload, self.secret_key)
        payload_bytes = encrypted_text.encode("utf-8")
        
        # NATS Protocol message: PUB <subject> <reply-to (optional)> <size>\r\n<payload>\r\n
        pub_cmd = f"PUB {self.subject} {len(payload_bytes)}\r\n".encode("utf-8")
        msg = pub_cmd + payload_bytes + b"\r\n"
        
        try:
            reader, writer = await asyncio.open_connection(self.nats_host, self.nats_port)
            # Read first line (INFO block)
            await reader.readline()
            
            # Send payload
            writer.write(msg)
            await writer.drain()
            
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            logger.error(f"Failed to publish to NATS socket: {e}")
            return False

    async def consume_one(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Connect, subscribe, wait for a message, decrypt and return it."""
        sid = "1"
        sub_cmd = f"SUB {self.subject} {sid}\r\n".encode("utf-8")
        
        try:
            reader, writer = await asyncio.open_connection(self.nats_host, self.nats_port)
            # Read INFO block
            await reader.readline()
            
            # Subscribe
            writer.write(sub_cmd)
            await writer.drain()
            
            # Wait for data: NATS MSG subject sid size\r\npayload\r\n
            try:
                line = await asyncio.wait_for(reader.readline(), timeout=timeout)
                if line.startswith(b"MSG"):
                    parts = line.split(b" ")
                    size = int(parts[-1].strip())
                    
                    data = await reader.readexactly(size)
                    await reader.readline()  # consume trailing \r\n
                    
                    writer.close()
                    await writer.wait_closed()
                    
                    decrypted = decrypt_payload(data.decode("utf-8"), self.secret_key)
                    return decrypted
            except asyncio.TimeoutError:
                pass
                
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            logger.error(f"NATS consumer socket error: {e}")
            
        return None
