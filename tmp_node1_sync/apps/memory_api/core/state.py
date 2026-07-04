"""
RAE State Representation - Mathematical formalization of system state.

This module implements the State space S in our MDP formulation:
  s_t = (working_context, memory_state, budget_state, graph_state)

Mathematical Background:
  - State: s_t ∈ S (complete system state at time t)
  - MDP: (S, A, P, R, γ) where S is defined here
  - Transition: s_{t+1} = T(s_t, a_t)
  - Reward: R(s_t, a_t, s_{t+1})

Usage:
    state = RAEState(
        tenant_id="demo",
        project_id="my-app",
        working_context=WorkingContext(content=["memory 1", "memory 2"]),
        memory_state=MemoryState(...),
        budget_state=BudgetState(...),
        graph_state=GraphState(...)
    )

    # State can be serialized for logging/debugging
    state_dict = state.to_dict()

    # State can be compared for transition analysis
    delta = state.compare(previous_state)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import numpy as np
import structlog
from pydantic import BaseModel, ConfigDict, Field

from apps.memory_api.observability.rae_tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


@dataclass
class WorkingContext:
    """
    Current context window being used for LLM interactions.

    This is the "information bottleneck" Z in our formulation:
      Z = Selected context from full memory X
      Goal: Maximize I(Z;Y) - β·I(Z;X)

    Attributes:
        content: List of content strings in context
        token_count: Total size in tokens
        embeddings: Vector representations (optional)
        importance_scores: Per-item importance (0-1)
        source_memory_ids: Memory IDs that contributed to context
    """

    content: List[str] = field(default_factory=list)
    token_count: int = 0
    embeddings: Optional[np.ndarray] = None
    importance_scores: List[float] = field(default_factory=list)
    source_memory_ids: List[UUID] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (for logging/storage)"""
        return {
            "content": self.content,
            "token_count": self.token_count,
            "importance_scores": self.importance_scores,
            "memory_count": len(self.content),
            "avg_importance": (
                np.mean(self.importance_scores) if self.importance_scores else 0.0
            ),
        }


@dataclass
class MemoryLayerState:
    """
    State of a single memory layer.

    RAE has 5 memory layers:
      1. Episodic: Short-term, event-based memories
      2. Working: Active memories being used in current context
      3. Semantic: Long-term, consolidated knowledge
      4. LTM: Stable, important long-term memories
      5. Reflective: Meta-cognitive insights

    Attributes:
        count: Number of memories in this layer
        avg_importance: Average importance score (0-1)
        recency_distribution: Distribution of memory ages (optional)
        coverage: Layer utilization (0-1)
        avg_age_hours: Average age of memories in hours
        last_consolidated: Last consolidation timestamp
    """

    count: int = 0
    avg_importance: float = 0.0
    recency_distribution: Optional[np.ndarray] = None
    coverage: float = 0.0
    avg_age_hours: float = 0.0
    last_consolidated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "count": self.count,
            "avg_importance": self.avg_importance,
            "coverage": self.coverage,
            "avg_age_hours": self.avg_age_hours,
            "last_consolidated": (
                self.last_consolidated.isoformat() if self.last_consolidated else None
            ),
        }


@dataclass
class MemoryState:
    """
    Complete memory system state across all 5 layers.

    Mathematical formulation:
      M = {M^episodic, M^working, M^semantic, M^ltm, M^reflective}

    Each layer has different dynamics:
      - Episodic: Fast decay, temporal access
      - Working: Active buffer, limited capacity
      - Semantic: Consolidated, organized by concepts
      - LTM: Stable, high-importance long-term storage
      - Reflective: Meta-insights, patterns across memories
    """

    episodic: MemoryLayerState = field(default_factory=MemoryLayerState)
    working: MemoryLayerState = field(default_factory=MemoryLayerState)
    semantic: MemoryLayerState = field(default_factory=MemoryLayerState)
    ltm: MemoryLayerState = field(default_factory=MemoryLayerState)
    reflective: MemoryLayerState = field(default_factory=MemoryLayerState)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "episodic": self.episodic.to_dict(),
            "working": self.working.to_dict(),
            "semantic": self.semantic.to_dict(),
            "ltm": self.ltm.to_dict(),
            "reflective": self.reflective.to_dict(),
            "total_count": self.total_count(),
        }

    def total_count(self) -> int:
        """Total memories across all layers"""
        return (
            self.episodic.count
            + self.working.count
            + self.semantic.count
            + self.ltm.count
            + self.reflective.count
        )


@dataclass
class BudgetState:
    """
    Resource budget state for cost-aware decision making.

    Used in reward function:
      R(s_t, a_t, s_{t+1}) = Quality - λ·tokens - μ·latency

    Attributes:
        remaining_tokens: Tokens left in budget
        remaining_cost_usd: Dollar budget remaining
        latency_budget_ms: Latency budget in milliseconds
        calls_remaining: Number of LLM calls remaining
    """

    remaining_tokens: int = 100000
    remaining_cost_usd: float = 10.0
    latency_budget_ms: int = 30000
    calls_remaining: int = 100

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "remaining_tokens": self.remaining_tokens,
            "remaining_cost_usd": self.remaining_cost_usd,
            "latency_budget_ms": self.latency_budget_ms,
            "calls_remaining": self.calls_remaining,
            "is_exhausted": self.is_exhausted(),
        }

    def is_exhausted(self) -> bool:
        """Check if any budget constraint is violated"""
        return (
            self.remaining_tokens <= 0
            or self.remaining_cost_usd <= 0.0
            or self.latency_budget_ms <= 0
            or self.calls_remaining <= 0
        )


@dataclass
class GraphState:
    """
    Knowledge graph state.

    Graph evolution:
      G_{t+1} = T(G_t, o_t, a_t)

    Attributes:
        node_count: Number of entities/concepts
        edge_count: Number of relationships
        avg_centrality: Average node centrality (importance in graph)
        connected_components: Number of disconnected subgraphs
        last_updated: Last graph update timestamp
    """

    node_count: int = 0
    edge_count: int = 0
    avg_centrality: float = 0.0
    connected_components: int = 0
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "avg_centrality": self.avg_centrality,
            "connected_components": self.connected_components,
            "last_updated": (
                self.last_updated.isoformat() if self.last_updated else None
            ),
        }


class RAEState(BaseModel):
    """
    Complete RAE system state at time t.

    Mathematical notation: s_t ∈ S

    This is the foundational state representation for:
      1. MDP formulation: Enables transition P(s_{t+1} | s_t, a_t)
      2. Reward calculation: R(s_t, a_t, s_{t+1})
      3. Policy definition: π(a_t | s_t)

    Components:
      - working_context: Current LLM context (information bottleneck Z)
      - memory_state: State across 5 memory layers
      - budget_state: Resource constraints
      - graph_state: Knowledge graph state

    Example:
        >>> state = RAEState(
        ...     tenant_id="demo",
        ...     project_id="my-app",
        ...     working_context=WorkingContext(content=["memory 1"]),
        ...     budget_state=BudgetState(remaining_tokens=50000)
        ... )
        >>> state.is_valid()
        True
        >>> state_dict = state.to_dict()
    """

    # Identity
    tenant_id: str = Field(..., description="Tenant identifier")
    project_id: str = Field(..., description="Project identifier")
    session_id: Optional[str] = Field(None, description="Optional session identifier")

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)

    # State components
    working_context: WorkingContext = Field(default_factory=WorkingContext)
    memory_state: MemoryState = Field(default_factory=MemoryState)
    budget_state: BudgetState = Field(default_factory=BudgetState)
    graph_state: GraphState = Field(default_factory=GraphState)

    # Optional: Last action taken (for transition tracking)
    last_action: Optional[Dict[str, Any]] = Field(
        None, description="Last action that led to this state"
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize state to dictionary.

        Returns:
            Dictionary representation of state (JSON-serializable)
        """
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "working_context": self.working_context.to_dict(),
            "memory_state": self.memory_state.to_dict(),
            "budget_state": self.budget_state.to_dict(),
            "graph_state": self.graph_state.to_dict(),
            "last_action": self.last_action,
        }

    def compare(self, other: "RAEState") -> Dict[str, Any]:
        """
        Compare this state with another to compute delta.

        This enables transition analysis:
          Δs = s_{t+1} - s_t

        Useful for:
          - Understanding action effects
          - Reward calculation (depends on state changes)
          - Debugging state transitions
          - Policy learning (observing consequences)

        Args:
            other: Previous state to compare against

        Returns:
            Dictionary with deltas for key metrics
        """
        with tracer.start_as_current_span("rae.state.compare") as span:
            span.set_attribute("rae.tenant_id", self.tenant_id)
            span.set_attribute("rae.project_id", self.project_id)

            delta = {
                "token_delta": (
                    self.budget_state.remaining_tokens
                    - other.budget_state.remaining_tokens
                ),
                "cost_delta": (
                    self.budget_state.remaining_cost_usd
                    - other.budget_state.remaining_cost_usd
                ),
                "context_size_delta": (
                    self.working_context.token_count - other.working_context.token_count
                ),
                "graph_nodes_delta": (
                    self.graph_state.node_count - other.graph_state.node_count
                ),
                "graph_edges_delta": (
                    self.graph_state.edge_count - other.graph_state.edge_count
                ),
                "memory_count_delta": (
                    self.memory_state.total_count() - other.memory_state.total_count()
                ),
                "time_delta_ms": (
                    (self.timestamp - other.timestamp).total_seconds() * 1000
                ),
            }

            # Record key deltas as span attributes for analysis
            span.set_attribute("rae.state.token_delta", delta["token_delta"])
            span.set_attribute("rae.state.cost_delta_usd", delta["cost_delta"])
            span.set_attribute("rae.state.memory_delta", delta["memory_count_delta"])
            span.set_attribute(
                "rae.state.graph_nodes_delta", delta["graph_nodes_delta"]
            )
            span.set_attribute("rae.state.time_delta_ms", delta["time_delta_ms"])

            return delta

    def is_valid(self) -> bool:
        """
        Validate state consistency.

        Checks:
          - Budget constraints not violated
          - Context size matches importance scores length
          - No negative values in critical fields
          - Logical consistency (e.g., working memory ≤ semantic)

        Returns:
            True if state is valid and consistent
        """
        with tracer.start_as_current_span("rae.state.validate") as span:
            span.set_attribute("rae.tenant_id", self.tenant_id)
            span.set_attribute("rae.project_id", self.project_id)

            # Record current state metrics
            span.set_attribute(
                "rae.state.budget_tokens", self.budget_state.remaining_tokens
            )
            span.set_attribute(
                "rae.state.budget_usd", self.budget_state.remaining_cost_usd
            )
            span.set_attribute(
                "rae.state.context_tokens", self.working_context.token_count
            )
            span.set_attribute(
                "rae.state.total_memories", self.memory_state.total_count()
            )
            span.set_attribute("rae.state.graph_nodes", self.graph_state.node_count)

            # Budget check
            if self.budget_state.is_exhausted():
                span.set_attribute(
                    "rae.state.validation_result", "failed_budget_exhausted"
                )
                span.set_attribute("rae.outcome.label", "fail")
                logger.warning(
                    "state_validation_failed_budget_exhausted",
                    tenant_id=self.tenant_id,
                    budget=self.budget_state.to_dict(),
                )
                return False

            # Context consistency
            if self.working_context.token_count < 0:
                span.set_attribute(
                    "rae.state.validation_result", "failed_negative_tokens"
                )
                span.set_attribute("rae.outcome.label", "fail")
                logger.warning(
                    "state_validation_failed_negative_tokens",
                    tenant_id=self.tenant_id,
                    token_count=self.working_context.token_count,
                )
                return False

            # Importance scores length matches content
            if len(self.working_context.content) != len(
                self.working_context.importance_scores
            ):
                # This is acceptable if importance_scores is empty (not yet computed)
                if self.working_context.importance_scores:
                    span.set_attribute(
                        "rae.state.validation_result", "warning_mismatched_scores"
                    )
                    logger.warning(
                        "state_validation_warning_mismatched_importance_scores",
                        tenant_id=self.tenant_id,
                        content_length=len(self.working_context.content),
                        scores_length=len(self.working_context.importance_scores),
                    )

            # Memory counts non-negative
            if any(
                layer.count < 0
                for layer in [
                    self.memory_state.episodic,
                    self.memory_state.working,
                    self.memory_state.semantic,
                    self.memory_state.ltm,
                    self.memory_state.reflective,
                ]
            ):
                span.set_attribute(
                    "rae.state.validation_result", "failed_negative_memory_count"
                )
                span.set_attribute("rae.outcome.label", "fail")
                logger.warning(
                    "state_validation_failed_negative_memory_count",
                    tenant_id=self.tenant_id,
                    memory_state=self.memory_state.to_dict(),
                )
                return False

            span.set_attribute("rae.state.validation_result", "success")
            span.set_attribute("rae.outcome.label", "success")
            return True

    def log_state(self, event: str = "state_snapshot") -> None:
        """
        Log current state with structured logging.

        Args:
            event: Event name for the log entry
        """
        logger.info(
            event,
            tenant_id=self.tenant_id,
            project_id=self.project_id,
            session_id=self.session_id,
            state=self.to_dict(),
        )
