"""
Additional coverage tests for information_bottleneck.py to hit edge cases.
"""

import numpy as np
import pytest

from apps.memory_api.core.information_bottleneck import (
    InformationBottleneckSelector,
    MemoryItem,
)


@pytest.fixture
def ib_selector():
    return InformationBottleneckSelector(beta=1.0)


@pytest.fixture
def mock_memory_item():
    return MemoryItem(
        id="1",
        content="test",
        embedding=np.array([0.1, 0.2]),
        importance=0.5,
        layer="episodic",
        tokens=100,
        metadata={},
    )


@pytest.mark.unit
def test_select_context_skip_low_relevance(ib_selector):
    # Line 153: if ib_score == -np.inf: continue

    # Create a memory that is irrelevant
    memory = MemoryItem(
        id="1",
        content="irrelevant",
        embedding=np.array([0.9, 0.9]),  # Far from query [0.1, 0.1]
        importance=0.0,
        layer="episodic",
        tokens=100,
        metadata={},
    )

    # Query [0.1, 0.1] vs Memory [0.9, 0.9] -> low similarity
    query_emb = np.array([0.1, 0.1])

    # Set min_relevance high to force filtering
    selected = ib_selector.select_context(
        query="test",
        query_embedding=query_emb,
        full_memory=[memory],
        min_relevance=0.99,  # Very high threshold
    )

    assert len(selected) == 0


@pytest.mark.unit
def test_compute_compression_costs_layers(ib_selector):
    # Lines 232, 234: Layer adjustments

    memories = [
        MemoryItem(
            id="1",
            content="ref",
            embedding=np.zeros(2),
            importance=0.5,
            layer="reflective",
            tokens=10,
            metadata={},
        ),
        MemoryItem(
            id="2",
            content="sem",
            embedding=np.zeros(2),
            importance=0.5,
            layer="semantic",
            tokens=10,
            metadata={},
        ),
        MemoryItem(
            id="3",
            content="ltm",
            embedding=np.zeros(2),
            importance=0.5,
            layer="ltm",
            tokens=10,
            metadata={},
        ),
        MemoryItem(
            id="4",
            content="work",
            embedding=np.zeros(2),
            importance=0.5,
            layer="working",
            tokens=10,
            metadata={},
        ),
        MemoryItem(
            id="5",
            content="epi",
            embedding=np.zeros(2),
            importance=0.5,
            layer="episodic",
            tokens=10,
            metadata={},
        ),
    ]

    costs = ib_selector._compute_compression_costs(memories)

    # Check relative ordering of costs (reflective should be cheapest)
    # reflective (0.5) < ltm (0.6) < semantic (0.7) < working (0.9) < episodic (1.0)
    # Wait, LTM is 0.6, Semantic is 0.7 in code.

    assert costs[0] < costs[1]  # Ref < Sem
    assert costs[2] < costs[3]  # LTM < Working
    assert costs[3] < costs[4]  # Working < Episodic


@pytest.mark.unit
def test_estimate_i_z_x_empty_full_memory(ib_selector):
    # Line 302: if not full_memory: return 0.0
    val = ib_selector.estimate_I_Z_X([], [])
    assert val == 0.0


@pytest.mark.unit
def test_adaptive_beta_budget_adjustment(ib_selector):
    # Line 405: budget_remaining < 0.2

    # Low budget -> increase beta (more compression)
    beta = ib_selector.adaptive_beta(query_complexity=0.5, budget_remaining=0.1)
    assert beta == 1.0 * 1.5  # Base 1.0 * 1.5

    # High budget -> decrease beta
    beta_high = ib_selector.adaptive_beta(query_complexity=0.5, budget_remaining=0.9)
    assert beta_high == 1.0 * 0.8


@pytest.mark.unit
def test_adaptive_beta_query_complexity(ib_selector):
    # Complex query -> lower beta
    beta_complex = ib_selector.adaptive_beta(query_complexity=0.8, budget_remaining=0.5)
    assert beta_complex == 1.0 * 0.7

    # Simple query -> higher beta
    beta_simple = ib_selector.adaptive_beta(query_complexity=0.2, budget_remaining=0.5)
    assert beta_simple == 1.0 * 1.3


@pytest.mark.unit
def test_adaptive_beta_user_preference(ib_selector):
    # Quality -> 0.5
    assert ib_selector.adaptive_beta(0.5, 0.5, "quality") == 0.5

    # Efficiency -> 2.0
    assert ib_selector.adaptive_beta(0.5, 0.5, "efficiency") == 2.0
