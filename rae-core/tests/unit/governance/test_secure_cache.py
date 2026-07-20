import asyncio
import pytest
from uuid import uuid4

from rae_core.governance.cache_serialization import (
    pack_cache_value,
    unpack_cache_value,
    CacheDecodeError,
)
from rae_core.governance.secure_cache import SecureCacheEngine


# 1. Serialization Tests

def test_cache_serialization_roundtrip():
    doc = {"query": "test query", "confidence": 0.95, "nested": {"list": [1, 2, 3]}}
    packed = pack_cache_value(doc)
    unpacked = unpack_cache_value(packed)
    assert unpacked == doc


def test_cache_serialization_compression():
    # Create large dict to trigger zstd compression
    large_doc = {"data": "a" * 50_000}
    packed = pack_cache_value(large_doc)
    unpacked = unpack_cache_value(packed)
    assert unpacked == large_doc
    # Verification of compressed envelope format
    import msgpack
    envelope = msgpack.unpackb(packed, raw=False)
    assert envelope["c"] == "zstd"
    assert envelope["n"] == len(msgpack.packb(large_doc, use_bin_type=True, strict_types=True))


def test_cache_serialization_size_limit():
    # Try unpacking an envelope with huge payload size
    import msgpack
    huge_envelope = {
        "v": 3,
        "c": "none",
        "n": 999_999_999,  # Exceeds MAX_DECOMPRESSED_BYTES
        "p": b"some bytes",
    }
    packed = msgpack.packb(huge_envelope, use_bin_type=True)
    with pytest.raises(CacheDecodeError, match="Niepoprawny rozmiar payloadu"):
        unpack_cache_value(packed)


# 2. Redis Outage Fallback Mock Tests

class MockBrokenRedis:
    async def get(self, key):
        raise ConnectionError("Redis is offline!")

    async def setex(self, key, ttl, value):
        raise ConnectionError("Redis is offline!")

    async def set(self, key, value, px=None, nx=None):
        raise ConnectionError("Redis is offline!")

    async def eval(self, script, keys_num, *args):
        raise ConnectionError("Redis is offline!")


@pytest.mark.asyncio
async def test_redis_outage_fallback():
    broken_redis = MockBrokenRedis()
    # Initialize engine with broken redis client
    engine = SecureCacheEngine(redis_client=broken_redis)  # type: ignore

    key = engine.generate_cache_key(
        tenant_id="t1",
        policy_version="1.0.0",
        scope=["working"],
        query="important info",
    )

    doc = {"resolved": True}
    # Set should still complete successfully in L1 process cache
    success = await engine.set(key, doc, ttl=60)
    assert success is True

    # Get should hit L1 and return the doc successfully
    res = await engine.get(key)
    assert res == doc


# 3. Secure Key Generation Tests

def test_secure_key_generation():
    engine = SecureCacheEngine(inventory_generation=5)
    key = engine.generate_cache_key(
        tenant_id="my-tenant-uuid",
        policy_version="v2.5",
        scope=["restricted", "confidential"],
        query="SELECT * FROM secret_table",
    )

    # Key format: rae:kg:v3:{tenant_hash}:{policy_version}:{inventory_generation}:{scope_hash}:{query_hash}
    parts = key.split(":")
    assert len(parts) == 8
    assert parts[0] == "rae"
    assert parts[1] == "kg"
    assert parts[2] == "v3"
    assert parts[4] == "v2.5"
    assert parts[5] == "5"

    # Make sure raw query is NOT leaked in the key
    assert "secret_table" not in key
    assert "SELECT" not in key


# 4. Stampede Lock Tests

class MockWorkingRedis:
    def __init__(self):
        self.storage = {}

    async def set(self, key, value, px=None, nx=None):
        if nx and key in self.storage:
            return None
        self.storage[key] = value
        return True

    async def eval(self, script, keys_num, lock_key, token):
        if self.storage.get(lock_key) == token:
            self.storage.pop(lock_key, None)
            return 1
        return 0


@pytest.mark.asyncio
async def test_stampede_lock_roundtrip():
    redis = MockWorkingRedis()
    engine = SecureCacheEngine(redis_client=redis)  # type: ignore

    lock_key = "lock:test_key"
    token = str(uuid4())

    # Acquire lock should succeed
    acq1 = await engine.acquire_lock(lock_key, token)
    assert acq1 is True

    # Secondary acquisition with same key should fail (NX constraint)
    acq2 = await engine.acquire_lock(lock_key, "different_token")
    assert acq2 is False

    # Releasing lock with different token should fail
    rel1 = await engine.release_lock(lock_key, "different_token")
    assert rel1 is False

    # Releasing lock with correct token should succeed
    rel2 = await engine.release_lock(lock_key, token)
    assert rel2 is True

    # After release, acquisition should succeed again
    acq3 = await engine.acquire_lock(lock_key, token)
    assert acq3 is True
