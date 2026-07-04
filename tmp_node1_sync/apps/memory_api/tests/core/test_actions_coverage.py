import pytest

from apps.memory_api.core.actions import (
    ActionType,
    CallLLMAction,
    ConsolidateEpisodicToWorkingAction,
    GenerateReflectionAction,
    PruneContextAction,
    RetrieveSemanticAction,
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


@pytest.fixture
def real_state():
    return RAEState(
        tenant_id="test_tenant",
        project_id="test_project",
        budget_state=BudgetState(
            remaining_cost_usd=100.0, remaining_tokens=100000, calls_remaining=100
        ),
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=10),
            semantic=MemoryLayerState(count=10),
            working=MemoryLayerState(count=10),
            ltm=MemoryLayerState(count=10),
            reflective=MemoryLayerState(count=10),
        ),
        graph_state=GraphState(node_count=10),
        working_context=WorkingContext(token_count=100),
    )


def test_retrieve_semantic_invalid_no_graph_warning(real_state):
    """Test warning when graph is requested but empty (Line 136)"""
    real_state.graph_state.node_count = 0
    action = RetrieveSemanticAction(
        action_type=ActionType.RETRIEVE_SEMANTIC, parameters={"use_graph": True}
    )

    # This should trigger the warning and return False
    assert action.is_valid_for_state(real_state) is False


def test_retrieve_semantic_cost_with_graph(real_state):
    """Test cost estimation with graph traversal (Line 154)"""
    action = RetrieveSemanticAction(
        action_type=ActionType.RETRIEVE_SEMANTIC,
        parameters={"use_graph": True, "graph_depth": 3, "k": 10},
    )

    cost = action.estimate_cost(real_state)
    # Base latency: k * 10 = 100
    # Graph latency: depth * 50 = 150
    # Total: 250
    assert cost["latency_ms"] == 250


def test_call_llm_invalid_no_context_warning(real_state):
    """Test warning when calling LLM with no context (Line 238, 241)"""
    real_state.working_context.token_count = 0
    action = CallLLMAction(action_type=ActionType.CALL_LLM, parameters={})

    assert action.is_valid_for_state(real_state) is False


def test_call_llm_invalid_tokens_exceeded(real_state):
    """Test validation when estimated tokens exceed budget (Line 272)"""
    real_state.budget_state.remaining_tokens = 10  # Very low budget
    # LLM Action defaults estimate > 10 tokens
    action = CallLLMAction(
        action_type=ActionType.CALL_LLM, parameters={"max_tokens": 1000}
    )

    assert action.is_valid_for_state(real_state) is False


def test_prune_context_validity(real_state):
    """Test PruneContext validity logic (Line 317)"""
    action = PruneContextAction(action_type=ActionType.PRUNE_CONTEXT, parameters={})

    # Case 1: Valid (tokens > 0) - already set in fixture
    assert action.is_valid_for_state(real_state) is True

    # Case 2: Invalid (tokens == 0)
    real_state.working_context.token_count = 0
    assert action.is_valid_for_state(real_state) is False


def test_generate_reflection_invalid_insufficient_memories_log(real_state):
    """Test logging when insufficient memories for reflection (Line 346, 349)"""
    real_state.memory_state.episodic.count = 2
    real_state.memory_state.semantic.count = 2
    # Total = 4. Required default min_cluster_size * 2 = 10.

    action = GenerateReflectionAction(
        action_type=ActionType.GENERATE_REFLECTION, parameters={"min_cluster_size": 5}
    )

    assert action.is_valid_for_state(real_state) is False


def test_update_graph_validity(real_state):
    """Test UpdateGraphAction is always valid (Line 397)"""
    action = UpdateGraphAction(action_type=ActionType.UPDATE_GRAPH, parameters={})
    assert action.is_valid_for_state(real_state) is True


def test_consolidate_episodic_invalid_working_full(real_state):
    """Test consolidation invalid when working memory full (Line 478)"""
    real_state.memory_state.working.count = 101  # > 100 limit

    action = ConsolidateEpisodicToWorkingAction(
        action_type=ActionType.CONSOLIDATE_EPISODIC_TO_WORKING, parameters={}
    )
    assert action.is_valid_for_state(real_state) is False


def test_summarize_context_invalid_budget(real_state):
    """Test summarize context invalid when budget exhausted (Line 549)"""
    real_state.budget_state.remaining_tokens = 0  # Force exhaustion

    action = SummarizeContextAction(
        action_type=ActionType.SUMMARIZE_CONTEXT, parameters={}
    )
    assert action.is_valid_for_state(real_state) is False


def test_summarize_context_invalid_empty(real_state):
    """Test summarize context invalid when context empty (Line 552)"""
    real_state.working_context.token_count = 0

    action = SummarizeContextAction(
        action_type=ActionType.SUMMARIZE_CONTEXT, parameters={}
    )
    assert action.is_valid_for_state(real_state) is False


def test_update_graph_cost_variations(real_state):
    """Test cost estimation for different graph operations (Lines 607, 610)"""
    action_merge = UpdateGraphAction(
        action_type=ActionType.UPDATE_GRAPH, parameters={"operation": "merge_nodes"}
    )
    cost_merge = action_merge.estimate_cost(real_state)
    assert cost_merge["latency_ms"] == 100

    action_prune = UpdateGraphAction(
        action_type=ActionType.UPDATE_GRAPH, parameters={"operation": "prune"}
    )
    cost_prune = action_prune.estimate_cost(real_state)
    assert cost_prune["latency_ms"] == 200
