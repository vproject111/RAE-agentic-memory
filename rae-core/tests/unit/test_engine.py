from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from rae_core.config import RAESettings
from rae_core.engine import RAEEngine
from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.llm import ILLMProvider
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.interfaces.vector import IVectorStore


@pytest.fixture
def mock_memory_storage():
    storage = Mock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock()
    storage.get_memory = AsyncMock()
    return storage


@pytest.fixture
def mock_vector_store():
    store = Mock(spec=IVectorStore)
    return store


@pytest.fixture
def mock_embedding_provider():
    provider = Mock(spec=IEmbeddingProvider)
    return provider


@pytest.fixture
def mock_llm_provider():
    provider = Mock(spec=ILLMProvider)
    return provider


@pytest.fixture
def mock_search_engine():
    mock = Mock()
    mock.search = AsyncMock()
    mock.rerank = AsyncMock()
    mock.strategies = {"vector": Mock(), "fulltext": Mock()}
    return mock


@pytest.fixture
def mock_reflection_engine():
    # In RAEEngine, reflection logic might be handled differently now,
    # but we keep the mock for compatibility if needed or until fully refactored.
    with patch(
        "rae_core.engine.RAEEngine.run_reflection_cycle", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def mock_llm_orchestrator():
    # LLM logic is now in ILLMProvider
    with patch("rae_core.interfaces.llm.ILLMProvider") as mock:
        instance = mock.return_value
        instance.generate_text = AsyncMock()
        yield instance


@pytest.fixture
def rae_engine(
    mock_memory_storage,
    mock_vector_store,
    mock_embedding_provider,
    mock_llm_provider,
    mock_search_engine,
    mock_reflection_engine,
    mock_llm_orchestrator,  # Added mock
):
    settings = RAESettings()
    return RAEEngine(
        memory_storage=mock_memory_storage,
        vector_store=mock_vector_store,
        embedding_provider=mock_embedding_provider,
        llm_provider=mock_llm_provider,
        settings=settings,
        search_engine=mock_search_engine,
    )


@pytest.mark.asyncio
async def test_store_memory(
    rae_engine, mock_memory_storage, mock_embedding_provider, mock_vector_store
):
    tenant_id = "test-tenant"
    agent_id = "test-agent"
    content = "test content"
    expected_uuid = uuid4()
    mock_emb = [0.1, 0.2]

    mock_memory_storage.store_memory.return_value = expected_uuid
    mock_embedding_provider.embed_text.return_value = mock_emb

    result = await rae_engine.store_memory(
        tenant_id=tenant_id,
        agent_id=agent_id,
        content=content,
    )

    assert result == expected_uuid
    mock_memory_storage.store_memory.assert_called_once()
    mock_embedding_provider.embed_text.assert_called_once_with(
        content, task_type="search_document"
    )
    mock_vector_store.store_vector.assert_called_once()


@pytest.mark.asyncio
async def test_search_memories(rae_engine, mock_search_engine, mock_memory_storage):
    tenant_id = "test-tenant"
    query = "test query"
    mem_id = uuid4()
    # RAE Engine expects 4-element tuples from search engine: (id, score, importance, audit)
    expected_results = [(mem_id, 0.9, 0.5, {"strategy": "test"})]
    expected_memory = {"id": mem_id, "content": "found", "importance": 0.5}

    mock_search_engine.search.return_value = expected_results
    mock_memory_storage.get_memory = AsyncMock(return_value=expected_memory)

    results = await rae_engine.search_memories(
        query=query,
        tenant_id=tenant_id,
    )

    assert len(results) == 1
    assert results[0]["id"] == mem_id
    assert "math_score" in results[0]
    mock_search_engine.search.assert_called_once()


@pytest.mark.asyncio
async def test_run_reflection_cycle(rae_engine, mock_reflection_engine):
    tenant_id = "test-tenant"
    agent_id = "test-agent"
    expected_summary = {
        "status": "completed",
        "reflections_created": 0,
        "memories_consolidated": 0,
        "tokens_saved": 0,
    }

    # Since we patched run_reflection_cycle on RAEEngine itself in fixture
    rae_engine.run_reflection_cycle.return_value = expected_summary

    result = await rae_engine.run_reflection_cycle(
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    assert result == expected_summary


@pytest.mark.asyncio
async def test_generate_text(rae_engine, mock_llm_orchestrator):
    prompt = "Hello"
    expected_response = "World"

    mock_llm_orchestrator.generate_text.return_value = expected_response
    rae_engine.llm_provider = mock_llm_orchestrator

    result = await rae_engine.generate_text(prompt=prompt)

    assert result == expected_response
    mock_llm_orchestrator.generate_text.assert_called_once()


@pytest.mark.asyncio
async def test_get_status(rae_engine):
    status = rae_engine.get_status()
    assert "engine" in status
    assert "components" in status
    assert "search_strategies" in status
