from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.models.semantic_models import SemanticNode
from apps.memory_api.services.semantic_search import SemanticSearchPipeline
from apps.memory_api.utils.datetime_utils import utc_now


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    pool.fetch = AsyncMock(return_value=[])
    return pool


@pytest.fixture
def mock_ml_client():
    with patch("apps.memory_api.services.semantic_search.MLServiceClient") as mock:
        instance = mock.return_value
        instance.get_embedding = AsyncMock(return_value=[0.1] * 1536)
        instance.generate_embeddings = AsyncMock(
            return_value={"embeddings": [[0.1] * 1536]}
        )
        yield instance


@pytest.fixture
def mock_semantic_extractor():
    with patch("apps.memory_api.services.semantic_search.SemanticExtractor") as mock:
        instance = mock.return_value
        instance.canonicalize_term = AsyncMock(side_effect=lambda x: x)
        yield instance


@pytest.fixture
def semantic_search_service(mock_pool, mock_ml_client, mock_semantic_extractor):
    service = SemanticSearchPipeline(mock_pool)
    # Inject mocks directly
    service.ml_client = mock_ml_client
    service.semantic_extractor = mock_semantic_extractor
    return service


@pytest.fixture
def sample_node_record():
    return {
        "id": uuid4(),
        "tenant_id": "tenant1",
        "project_id": "project1",
        "node_id": "node1",
        "label": "Test Node",
        "node_type": "concept",
        "canonical_form": "test node",
        "aliases": [],
        "definition": "A test node",
        "definitions": [],
        "context": None,
        "examples": [],
        "categories": [],
        "domain": "general",
        "relations": {},
        "embedding": [0.1] * 1536,
        "priority": 1,
        "importance_score": 0.5,
        "last_reinforced_at": utc_now(),
        "reinforcement_count": 1,
        "decay_rate": 0.1,
        "is_degraded": False,
        "degradation_timestamp": None,
        "source_memory_ids": [],
        "extraction_model": "model1",
        "extraction_confidence": 0.9,
        "tags": [],
        "metadata": {},
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "last_accessed_at": utc_now(),
        "accessed_count": 5,
    }


@pytest.mark.asyncio
async def test_search_stage1_only(
    semantic_search_service, mock_pool, sample_node_record
):
    # Arrange
    mock_pool.fetch.return_value = [sample_node_record]

    # Act
    results, stats = await semantic_search_service.search(
        tenant_id="tenant1",
        project_id="project1",
        query="test query",
        k=5,
        enable_topic_matching=True,
        enable_canonicalization=False,
        enable_reranking=False,
    )

    # Assert
    assert len(results) == 1
    assert stats["stage1_results"] == 1
    assert stats["stage2_results"] == 0
    assert len(stats["identified_topics"]) > 0
    semantic_search_service.ml_client.generate_embeddings.assert_called_once()
    mock_pool.fetch.assert_called_once()


@pytest.mark.asyncio
async def test_search_stage2_only(
    semantic_search_service, mock_pool, sample_node_record
):
    # Arrange
    mock_pool.fetch.return_value = [sample_node_record]

    # Act
    results, stats = await semantic_search_service.search(
        tenant_id="tenant1",
        project_id="project1",
        query="test query",
        k=5,
        enable_topic_matching=False,
        enable_canonicalization=True,
        enable_reranking=False,
    )

    # Assert
    assert len(results) == 1  # May be more if deduplication fails or multiple terms
    assert stats["stage1_results"] == 0
    assert stats["stage2_results"] >= 1
    assert len(stats["canonical_terms"]) > 0
    semantic_search_service.semantic_extractor.canonicalize_term.assert_called()


@pytest.mark.asyncio
async def test_search_stage3_reranking(
    semantic_search_service, mock_pool, sample_node_record
):
    # Arrange
    # Create two nodes with different importance
    high_imp_record = sample_node_record.copy()
    high_imp_record["id"] = uuid4()
    high_imp_record["importance_score"] = 0.9
    high_imp_record["priority"] = 5

    low_imp_record = sample_node_record.copy()
    low_imp_record["id"] = uuid4()
    low_imp_record["importance_score"] = 0.1
    low_imp_record["priority"] = 1

    mock_pool.fetch.return_value = [low_imp_record, high_imp_record]

    # Act
    results, stats = await semantic_search_service.search(
        tenant_id="tenant1",
        project_id="project1",
        query="test query",
        k=5,
        enable_topic_matching=True,
        enable_canonicalization=False,
        enable_reranking=True,
    )

    # Assert
    assert len(results) == 2
    assert stats["stage3_results"] == 2
    # Check if re-ranking happened (high importance should be first)
    assert results[0].importance_score == 0.9


@pytest.mark.asyncio
async def test_filters(semantic_search_service, mock_pool, sample_node_record):
    # Arrange
    degraded_record = sample_node_record.copy()
    degraded_record["id"] = uuid4()
    degraded_record["is_degraded"] = True

    mock_pool.fetch.return_value = [sample_node_record, degraded_record]

    # Act
    results, stats = await semantic_search_service.search(
        tenant_id="tenant1",
        project_id="project1",
        query="test query",
        k=5,
        enable_topic_matching=True,
        enable_canonicalization=False,
        enable_reranking=False,
        exclude_degraded=True,
    )

    # Assert
    assert len(results) == 1
    assert not results[0].is_degraded


@pytest.mark.asyncio
async def test_extract_topics_simple(semantic_search_service):
    topics = semantic_search_service._extract_topics_simple("The quick brown fox jumps")
    assert "quick" in topics
    assert "brown" in topics
    assert "fox" in topics
    assert "the" not in topics  # Stop word


@pytest.mark.asyncio
async def test_deduplication(semantic_search_service, mock_pool, sample_node_record):
    # Arrange
    # Return same record twice from different stages
    # Add extra empty lists to prevent StopAsyncIteration
    mock_pool.fetch.side_effect = [[sample_node_record], [sample_node_record], [], []]

    # Act
    results, stats = await semantic_search_service.search(
        tenant_id="tenant1",
        project_id="project1",
        query="test query",
        k=5,
        enable_topic_matching=True,
        enable_canonicalization=True,
        enable_reranking=False,
    )

    # Assert
    assert len(results) == 1  # Should be deduplicated


@pytest.mark.asyncio
async def test_empty_results(semantic_search_service, mock_pool):
    mock_pool.fetch.return_value = []

    results, stats = await semantic_search_service.search(
        tenant_id="tenant1", project_id="project1", query="test query"
    )

    assert len(results) == 0


@pytest.mark.asyncio
async def test_reranking_logic(semantic_search_service):
    # Create mock nodes
    now = utc_now()
    node1 = SemanticNode(
        id=uuid4(),
        tenant_id="t",
        project_id="p",
        node_id="n1",
        label="1",
        node_type="concept",
        canonical_form="1",
        created_at=now,
        updated_at=now,
        importance_score=0.5,
        priority=3,
        reinforcement_count=10,
        accessed_count=10,
        is_degraded=False,
        decay_rate=0.1,
        last_reinforced_at=now,
        last_accessed_at=now,
    )
    node2 = SemanticNode(
        id=uuid4(),
        tenant_id="t",
        project_id="p",
        node_id="n2",
        label="2",
        node_type="concept",
        canonical_form="2",
        created_at=now,
        updated_at=now,
        importance_score=0.9,
        priority=5,
        reinforcement_count=100,
        accessed_count=100,
        is_degraded=False,
        decay_rate=0.1,
        last_reinforced_at=now,
        last_accessed_at=now,
    )

    nodes = [node1, node2]
    reranked = await semantic_search_service._stage3_reranking(nodes, "query", 2)

    assert reranked[0].id == node2.id  # Node 2 should be ranked higher due to scores


@pytest.mark.asyncio
async def test_filter_by_domain(semantic_search_service, mock_pool, sample_node_record):
    # Arrange
    tech_record = sample_node_record.copy()
    tech_record["id"] = uuid4()
    tech_record["domain"] = "tech"

    health_record = sample_node_record.copy()
    health_record["id"] = uuid4()
    health_record["domain"] = "health"

    mock_pool.fetch.return_value = [tech_record, health_record]

    # Act
    results, _ = await semantic_search_service.search(
        tenant_id="t",
        project_id="p",
        query="q",
        enable_topic_matching=True,
        enable_canonicalization=False,
        enable_reranking=False,
        domains=["tech"],
    )

    assert len(results) == 1
    assert results[0].domain == "tech"
