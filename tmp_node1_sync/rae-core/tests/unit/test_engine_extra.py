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
async def test_engine_init_with_cache_and_sync(
    mock_storage,
    mock_vector_store,
    mock_embedding_provider,
    mock_cache_provider,
    mock_sync_provider,
):
    settings = RAESettings(sync_enabled=True, cache_enabled=True)
    engine = RAEEngine(
        memory_storage=mock_storage,
        vector_store=mock_vector_store,
        embedding_provider=mock_embedding_provider,
        settings=settings,
        cache_provider=mock_cache_provider,
        sync_provider=mock_sync_provider,
    )
    assert engine.search_engine.cache is not None
    assert engine.sync_protocol is not None


@pytest.mark.asyncio
async def test_store_memory_with_embedding_manager(mock_storage, mock_vector_store):
    # Mock embedding provider with generate_all_embeddings
    mock_provider = MagicMock()
    mock_provider.generate_all_embeddings = AsyncMock(
        return_value={"default": [[0.1] * 128], "other": [[0.2] * 128]}
    )

    engine = RAEEngine(mock_storage, mock_vector_store, mock_provider)
    await engine.store_memory("t1", "a1", "content")

    assert mock_storage.save_embedding.call_count == 2
    mock_provider.generate_all_embeddings.assert_called_once()


@pytest.mark.asyncio
async def test_store_memory_with_embedding_fallback(mock_storage, mock_vector_store):
    # Mock embedding provider without 'default' key
    mock_provider = MagicMock()
    mock_provider.generate_all_embeddings = AsyncMock(
        return_value={"custom_model": [[0.3] * 128]}
    )

    engine = RAEEngine(mock_storage, mock_vector_store, mock_provider)
    await engine.store_memory("t1", "a1", "content")

    assert mock_storage.store_memory.called
    # Should have used the first available embedding
    call_args = mock_storage.store_memory.call_args
    assert call_args.kwargs["embedding"] == [0.3] * 128


@pytest.mark.asyncio
async def test_store_memory_with_ttl(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    """Test storing memory with TTL to cover expiration logic."""
    # Ensure generate_all_embeddings works if detected
    mock_embedding_provider.generate_all_embeddings = AsyncMock(
        return_value={"default": [[0.1] * 128]}
    )

    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)
    mock_storage.store_memory.return_value = uuid4()

    await engine.store_memory("t1", "a1", "content", ttl=60)

    assert mock_storage.store_memory.called
    call_args = mock_storage.store_memory.call_args
    assert call_args.kwargs["expires_at"] is not None

    # Check if expires_at is roughly 60s from now
    from datetime import datetime, timezone

    expires_at = call_args.kwargs["expires_at"]
    now = datetime.now(timezone.utc)
    diff = (expires_at - now).total_seconds()
    assert 58 < diff < 62


@pytest.mark.asyncio
async def test_search_memories_with_reranker(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)

    # Mock search engine results
    mem_id = uuid4()

    # We must mock the methods on the actual search_engine object instance
    with (
        patch.object(
            engine.search_engine, "search", AsyncMock(return_value=[(mem_id, 0.8)])
        ),
        patch.object(
            engine.search_engine, "rerank", AsyncMock(return_value=[(mem_id, 0.9)])
        ) as mock_rerank,
    ):
        mock_storage.get_memory.return_value = {"id": mem_id, "content": "test"}

        results = await engine.search_memories(
            "query", "t1", agent_id="a1", layer="episodic", use_reranker=True
        )

        assert len(results) == 1
        assert results[0]["search_score"] == 0.9
        assert mock_rerank.called


@pytest.mark.asyncio
async def test_generate_reflection(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)
    with patch.object(
        engine.reflection_engine,
        "generate_reflection",
        AsyncMock(return_value={"status": "ok"}),
    ):
        result = await engine.generate_reflection([uuid4()], "t1", "a1")
        assert result == {"status": "ok"}


@pytest.mark.asyncio
async def test_sync_memories(
    mock_storage, mock_vector_store, mock_embedding_provider, mock_sync_provider
):
    settings = RAESettings(sync_enabled=True)
    engine = RAEEngine(
        mock_storage,
        mock_vector_store,
        mock_embedding_provider,
        settings=settings,
        sync_provider=mock_sync_provider,
    )

    # Mock sync response
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.synced_memory_ids = [uuid4()]
    mock_response.conflicts = []
    mock_response.error_message = None

    if engine.sync_protocol:
        with patch.object(
            engine.sync_protocol, "sync", AsyncMock(return_value=mock_response)
        ):
            result = await engine.sync_memories("t1", "a1")
            assert result is not None
            assert result["success"] is True
            assert result["synced_count"] == 1


@pytest.mark.asyncio
async def test_sync_memories_disabled(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)
    result = await engine.sync_memories("t1", "a1")
    assert result is None


@pytest.mark.asyncio
async def test_generate_text_no_orchestrator(
    mock_storage, mock_vector_store, mock_embedding_provider
):
    engine = RAEEngine(mock_storage, mock_vector_store, mock_embedding_provider)
    result = await engine.generate_text("prompt")
    assert result is None
