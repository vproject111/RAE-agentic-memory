"""
Tests for RAE State Representation.

Tests the mathematical formalization of system state:
  s_t = (working_context, memory_state, budget_state, graph_state)
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from apps.memory_api.core.state import (
    BudgetState,
    GraphState,
    MemoryLayerState,
    MemoryState,
    RAEState,
    WorkingContext,
)


@pytest.mark.unit
def test_working_context_creation():
    """Test WorkingContext creation and serialization"""
    context = WorkingContext(
        content=["memory 1", "memory 2", "memory 3"],
        token_count=150,
        importance_scores=[0.8, 0.6, 0.9],
        source_memory_ids=[uuid4(), uuid4(), uuid4()],
    )

    assert len(context.content) == 3
    assert context.token_count == 150
    assert len(context.importance_scores) == 3

    # Test serialization
    context_dict = context.to_dict()
    assert context_dict["token_count"] == 150
    assert context_dict["memory_count"] == 3
    assert abs(context_dict["avg_importance"] - 0.7667) < 0.01


@pytest.mark.unit
def test_memory_layer_state():
    """Test MemoryLayerState creation and serialization"""
    layer = MemoryLayerState(
        count=42,
        avg_importance=0.75,
        coverage=0.85,
        avg_age_hours=24.5,
        last_consolidated=datetime.now(),
    )

    assert layer.count == 42
    assert layer.avg_importance == 0.75

    # Test serialization
    layer_dict = layer.to_dict()
    assert layer_dict["count"] == 42
    assert layer_dict["avg_importance"] == 0.75
    assert "last_consolidated" in layer_dict


@pytest.mark.unit
def test_memory_state_total_count():
    """Test MemoryState total count calculation"""
    memory_state = MemoryState(
        episodic=MemoryLayerState(count=10),
        working=MemoryLayerState(count=5),
        semantic=MemoryLayerState(count=50),
        ltm=MemoryLayerState(count=100),
        reflective=MemoryLayerState(count=8),
    )

    assert memory_state.total_count() == 173

    # Test serialization includes total
    state_dict = memory_state.to_dict()
    assert state_dict["total_count"] == 173


@pytest.mark.unit
def test_budget_state_exhaustion():
    """Test BudgetState exhaustion checking"""
    # Normal budget - not exhausted
    budget = BudgetState(
        remaining_tokens=10000, remaining_cost_usd=5.0, latency_budget_ms=10000
    )
    assert not budget.is_exhausted()
    assert budget.to_dict()["is_exhausted"] is False

    # Exhausted by tokens
    budget_no_tokens = BudgetState(remaining_tokens=0)
    assert budget_no_tokens.is_exhausted()

    # Exhausted by cost
    budget_no_cost = BudgetState(remaining_cost_usd=0.0)
    assert budget_no_cost.is_exhausted()

    # Exhausted by latency
    budget_no_latency = BudgetState(latency_budget_ms=0)
    assert budget_no_latency.is_exhausted()

    # Exhausted by calls
    budget_no_calls = BudgetState(calls_remaining=0)
    assert budget_no_calls.is_exhausted()


@pytest.mark.unit
def test_graph_state():
    """Test GraphState creation and serialization"""
    graph = GraphState(
        node_count=150,
        edge_count=300,
        avg_centrality=0.42,
        connected_components=3,
        last_updated=datetime.now(),
    )

    assert graph.node_count == 150
    assert graph.edge_count == 300

    graph_dict = graph.to_dict()
    assert graph_dict["node_count"] == 150
    assert "last_updated" in graph_dict


@pytest.mark.unit
def test_rae_state_creation():
    """Test basic RAEState creation"""
    state = RAEState(tenant_id="test", project_id="test-project")

    assert state.tenant_id == "test"
    assert state.project_id == "test-project"
    assert state.is_valid()

    # Check defaults initialized
    assert state.working_context.token_count == 0
    assert state.budget_state.remaining_tokens == 100000
    assert state.memory_state.total_count() == 0


@pytest.mark.unit
def test_rae_state_with_full_initialization():
    """Test RAEState with all components initialized"""
    state = RAEState(
        tenant_id="test",
        project_id="test-project",
        session_id="session-123",
        working_context=WorkingContext(
            content=["memory 1", "memory 2"],
            token_count=100,
            importance_scores=[0.8, 0.9],
        ),
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=10, avg_importance=0.7),
            semantic=MemoryLayerState(count=50, avg_importance=0.85),
        ),
        budget_state=BudgetState(remaining_tokens=50000, remaining_cost_usd=5.0),
        graph_state=GraphState(node_count=100, edge_count=200),
    )

    assert state.is_valid()
    assert state.session_id == "session-123"
    assert state.working_context.token_count == 100
    assert state.memory_state.total_count() == 60  # 10 + 50
    assert state.graph_state.node_count == 100


@pytest.mark.unit
def test_rae_state_validation_budget_exhausted():
    """Test RAEState validation with exhausted budget"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=0),  # Exhausted
    )

    assert not state.is_valid()


@pytest.mark.unit
def test_rae_state_validation_negative_tokens():
    """Test RAEState validation with negative token count"""
    state = RAEState(tenant_id="test", project_id="test")

    # Manually set invalid value (in real usage, this shouldn't happen)
    state.working_context.token_count = -100

    assert not state.is_valid()


@pytest.mark.unit
def test_rae_state_comparison():
    """Test state delta computation via compare()"""
    state1 = RAEState(
        tenant_id="test",
        project_id="test",
        timestamp=datetime.now(),
        budget_state=BudgetState(remaining_tokens=100000, remaining_cost_usd=10.0),
        working_context=WorkingContext(content=["memory 1"], token_count=50),
        graph_state=GraphState(node_count=100, edge_count=200),
    )

    # Simulate state after action
    state2 = RAEState(
        tenant_id="test",
        project_id="test",
        timestamp=datetime.now() + timedelta(milliseconds=500),
        budget_state=BudgetState(remaining_tokens=95000, remaining_cost_usd=9.5),
        working_context=WorkingContext(
            content=["memory 1", "memory 2", "memory 3"], token_count=200
        ),
        graph_state=GraphState(node_count=105, edge_count=210),
    )

    delta = state2.compare(state1)

    # Check deltas
    assert delta["token_delta"] == -5000  # Used 5000 tokens
    assert delta["cost_delta"] == -0.5  # Spent $0.50
    assert delta["context_size_delta"] == 150  # Added 150 tokens to context
    assert delta["graph_nodes_delta"] == 5  # Added 5 nodes
    assert delta["graph_edges_delta"] == 10  # Added 10 edges
    assert delta["time_delta_ms"] >= 500  # At least 500ms elapsed


@pytest.mark.unit
def test_rae_state_serialization():
    """Test RAEState can be fully serialized to dict"""
    state = RAEState(
        tenant_id="test",
        project_id="test-project",
        session_id="session-123",
        working_context=WorkingContext(content=["memory 1"], token_count=50),
        budget_state=BudgetState(remaining_tokens=50000),
        last_action={"type": "retrieve_episodic", "params": {"k": 10}},
    )

    state_dict = state.to_dict()

    # Check all components present
    assert state_dict["tenant_id"] == "test"
    assert state_dict["project_id"] == "test-project"
    assert state_dict["session_id"] == "session-123"
    assert "timestamp" in state_dict
    assert "working_context" in state_dict
    assert "memory_state" in state_dict
    assert "budget_state" in state_dict
    assert "graph_state" in state_dict
    assert "last_action" in state_dict

    # Check nested serialization
    assert state_dict["working_context"]["token_count"] == 50
    assert state_dict["budget_state"]["remaining_tokens"] == 50000
    assert state_dict["last_action"]["type"] == "retrieve_episodic"


@pytest.mark.unit
def test_rae_state_log_state():
    """Test state logging doesn't raise errors"""
    state = RAEState(tenant_id="test", project_id="test-project")

    # Should not raise
    state.log_state("test_event")


@pytest.mark.unit
def test_memory_state_serialization():
    """Test MemoryState serialization includes all layers"""
    memory_state = MemoryState(
        episodic=MemoryLayerState(count=10),
        working=MemoryLayerState(count=5),
        semantic=MemoryLayerState(count=50),
        ltm=MemoryLayerState(count=100),
        reflective=MemoryLayerState(count=8),
    )

    state_dict = memory_state.to_dict()

    assert "episodic" in state_dict
    assert "working" in state_dict
    assert "semantic" in state_dict
    assert "ltm" in state_dict
    assert "reflective" in state_dict
    assert state_dict["total_count"] == 173


@pytest.mark.unit
def test_working_context_empty_importance():
    """Test WorkingContext handles empty importance scores"""
    context = WorkingContext(content=["memory 1", "memory 2"], token_count=100)

    # No importance scores set
    assert len(context.importance_scores) == 0

    context_dict = context.to_dict()
    assert context_dict["avg_importance"] == 0.0


@pytest.mark.unit
def test_state_comparison_time_delta():
    """Test state comparison correctly calculates time delta"""
    t1 = datetime.now()
    state1 = RAEState(tenant_id="test", project_id="test", timestamp=t1)

    t2 = t1 + timedelta(seconds=2)
    state2 = RAEState(tenant_id="test", project_id="test", timestamp=t2)

    delta = state2.compare(state1)

    # Should be approximately 2000ms
    assert 1900 <= delta["time_delta_ms"] <= 2100


@pytest.mark.unit
def test_budget_state_partial_exhaustion():
    """Test budget can be partially exhausted"""
    budget = BudgetState(
        remaining_tokens=1000,  # Low but not zero
        remaining_cost_usd=10.0,  # Good
        latency_budget_ms=30000,  # Good
        calls_remaining=100,  # Good
    )

    # Should be valid (not fully exhausted)
    assert not budget.is_exhausted()

    # Now exhaust tokens
    budget.remaining_tokens = 0
    assert budget.is_exhausted()


@pytest.mark.unit
def test_memory_layer_none_values():
    """Test MemoryLayerState handles None values gracefully"""
    layer = MemoryLayerState(count=10, last_consolidated=None)

    layer_dict = layer.to_dict()
    assert layer_dict["last_consolidated"] is None


@pytest.mark.unit
def test_rae_state_identity_fields():
    """Test RAEState identity fields (tenant, project, session)"""
    state = RAEState(
        tenant_id="tenant-123", project_id="project-456", session_id="session-789"
    )

    assert state.tenant_id == "tenant-123"
    assert state.project_id == "project-456"
    assert state.session_id == "session-789"


@pytest.mark.unit
def test_rae_state_validation_mismatched_importance_scores():
    """Test RAEState validation warns on mismatched content and importance scores."""
    state = RAEState(tenant_id="test", project_id="test")

    state.working_context.content = ["item1", "item2"]
    state.working_context.importance_scores = [0.5]  # Mismatched length

    # The validation should still return True as it's a warning, not an error
    assert state.is_valid()


@pytest.mark.unit
def test_rae_state_validation_negative_memory_count():
    """Test RAEState validation fails with negative memory layer count."""
    state = RAEState(tenant_id="test", project_id="test")

    # Manually set an invalid negative count
    state.memory_state.episodic.count = -5

    assert not state.is_valid()
