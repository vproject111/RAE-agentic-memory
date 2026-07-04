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
    with patch("rae_core.engine.HybridSearchEngine") as mock:
        instance = mock.return_value
        instance.search = AsyncMock()
        instance.rerank = AsyncMock()
        yield instance


@pytest.fixture
def mock_reflection_engine():
    with patch("rae_core.engine.ReflectionEngine") as mock:
        instance = mock.return_value
        instance.run_reflection_cycle = AsyncMock()
        instance.generate_reflection = AsyncMock()
        yield instance


@pytest.fixture
def mock_llm_orchestrator():
    with patch("rae_core.engine.LLMOrchestrator") as mock:
        instance = mock.return_value
        instance.generate = AsyncMock()
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
    )


@pytest.mark.asyncio
async def test_store_memory(rae_engine, mock_memory_storage):
    tenant_id = "test-tenant"
    agent_id = "test-agent"
    content = "test content"
    expected_uuid = uuid4()

    mock_memory_storage.store_memory.return_value = expected_uuid

    result = await rae_engine.store_memory(
        tenant_id=tenant_id,
        agent_id=agent_id,
        content=content,
    )

    assert result == expected_uuid
    from unittest.mock import ANY

    mock_memory_storage.store_memory.assert_called_once_with(
        tenant_id=tenant_id,
        agent_id=agent_id,
        content=content,
        layer="sensory",
        importance=0.5,
        tags=[],
        metadata={},
        embedding=ANY,
        memory_type="text",
        project=None,
        session_id=None,
        expires_at=None,
        source=None,
        strength=1.0,
        info_class="internal",
        governance={},
    )


@pytest.mark.asyncio
async def test_retrieve_memory(rae_engine, mock_memory_storage):
    tenant_id = "test-tenant"
    memory_id = uuid4()
    expected_memory = {"id": memory_id, "content": "test"}

    mock_memory_storage.get_memory.return_value = expected_memory

    result = await rae_engine.retrieve_memory(
        memory_id=memory_id,
        tenant_id=tenant_id,
    )

    assert result == expected_memory
    mock_memory_storage.get_memory.assert_called_once_with(
        memory_id=memory_id,
        tenant_id=tenant_id,
    )


@pytest.mark.asyncio
async def test_search_memories(rae_engine, mock_search_engine, mock_memory_storage):
    tenant_id = "test-tenant"
    query = "test query"
    mem_id = uuid4()
    expected_results = [(mem_id, 0.9)]
    expected_memory = {"id": mem_id, "content": "found"}

    mock_search_engine.search.return_value = expected_results
    mock_memory_storage.get_memory.return_value = expected_memory

    results = await rae_engine.search_memories(
        query=query,
        tenant_id=tenant_id,
    )

    assert len(results) == 1
    assert results[0]["id"] == mem_id
    assert results[0]["search_score"] == 0.9
    mock_search_engine.search.assert_called_once()


@pytest.mark.asyncio
async def test_search_memories_with_rerank(
    rae_engine, mock_search_engine, mock_memory_storage
):
    tenant_id = "test-tenant"
    query = "test query"
    mem_id = uuid4()
    search_results = [(mem_id, 0.5)]
    reranked_results = [(mem_id, 0.9)]
    expected_memory = {"id": mem_id, "content": "found"}

    mock_search_engine.search.return_value = search_results
    mock_search_engine.rerank.return_value = reranked_results
    mock_memory_storage.get_memory.return_value = expected_memory

    results = await rae_engine.search_memories(
        query=query,
        tenant_id=tenant_id,
        use_reranker=True,
    )

    assert len(results) == 1
    assert results[0]["search_score"] == 0.9
    mock_search_engine.search.assert_called_once()
    mock_search_engine.rerank.assert_called_once()


@pytest.mark.asyncio
async def test_run_reflection_cycle(rae_engine, mock_reflection_engine):
    tenant_id = "test-tenant"
    agent_id = "test-agent"
    expected_summary = {"status": "completed"}

    mock_reflection_engine.run_reflection_cycle.return_value = expected_summary

    result = await rae_engine.run_reflection_cycle(
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    assert result == expected_summary
    mock_reflection_engine.run_reflection_cycle.assert_called_once_with(
        tenant_id=tenant_id,
        agent_id=agent_id,
        trigger_type="scheduled",
    )


@pytest.mark.asyncio
async def test_generate_text(rae_engine, mock_llm_orchestrator):
    prompt = "Hello"
    expected_response = "World"

    mock_llm_orchestrator.generate.return_value = (expected_response, {})

    result = await rae_engine.generate_text(prompt=prompt)

    assert result == expected_response
    mock_llm_orchestrator.generate.assert_called_once()


@pytest.mark.asyncio
async def test_get_status(rae_engine):
    status = rae_engine.get_status()
    assert "settings" in status
    assert "features" in status
    assert "version" in status
    assert status["features"]["llm_enabled"] is True
