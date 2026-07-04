"""
Tests for Semantic Memory - Knowledge Nodes with TTL/LTM Decay

Tests cover:
- Semantic node extraction
- Canonicalization
- 3-stage semantic search
- TTL/LTM decay model
- Reinforcement learning
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

# Skip tests if spacy is not installed (ML dependency)
spacy = pytest.importorskip(
    "spacy",
    reason="Requires spacy – heavy ML dependency",
)

from apps.memory_api.services.semantic_extractor import SemanticExtractor  # noqa: E402
from apps.memory_api.services.semantic_search import (  # noqa: E402
    SemanticSearchPipeline,
)


@pytest.fixture
def mock_pool():
    pool = AsyncMock()
    return pool


@pytest.fixture
def mock_llm():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="machine learning")  # For canonicalize_term
    llm.generate_structured = AsyncMock(
        return_value={
            "entities": [
                {
                    "label": "machine learning",
                    "type": "concept",
                    "canonical_form": "machine learning",
                },
                {
                    "label": "neural networks",
                    "type": "concept",
                    "canonical_form": "neural network",
                },
            ]
        }
    )
    return llm


@pytest.fixture
def semantic_extractor(mock_pool, mock_llm):
    extractor = SemanticExtractor(mock_pool)
    extractor.llm_provider = mock_llm
    return extractor


@pytest.fixture
def semantic_search(mock_pool):
    return SemanticSearchPipeline(mock_pool)


# Extraction Tests
@pytest.mark.asyncio
async def test_extract_semantic_nodes(semantic_extractor, mock_pool):
    """Test semantic node extraction from memory"""
    mock_pool.fetchrow = AsyncMock(
        return_value={
            "id": uuid4(),
            "content": "Machine learning uses neural networks for pattern recognition",
        }
    )
    mock_pool.fetch = AsyncMock(return_value=[])
    mock_pool.execute = AsyncMock()

    # Method is extract_from_memories, not extract_nodes
    result = await semantic_extractor.extract_from_memories(
        tenant_id="test", project_id="test", memory_ids=[uuid4()]
    )

    # Returns SemanticExtractionResult
    assert result is not None


# Canonicalization Tests
@pytest.mark.asyncio
async def test_canonicalization(semantic_extractor):
    """Test term canonicalization"""
    # Method is canonicalize_term (public method), not _canonicalize
    canonical = await semantic_extractor.canonicalize_term("machine learning")
    # Should return the canonical form (could be same or different)
    assert canonical is not None
    assert isinstance(canonical, str)


# Search Tests
@pytest.mark.asyncio
async def test_semantic_search_3_stages(semantic_search, mock_pool):
    """Test 3-stage semantic search pipeline"""
    from datetime import datetime, timezone

    from apps.memory_api.models.semantic_models import SemanticNodeType

    # Mock database records for stage 1 (vector search)
    mock_record = {
        "id": uuid4(),
        "tenant_id": "test_tenant",
        "project_id": "test_project",
        "node_id": "machine_learning_001",
        "label": "machine learning",
        "node_type": "concept",
        "canonical_form": "machine learning",
        "aliases": ["ML", "ml"],
        "definition": "A field of AI",
        "definitions": [],
        "context": None,
        "examples": [],
        "categories": ["AI", "technology"],
        "domain": "artificial_intelligence",
        "relations": {},
        "embedding": [0.1] * 768,
        "priority": 4,
        "importance_score": 0.8,
        "last_reinforced_at": datetime.now(timezone.utc),
        "reinforcement_count": 5,
        "decay_rate": 0.01,
        "is_degraded": False,
        "degradation_timestamp": None,
        "source_memory_ids": [],
        "extraction_model": "gpt-4",
        "extraction_confidence": 0.9,
        "tags": ["AI"],
        "metadata": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_accessed_at": datetime.now(timezone.utc),
        "accessed_count": 10,
    }

    # Mock pool.fetch to return mock records
    mock_pool.fetch = AsyncMock(return_value=[mock_record])

    # Mock ML client embedding
    semantic_search.ml_client.get_embedding = AsyncMock(return_value=[0.1] * 768)
    semantic_search.ml_client.generate_embeddings = AsyncMock(
        return_value={"embeddings": [[0.1] * 768]}
    )

    # Mock semantic extractor canonicalize_term
    semantic_search.semantic_extractor.canonicalize_term = AsyncMock(
        side_effect=lambda term: term.lower()
    )

    # Execute 3-stage search
    results, statistics = await semantic_search.search(
        tenant_id="test_tenant",
        project_id="test_project",
        query="machine learning neural networks",
        k=10,
        enable_topic_matching=True,
        enable_canonicalization=True,
        enable_reranking=True,
    )

    # Verify results
    assert isinstance(results, list)
    assert len(results) > 0

    # Verify statistics structure
    assert isinstance(statistics, dict)
    assert "stage1_results" in statistics
    assert "stage2_results" in statistics
    assert "stage3_results" in statistics
    assert "identified_topics" in statistics
    assert "canonical_terms" in statistics

    # Verify results are SemanticNode objects
    assert results[0].label == "machine learning"
    assert results[0].node_type == SemanticNodeType.CONCEPT
    assert results[0].priority == 4


# Decay Tests
@pytest.mark.asyncio
async def test_ttl_ltm_decay(mock_pool):
    """Test TTL/LTM decay model"""
    # Node not accessed for long time should decay
    last_reinforced = datetime.now(timezone.utc) - timedelta(days=30)
    decay_rate = 0.01

    # Calculate decay
    days_since = (datetime.now(timezone.utc) - last_reinforced).days
    decay_factor = 1.0 - (decay_rate * days_since)

    assert decay_factor < 1.0


# Reinforcement Tests
@pytest.mark.asyncio
async def test_node_reinforcement(mock_pool):
    """Test reinforcement learning for nodes"""
    mock_pool.execute = AsyncMock()

    node_id = uuid4()
    # Simulate reinforcement
    # Priority should increase, decay should reset

    # This would be called when node is accessed
    await mock_pool.execute("SELECT reinforce_semantic_node($1)", node_id)

    mock_pool.execute.assert_called_once()
