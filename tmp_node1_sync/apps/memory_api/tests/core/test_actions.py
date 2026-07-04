"""
Tests for RAE Action Space.

Tests the mathematical formalization of action space:
  a_t in A (action space)
"""

import pytest

from apps.memory_api.core.actions import (
    ActionType,
    CallLLMAction,
    ConsolidateEpisodicToWorkingAction,
    GenerateReflectionAction,
    PruneContextAction,
    RetrieveEpisodicAction,
    RetrieveLTMAction,
    RetrieveReflectiveAction,
    RetrieveSemanticAction,
    RetrieveWorkingAction,
    SummarizeContextAction,
    UpdateGraphAction,
)
from apps.memory_api.core.state import (
    BudgetState,
    GraphState,
    MemoryLayerState,
    MemoryState,
    RAEState,
    WorkingContext,
)


@pytest.mark.unit
def test_action_type_enum():
    """Test ActionType enum has all expected values"""
    assert ActionType.RETRIEVE_EPISODIC == "retrieve_episodic"
    assert ActionType.RETRIEVE_SEMANTIC == "retrieve_semantic"
    assert ActionType.CALL_LLM == "call_llm"
    assert ActionType.GENERATE_REFLECTION == "generate_reflection"
    assert ActionType.UPDATE_GRAPH == "update_graph"


@pytest.mark.unit
def test_retrieve_episodic_action_creation():
    """Test RetrieveEpisodicAction creation"""
    action = RetrieveEpisodicAction(
        parameters={"k": 10, "threshold": 0.7}, reason="User query requires context"
    )

    assert action.action_type == ActionType.RETRIEVE_EPISODIC
    assert action.parameters["k"] == 10
    assert action.reason == "User query requires context"


@pytest.mark.unit
def test_retrieve_episodic_valid_state():
    """Test RetrieveEpisodicAction validity with valid state"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=10000),
        memory_state=MemoryState(episodic=MemoryLayerState(count=50)),
    )

    action = RetrieveEpisodicAction(parameters={"k": 10})

    assert action.is_valid_for_state(state)


@pytest.mark.unit
def test_retrieve_episodic_invalid_no_memories():
    """Test RetrieveEpisodicAction invalid with no episodic memories"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(episodic=MemoryLayerState(count=0)),
    )

    action = RetrieveEpisodicAction(parameters={"k": 10})

    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_retrieve_episodic_invalid_budget_exhausted():
    """Test RetrieveEpisodicAction invalid with exhausted budget"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=0),
        memory_state=MemoryState(episodic=MemoryLayerState(count=50)),
    )

    action = RetrieveEpisodicAction(parameters={"k": 10})

    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_retrieve_episodic_cost_estimation():
    """Test RetrieveEpisodicAction cost estimation"""
    state = RAEState(tenant_id="test", project_id="test")

    action = RetrieveEpisodicAction(parameters={"k": 15})

    costs = action.estimate_cost(state)

    assert costs["tokens"] == 1500  # 15 * 100
    assert costs["cost_usd"] == 0.0  # No LLM cost
    assert costs["latency_ms"] == 75  # 15 * 5


@pytest.mark.unit
def test_retrieve_working_action():
    """Test RetrieveWorkingAction"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(working=MemoryLayerState(count=10)),
    )

    action = RetrieveWorkingAction(parameters={"k": 5})

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 400  # 5 * 80
    assert costs["latency_ms"] == 15  # 5 * 3


@pytest.mark.unit
def test_retrieve_semantic_without_graph():
    """Test RetrieveSemanticAction without graph"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(semantic=MemoryLayerState(count=100)),
    )

    action = RetrieveSemanticAction(parameters={"k": 20, "use_graph": False})

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 3000  # 20 * 150


@pytest.mark.unit
def test_retrieve_semantic_with_graph():
    """Test RetrieveSemanticAction with graph traversal"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(semantic=MemoryLayerState(count=100)),
        graph_state=GraphState(node_count=200, edge_count=400),
    )

    action = RetrieveSemanticAction(
        parameters={"k": 20, "use_graph": True, "graph_depth": 3}
    )

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    # Tokens: 20 * 150 = 3000
    # Latency: 20 * 10 + 3 * 50 = 350
    assert costs["tokens"] == 3000
    assert costs["latency_ms"] == 350


@pytest.mark.unit
def test_retrieve_semantic_invalid_no_graph():
    """Test RetrieveSemanticAction invalid when graph required but missing"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(semantic=MemoryLayerState(count=100)),
        graph_state=GraphState(node_count=0),  # No graph
    )

    action = RetrieveSemanticAction(parameters={"k": 20, "use_graph": True})

    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_retrieve_ltm_action():
    """Test RetrieveLTMAction"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(ltm=MemoryLayerState(count=50)),
    )

    action = RetrieveLTMAction(parameters={"k": 10, "min_stability": 0.8})

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 2000  # 10 * 200
    assert costs["latency_ms"] == 150  # 10 * 15


@pytest.mark.unit
def test_retrieve_reflective_action():
    """Test RetrieveReflectiveAction"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(reflective=MemoryLayerState(count=10)),
    )

    action = RetrieveReflectiveAction(parameters={"level": "L2", "k": 5})

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 1500  # 5 * 300


@pytest.mark.unit
def test_call_llm_action_valid():
    """Test CallLLMAction with valid state"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(content=["memory 1"], token_count=500),
        budget_state=BudgetState(remaining_tokens=10000, remaining_cost_usd=5.0),
    )

    action = CallLLMAction(parameters={"model": "gpt-4o-mini", "max_tokens": 1000})

    assert action.is_valid_for_state(state)


@pytest.mark.unit
def test_call_llm_action_invalid_no_context():
    """Test CallLLMAction invalid with no context"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=0),
    )

    action = CallLLMAction(parameters={"model": "gpt-4o-mini", "max_tokens": 1000})

    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_call_llm_action_cost_estimation():
    """Test CallLLMAction cost estimation"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=2000),
    )

    action = CallLLMAction(parameters={"model": "gpt-4o-mini", "max_tokens": 1000})

    costs = action.estimate_cost(state)

    assert costs["tokens"] == 3000  # 2000 input + 1000 output
    assert costs["cost_usd"] > 0  # Should have some cost
    assert costs["latency_ms"] > 1000  # Base latency + output


@pytest.mark.unit
def test_call_llm_action_exceeds_budget():
    """Test CallLLMAction invalid when exceeding budget"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=2000),
        budget_state=BudgetState(
            remaining_tokens=10000, remaining_cost_usd=0.001
        ),  # Very low budget
    )

    action = CallLLMAction(parameters={"model": "gpt-4o", "max_tokens": 10000})

    # Should be invalid because estimated cost exceeds budget
    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_prune_context_action():
    """Test PruneContextAction"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=5000),
    )

    action = PruneContextAction(
        parameters={"strategy": "importance", "target_size": 2000}
    )

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 0  # No token cost
    assert costs["cost_usd"] == 0.0
    assert costs["latency_ms"] == 10  # Fast


@pytest.mark.unit
def test_prune_context_invalid_empty():
    """Test PruneContextAction invalid with empty context"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=0),
    )

    action = PruneContextAction(
        parameters={"strategy": "importance", "target_size": 2000}
    )

    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_generate_reflection_action_valid():
    """Test GenerateReflectionAction with sufficient memories"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=50), semantic=MemoryLayerState(count=100)
        ),
        budget_state=BudgetState(remaining_tokens=100000, remaining_cost_usd=10.0),
    )

    action = GenerateReflectionAction(
        parameters={"max_memories": 100, "min_cluster_size": 5, "level": "L1"}
    )

    assert action.is_valid_for_state(state)


@pytest.mark.unit
def test_generate_reflection_action_invalid_insufficient_memories():
    """Test GenerateReflectionAction invalid with insufficient memories"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=3), semantic=MemoryLayerState(count=2)
        ),
    )

    action = GenerateReflectionAction(
        parameters={"max_memories": 100, "min_cluster_size": 5}
    )

    # Need min_cluster_size * 2 = 10 memories, only have 5
    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_generate_reflection_cost_estimation():
    """Test GenerateReflectionAction cost estimation"""
    state = RAEState(tenant_id="test", project_id="test")

    action = GenerateReflectionAction(
        parameters={"max_memories": 100, "min_cluster_size": 5}
    )

    costs = action.estimate_cost(state)

    # 100 / 5 = 20 clusters, 20 * 2000 = 40000 tokens
    assert costs["tokens"] == 40000
    assert costs["cost_usd"] > 0
    assert costs["latency_ms"] > 5000  # Includes clustering time


@pytest.mark.unit
def test_update_graph_action():
    """Test UpdateGraphAction"""
    state = RAEState(tenant_id="test", project_id="test")

    action = UpdateGraphAction(
        parameters={"operation": "add_node", "node_data": {"name": "test"}}
    )

    # Always valid
    assert action.is_valid_for_state(state)

    costs = action.estimate_cost(state)
    assert costs["tokens"] == 0
    assert costs["cost_usd"] == 0.0
    assert costs["latency_ms"] == 20  # Fast local operation


@pytest.mark.unit
def test_consolidate_episodic_to_working_action():
    """Test ConsolidateEpisodicToWorkingAction"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=50), working=MemoryLayerState(count=10)
        ),
    )

    action = ConsolidateEpisodicToWorkingAction(
        parameters={"max_memories": 10, "min_importance": 0.6}
    )

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 0  # No LLM cost
    assert costs["latency_ms"] == 50  # 10 * 5


@pytest.mark.unit
def test_consolidate_invalid_no_episodic():
    """Test ConsolidateEpisodicToWorkingAction invalid with no episodic memories"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(episodic=MemoryLayerState(count=0)),
    )

    action = ConsolidateEpisodicToWorkingAction(parameters={"max_memories": 10})

    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_consolidate_invalid_working_full():
    """Test ConsolidateEpisodicToWorkingAction invalid with full working memory"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=50), working=MemoryLayerState(count=150)
        ),
    )

    action = ConsolidateEpisodicToWorkingAction(parameters={"max_memories": 10})

    # Working memory "full" (> 100)
    assert not action.is_valid_for_state(state)


@pytest.mark.unit
def test_summarize_context_extractive():
    """Test SummarizeContextAction with extractive method"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=5000),
    )

    action = SummarizeContextAction(
        parameters={"compression_ratio": 0.5, "method": "extractive"}
    )

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 0  # No LLM for extractive
    assert costs["cost_usd"] == 0.0
    assert costs["latency_ms"] == 50


@pytest.mark.unit
def test_summarize_context_abstractive():
    """Test SummarizeContextAction with abstractive method"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=4000),
    )

    action = SummarizeContextAction(
        parameters={"compression_ratio": 0.5, "method": "abstractive"}
    )

    assert action.is_valid_for_state(state)
    costs = action.estimate_cost(state)
    assert costs["tokens"] == 6000  # 4000 input + 2000 output
    assert costs["cost_usd"] > 0
    assert costs["latency_ms"] > 2000


@pytest.mark.unit
def test_action_serialization():
    """Test action can be serialized to dict"""
    action = RetrieveEpisodicAction(
        parameters={"k": 10, "threshold": 0.7}, reason="Test reason"
    )

    action_dict = action.to_dict()

    assert action_dict["action_type"] == "retrieve_episodic"
    assert action_dict["parameters"]["k"] == 10
    assert action_dict["reason"] == "Test reason"
    assert "created_at" in action_dict


@pytest.mark.unit
def test_multiple_actions_in_sequence():
    """Test multiple actions can be created and validated in sequence"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        working_context=WorkingContext(token_count=1000),
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=50), semantic=MemoryLayerState(count=100)
        ),
        budget_state=BudgetState(remaining_tokens=10000, remaining_cost_usd=5.0),
    )

    # Sequence of actions
    action1 = RetrieveEpisodicAction(parameters={"k": 10})
    action2 = RetrieveSemanticAction(parameters={"k": 20})
    action3 = CallLLMAction(parameters={"model": "gpt-4o-mini", "max_tokens": 500})

    # All should be valid for this state
    assert action1.is_valid_for_state(state)
    assert action2.is_valid_for_state(state)
    assert action3.is_valid_for_state(state)

    # Total estimated cost
    total_cost = (
        action1.estimate_cost(state)["cost_usd"]
        + action2.estimate_cost(state)["cost_usd"]
        + action3.estimate_cost(state)["cost_usd"]
    )

    assert total_cost <= state.budget_state.remaining_cost_usd
