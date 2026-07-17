from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from rae_core.config import RAESettings
from rae_core.engine import RAEEngine


@pytest.fixture
def mock_storage():
    storage = MagicMock()
    storage.store_memory = AsyncMock(return_value=uuid4())
    storage.save_embedding = AsyncMock()
    storage.get_memory = AsyncMock()
    return storage


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.store_vector = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_provider():
    provider = MagicMock()
    provider.embed_batch = AsyncMock(return_value=[[0.1] * 128])
    provider.embed_text = AsyncMock(return_value=[0.1] * 128)
    provider.generate_all_embeddings = AsyncMock(return_value={"dense": [[0.1] * 128]})
    return provider


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=("response", {}))
    return provider


@pytest.fixture
def mock_cache_provider():
    return MagicMock()


@pytest.fixture
def mock_sync_provider():
    return MagicMock()


@pytest.mark.asyncio
async def test_engine_init_with_cache(
    mock_storage,
    mock_vector_store,
    mock_embedding_provider,
    mock_cache_provider,
):
    settings = RAESettings(cache_enabled=True)
    # HybridSearchEngine is initialized inside RAEEngine if not provided
    engine = RAEEngine(
        memory_storage=mock_storage,
        vector_store=mock_vector_store,
        embedding_provider=mock_embedding_provider,
        settings=settings,
        cache_provider=mock_cache_provider,
    )
    assert engine.search_engine is not None


@pytest.mark.asyncio
async def test_store_memory_basic(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    mock_embedding_provider.embed_text = AsyncMock(return_value=[0.1] * 128)
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)

    await engine.store_memory(tenant_id="t1", agent_id="a1", content="content")

    assert mock_storage.store_memory.called
    assert mock_vector_store.store_vector.called


@pytest.mark.asyncio
async def test_search_memories_with_custom_weights(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)
    mem_id = uuid4()

    # Mock search engine results
    with patch.object(
        engine.search_engine,
        "search",
        AsyncMock(return_value=[(mem_id, 0.8, 0.5, {"strategy": "test"})]),
    ):
        mock_storage.get_memory.return_value = {
            "id": mem_id,
            "content": "test",
            "importance": 0.5,
        }
        # Add mock for new resonance call
        mock_storage.get_neighbors_batch = AsyncMock(return_value=[])

        results = await engine.search_memories(
            "query", "t1", custom_weights={"alpha": 1.0, "beta": 0.0, "gamma": 0.0}
        )

        assert len(results) == 1
        assert "math_score" in results[0]


@pytest.mark.asyncio
async def test_get_status_detailed(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)
    status = engine.get_status()
    assert status["engine"].startswith("RAE-Core")
    assert "vector" in status["search_strategies"]
    assert status["components"]["storage"] == "MagicMock"
