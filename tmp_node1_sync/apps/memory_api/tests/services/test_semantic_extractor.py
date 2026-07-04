from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.models.semantic_models import (
    ExtractedRelation,
    ExtractedTerm,
    ExtractedTopic,
    SemanticExtractionResult,
    SemanticNodeType,
)
from apps.memory_api.services.semantic_extractor import SemanticExtractor

# Test data
TENANT_ID = "t1"
PROJECT_ID = "p1"


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    # Mock acquire context manager
    mock_context = MagicMock()
    conn = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=conn)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    pool.acquire.return_value = mock_context

    # Mock fetch methods as AsyncMock because they are awaited
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.fetchval = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value=None)

    return pool


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=MagicMock(text="canonical_term"))

    # Mock structured response
    extraction_result = SemanticExtractionResult(
        topics=[ExtractedTopic(topic="AI", normalized_topic="ai", confidence=0.9)],
        terms=[
            ExtractedTerm(
                original="ML",
                canonical="Machine Learning",
                definition="...",
                confidence=0.85,
            )
        ],
        relations=[
            ExtractedRelation(source="ML", relation="is_a", target="AI", confidence=0.9)
        ],
        domain="tech",
        categories=["science"],
    )
    provider.generate_structured = AsyncMock(return_value=extraction_result)
    return provider


@pytest.fixture
def mock_ml_client():
    client = MagicMock()
    client.generate_embeddings = AsyncMock(return_value={"embeddings": [[0.1] * 1536]})
    return client


@pytest.fixture
def mock_rae_service(mock_pool):
    service = MagicMock()
    service.postgres_pool = mock_pool
    service.list_memories = AsyncMock(return_value=[])

    # Mock the 'db' property to return an actual provider wrapping our mock pool
    from rae_adapters.postgres_db import PostgresDatabaseProvider

    service.db = PostgresDatabaseProvider(mock_pool)

    return service


@pytest.fixture
def extractor(mock_rae_service, mock_llm_provider, mock_ml_client):
    with (
        patch(
            "apps.memory_api.services.semantic_extractor.get_llm_provider",
            return_value=mock_llm_provider,
        ),
        patch(
            "apps.memory_api.services.semantic_extractor.MLServiceClient",
            return_value=mock_ml_client,
        ),
    ):
        svc = SemanticExtractor(mock_rae_service)
        svc.llm_provider = mock_llm_provider
        svc.ml_client = mock_ml_client
        return svc


@pytest.mark.asyncio
async def test_initialization(extractor, mock_rae_service):
    assert extractor.rae_service == mock_rae_service
    assert extractor.llm_provider is not None
    assert extractor.ml_client is not None


@pytest.mark.asyncio
async def test_extract_from_memories_no_memories(extractor, mock_rae_service):
    """Test early exit when no memories found."""
    mock_rae_service.list_memories.return_value = []

    stats = await extractor.extract_from_memories(
        TENANT_ID, PROJECT_ID, max_memories=10
    )

    assert stats["memories_processed"] == 0
    mock_rae_service.list_memories.assert_called_once()


@pytest.mark.asyncio
async def test_extract_from_memories_success(
    extractor, mock_rae_service, mock_llm_provider
):
    """Test full extraction flow."""
    # Mock memories
    memories = [{"id": uuid4(), "content": "text"}]
    mock_rae_service.list_memories.return_value = memories

    # Mock node creation returns (UUIDs)
    mock_pool = mock_rae_service.postgres_pool
    mock_pool.fetchrow.side_effect = [
        None,  # Topic check
        {"id": uuid4()},  # Topic insert
        None,  # Term check
        {"id": uuid4()},  # Term insert
    ]

    # Mock relations UUID lookup
    mock_pool.fetchval.side_effect = [uuid4(), uuid4()]  # Source UUID, Target UUID

    stats = await extractor.extract_from_memories(
        TENANT_ID, PROJECT_ID, max_memories=10
    )

    assert stats["memories_processed"] == 1
    assert stats["nodes_extracted"] == 2  # 1 topic + 1 term
    assert stats["relationships_created"] == 1  # 1 relation

    mock_llm_provider.generate_structured.assert_called_once()


@pytest.mark.asyncio
async def test_canonicalize_term(extractor, mock_llm_provider):
    """Test term canonicalization."""
    term = await extractor.canonicalize_term("auth")
    assert term == "canonical_term"
    mock_llm_provider.generate.assert_called_once()


@pytest.mark.asyncio
async def test_create_or_update_semantic_node_existing(extractor, mock_pool):
    """Test updating an existing node."""
    node_id = uuid4()
    # fetchrow returns existing record
    mock_pool.fetchrow.return_value = {
        "id": node_id,
        "reinforcement_count": 1,
        "source_memory_ids": [uuid4()],
    }

    result_id = await extractor._create_or_update_semantic_node(
        TENANT_ID, PROJECT_ID, "Topic", "topic", SemanticNodeType.TOPIC, 0.9, [uuid4()]
    )

    assert result_id == node_id
    # verify update query executed
    assert mock_pool.execute.call_count >= 2  # reinforce + update


@pytest.mark.asyncio
async def test_create_or_update_semantic_node_new(extractor, mock_pool):
    """Test creating a new node."""
    new_id = uuid4()
    # fetchrow returns None first (check), then returns record (insert)
    mock_pool.fetchrow.side_effect = [
        None,  # Check if exists -> None
        {"id": new_id},  # Insert returning -> record
    ]

    result_id = await extractor._create_or_update_semantic_node(
        TENANT_ID, PROJECT_ID, "Topic", "topic", SemanticNodeType.TOPIC, 0.9, [uuid4()]
    )

    assert result_id == new_id
    # verify insert happened (fetchrow called twice)
    assert mock_pool.fetchrow.call_count == 2


@pytest.mark.asyncio
async def test_create_semantic_relationship_success(extractor, mock_pool):
    """Test creating a relationship."""
    # fetchval returns IDs for source and target
    mock_pool.fetchval.side_effect = [uuid4(), uuid4()]

    result = await extractor._create_semantic_relationship(
        TENANT_ID, PROJECT_ID, "source", "is_a", "target", 0.9
    )

    assert result is True
    mock_pool.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_semantic_relationship_nodes_missing(extractor, mock_pool):
    """Test relationship failure when nodes are missing."""
    # fetchval returns None for one of them
    mock_pool.fetchval.side_effect = [uuid4(), None]

    result = await extractor._create_semantic_relationship(
        TENANT_ID, PROJECT_ID, "source", "is_a", "target", 0.9
    )

    assert result is False
    mock_pool.execute.assert_not_called()


@pytest.mark.asyncio
async def test_extract_semantic_knowledge_error(extractor, mock_llm_provider):
    """Test LLM failure handling."""
    mock_llm_provider.generate_structured.side_effect = Exception("LLM Error")

    result = await extractor._extract_semantic_knowledge([{}])

    # Should return empty result, not raise
    assert len(result.topics) == 0
    assert len(result.terms) == 0


@pytest.mark.asyncio
async def test_extract_from_memories_with_ids(extractor, mock_rae_service):
    """Test fetching specific memories."""
    memory_ids = [uuid4(), uuid4()]
    mock_rae_service.list_memories.return_value = []

    await extractor.extract_from_memories(TENANT_ID, PROJECT_ID, memory_ids=memory_ids)

    # Verify list_memories call
    mock_rae_service.list_memories.assert_called_once()
    call_args = mock_rae_service.list_memories.call_args
    assert call_args.kwargs["filters"]["memory_ids"] == memory_ids


@pytest.mark.asyncio
async def test_node_creation_exceptions(extractor, mock_rae_service, mock_llm_provider):
    """Test exception handling during node creation loop."""
    # Setup extraction result
    result = SemanticExtractionResult(
        topics=[ExtractedTopic(topic="T1", normalized_topic="t1", confidence=0.9)],
        terms=[ExtractedTerm(original="tm", canonical="term", confidence=0.9)],
        relations=[
            ExtractedRelation(
                source="T1", relation="is_a", target="term", confidence=0.9
            )
        ],
        domain="d",
        categories=[],
    )
    mock_llm_provider.generate_structured.return_value = result
    mock_rae_service.list_memories.return_value = [{"id": uuid4()}]

    # Make create_or_update fail
    # We can patch the private method on the instance or use side_effect on pool calls if we knew exact sequence
    # Easier to patch the method on the extractor instance
    with (
        patch.object(
            extractor,
            "_create_or_update_semantic_node",
            side_effect=Exception("DB Error"),
        ) as mock_create_node,
        patch.object(
            extractor,
            "_create_semantic_relationship",
            side_effect=Exception("Rel Error"),
        ) as mock_create_rel,
    ):
        stats = await extractor.extract_from_memories(TENANT_ID, PROJECT_ID)

        assert stats["nodes_extracted"] == 0
        assert stats["relationships_created"] == 0
        # Should try to create 2 nodes (1 topic + 1 term)
        assert mock_create_node.call_count == 2
        assert mock_create_rel.call_count == 1


@pytest.mark.asyncio
async def test_canonicalize_term_fallback(extractor, mock_llm_provider):
    """Test canonicalization fallback on error."""
    mock_llm_provider.generate.side_effect = Exception("LLM Error")

    term = await extractor.canonicalize_term("  AuTh  ")
    assert term == "auth"  # Lowercase stripped


@pytest.mark.asyncio
async def test_generate_embedding_fallback(extractor, mock_ml_client):
    """Test embedding generation fallback."""
    mock_ml_client.generate_embeddings.side_effect = Exception("ML Error")

    emb = await extractor._generate_embedding("text")
    assert emb == [0.0] * 1536


@pytest.mark.asyncio
async def test_create_semantic_relationship_db_error(extractor, mock_pool):
    """Test DB error during relationship creation."""
    mock_pool.fetchval.side_effect = [uuid4(), uuid4()]
    mock_pool.execute.side_effect = Exception("DB Insert Error")

    result = await extractor._create_semantic_relationship(
        TENANT_ID, PROJECT_ID, "s", "is_a", "t", 0.9
    )
    assert result is False
