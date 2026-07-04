from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.services.graph_extraction import (
    GraphExtractionResult,
    GraphExtractionService,
    GraphTriple,
    _normalize_entity_name,
)


@pytest.fixture
def mock_rae_service():
    return AsyncMock()


@pytest.fixture
def mock_graph_repo():
    return AsyncMock()


@pytest.fixture
def mock_llm_provider():
    return AsyncMock()


@pytest.fixture
def service(mock_rae_service, mock_graph_repo, mock_llm_provider):
    with (
        patch(
            "apps.memory_api.services.graph_extraction.get_llm_provider",
            return_value=mock_llm_provider,
        ),
        patch.object(
            GraphExtractionService, "_ensure_spacy_available", return_value=None
        ),
    ):
        svc = GraphExtractionService(mock_rae_service, mock_graph_repo)
        svc.llm_provider = mock_llm_provider
        yield svc


@pytest.mark.asyncio
async def test_extract_knowledge_graph_success(
    service, mock_rae_service, mock_llm_provider
):
    # Setup
    project_id = "p-1"
    tenant_id = "t-1"

    # 1. Mock memories
    mock_rae_service.list_memories.return_value = [
        {"id": uuid4(), "content": "User likes Python.", "created_at": "2023-01-01"}
    ]

    # 2. Mock Gatekeeper response (FactualIndices)
    # We need a class that matches the Pydantic model structure used in _filter_factual_memories
    class MockFactualIndices:
        indices = [1]

    # 3. Mock Extraction Result (GraphExtractionResult)
    extraction_result = GraphExtractionResult(
        triples=[
            GraphTriple(
                source="User", relation="LIKES", target="Python", confidence=0.9
            )
        ],
        extracted_entities=["User", "Python"],
        statistics={},
    )

    # Configure side_effect for generate_structured calls
    # First call is Gatekeeper, second is Extraction
    mock_llm_provider.generate_structured.side_effect = [
        MockFactualIndices(),
        extraction_result,
    ]

    # Execute
    result = await service.extract_knowledge_graph(project_id, tenant_id)

    # Verify
    assert isinstance(result, GraphExtractionResult)
    assert len(result.triples) == 1
    assert result.triples[0].source == "user"  # normalized
    assert result.triples[0].relation == "LIKES"
    assert result.statistics["memories_processed"] == 1

    # Verify gatekeeper call
    assert mock_llm_provider.generate_structured.call_count == 2


@pytest.mark.asyncio
async def test_extract_knowledge_graph_no_memories(service, mock_rae_service):
    mock_rae_service.list_memories.return_value = []

    result = await service.extract_knowledge_graph("p-1", "t-1")

    assert result.statistics["memories_processed"] == 0
    assert len(result.triples) == 0


@pytest.mark.asyncio
async def test_extract_knowledge_graph_gatekeeper_filters_all(
    service, mock_rae_service, mock_llm_provider
):
    # Memories exist but are non-factual
    mock_rae_service.list_memories.return_value = [
        {"id": uuid4(), "content": "Hi there", "created_at": "2023-01-01"}
    ]

    class MockFactualIndices:
        indices = []  # Empty list means no factual memories

    mock_llm_provider.generate_structured.return_value = MockFactualIndices()

    result = await service.extract_knowledge_graph("p-1", "t-1")

    assert result.statistics["memories_processed"] == 1
    assert len(result.triples) == 0
    # Should only call gatekeeper, not extraction
    assert mock_llm_provider.generate_structured.call_count == 1


def test_normalize_entity_name():
    assert _normalize_entity_name("  User  ") == "user"
    assert _normalize_entity_name("my_variable") == "my variable"
    # Lemmatization check (if spacy is available/mocked, otherwise simple fallback)
    # Since we don't mock spacy here, it might use the installed one or skip.
    # Basic normalization should work regardless.
    assert _normalize_entity_name("Test-Entity") == "test entity"


def test_format_memories(service):
    memories = [
        {
            "content": "First memory",
            "tags": ["tag1"],
            "source": "chat",
            "created_at": "2023",
        },
        {"content": "Second memory"},
    ]
    formatted = service._format_memories(memories)

    assert "1. [2023] First memory [tags: tag1] (source: chat)" in formatted
    assert "2. [] Second memory" in formatted


@pytest.mark.asyncio
async def test_store_graph_triples(service, mock_graph_repo):
    triples = [GraphTriple(source="A", relation="B", target="C", confidence=0.8)]
    mock_graph_repo.store_graph_triples.return_value = {
        "nodes_created": 2,
        "edges_created": 1,
    }

    result = await service.store_graph_triples(triples, "p-1", "t-1")

    assert result["nodes_created"] == 2
    mock_graph_repo.store_graph_triples.assert_called_once()

    # Check arguments passed to repo
    call_args = mock_graph_repo.store_graph_triples.call_args[1]
    assert call_args["project_id"] == "p-1"
    assert len(call_args["triples"]) == 1
    assert call_args["triples"][0]["source"] == "a"  # normalized
