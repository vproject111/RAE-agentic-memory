from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.memory_api.core.contract import (
    CacheContract,
    MemoryContract,
    VectorCollectionContract,
    VectorStoreContract,
)
from rae_adapters.qdrant_adapter import QdrantAdapter
from rae_adapters.redis_adapter import RedisAdapter

# --- Redis Adapter Tests ---


@pytest.mark.asyncio
async def test_redis_validation_success():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    # Mock set/get
    mock_redis.set.return_value = True
    mock_redis.get.return_value = "1"

    contract = MemoryContract(
        version="1.0", entities=[], cache=CacheContract(required_namespaces=["rae:"])
    )

    adapter = RedisAdapter(mock_redis)
    result = await adapter.validate(contract)

    assert result.valid is True
    mock_redis.ping.assert_called_once()
    mock_redis.set.assert_called()
    mock_redis.get.assert_called()


@pytest.mark.asyncio
async def test_redis_validation_connection_fail():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = False  # Ping fail

    contract = MemoryContract(
        version="1.0", entities=[], cache=CacheContract(required_namespaces=["rae:"])
    )

    adapter = RedisAdapter(mock_redis)
    result = await adapter.validate(contract)

    assert result.valid is False
    assert result.violations[0].issue_type == "CONNECTION_FAILED"


@pytest.mark.asyncio
async def test_redis_validation_write_fail():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.set.return_value = True
    mock_redis.get.return_value = "0"  # Incorrect value

    contract = MemoryContract(
        version="1.0", entities=[], cache=CacheContract(required_namespaces=["rae:"])
    )

    adapter = RedisAdapter(mock_redis)
    result = await adapter.validate(contract)

    assert result.valid is False
    assert result.violations[0].issue_type == "WRITE_FAILED"


@pytest.mark.asyncio
async def test_redis_connect_success():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    adapter = RedisAdapter(mock_redis)
    await adapter.connect()
    mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_redis_connect_fail():
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = False
    adapter = RedisAdapter(mock_redis)
    with pytest.raises(ConnectionError, match="Redis server did not respond to PING."):
        await adapter.connect()
    mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_redis_report_success():
    mock_redis = AsyncMock()
    mock_redis.info.return_value = {
        "redis_version": "6.0.0",
        "uptime_in_seconds": "1000",
        "connected_clients": "5",
        "used_memory_human": "1M",
        "rdb_bgsave_in_progress": "0",
        "aof_rewrite_in_progress": "0",
    }
    adapter = RedisAdapter(mock_redis)
    report = await adapter.report()
    assert report["status"] == "connected"
    assert report["version"] == "6.0.0"
    assert report["persistence_enabled"] == "no"
    mock_redis.info.assert_called_once()


@pytest.mark.asyncio
async def test_redis_report_fail():
    mock_redis = AsyncMock()
    mock_redis.info.side_effect = Exception("Redis error")
    adapter = RedisAdapter(mock_redis)
    report = await adapter.report()
    assert report["status"] == "error"
    assert "Redis error" in report["details"]
    mock_redis.info.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_connect_success():
    mock_qdrant = AsyncMock()
    collections_resp = MagicMock()
    collections_resp.collections = []
    mock_qdrant.get_collections.return_value = collections_resp
    adapter = QdrantAdapter(mock_qdrant)
    await adapter.connect()
    mock_qdrant.get_collections.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_connect_fail():
    mock_qdrant = AsyncMock()
    mock_qdrant.get_collections.side_effect = Exception("Qdrant connection error")
    adapter = QdrantAdapter(mock_qdrant)
    with pytest.raises(Exception, match="Qdrant connection error"):
        await adapter.connect()
    mock_qdrant.get_collections.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_report_success():
    mock_qdrant = AsyncMock()
    cluster_info = MagicMock()
    cluster_info.status.value = "green"
    cluster_info.peers_bootstrap = ["peer1"]
    cluster_info.peers_web = ["peer2"]
    mock_qdrant.cluster_info.return_value = cluster_info

    collections_resp = MagicMock()
    col_mock1 = MagicMock()
    col_mock1.name = "memories"
    col_mock2 = MagicMock()
    col_mock2.name = "users"
    collections_resp.collections = [col_mock1, col_mock2]
    mock_qdrant.get_collections.return_value = collections_resp

    adapter = QdrantAdapter(mock_qdrant)
    report = await adapter.report()

    assert report["status"] == "connected"
    assert report["cluster_status"] == "green"
    assert report["peer_count"] == 2
    assert "memories" in report["collections"]
    assert "users" in report["collections"]
    mock_qdrant.cluster_info.assert_called_once()
    mock_qdrant.get_collections.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_report_fail():
    mock_qdrant = AsyncMock()
    mock_qdrant.cluster_info.side_effect = Exception("Qdrant report error")
    adapter = QdrantAdapter(mock_qdrant)
    report = await adapter.report()
    assert report["status"] == "error"
    assert "Qdrant report error" in report["details"]
    mock_qdrant.cluster_info.assert_called_once()


@pytest.mark.asyncio
async def test_qdrant_validation_success():
    mock_qdrant = AsyncMock()

    # Mock collections list
    col_mock = MagicMock()
    col_mock.name = "memories"

    collections_resp = MagicMock()
    collections_resp.collections = [col_mock]
    mock_qdrant.get_collections.return_value = collections_resp

    # Mock collection config
    col_info = MagicMock()
    # config.params.vectors can be dict or object
    # Let's mock single vector object style for simplicity or what adapter expects
    vector_params = MagicMock()
    vector_params.size = 384
    vector_params.distance = "Cosine"

    col_info.config.params.vectors = vector_params

    mock_qdrant.get_collection.return_value = col_info

    contract = MemoryContract(
        version="1.0",
        entities=[],
        vector_store=VectorStoreContract(
            collections=[
                VectorCollectionContract(
                    name="memories", vector_size=384, distance_metric="Cosine"
                )
            ]
        ),
    )

    adapter = QdrantAdapter(mock_qdrant)
    result = await adapter.validate(contract)

    assert result.valid is True


@pytest.mark.asyncio
async def test_qdrant_validation_missing_collection():
    mock_qdrant = AsyncMock()
    collections_resp = MagicMock()
    collections_resp.collections = []  # Empty
    mock_qdrant.get_collections.return_value = collections_resp

    contract = MemoryContract(
        version="1.0",
        entities=[],
        vector_store=VectorStoreContract(
            collections=[VectorCollectionContract(name="memories", vector_size=384)]
        ),
    )

    adapter = QdrantAdapter(mock_qdrant)
    result = await adapter.validate(contract)

    assert result.valid is False
    assert result.violations[0].issue_type == "MISSING_COLLECTION"


@pytest.mark.asyncio
async def test_qdrant_validation_dimension_mismatch():
    mock_qdrant = AsyncMock()

    col_mock = MagicMock()
    col_mock.name = "memories"
    collections_resp = MagicMock()
    collections_resp.collections = [col_mock]
    mock_qdrant.get_collections.return_value = collections_resp

    # Mock collection with wrong size
    col_info = MagicMock()
    vector_params = MagicMock()
    vector_params.size = 768  # Wrong size
    vector_params.distance = "Cosine"
    col_info.config.params.vectors = vector_params
    mock_qdrant.get_collection.return_value = col_info

    contract = MemoryContract(
        version="1.0",
        entities=[],
        vector_store=VectorStoreContract(
            collections=[VectorCollectionContract(name="memories", vector_size=384)]
        ),
    )

    adapter = QdrantAdapter(mock_qdrant)
    result = await adapter.validate(contract)

    assert result.valid is False
    assert result.violations[0].issue_type == "DIMENSION_MISMATCH"
