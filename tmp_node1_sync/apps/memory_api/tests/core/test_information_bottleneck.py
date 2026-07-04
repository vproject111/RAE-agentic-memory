"""
Tests for Information Bottleneck Context Selector (Iteration 4).

Tests cover:
  1. IB selector creation and configuration
  2. Context selection with different beta values
  3. Relevance and compression cost computation
  4. I(Z;Y) and I(Z;X) estimation
  5. Adaptive beta tuning
  6. Edge cases and error handling
"""

import numpy as np
import pytest

from apps.memory_api.core.information_bottleneck import (
    InformationBottleneckSelector,
    MemoryItem,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def ib_selector():
    """Create IB selector with standard beta"""
    return InformationBottleneckSelector(beta=1.0)


@pytest.fixture
def query_embedding():
    """Create mock query embedding"""
    np.random.seed(42)
    return np.random.randn(384)


@pytest.fixture
def mock_memories():
    """Create mock memory items for testing"""
    np.random.seed(42)

    memories = []
    for i in range(20):
        # Create memories with varying relevance
        embedding = np.random.randn(384)
        if i < 5:
            # High relevance memories (similar to query)
            embedding[0] = 1.0
            importance = 0.9
        elif i < 10:
            # Medium relevance
            embedding[0] = 0.5
            importance = 0.6
        else:
            # Low relevance
            embedding[0] = -0.5
            importance = 0.3

        memory = MemoryItem(
            id=f"mem_{i}",
            content=f"Memory content {i}",
            embedding=embedding,
            importance=importance,
            layer="episodic" if i < 10 else "semantic",
            tokens=100 + i * 10,
            metadata={"index": i},
        )
        memories.append(memory)

    return memories


# ============================================================================
# Test IB Selector Creation
# ============================================================================


def test_ib_selector_creation():
    """Test creating IB selector with different beta values"""
    selector = InformationBottleneckSelector(beta=0.5)
    assert selector.beta == 0.5

    selector2 = InformationBottleneckSelector(beta=2.0)
    assert selector2.beta == 2.0


def test_ib_selector_default_beta():
    """Test default beta value"""
    selector = InformationBottleneckSelector()
    assert selector.beta == 1.0


# ============================================================================
# Test Context Selection
# ============================================================================


def test_select_context_basic(ib_selector, query_embedding, mock_memories):
    """Test basic context selection"""
    selected = ib_selector.select_context(
        query="test query",
        query_embedding=query_embedding,
        full_memory=mock_memories,
        max_tokens=500,
    )

    assert len(selected) > 0
    assert len(selected) <= len(mock_memories)

    # Check that total tokens don't exceed max
    total_tokens = sum(m.tokens for m in selected)
    assert total_tokens <= 500


def test_select_context_empty_memory(ib_selector, query_embedding):
    """Test selection with empty memory"""
    selected = ib_selector.select_context(
        query="test query",
        query_embedding=query_embedding,
        full_memory=[],
        max_tokens=500,
    )

    assert len(selected) == 0


def test_select_context_high_beta_compression(query_embedding, mock_memories):
    """Test that high beta increases compression"""
    # Low beta (lower compression - prefers relevance)
    selector_low = InformationBottleneckSelector(beta=0.1)
    selected_low = selector_low.select_context(
        query="test",
        query_embedding=query_embedding,
        full_memory=mock_memories,
        max_tokens=2000,
    )

    # High beta (higher compression - penalizes token usage heavily)
    selector_high = InformationBottleneckSelector(beta=10.0)
    selected_high = selector_high.select_context(
        query="test",
        query_embedding=query_embedding,
        full_memory=mock_memories,
        max_tokens=2000,
    )

    # High beta should select fewer tokens (higher compression)
    # Count total tokens instead of memory count for more reliable test
    tokens_low = sum(m.tokens for m in selected_low)
    tokens_high = sum(m.tokens for m in selected_high)

    # High beta should use fewer tokens OR equal (if both hit max_tokens)
    # We allow equality because both might select up to max_tokens
    assert tokens_high <= tokens_low, (
        f"High beta should use fewer or equal tokens: "
        f"high={tokens_high}, low={tokens_low}"
    )


def test_select_context_respects_min_relevance(
    ib_selector, query_embedding, mock_memories
):
    """Test that memories below min_relevance are filtered out"""
    selected = ib_selector.select_context(
        query="test",
        query_embedding=query_embedding,
        full_memory=mock_memories,
        max_tokens=5000,
        min_relevance=0.8,  # Very high threshold
    )

    # Should select only highly relevant memories
    # Since we set min_relevance very high, we might select fewer items
    assert len(selected) < len(mock_memories)


def test_select_context_respects_max_tokens(
    ib_selector, query_embedding, mock_memories
):
    """Test that selection respects max_tokens constraint"""
    max_tokens = 300

    selected = ib_selector.select_context(
        query="test",
        query_embedding=query_embedding,
        full_memory=mock_memories,
        max_tokens=max_tokens,
    )

    total_tokens = sum(m.tokens for m in selected)
    assert total_tokens <= max_tokens


# ============================================================================
# Test Relevance and Compression Cost Computation
# ============================================================================


def test_compute_relevance_scores(ib_selector, query_embedding, mock_memories):
    """Test relevance score computation"""
    relevance_scores = ib_selector._compute_relevance_scores(
        memories=mock_memories, query_embedding=query_embedding
    )

    assert len(relevance_scores) == len(mock_memories)
    # All scores should be in [0, 1]
    assert all(0.0 <= score <= 1.0 for score in relevance_scores)


def test_compute_compression_costs(ib_selector, mock_memories):
    """Test compression cost computation"""
    compression_costs = ib_selector._compute_compression_costs(memories=mock_memories)

    assert len(compression_costs) == len(mock_memories)
    # All costs should be in [0, 1]
    assert all(0.0 <= cost <= 1.0 for cost in compression_costs)


def test_compression_cost_layer_penalty(ib_selector):
    """Test that different layers have different compression costs"""
    # Create memories with different layers
    reflective_mem = MemoryItem(
        id="ref",
        content="content",
        embedding=np.zeros(384),
        importance=0.5,
        layer="reflective",
        tokens=100,
        metadata={},
    )

    episodic_mem = MemoryItem(
        id="epi",
        content="content",
        embedding=np.zeros(384),
        importance=0.5,
        layer="episodic",
        tokens=100,
        metadata={},
    )

    costs = ib_selector._compute_compression_costs([reflective_mem, episodic_mem])

    # Reflective should have lower cost (already compressed)
    assert costs[0] < costs[1]


# ============================================================================
# Test I(Z;Y) and I(Z;X) Estimation
# ============================================================================


def test_estimate_I_Z_Y(ib_selector, query_embedding, mock_memories):
    """Test I(Z;Y) estimation"""
    # Select a subset
    selected = mock_memories[:5]

    I_Z_Y = ib_selector.estimate_I_Z_Y(
        selected_context=selected,
        query_embedding=query_embedding,
        full_memory=mock_memories,
    )

    assert 0.0 <= I_Z_Y <= 1.0


def test_estimate_I_Z_Y_empty_context(ib_selector, query_embedding, mock_memories):
    """Test I(Z;Y) with empty context"""
    I_Z_Y = ib_selector.estimate_I_Z_Y(
        selected_context=[], query_embedding=query_embedding, full_memory=mock_memories
    )

    assert I_Z_Y == 0.0


def test_estimate_I_Z_X(ib_selector, mock_memories):
    """Test I(Z;X) estimation"""
    # Select half the memories
    selected = mock_memories[:10]

    I_Z_X = ib_selector.estimate_I_Z_X(
        selected_context=selected, full_memory=mock_memories
    )

    # Should be around 0.5 (half the memories selected)
    assert 0.3 <= I_Z_X <= 0.7


def test_estimate_I_Z_X_all_memories(ib_selector, mock_memories):
    """Test I(Z;X) when all memories selected"""
    I_Z_X = ib_selector.estimate_I_Z_X(
        selected_context=mock_memories, full_memory=mock_memories
    )

    # Should be close to 1.0 (all memories selected)
    assert I_Z_X > 0.95


def test_estimate_I_Z_X_empty_context(ib_selector, mock_memories):
    """Test I(Z;X) with empty context"""
    I_Z_X = ib_selector.estimate_I_Z_X(selected_context=[], full_memory=mock_memories)

    assert I_Z_X == 0.0


# ============================================================================
# Test Cosine Similarity
# ============================================================================


def test_cosine_similarity_identical_vectors(ib_selector):
    """Test cosine similarity for identical vectors"""
    vec = np.array([1.0, 2.0, 3.0])

    similarity = ib_selector._cosine_similarity(vec, vec)

    assert 0.9 <= similarity <= 1.0  # Should be close to 1.0


def test_cosine_similarity_orthogonal_vectors(ib_selector):
    """Test cosine similarity for orthogonal vectors"""
    vec1 = np.array([1.0, 0.0, 0.0])
    vec2 = np.array([0.0, 1.0, 0.0])

    similarity = ib_selector._cosine_similarity(vec1, vec2)

    assert 0.4 <= similarity <= 0.6  # Should be around 0.5 (normalized from 0)


def test_cosine_similarity_zero_vector(ib_selector):
    """Test cosine similarity with zero vector"""
    vec1 = np.array([1.0, 2.0, 3.0])
    vec2 = np.zeros(3)

    similarity = ib_selector._cosine_similarity(vec1, vec2)

    assert similarity == 0.0


# ============================================================================
# Test Diversity Computation
# ============================================================================


def test_compute_diversity(ib_selector):
    """Test diversity computation"""
    # Create diverse embeddings
    embeddings = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])

    diversity = ib_selector._compute_diversity(embeddings)

    # Orthogonal vectors should have high diversity
    assert diversity > 0.3


def test_compute_diversity_single_embedding(ib_selector):
    """Test diversity with single embedding"""
    embeddings = np.array([[1.0, 0.0, 0.0]])

    diversity = ib_selector._compute_diversity(embeddings)

    assert diversity == 0.0


def test_compute_diversity_identical_embeddings(ib_selector):
    """Test diversity with identical embeddings"""
    embeddings = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    diversity = ib_selector._compute_diversity(embeddings)

    # Identical embeddings should have low diversity
    assert diversity < 0.1


# ============================================================================
# Test Adaptive Beta
# ============================================================================


def test_adaptive_beta_complex_query(ib_selector):
    """Test adaptive beta for complex query"""
    beta = ib_selector.adaptive_beta(
        query_complexity=0.9,  # Very complex
        budget_remaining=0.8,
        user_preference="balanced",
    )

    # Complex query should get lower beta (lower compression)
    assert beta < 1.0


def test_adaptive_beta_low_budget(ib_selector):
    """Test adaptive beta with low budget"""
    beta = ib_selector.adaptive_beta(
        query_complexity=0.5,
        budget_remaining=0.1,  # Very low budget
        user_preference="balanced",
    )

    # Low budget should get higher beta (higher compression)
    assert beta > 1.0


def test_adaptive_beta_user_preferences(ib_selector):
    """Test adaptive beta with different user preferences"""
    beta_quality = ib_selector.adaptive_beta(
        query_complexity=0.5, budget_remaining=0.5, user_preference="quality"
    )

    beta_efficiency = ib_selector.adaptive_beta(
        query_complexity=0.5, budget_remaining=0.5, user_preference="efficiency"
    )

    beta_balanced = ib_selector.adaptive_beta(
        query_complexity=0.5, budget_remaining=0.5, user_preference="balanced"
    )

    # Quality should have lowest beta, efficiency highest
    assert beta_quality < beta_balanced < beta_efficiency


# ============================================================================
# Test IB Objective Computation
# ============================================================================


def test_compute_ib_objective(ib_selector, query_embedding, mock_memories):
    """Test full IB objective computation"""
    selected = mock_memories[:5]

    objective = ib_selector.compute_ib_objective(
        selected_context=selected,
        query_embedding=query_embedding,
        full_memory=mock_memories,
    )

    assert "I_Z_Y" in objective
    assert "I_Z_X" in objective
    assert "beta" in objective
    assert "objective" in objective
    assert "compression_ratio" in objective
    assert "context_efficiency" in objective

    # Objective should be I_Z_Y - beta * I_Z_X
    expected = objective["I_Z_Y"] - objective["beta"] * objective["I_Z_X"]
    assert abs(objective["objective"] - expected) < 0.001


# ============================================================================
# Test Integration
# ============================================================================


def test_ib_selection_prefers_relevant_memories(query_embedding, mock_memories):
    """Test that IB selection prefers relevant memories"""
    selector = InformationBottleneckSelector(beta=1.0)

    selected = selector.select_context(
        query="test",
        query_embedding=query_embedding,
        full_memory=mock_memories,
        max_tokens=500,
    )

    # Check that selected memories are mostly high relevance
    # (first 5 memories in our fixture are high relevance)
    high_relevance_selected = sum(1 for m in selected if int(m.id.split("_")[1]) < 5)

    # At least half should be high relevance
    assert high_relevance_selected >= len(selected) / 2
