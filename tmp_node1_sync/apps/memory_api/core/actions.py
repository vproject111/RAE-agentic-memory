"""
RAE Action Space - Formalization of all system operations.

Mathematical notation: a_t ∈ A

Actions are the primitives that transform state:
  s_{t+1} = T(s_t, a_t)  (deterministic transition)

Each action has:
  - Type: What operation to perform
  - Parameters: Configuration for the operation
  - Cost estimation: Expected resource usage
  - Preconditions: State requirements

Usage:
    # Create action
    action = RetrieveEpisodicAction(
        parameters={"k": 10, "threshold": 0.7},
        reason="User query requires recent context"
    )

    # Check if action is valid for current state
    if action.is_valid_for_state(current_state):
        costs = action.estimate_cost(current_state)
        logger.info("action_cost_estimate", costs=costs)
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

import structlog
from pydantic import BaseModel, ConfigDict, Field

from apps.memory_api.core.state import RAEState
from apps.memory_api.observability.rae_tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


class ActionType(str, Enum):
    """All possible action types in RAE system"""

    # Retrieval actions
    RETRIEVE_EPISODIC = "retrieve_episodic"
    RETRIEVE_WORKING = "retrieve_working"
    RETRIEVE_SEMANTIC = "retrieve_semantic"
    RETRIEVE_LTM = "retrieve_ltm"
    RETRIEVE_REFLECTIVE = "retrieve_reflective"
    RETRIEVE_HYBRID = "retrieve_hybrid"

    # Memory management actions
    UPDATE_MEMORY = "update_memory"
    CONSOLIDATE_EPISODIC_TO_WORKING = "consolidate_episodic_to_working"
    CONSOLIDATE_WORKING_TO_SEMANTIC = "consolidate_working_to_semantic"
    CONSOLIDATE_SEMANTIC_TO_LTM = "consolidate_semantic_to_ltm"
    PRUNE_CONTEXT = "prune_context"

    # Reflection actions
    GENERATE_REFLECTION = "generate_reflection"
    CLUSTER_MEMORIES = "cluster_memories"

    # LLM actions
    CALL_LLM = "call_llm"
    CALL_LLM_WITH_ROUTING = "call_llm_with_routing"

    # Graph actions
    EXTRACT_GRAPH = "extract_graph"
    TRAVERSE_GRAPH = "traverse_graph"
    UPDATE_GRAPH = "update_graph"

    # Context actions
    SUMMARIZE_CONTEXT = "summarize_context"
    EXPAND_CONTEXT = "expand_context"
    RERANK_CONTEXT = "rerank_context"


class Action(BaseModel, ABC):
    """
    Base class for all RAE actions.

    Each action represents a discrete operation that can be taken
    given the current state s_t, producing new state s_{t+1}.

    Mathematical formulation:
      - State transition: s_{t+1} = T(s_t, a_t)
      - Cost function: C(a_t, s_t) → (tokens, cost_usd, latency_ms)
      - Preconditions: P(a_t, s_t) → bool

    Attributes:
        action_type: Type of action from ActionType enum
        parameters: Action-specific parameters
        estimated_tokens: Expected token usage
        estimated_cost_usd: Expected dollar cost
        estimated_latency_ms: Expected latency
        created_at: Timestamp of action creation
        reason: Human-readable explanation for why this action was chosen
    """

    action_type: ActionType = Field(..., description="Type of action")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )

    # Cost estimation (for planning and reward calculation)
    estimated_tokens: int = Field(0, description="Estimated token usage")
    estimated_cost_usd: float = Field(0.0, description="Estimated dollar cost")
    estimated_latency_ms: int = Field(0, description="Estimated latency")

    # Metadata
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Action creation timestamp",
    )
    reason: Optional[str] = Field(None, description="Why this action was selected")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def is_valid_for_state(self, state: RAEState) -> bool:
        """
        Check if action can be executed in given state.

        Validates preconditions:
          - Budget constraints
          - Required resources exist
          - No conflicting operations

        Args:
            state: Current RAE state

        Returns:
            True if preconditions are met, False otherwise
        """
        pass

    @abstractmethod
    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        """
        Estimate resource costs for this action in given state.

        Cost function: C(a_t, s_t) → (tokens, cost_usd, latency_ms)

        Args:
            state: Current RAE state

        Returns:
            Dictionary with:
              - tokens: Expected token usage
              - cost_usd: Expected dollar cost
              - latency_ms: Expected latency
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Serialize action to dictionary"""
        return {
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_latency_ms": self.estimated_latency_ms,
            "created_at": self.created_at,
            "reason": self.reason,
        }


# ============================================================================
# Concrete Action Implementations
# ============================================================================


class RetrieveEpisodicAction(Action):
    """
    Retrieve recent episodic memories.

    Episodic memories are short-term, event-based memories with temporal decay.

    Parameters:
      - k: Number of memories to retrieve (default: 10)
      - threshold: Minimum relevance threshold 0-1 (default: 0.7)
      - time_window_days: Only retrieve from last N days (default: 7)

    Mathematical model:
      - Relevance score: cos_sim(query_emb, memory_emb) × temporal_decay
      - Temporal decay: exp(-age_hours / half_life)
    """

    action_type: ActionType = ActionType.RETRIEVE_EPISODIC

    def is_valid_for_state(self, state: RAEState) -> bool:
        with tracer.start_as_current_span(
            "rae.action.retrieve_episodic.validate"
        ) as span:
            span.set_attribute("rae.action.type", self.action_type.value)
            span.set_attribute("rae.tenant_id", state.tenant_id)
            span.set_attribute("rae.project_id", state.project_id)
            span.set_attribute("rae.memory.layer", "episodic")
            span.set_attribute("rae.memory.count", state.memory_state.episodic.count)

            # Check budget
            if state.budget_state.is_exhausted():
                span.set_attribute(
                    "rae.action.validation_result", "failed_budget_exhausted"
                )
                span.set_attribute("rae.outcome.label", "fail")
                logger.warning(
                    "retrieve_episodic_invalid_budget_exhausted",
                    tenant_id=state.tenant_id,
                )
                return False

            # Check we have episodic memories
            if state.memory_state.episodic.count == 0:
                span.set_attribute("rae.action.validation_result", "failed_no_memories")
                span.set_attribute("rae.outcome.label", "fail")
                logger.info(
                    "retrieve_episodic_invalid_no_memories", tenant_id=state.tenant_id
                )
                return False

            span.set_attribute("rae.action.validation_result", "success")
            span.set_attribute("rae.outcome.label", "success")
            return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        with tracer.start_as_current_span(
            "rae.action.retrieve_episodic.estimate_cost"
        ) as span:
            k = self.parameters.get("k", 10)
            threshold = self.parameters.get("threshold", 0.7)
            time_window_days = self.parameters.get("time_window_days", 7)

            span.set_attribute("rae.action.type", self.action_type.value)
            span.set_attribute("rae.memory.layer", "episodic")
            span.set_attribute("rae.action.k", k)
            span.set_attribute("rae.action.threshold", threshold)
            span.set_attribute("rae.action.time_window_days", time_window_days)

            # Episodic retrieval: mainly embedding computation cost
            # Assume ~100 tokens per memory
            estimated_tokens = k * 100

            span.set_attribute("rae.action.estimated_tokens", estimated_tokens)
            span.set_attribute("rae.action.estimated_latency_ms", k * 5)

            return {
                "tokens": estimated_tokens,
                "cost_usd": 0.0,  # No LLM cost, just retrieval
                "latency_ms": k * 5,  # ~5ms per memory retrieval
            }


class RetrieveWorkingAction(Action):
    """
    Retrieve from working memory buffer.

    Working memory is the active memory currently being used.

    Parameters:
      - k: Number of memories to retrieve (default: 5)
      - active_only: Only retrieve currently active memories (default: True)
    """

    action_type: ActionType = ActionType.RETRIEVE_WORKING

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.budget_state.is_exhausted():
            return False

        if state.memory_state.working.count == 0:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        k = self.parameters.get("k", 5)
        estimated_tokens = k * 80  # Working memory typically smaller

        return {
            "tokens": estimated_tokens,
            "cost_usd": 0.0,
            "latency_ms": k * 3,  # Faster than episodic (already in cache)
        }


class RetrieveSemanticAction(Action):
    """
    Retrieve semantically similar memories.

    Semantic memories are long-term, consolidated knowledge organized by concepts.

    Parameters:
      - k: Number of memories to retrieve (default: 20)
      - use_graph: Whether to use graph traversal (default: False)
      - graph_depth: If using graph, how deep to traverse (default: 2)
    """

    action_type: ActionType = ActionType.RETRIEVE_SEMANTIC

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.budget_state.is_exhausted():
            return False

        if state.memory_state.semantic.count == 0:
            return False

        # If use_graph requested, check graph exists
        if self.parameters.get("use_graph", False):
            if state.graph_state.node_count == 0:
                logger.warning(
                    "retrieve_semantic_invalid_no_graph", tenant_id=state.tenant_id
                )
                return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        k = self.parameters.get("k", 20)
        use_graph = self.parameters.get("use_graph", False)

        estimated_tokens = k * 150  # Semantic memories typically longer
        latency = k * 10

        if use_graph:
            graph_depth = self.parameters.get("graph_depth", 2)
            # Graph traversal adds latency
            latency += graph_depth * 50

        return {"tokens": estimated_tokens, "cost_usd": 0.0, "latency_ms": latency}


class RetrieveLTMAction(Action):
    """
    Retrieve from long-term memory (LTM).

    LTM contains stable, high-importance memories.

    Parameters:
      - k: Number of memories to retrieve (default: 10)
      - min_stability: Minimum stability score 0-1 (default: 0.8)
    """

    action_type: ActionType = ActionType.RETRIEVE_LTM

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.budget_state.is_exhausted():
            return False

        if state.memory_state.ltm.count == 0:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        k = self.parameters.get("k", 10)
        estimated_tokens = k * 200  # LTM memories are typically comprehensive

        return {"tokens": estimated_tokens, "cost_usd": 0.0, "latency_ms": k * 15}


class RetrieveReflectiveAction(Action):
    """
    Retrieve reflective memories (meta-insights).

    Reflective memories are high-level patterns and insights.

    Parameters:
      - level: Reflection level "L1" | "L2" | "L3" (default: "L1")
      - k: Number of reflections to retrieve (default: 5)
    """

    action_type: ActionType = ActionType.RETRIEVE_REFLECTIVE

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.budget_state.is_exhausted():
            return False

        if state.memory_state.reflective.count == 0:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        k = self.parameters.get("k", 5)
        estimated_tokens = k * 300  # Reflections are comprehensive

        return {"tokens": estimated_tokens, "cost_usd": 0.0, "latency_ms": k * 20}


class CallLLMAction(Action):
    """
    Call LLM with current context.

    This is typically the most expensive action.

    Parameters:
      - model: Model name (gpt-4o, claude-3.5-sonnet, etc.)
      - max_tokens: Maximum output tokens (default: 1000)
      - temperature: Sampling temperature (default: 0.7)
      - system_prompt: Optional system prompt
    """

    action_type: ActionType = ActionType.CALL_LLM

    def is_valid_for_state(self, state: RAEState) -> bool:
        with tracer.start_as_current_span("rae.action.call_llm.validate") as span:
            span.set_attribute("rae.action.type", self.action_type.value)
            span.set_attribute("rae.tenant_id", state.tenant_id)
            span.set_attribute("rae.project_id", state.project_id)
            span.set_attribute(
                "rae.action.model", self.parameters.get("model", "gpt-4o-mini")
            )

            # Check budget
            if state.budget_state.is_exhausted():
                span.set_attribute(
                    "rae.action.validation_result", "failed_budget_exhausted"
                )
                span.set_attribute("rae.outcome.label", "fail")
                return False

            # Check we have context
            if state.working_context.token_count == 0:
                span.set_attribute("rae.action.validation_result", "failed_no_context")
                span.set_attribute("rae.outcome.label", "fail")
                logger.warning("call_llm_invalid_no_context", tenant_id=state.tenant_id)
                return False

            # Check estimated cost doesn't exceed budget
            estimated = self.estimate_cost(state)
            span.set_attribute("rae.action.estimated_cost_usd", estimated["cost_usd"])
            span.set_attribute("rae.action.estimated_tokens", estimated["tokens"])
            span.set_attribute(
                "rae.state.budget_remaining_usd", state.budget_state.remaining_cost_usd
            )

            if estimated["cost_usd"] > state.budget_state.remaining_cost_usd:
                span.set_attribute(
                    "rae.action.validation_result", "failed_exceeds_cost_budget"
                )
                span.set_attribute("rae.outcome.label", "fail")
                logger.warning(
                    "call_llm_invalid_exceeds_budget",
                    tenant_id=state.tenant_id,
                    estimated_cost=estimated["cost_usd"],
                    remaining_budget=state.budget_state.remaining_cost_usd,
                )
                return False

            if estimated["tokens"] > state.budget_state.remaining_tokens:
                span.set_attribute(
                    "rae.action.validation_result", "failed_exceeds_token_budget"
                )
                span.set_attribute("rae.outcome.label", "fail")
                return False

            span.set_attribute("rae.action.validation_result", "success")
            span.set_attribute("rae.outcome.label", "success")
            return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        with tracer.start_as_current_span("rae.action.call_llm.estimate_cost") as span:
            model = self.parameters.get("model", "gpt-4o-mini")
            max_tokens = self.parameters.get("max_tokens", 1000)

            span.set_attribute("rae.action.type", self.action_type.value)
            span.set_attribute("rae.action.model", model)
            span.set_attribute("rae.action.max_output_tokens", max_tokens)

            # Input tokens = current context
            input_tokens = state.working_context.token_count
            output_tokens = max_tokens

            span.set_attribute("rae.action.input_tokens", input_tokens)
            span.set_attribute("rae.action.output_tokens", output_tokens)

            # Simple cost model (should be imported from cost_model module)
            # Rough estimates:
            costs_per_million = {
                "gpt-4o": {"input": 2.50, "output": 10.00},
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
                "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
                "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
            }

            costs = costs_per_million.get(
                model, {"input": 0.15, "output": 0.60}
            )  # Default to mini
            input_cost = (input_tokens / 1_000_000) * costs["input"]
            output_cost = (output_tokens / 1_000_000) * costs["output"]
            total_cost = input_cost + output_cost

            # Latency estimate (very rough)
            latency = 1000 + (output_tokens * 50)  # ~50ms per output token

            span.set_attribute("rae.action.estimated_cost_usd", total_cost)
            span.set_attribute(
                "rae.action.estimated_tokens", input_tokens + output_tokens
            )
            span.set_attribute("rae.action.estimated_latency_ms", latency)

            return {
                "tokens": input_tokens + output_tokens,
                "cost_usd": total_cost,
                "latency_ms": latency,
            }


class PruneContextAction(Action):
    """
    Prune context to reduce size.

    Important for staying within budget constraints.

    Parameters:
      - strategy: "importance" | "recency" | "relevance" (default: "importance")
      - target_size: Target token count (default: 2000)
      - min_keep: Minimum items to keep (default: 3)
    """

    action_type: ActionType = ActionType.PRUNE_CONTEXT

    def is_valid_for_state(self, state: RAEState) -> bool:
        # Only makes sense if context is non-empty
        return state.working_context.token_count > 0

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        # Pruning is cheap - just sorting and filtering
        return {
            "tokens": 0,  # No token cost
            "cost_usd": 0.0,
            "latency_ms": 10,  # Fast operation
        }


class GenerateReflectionAction(Action):
    """
    Generate reflection from memories.

    Reflections are meta-insights derived from patterns in memories.

    Parameters:
      - max_memories: Maximum memories to reflect on (default: 100)
      - min_cluster_size: Minimum cluster size for insights (default: 5)
      - level: "L1" | "L2" | "L3" reflection depth (default: "L1")
    """

    action_type: ActionType = ActionType.GENERATE_REFLECTION

    def is_valid_for_state(self, state: RAEState) -> bool:
        with tracer.start_as_current_span(
            "rae.action.generate_reflection.validate"
        ) as span:
            span.set_attribute("rae.action.type", self.action_type.value)
            span.set_attribute("rae.tenant_id", state.tenant_id)
            span.set_attribute("rae.project_id", state.project_id)
            span.set_attribute("rae.memory.layer", "reflective")

            if state.budget_state.is_exhausted():
                span.set_attribute(
                    "rae.action.validation_result", "failed_budget_exhausted"
                )
                span.set_attribute("rae.outcome.label", "fail")
                return False

            # Need sufficient memories to reflect on
            total_memories = (
                state.memory_state.episodic.count + state.memory_state.semantic.count
            )

            span.set_attribute("rae.memory.total_available", total_memories)

            min_memories = self.parameters.get("min_cluster_size", 5) * 2
            if total_memories < min_memories:
                span.set_attribute(
                    "rae.action.validation_result", "failed_insufficient_memories"
                )
                span.set_attribute("rae.outcome.label", "fail")
                span.set_attribute("rae.memory.required", min_memories)
                logger.info(
                    "generate_reflection_invalid_insufficient_memories",
                    tenant_id=state.tenant_id,
                    total_memories=total_memories,
                    required=min_memories,
                )
                return False

            span.set_attribute("rae.action.validation_result", "success")
            span.set_attribute("rae.outcome.label", "success")
            return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        with tracer.start_as_current_span(
            "rae.action.generate_reflection.estimate_cost"
        ) as span:
            max_memories = self.parameters.get("max_memories", 100)
            min_cluster_size = self.parameters.get("min_cluster_size", 5)
            level = self.parameters.get("level", "L1")

            span.set_attribute("rae.action.type", self.action_type.value)
            span.set_attribute("rae.memory.layer", "reflective")
            span.set_attribute("rae.action.max_memories", max_memories)
            span.set_attribute("rae.action.min_cluster_size", min_cluster_size)
            span.set_attribute("rae.action.reflection_level", level)

            # Reflection involves:
            # 1. Clustering (local computation)
            # 2. LLM call per cluster
            # 3. Embedding generation

            estimated_clusters = max_memories // min_cluster_size
            estimated_tokens_per_cluster = 2000  # Context + output

            total_tokens = estimated_clusters * estimated_tokens_per_cluster

            # Rough cost estimate (using gpt-4o-mini for reflections)
            cost_per_million = 1.0  # $1 per million tokens (mixed input/output)
            total_cost = (total_tokens / 1_000_000) * cost_per_million

            # Latency: clustering + LLM calls
            latency = 5000 + (estimated_clusters * 3000)  # 3s per cluster

            span.set_attribute("rae.action.estimated_clusters", estimated_clusters)
            span.set_attribute("rae.action.estimated_tokens", total_tokens)
            span.set_attribute("rae.action.estimated_cost_usd", total_cost)
            span.set_attribute("rae.action.estimated_latency_ms", latency)

            return {
                "tokens": total_tokens,
                "cost_usd": total_cost,
                "latency_ms": latency,
            }


class UpdateGraphAction(Action):
    """
    Update knowledge graph with new information.

    Graph evolution: G_{t+1} = T(G_t, o_t, a_t)

    Parameters:
      - operation: "add_node" | "add_edge" | "merge_nodes" | "prune"
      - node_data: Data for node operations
      - edge_data: Data for edge operations
    """

    action_type: ActionType = ActionType.UPDATE_GRAPH

    def is_valid_for_state(self, state: RAEState) -> bool:
        # Graph updates always valid (they initialize if needed)
        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        # Graph operations are local (no LLM)
        operation = self.parameters.get("operation", "add_node")

        if operation == "merge_nodes":
            # Entity resolution might use embeddings
            latency = 100
        elif operation == "prune":
            # Pruning requires graph analysis
            latency = 200
        else:
            latency = 20

        return {"tokens": 0, "cost_usd": 0.0, "latency_ms": latency}


class ConsolidateEpisodicToWorkingAction(Action):
    """
    Consolidate episodic memories to working memory.

    Memory flow: Episodic → Working → Semantic → LTM

    Parameters:
      - max_memories: Maximum memories to consolidate (default: 10)
      - min_importance: Minimum importance threshold (default: 0.6)
    """

    action_type: ActionType = ActionType.CONSOLIDATE_EPISODIC_TO_WORKING

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.memory_state.episodic.count == 0:
            return False

        # Check working memory not full (arbitrary limit)
        if state.memory_state.working.count > 100:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        max_memories = self.parameters.get("max_memories", 10)

        return {
            "tokens": 0,  # No LLM cost, just data movement
            "cost_usd": 0.0,
            "latency_ms": max_memories * 5,
        }


class SummarizeContextAction(Action):
    """
    Summarize context to reduce size while preserving information.

    Information bottleneck: compress X to Z while maximizing I(Z;Y)

    Parameters:
      - compression_ratio: Target ratio 0-1 (default: 0.5)
      - method: "extractive" | "abstractive" (default: "extractive")
    """

    action_type: ActionType = ActionType.SUMMARIZE_CONTEXT

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.budget_state.is_exhausted():
            return False

        if state.working_context.token_count == 0:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        method = self.parameters.get("method", "extractive")

        if method == "extractive":
            # Fast, no LLM
            return {"tokens": 0, "cost_usd": 0.0, "latency_ms": 50}
        else:
            # Abstractive requires LLM
            input_tokens = state.working_context.token_count
            output_tokens = int(input_tokens * 0.5)  # Compression
            cost_per_million = 0.15 + 0.60  # gpt-4o-mini
            total_cost = ((input_tokens + output_tokens) / 1_000_000) * cost_per_million

            return {
                "tokens": input_tokens + output_tokens,
                "cost_usd": total_cost,
                "latency_ms": 2000 + (output_tokens * 50),
            }
