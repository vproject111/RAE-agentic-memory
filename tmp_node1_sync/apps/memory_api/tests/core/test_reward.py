"""
Tests for RAE Reward Function (Iteration 3).

Tests cover:
  1. Reward function creation and configuration
  2. Reward computation for different action types
  3. Quality evaluation heuristics
  4. Metrics tracker integration
  5. Edge cases and error handling
"""

import pytest

from apps.memory_api.core.actions import (
    CallLLMAction,
    PruneContextAction,
    RetrieveEpisodicAction,
    RetrieveSemanticAction,
    UpdateGraphAction,
)
from apps.memory_api.core.metrics import MetricsTracker
from apps.memory_api.core.reward import RewardComponents, RewardFunction
from apps.memory_api.core.state import (
    BudgetState,
    MemoryLayerState,
    MemoryState,
    RAEState,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def reward_function():
    """Create reward function with standard parameters"""
    return RewardFunction(lambda_=0.001, mu=0.01)


@pytest.fixture
def base_state():
    """Create base RAE state for testing"""
    return RAEState(
        tenant_id="test_tenant",
        project_id="test_project",
        budget_state=BudgetState(
            remaining_tokens=100000,
            remaining_cost_usd=10.0,
            latency_budget_ms=60000,
            calls_remaining=100,
        ),
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=100, avg_importance=0.7),
            working=MemoryLayerState(count=10, avg_importance=0.8),
            semantic=MemoryLayerState(count=50, avg_importance=0.6),
            ltm=MemoryLayerState(count=200, avg_importance=0.5),
            reflective=MemoryLayerState(count=5, avg_importance=0.9),
        ),
    )


# ============================================================================
# Test Reward Function Creation
# ============================================================================


def test_reward_function_creation():
    """Test creating reward function with custom hyperparameters"""
    reward_fn = RewardFunction(lambda_=0.002, mu=0.005, discount_factor=0.90)

    assert reward_fn.lambda_ == 0.002
    assert reward_fn.mu == 0.005
    assert reward_fn.gamma == 0.90


def test_reward_function_defaults():
    """Test default hyperparameters"""
    reward_fn = RewardFunction()

    assert reward_fn.lambda_ == 0.001
    assert reward_fn.mu == 0.01
    assert reward_fn.gamma == 0.95


# ============================================================================
# Test Reward Computation
# ============================================================================


def test_reward_computation_basic(reward_function, base_state):
    """Test basic reward computation for retrieval action"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)
    state_after.budget_state.remaining_tokens = 99000  # Used 1000 tokens
    state_after.working_context.token_count = 1000

    action = RetrieveEpisodicAction(parameters={"k": 10})

    execution_result = {"memories_retrieved": 10}

    reward = reward_function.compute_reward(
        state_before=state_before,
        action=action,
        state_after=state_after,
        execution_result=execution_result,
    )

    assert isinstance(reward, RewardComponents)
    assert 0.0 <= reward.quality_score <= 1.0
    assert reward.token_cost == 1000
    assert reward.total_reward < reward.quality_reward  # Penalty reduces total


def test_reward_components_structure(reward_function, base_state):
    """Test that reward components have correct structure"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)

    action = RetrieveEpisodicAction(parameters={"k": 10})
    execution_result = {"memories_retrieved": 10}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Check all components present
    assert hasattr(reward, "quality_score")
    assert hasattr(reward, "token_cost")
    assert hasattr(reward, "latency_cost")
    assert hasattr(reward, "quality_reward")
    assert hasattr(reward, "token_penalty")
    assert hasattr(reward, "latency_penalty")
    assert hasattr(reward, "total_reward")
    assert hasattr(reward, "lambda_weight")
    assert hasattr(reward, "mu_weight")

    # Check to_dict works
    reward_dict = reward.to_dict()
    assert isinstance(reward_dict, dict)
    assert "total_reward" in reward_dict


def test_high_quality_high_reward(reward_function, base_state):
    """Test that high quality actions get high rewards"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)

    action = RetrieveSemanticAction(parameters={"k": 20})

    # High quality result: many relevant memories
    execution_result = {"memories_retrieved": 20}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Quality should be reasonably high (we retrieved many memories)
    assert reward.quality_score > 0.5
    # Total reward might be negative due to costs, but quality component is positive
    assert reward.quality_reward > 0.5


def test_zero_memories_zero_quality(reward_function, base_state):
    """Test that retrieving zero memories gives zero quality"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)

    action = RetrieveEpisodicAction(parameters={"k": 10})

    # No memories retrieved
    execution_result = {"memories_retrieved": 0}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    assert reward.quality_score == 0.0


def test_token_penalty_scaling(base_state):
    """Test that token penalty scales with lambda"""
    # High lambda (expensive tokens)
    reward_fn_expensive = RewardFunction(lambda_=0.01, mu=0.01)

    # Low lambda (cheap tokens)
    reward_fn_cheap = RewardFunction(lambda_=0.0001, mu=0.01)

    state_before = base_state
    state_after = base_state.model_copy(deep=True)
    state_after.budget_state.remaining_tokens = 99000  # Used 1000 tokens

    action = RetrieveEpisodicAction(parameters={"k": 10})
    execution_result = {"memories_retrieved": 10}

    reward_expensive = reward_fn_expensive.compute_reward(
        state_before, action, state_after, execution_result
    )

    reward_cheap = reward_fn_cheap.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Expensive tokens should have larger penalty
    assert reward_expensive.token_penalty > reward_cheap.token_penalty
    # Therefore total reward should be lower
    assert reward_expensive.total_reward < reward_cheap.total_reward


# ============================================================================
# Test Quality Evaluation for Different Action Types
# ============================================================================


def test_retrieval_quality_evaluation(reward_function, base_state):
    """Test quality evaluation for retrieval actions"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)

    action = RetrieveEpisodicAction(parameters={"k": 15})
    execution_result = {"memories_retrieved": 15}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Should have reasonable quality (between 0.5 and 1.0)
    assert 0.5 <= reward.quality_score <= 1.0


def test_llm_quality_evaluation(reward_function, base_state):
    """Test quality evaluation for LLM actions"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)
    state_after.budget_state.remaining_tokens -= 1500

    action = CallLLMAction(parameters={"model": "gpt-4o-mini", "max_tokens": 1000})

    # Mock LLM result
    mock_result = type(
        "obj",
        (object,),
        {
            "text": "This is a reasonable length response from the LLM that should get decent quality score."
        },
    )()
    execution_result = {"llm_result": mock_result}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # LLM output with reasonable length should get decent quality
    assert 0.4 <= reward.quality_score <= 0.8


def test_pruning_quality_evaluation(reward_function, base_state):
    """Test quality evaluation for context pruning"""
    state_before = base_state
    state_before.working_context.token_count = 4000

    state_after = base_state.model_copy(deep=True)
    state_after.working_context.token_count = 2000

    action = PruneContextAction(
        parameters={"strategy": "importance", "target_size": 2000}
    )

    execution_result = {"tokens_saved": 2000, "items_removed": 10}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Good pruning (50% compression) should get high quality
    assert reward.quality_score > 0.8


def test_graph_update_quality_evaluation(reward_function, base_state):
    """Test quality evaluation for graph updates"""
    state_before = base_state
    state_before.graph_state.node_count = 100
    state_before.graph_state.edge_count = 200

    state_after = base_state.model_copy(deep=True)
    state_after.graph_state.node_count = 101  # Added node
    state_after.graph_state.edge_count = 203  # Added edges

    action = UpdateGraphAction(parameters={"operation": "add_node"})

    execution_result = {"node_added": True}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Adding nodes/edges should get positive quality
    assert reward.quality_score >= 0.7


# ============================================================================
# Test Metrics Tracker Integration
# ============================================================================


def test_metrics_tracker_creation():
    """Test creating metrics tracker"""
    tracker = MetricsTracker(window_size=100)

    assert tracker.window_size == 100
    assert tracker.mdp_metrics.total_transitions == 0
    assert tracker.mdp_metrics.cumulative_reward == 0.0


def test_metrics_tracker_records_transition(reward_function, base_state):
    """Test that metrics tracker records transitions"""
    tracker = MetricsTracker()

    state_before = base_state
    state_after = base_state.model_copy(deep=True)
    state_after.budget_state.remaining_tokens = 99000

    action = RetrieveEpisodicAction(parameters={"k": 10})

    reward = reward_function.compute_reward(
        state_before, action, state_after, {"memories_retrieved": 10}
    )

    tracker.record_transition(state_before, action, state_after, reward)

    assert tracker.mdp_metrics.total_transitions == 1
    assert tracker.mdp_metrics.cumulative_reward == reward.total_reward


def test_metrics_tracker_averages(reward_function, base_state):
    """Test that metrics tracker computes averages correctly"""
    tracker = MetricsTracker()

    action = RetrieveEpisodicAction(parameters={"k": 10})

    # Record multiple transitions
    for i in range(5):
        state_before = base_state
        state_after = base_state.model_copy(deep=True)
        state_after.budget_state.remaining_tokens -= 1000 * (i + 1)

        reward = reward_function.compute_reward(
            state_before, action, state_after, {"memories_retrieved": 10}
        )

        tracker.record_transition(state_before, action, state_after, reward)

    assert tracker.mdp_metrics.total_transitions == 5
    assert "retrieve_episodic" in tracker.mdp_metrics.avg_reward_per_action

    # Average quality should be positive
    assert tracker.mdp_metrics.avg_quality_score > 0.0


def test_metrics_best_and_worst_actions(reward_function, base_state):
    """Test getting best and worst performing actions"""
    tracker = MetricsTracker()

    # Record good action
    action_good = RetrieveSemanticAction(parameters={"k": 20})
    state_after_good = base_state.model_copy(deep=True)
    reward_good = reward_function.compute_reward(
        base_state, action_good, state_after_good, {"memories_retrieved": 20}
    )
    tracker.record_transition(base_state, action_good, state_after_good, reward_good)

    # Record bad action (no results)
    action_bad = RetrieveEpisodicAction(parameters={"k": 10})
    state_after_bad = base_state.model_copy(deep=True)
    state_after_bad.budget_state.remaining_tokens -= 5000  # High cost
    reward_bad = reward_function.compute_reward(
        base_state,
        action_bad,
        state_after_bad,
        {"memories_retrieved": 0},  # No results
    )
    tracker.record_transition(base_state, action_bad, state_after_bad, reward_bad)

    best_actions = tracker.get_best_actions(top_k=1)
    worst_actions = tracker.get_worst_actions(top_k=1)

    assert len(best_actions) >= 1
    assert len(worst_actions) >= 1


def test_metrics_get_current_metrics(reward_function, base_state):
    """Test getting current metrics snapshot"""
    tracker = MetricsTracker()

    action = RetrieveEpisodicAction(parameters={"k": 10})
    state_after = base_state.model_copy(deep=True)
    reward = reward_function.compute_reward(
        base_state, action, state_after, {"memories_retrieved": 10}
    )

    tracker.record_transition(base_state, action, state_after, reward)

    metrics = tracker.get_current_metrics()

    assert "mdp" in metrics
    assert "information_bottleneck" in metrics
    assert "graph" in metrics
    assert "metadata" in metrics

    assert metrics["mdp"]["total_transitions"] == 1


# ============================================================================
# Test Edge Cases
# ============================================================================


def test_reward_with_no_execution_result(reward_function, base_state):
    """Test reward computation when execution_result is None"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)

    action = RetrieveEpisodicAction(parameters={"k": 10})

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result=None
    )

    # Should return neutral quality
    assert 0.0 <= reward.quality_score <= 1.0
    assert reward.total_reward is not None


def test_reward_with_zero_cost(reward_function, base_state):
    """Test reward when action has zero cost"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)  # No change

    action = RetrieveEpisodicAction(parameters={"k": 10})
    execution_result = {"memories_retrieved": 10}

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    # Token cost should be zero (no budget change)
    assert reward.token_cost == 0
    assert reward.token_penalty == 0.0


def test_quality_score_clamped_to_0_1(reward_function, base_state):
    """Test that quality scores are always clamped to [0, 1]"""
    state_before = base_state
    state_after = base_state.model_copy(deep=True)

    action = RetrieveEpisodicAction(parameters={"k": 10})

    # Even with extreme inputs, quality should be clamped
    execution_result = {"memories_retrieved": 1000}  # Very high

    reward = reward_function.compute_reward(
        state_before, action, state_after, execution_result
    )

    assert 0.0 <= reward.quality_score <= 1.0
