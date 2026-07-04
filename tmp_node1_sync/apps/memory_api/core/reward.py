"""
RAE Reward Function - Formal objective for optimization.

Mathematical formulation:
  R(s_t, a_t, s_{t+1}) = Quality(s_{t+1}) - λ·TokenCost(a_t) - μ·Latency(a_t)

Where:
  - Quality: How well does action serve the goal? (0-1)
  - TokenCost: Resource consumption (tokens used)
  - Latency: Time cost (milliseconds)
  - λ, μ: Hyperparameters balancing quality vs cost

Goal: Learn policy π* that maximizes cumulative reward:
  π* = argmax_π E[Σ γ^t · R(s_t, a_t, s_{t+1})]
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

import structlog

from apps.memory_api.core.actions import Action, ActionType
from apps.memory_api.core.state import RAEState
from apps.memory_api.observability.rae_tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


@dataclass
class RewardComponents:
    """
    Breakdown of reward into interpretable components.

    Useful for:
      - Debugging policy behavior
      - Hyperparameter tuning
      - Understanding trade-offs
    """

    quality_score: float  # 0-1
    token_cost: float  # Absolute tokens used
    latency_cost: float  # Absolute milliseconds

    # Weighted components
    quality_reward: float
    token_penalty: float
    latency_penalty: float

    # Final reward
    total_reward: float

    # Metadata
    lambda_weight: float  # Token cost weight
    mu_weight: float  # Latency cost weight

    def to_dict(self) -> Dict:
        return {
            "quality_score": self.quality_score,
            "token_cost": self.token_cost,
            "latency_cost": self.latency_cost,
            "quality_reward": self.quality_reward,
            "token_penalty": self.token_penalty,
            "latency_penalty": self.latency_penalty,
            "total_reward": self.total_reward,
            "lambda_weight": self.lambda_weight,
            "mu_weight": self.mu_weight,
        }


class RewardFunction:
    """
    Computes rewards for state-action-state transitions.

    Usage:
        reward_fn = RewardFunction(lambda_=0.001, mu=0.01)

        # After action execution
        transition = executor.get_last_transition()
        reward = reward_fn.compute_reward(
            state_before=transition["state_before"],
            action=transition["action"],
            state_after=transition["state_after"],
            execution_result=transition["execution_result"]
        )

        # Log reward
        logger.info("reward_computed", reward=reward.to_dict())
    """

    def __init__(
        self,
        lambda_: float = 0.001,  # Token cost weight: $1 = 1000 reward points
        mu: float = 0.01,  # Latency weight: 1ms = 0.01 penalty
        discount_factor: float = 0.95,
    ):
        """
        Initialize reward function with hyperparameters.

        Args:
            lambda_: Weight for token cost penalty
            mu: Weight for latency penalty
            discount_factor: Discount factor for future rewards (γ)
        """
        self.lambda_ = lambda_
        self.mu = mu
        self.gamma = discount_factor

    def compute_reward(
        self,
        state_before: RAEState,
        action: Action,
        state_after: RAEState,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> RewardComponents:
        """
        Compute reward for state-action-state transition.

        R(s_t, a_t, s_{t+1}) = Quality(s_{t+1}) - λ·tokens - μ·latency

        Args:
            state_before: State before action
            action: Action taken
            state_after: State after action
            execution_result: Optional execution metadata

        Returns:
            RewardComponents with detailed breakdown
        """
        with tracer.start_as_current_span("rae.reward.compute") as span:
            span.set_attribute("rae.action.type", action.action_type.value)
            span.set_attribute("rae.tenant_id", state_after.tenant_id)
            span.set_attribute("rae.project_id", state_after.project_id)
            span.set_attribute("rae.reward.lambda", self.lambda_)
            span.set_attribute("rae.reward.mu", self.mu)
            span.set_attribute("rae.reward.gamma", self.gamma)

            # Component 1: Quality
            quality_score = self._evaluate_quality(
                state_before, action, state_after, execution_result
            )
            span.set_attribute("rae.reward.quality_score", quality_score)

            # Component 2: Token cost
            state_delta = state_after.compare(state_before)
            token_cost = abs(state_delta["token_delta"])  # Tokens consumed
            span.set_attribute("rae.reward.token_cost", token_cost)

            # Component 3: Latency
            latency_cost = state_delta["time_delta_ms"]
            span.set_attribute("rae.reward.latency_cost_ms", latency_cost)

            # Compute weighted components
            quality_reward = quality_score  # Already 0-1
            token_penalty = self.lambda_ * token_cost
            latency_penalty = self.mu * latency_cost

            span.set_attribute("rae.reward.quality_reward", quality_reward)
            span.set_attribute("rae.reward.token_penalty", token_penalty)
            span.set_attribute("rae.reward.latency_penalty", latency_penalty)

            # Total reward
            total_reward = quality_reward - token_penalty - latency_penalty
            span.set_attribute("rae.reward.total", total_reward)

            components = RewardComponents(
                quality_score=quality_score,
                token_cost=token_cost,
                latency_cost=latency_cost,
                quality_reward=quality_reward,
                token_penalty=token_penalty,
                latency_penalty=latency_penalty,
                total_reward=total_reward,
                lambda_weight=self.lambda_,
                mu_weight=self.mu,
            )

            logger.debug(
                "reward_computed",
                action_type=action.action_type.value,
                reward_components=components.to_dict(),
            )

            return components

    def _evaluate_quality(
        self,
        state_before: RAEState,
        action: Action,
        state_after: RAEState,
        execution_result: Optional[Dict] = None,
    ) -> float:
        """
        Evaluate quality of action outcome.

        Quality metrics depend on action type:
          - Retrieval: Relevance of retrieved memories
          - LLM call: Output quality (requires user feedback or heuristics)
          - Reflection: Novelty and importance of generated reflections
          - Graph update: Centrality improvement

        Returns quality score 0-1 (higher is better).

        NOTE: This is a HEURISTIC implementation. In production, quality should be:
          - Learned from user feedback
          - Measured via A/B testing
          - Proxy metrics (click-through, engagement, etc.)
        """
        with tracer.start_as_current_span("rae.reward.evaluate_quality") as span:
            action_type = action.action_type
            span.set_attribute("rae.action.type", action_type.value)

            if action_type in [
                ActionType.RETRIEVE_EPISODIC,
                ActionType.RETRIEVE_SEMANTIC,
                ActionType.RETRIEVE_WORKING,
                ActionType.RETRIEVE_LTM,
                ActionType.RETRIEVE_REFLECTIVE,
            ]:
                # Quality = relevance + diversity of retrieved memories
                span.set_attribute("rae.reward.quality_method", "retrieval")
                quality = self._evaluate_retrieval_quality(execution_result)

            elif action_type == ActionType.CALL_LLM:
                # Quality = heuristic based on output length and coherence
                # (In production: user feedback, human ratings, etc.)
                span.set_attribute("rae.reward.quality_method", "llm_output")
                quality = self._evaluate_llm_quality(execution_result)

            elif action_type == ActionType.GENERATE_REFLECTION:
                # Quality = novelty and importance scores from reflection
                span.set_attribute("rae.reward.quality_method", "reflection")
                quality = self._evaluate_reflection_quality(execution_result)

            elif action_type == ActionType.PRUNE_CONTEXT:
                # Quality = how much we compressed while preserving importance
                span.set_attribute("rae.reward.quality_method", "pruning")
                quality = self._evaluate_pruning_quality(
                    state_before, state_after, execution_result
                )

            elif action_type == ActionType.UPDATE_GRAPH:
                # Quality = graph structure improvement
                span.set_attribute("rae.reward.quality_method", "graph_update")
                quality = self._evaluate_graph_update_quality(state_before, state_after)

            else:
                # Default: neutral quality
                span.set_attribute("rae.reward.quality_method", "default")
                quality = 0.5

            clamped_quality = max(0.0, min(1.0, quality))
            span.set_attribute("rae.reward.quality_raw", quality)
            span.set_attribute("rae.reward.quality_clamped", clamped_quality)

            return clamped_quality  # Clamp to [0, 1]

    def _evaluate_retrieval_quality(self, execution_result: Optional[Dict]) -> float:
        """
        Evaluate quality of memory retrieval.

        Heuristics:
          - More memories retrieved = higher quality (up to a point)
          - Higher average relevance score = higher quality
          - Diversity bonus
        """
        if not execution_result:
            return 0.5

        memories_retrieved = execution_result.get("memories_retrieved", 0)

        if memories_retrieved == 0:
            return 0.0

        # Base quality from count (diminishing returns)
        count_score = min(1.0, memories_retrieved / 20.0)  # Max at 20 memories

        # TODO: Add relevance scoring when available
        # relevance_score = execution_result.get("avg_relevance", 0.7)
        relevance_score = 0.7  # Assume decent relevance

        # Combine
        quality = 0.6 * relevance_score + 0.4 * count_score

        return float(quality)

    def _evaluate_llm_quality(self, execution_result: Optional[Dict]) -> float:
        """
        Evaluate quality of LLM output.

        PLACEHOLDER: In production, this should use:
          - User feedback (thumbs up/down)
          - Human ratings
          - Automated metrics (BLEU, ROUGE, etc.)
          - Task-specific evaluation

        For now: heuristic based on output length and presence of result.
        """
        if not execution_result:
            return 0.5

        llm_result = execution_result.get("llm_result")

        if not llm_result:
            return 0.0

        # Heuristic: assume reasonable length output is good
        output_text = (
            llm_result.text if hasattr(llm_result, "text") else str(llm_result)
        )
        output_length = len(output_text)

        if output_length == 0:
            return 0.0
        elif output_length < 50:
            return 0.4  # Very short, might be low quality
        elif output_length > 2000:
            return 0.7  # Long, probably detailed
        else:
            return 0.6  # Reasonable length

    def _evaluate_reflection_quality(self, execution_result: Optional[Dict]) -> float:
        """
        Evaluate quality of generated reflections.

        Uses reflection scoring: novelty, importance, utility, confidence.
        """
        if not execution_result:
            return 0.5

        reflections = execution_result.get("reflections", [])

        if not reflections:
            return 0.0

        # Average composite score across reflections
        scores = []
        for reflection in reflections:
            if hasattr(reflection, "scoring") and reflection.scoring:
                composite_score = reflection.scoring.composite_score
                scores.append(composite_score)

        if scores:
            avg_quality = sum(scores) / len(scores)
            return float(avg_quality)
        else:
            return 0.6  # Default if no scoring available

    def _evaluate_pruning_quality(
        self,
        state_before: RAEState,
        state_after: RAEState,
        execution_result: Optional[Dict],
    ) -> float:
        """
        Evaluate quality of context pruning.

        Good pruning:
          - Removes many tokens (high compression)
          - Preserves high-importance items
        """
        if not execution_result:
            return 0.5

        tokens_saved = execution_result.get("tokens_saved", 0)

        if tokens_saved == 0:
            return 0.0

        # Compression ratio
        compression_ratio = tokens_saved / max(
            1, state_before.working_context.token_count
        )

        # Quality = compression achieved (good pruning removes a lot)
        quality = min(1.0, compression_ratio * 2)  # Max at 50% compression

        return float(quality)

    def _evaluate_graph_update_quality(
        self, state_before: RAEState, state_after: RAEState
    ) -> float:
        """
        Evaluate quality of graph update.

        Good graph updates:
          - Increase connectivity (more edges relative to nodes)
          - Improve centrality distribution
          - Add valuable nodes
        """
        nodes_before = state_before.graph_state.node_count
        nodes_after = state_after.graph_state.node_count

        edges_before = state_before.graph_state.edge_count
        edges_after = state_after.graph_state.edge_count

        # Heuristic: adding edges or nodes is positive
        if nodes_after > nodes_before or edges_after > edges_before:
            quality = 0.7
        elif nodes_after == nodes_before and edges_after == edges_before:
            quality = 0.5  # No change
        else:
            quality = 0.6  # Pruning (might be good for cleanup)

        return quality
