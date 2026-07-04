# RAE Mathematical Refactoring Guide

**Purpose:** Transform RAE from a working framework into a mathematically grounded engineering system
**Target Audience:** AI agents performing autonomous code refactoring
**Approach:** 5 iterative refactorings with validation at each step
**Philosophy:** *"Majstersztyk inżynierski, nie papierowy potwór"* - Implementation over theory

**Version:** 1.0
**Last Updated:** 2025-12-04
**Status:** Ready for agent execution

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Mathematical Foundation](#mathematical-foundation)
3. [Current State Analysis](#current-state-analysis)
4. [5-Iteration Refactoring Plan](#5-iteration-refactoring-plan)
5. [Validation Framework](#validation-framework)
6. [Agent Execution Guidelines](#agent-execution-guidelines)
7. [Success Metrics](#success-metrics)

---

## Executive Summary

### Vision

Transform RAE into a **mathematically grounded engineering system** where every component maps to formal mathematical concepts:

1. **RAE as Markov Decision Process (MDP)** - Optimal control of memory retrieval and LLM usage
2. **RAE as Information Bottleneck** - Justified context compression with information theory
3. **RAE as Knowledge Graph with Update Operators** - Formal memory evolution dynamics

### Key Constraints

✅ **Must preserve:** All existing functionality, API compatibility, test coverage
✅ **Must add:** Mathematical formalization, measurable metrics, optimization framework
✅ **Must avoid:** Over-engineering, premature abstractions, breaking changes
✅ **Must document:** Every mathematical concept with code mapping

### Expected Outcomes

After 5 iterations:
- RAE state formally defined: `s_t = (context, M^episodic, M^working, M^semantic, M^ltm, M^reflective, budget)`
- **5-layer memory architecture** explicitly modeled: episodic → working → semantic → LTM + reflective
- Actions mathematically specified: `a_t ∈ {retrieve, consolidate, summarize, reflect, call_LLM(i), update}`
- Reward function implemented: `r_t = Quality - λ·tokens - μ·latency`
- Information bottleneck metrics: `I(Z;Y)`, `I(Z;X)`
- Graph update operator: `G_{t+1} = T(G_t, o_t, a_t)`

---

## Mathematical Foundation

### Pillar 1: RAE as Markov Decision Process (MDP)

**Formal Definition:**

```
MDP = (S, A, P, R, γ)

Where:
  S = State space (RAE internal state)
  A = Action space (retrieve, reflect, call_LLM, etc.)
  P = Transition dynamics P(s_{t+1} | s_t, a_t)
  R = Reward function R(s_t, a_t, s_{t+1})
  γ = Discount factor (0.95 for balancing immediate vs future rewards)
```

**RAE State Representation:**

```python
s_t = {
    "working_context": {
        "content": List[str],           # Current context window
        "token_count": int,              # Size in tokens
        "embeddings": np.ndarray,        # Vector representation
        "importance_scores": List[float] # Per-item importance
    },
    "memory_state": {
        "episodic": {
            "count": int,
            "avg_importance": float,
            "recency_distribution": np.ndarray,
            "avg_age_hours": float  # How fresh are episodic memories
        },
        "working": {
            "count": int,
            "active_count": int,  # Currently in use
            "avg_access_count": float,
            "buffer_utilization": float  # 0-1, how full is working memory
        },
        "semantic": {
            "count": int,
            "cluster_count": int,
            "coverage": float,  # 0-1, how much knowledge is covered
            "consolidation_rate": float  # Memories/day being consolidated
        },
        "ltm": {
            "count": int,
            "avg_importance": float,
            "stability_score": float,  # 0-1, how stable is LTM
            "last_consolidated": datetime
        },
        "reflective": {
            "count": int,
            "last_generated": datetime,
            "avg_novelty": float,
            "meta_insights_count": int  # L2/L3 reflections
        }
    },
    "budget_state": {
        "remaining_tokens": int,
        "remaining_cost_usd": float,
        "latency_budget_ms": int,
        "calls_remaining": int
    },
    "graph_state": {
        "node_count": int,
        "edge_count": int,
        "avg_centrality": float,
        "connected_components": int
    }
}
```

**RAE Action Space:**

```python
A = {
    "retrieve_episodic": {
        "params": {"k": int, "threshold": float, "time_window_hours": int}
    },
    "retrieve_working": {
        "params": {"k": int, "active_only": bool}
    },
    "retrieve_semantic": {
        "params": {"k": int, "use_graph": bool}
    },
    "retrieve_ltm": {
        "params": {"k": int, "min_stability": float}
    },
    "retrieve_reflective": {
        "params": {"level": str, "k": int}
    },
    "consolidate_episodic_to_working": {
        "params": {"max_memories": int, "min_importance": float}
    },
    "consolidate_working_to_semantic": {
        "params": {"max_memories": int, "clustering_threshold": float}
    },
    "consolidate_semantic_to_ltm": {
        "params": {"max_memories": int, "min_age_days": int, "min_importance": float}
    },
    "summarize": {
        "params": {"compression_ratio": float, "method": str}
    },
    "reflect": {
        "params": {"min_memories": int, "depth": int}
    },
    "call_llm": {
        "params": {"model": str, "max_tokens": int, "temperature": float}
    },
    "update_memory": {
        "params": {"layer": str, "consolidate": bool}
    },
    "prune_context": {
        "params": {"strategy": str, "target_size": int}
    }
}
```

**Reward Function:**

```python
def compute_reward(s_t, a_t, s_next) -> float:
    """
    R(s_t, a_t, s_{t+1}) = Quality - λ·tokens - μ·latency

    Quality: How well does the action serve the user's goal?
    Cost: Token usage penalty
    Latency: Time penalty for responsiveness
    """
    quality = evaluate_quality(s_next)  # 0-1 score
    tokens = s_t["budget_state"]["remaining_tokens"] - s_next["budget_state"]["remaining_tokens"]
    latency = s_next.get("action_latency_ms", 0)

    # Hyperparameters (tunable)
    λ = 0.001  # Cost weight: $1 = 1000 reward points
    μ = 0.01   # Latency weight: 1ms = 0.01 penalty

    reward = quality - λ * tokens - μ * latency

    return reward
```

**Transition Dynamics:**

```python
def transition(s_t: State, a_t: Action) -> State:
    """
    P(s_{t+1} | s_t, a_t)

    Deterministic transitions for RAE (we control the system)
    Stochastic elements: LLM response quality, retrieval relevance
    """
    s_next = copy.deepcopy(s_t)

    # Update based on action
    if a_t["type"] == "retrieve_episodic":
        memories = retrieve_episodic(a_t["params"])
        s_next["working_context"]["content"].extend(memories)
        s_next["working_context"]["token_count"] += count_tokens(memories)

    elif a_t["type"] == "call_llm":
        response = call_llm(s_t["working_context"], a_t["params"])
        s_next["budget_state"]["remaining_tokens"] -= response.tokens_used
        s_next["budget_state"]["remaining_cost_usd"] -= response.cost_usd

    # ... other actions

    return s_next
```

**Policy (to be optimized):**

```python
def policy(s_t: State) -> Action:
    """
    π(a_t | s_t): Policy mapping states to actions

    Initial: Heuristic policy (current RAE behavior)
    Target: Learned optimal policy π* maximizing cumulative reward
    """
    # Current heuristic approach
    if s_t["budget_state"]["remaining_tokens"] < 1000:
        return action("prune_context", {"strategy": "importance", "target_size": 500})

    if user_query_requires_recent_context():
        return action("retrieve_episodic", {"k": 10, "threshold": 0.7})

    if context_is_sparse():
        return action("retrieve_semantic", {"k": 20, "use_graph": True})

    # ... more heuristics

    # Future: Learn optimal policy using RL or planning algorithms
```

---

### Pillar 2: RAE as Information Bottleneck

**Formal Definition:**

The Information Bottleneck principle for optimal compression:

```
Minimize: I(Z; X)  [Compression: Z contains minimal info from X]
Maximize: I(Z; Y)  [Relevance: Z maximally predicts Y]

Where:
  X = Full memory history (all episodic, semantic, reflective memories)
  Z = Selected context (what we pass to LLM)
  Y = Desired output (answer to query)

Lagrangian: L = I(Z; Y) - β·I(Z; X)
```

**RAE Context Selection as Information Bottleneck:**

```python
def select_context_information_bottleneck(
    query: str,
    full_memory_X: List[Memory],
    beta: float = 1.0,  # Trade-off parameter
    max_tokens: int = 4000
) -> List[Memory]:
    """
    Select optimal context Z from full memory X using information bottleneck.

    Goal:
      - Z should maximally predict answer Y
      - Z should minimally depend on X (compression)

    Practical approximation:
      - I(Z; Y) ≈ semantic_relevance(Z, query)
      - I(Z; X) ≈ |Z| (size of context)
    """

    # Compute relevance to query (approximation of I(Z; Y))
    relevance_scores = []
    for memory in full_memory_X:
        relevance = cosine_similarity(
            embed(memory.content),
            embed(query)
        )
        relevance_scores.append(relevance)

    # Compute compression cost (approximation of I(Z; X))
    def compression_cost(memories: List[Memory]) -> float:
        # Larger context = higher mutual information with X
        return len(memories) / len(full_memory_X)

    # Iteratively select memories optimizing bottleneck objective
    selected_context = []
    current_tokens = 0

    # Greedy selection (future: exact optimization)
    memories_ranked = sorted(
        zip(full_memory_X, relevance_scores),
        key=lambda x: x[1] - beta * (count_tokens(x[0].content) / max_tokens),
        reverse=True
    )

    for memory, score in memories_ranked:
        tokens = count_tokens(memory.content)
        if current_tokens + tokens <= max_tokens:
            selected_context.append(memory)
            current_tokens += tokens

    # Log information bottleneck metrics
    I_Z_Y = compute_mutual_information_relevance(selected_context, query)
    I_Z_X = compute_mutual_information_compression(selected_context, full_memory_X)

    logger.info(
        "information_bottleneck_selection",
        I_Z_Y=I_Z_Y,
        I_Z_X=I_Z_X,
        compression_ratio=len(selected_context) / len(full_memory_X),
        beta=beta
    )

    return selected_context
```

**Measuring Mutual Information:**

```python
def compute_mutual_information_relevance(context_Z: List[Memory], query: str) -> float:
    """
    Estimate I(Z; Y) - how much does Z tell us about desired output Y?

    Approximation: Use embedding similarity and diversity
    """
    # Average relevance to query
    relevance = np.mean([
        cosine_similarity(embed(m.content), embed(query))
        for m in context_Z
    ])

    # Diversity bonus (more diverse context = more information)
    embeddings = np.array([embed(m.content) for m in context_Z])
    diversity = compute_diversity(embeddings)

    # Combined score (heuristic for I(Z; Y))
    I_Z_Y = 0.7 * relevance + 0.3 * diversity

    return I_Z_Y


def compute_mutual_information_compression(context_Z: List[Memory], full_X: List[Memory]) -> float:
    """
    Estimate I(Z; X) - how much of X is preserved in Z?

    Should be LOW (good compression)
    """
    # Simple approximation: size ratio
    size_ratio = len(context_Z) / len(full_X)

    # Coverage: what fraction of clusters/topics in X are represented in Z?
    # (Future: cluster X and Z, measure overlap)

    # For now: linear approximation
    I_Z_X = size_ratio

    return I_Z_X
```

**Adaptive Beta Tuning:**

```python
def adaptive_beta(query_complexity: float, budget_remaining: float) -> float:
    """
    Adaptively set β based on query and budget.

    High β (>1): Aggressive compression (tight budget, simple query)
    Low β (<1): Less compression (high budget, complex query)
    """
    # Simple heuristic (future: learn from data)
    if budget_remaining < 0.3:  # Less than 30% budget left
        beta = 2.0  # Aggressive compression
    elif query_complexity > 0.7:  # Complex query needing rich context
        beta = 0.5  # Gentle compression
    else:
        beta = 1.0  # Balanced

    return beta
```

---

### Pillar 3: RAE as Knowledge Graph with Update Operator

**Formal Definition:**

```
Graph: G_t = (V_t, E_t)

Where:
  V_t = Nodes (entities, concepts) at time t
  E_t = Edges (relationships) at time t

Update Operator: G_{t+1} = T(G_t, o_t, a_t)

Where:
  o_t = Observation (new memory, query result)
  a_t = Action (extract entities, create edges, prune)
  T = Transition function (deterministic graph transformation)
```

**Update Operator Implementation:**

```python
def graph_update_operator(
    G_t: KnowledgeGraph,
    observation: Observation,
    action: GraphAction
) -> KnowledgeGraph:
    """
    G_{t+1} = T(G_t, o_t, a_t)

    Deterministic graph transformation based on new information.

    Possible actions:
      - add_node: Create new entity
      - add_edge: Create new relationship
      - update_edge_weight: Strengthen/weaken relationship
      - merge_nodes: Consolidate duplicate entities
      - prune_nodes: Remove low-value nodes
      - extract_subgraph: Create focused view
    """
    G_next = G_t.copy()

    if action["type"] == "add_node":
        node = create_node_from_observation(observation)
        G_next.add_node(node)

    elif action["type"] == "add_edge":
        source = action["source"]
        target = action["target"]
        relation = action["relation"]

        edge_weight = compute_edge_weight(source, target, relation, observation)
        G_next.add_edge(source, target, relation, edge_weight)

    elif action["type"] == "update_edge_weight":
        edge = G_next.get_edge(action["edge_id"])

        # Temporal decay + reinforcement
        time_delta = (now - edge.last_updated).total_seconds()
        decay = np.exp(-time_delta / EDGE_HALF_LIFE)

        if observation_supports_edge(observation, edge):
            edge.weight = min(1.0, edge.weight * decay + REINFORCEMENT_BOOST)
        else:
            edge.weight = edge.weight * decay

        # Prune if weight too low
        if edge.weight < EDGE_PRUNE_THRESHOLD:
            G_next.remove_edge(edge)

    elif action["type"] == "merge_nodes":
        node1, node2 = action["nodes"]

        # Entity resolution: merge duplicate nodes
        merged_node = merge_entities(node1, node2)
        G_next.remove_node(node1)
        G_next.remove_node(node2)
        G_next.add_node(merged_node)

        # Redirect all edges
        for edge in G_t.edges_from(node1) + G_t.edges_from(node2):
            G_next.add_edge(merged_node, edge.target, edge.relation, edge.weight)

    # Log graph evolution metrics
    logger.info(
        "graph_update",
        nodes_added=len(G_next.nodes) - len(G_t.nodes),
        edges_added=len(G_next.edges) - len(G_t.edges),
        action_type=action["type"]
    )

    return G_next
```

**Graph Evolution Dynamics:**

```python
def analyze_graph_convergence(history: List[KnowledgeGraph]) -> Dict[str, float]:
    """
    Analyze whether graph is converging to stable structure.

    Metrics:
      - Spectral gap: λ_2 - λ_1 (stability indicator)
      - Clustering coefficient evolution
      - Node churn rate (additions/deletions per timestep)
      - Edge weight distribution convergence
    """
    # Compute adjacency matrix spectrum
    A = history[-1].adjacency_matrix()
    eigenvalues = np.linalg.eigvals(A)
    eigenvalues_sorted = np.sort(eigenvalues)[::-1]

    spectral_gap = eigenvalues_sorted[1] - eigenvalues_sorted[0]

    # Node churn
    node_additions = [
        len(history[i+1].nodes) - len(history[i].nodes)
        for i in range(len(history)-1)
    ]
    node_churn = np.std(node_additions)

    # Clustering coefficient
    clustering_coeffs = [
        G.average_clustering_coefficient()
        for G in history[-10:]  # Last 10 snapshots
    ]
    clustering_variance = np.var(clustering_coeffs)

    return {
        "spectral_gap": spectral_gap,
        "node_churn": node_churn,
        "clustering_variance": clustering_variance,
        "is_converging": spectral_gap < 0.1 and node_churn < 5 and clustering_variance < 0.01
    }
```

**Graph-Guided Retrieval:**

```python
def retrieve_via_graph_walk(
    query: str,
    G: KnowledgeGraph,
    max_depth: int = 3,
    max_nodes: int = 20
) -> List[Memory]:
    """
    Retrieve memories using graph-guided walk from query entities.

    Algorithm:
      1. Extract entities from query
      2. Find corresponding nodes in G
      3. Perform weighted BFS/DFS from these nodes
      4. Collect memories associated with traversed nodes
      5. Rank by path strength and relevance
    """
    # Extract query entities
    query_entities = extract_entities(query)

    # Map to graph nodes
    start_nodes = []
    for entity in query_entities:
        nodes = G.find_nodes_by_label(entity, similarity_threshold=0.8)
        start_nodes.extend(nodes)

    if not start_nodes:
        return []  # Fall back to vector search

    # Weighted graph walk
    visited = set()
    memory_scores = {}

    queue = [(node, 1.0, 0) for node in start_nodes]  # (node, score, depth)

    while queue and len(visited) < max_nodes:
        node, score, depth = queue.pop(0)

        if node in visited or depth > max_depth:
            continue

        visited.add(node)

        # Collect memories associated with this node
        memories = G.get_memories_for_node(node)
        for memory in memories:
            if memory.id not in memory_scores:
                memory_scores[memory.id] = 0.0
            memory_scores[memory.id] += score

        # Add neighbors to queue
        for edge in G.edges_from(node):
            neighbor_score = score * edge.weight * (0.9 ** depth)  # Decay with depth
            queue.append((edge.target, neighbor_score, depth + 1))

    # Rank memories by accumulated score
    ranked_memories = sorted(
        memory_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return [memory_id for memory_id, score in ranked_memories[:max_nodes]]
```

---

## Current State Analysis

### Existing Components Mapping

| RAE Component | Math Concept | Implementation Status | File Location |
|---------------|-------------|----------------------|---------------|
| **5-layer memory** (episodic/working/semantic/ltm/reflective) | State space S | ✅ Implicit | `apps/memory_api/services/hybrid_search.py` |
| Memory consolidation | State transitions | ✅ Implemented | `apps/memory_api/services/memory_consolidation.py` |
| Retrieval methods | Action space A | ✅ Implicit | `apps/memory_api/services/hybrid_search.py` |
| Importance scoring | Partial reward | ⚠️ No cost integration | `apps/memory_api/services/importance_scoring.py` |
| Cost calculation | Cost term in reward | ✅ Implemented | `apps/memory_api/services/cost_controller.py` |
| Graph operations | Graph G_t | ✅ Implemented | `apps/memory_api/repositories/graph_repository.py` |
| Reflection pipeline | Meta-learning | ✅ Implemented | `apps/memory_api/services/reflection_pipeline.py` |
| Context selection | Information bottleneck Z | ❌ No IB formalization | `apps/memory_api/services/hybrid_search.py` |

### Gaps to Address

1. **No explicit state representation** - State is implicit in function calls
2. **No action abstraction** - Actions are scattered across services
3. **No reward computation** - Success is not formally measured
4. **No policy framework** - Decision-making is heuristic, not optimizable
5. **No information bottleneck metrics** - Context selection lacks theoretical grounding
6. **No graph update operator** - Graph evolution is ad-hoc, not formalized

---

## 5-Iteration Refactoring Plan

Each iteration is **self-contained**, **testable**, and **incrementally valuable**.

---

### Iteration 1: Formalize State Representation

**Goal:** Create explicit `RAEState` class that captures system state at any moment.

**Mathematical Concept:** Define `s_t ∈ S` (state space)

**Why First:** Foundation for MDP - everything else depends on state definition

**Files to Create/Modify:**

1. **Create:** `apps/memory_api/core/state.py`
2. **Modify:** `apps/memory_api/services/hybrid_search.py`
3. **Create:** `tests/core/test_state.py`

**Implementation Steps:**

#### Step 1.1: Define `RAEState` class

Create `apps/memory_api/core/state.py`:

```python
"""
RAE State Representation - Mathematical formalization of system state.

This module implements the State space S in our MDP formulation:
  s_t = (working_context, memory_state, budget_state, graph_state)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
from pydantic import BaseModel, Field


@dataclass
class WorkingContext:
    """
    Current context window being used for LLM interactions.

    This is the "information bottleneck" Z in our formulation.
    """
    content: List[str] = field(default_factory=list)
    token_count: int = 0
    embeddings: Optional[np.ndarray] = None
    importance_scores: List[float] = field(default_factory=list)
    source_memory_ids: List[UUID] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "token_count": self.token_count,
            "importance_scores": self.importance_scores,
            "memory_count": len(self.content)
        }


@dataclass
class MemoryLayerState:
    """State of a single memory layer (episodic/semantic/reflective)"""
    count: int = 0
    avg_importance: float = 0.0
    recency_distribution: Optional[np.ndarray] = None
    coverage: float = 0.0  # 0-1: how much of this layer is "active"

    def to_dict(self) -> Dict:
        return {
            "count": self.count,
            "avg_importance": self.avg_importance,
            "coverage": self.coverage
        }


@dataclass
class MemoryState:
    """Complete memory system state across all layers"""
    episodic: MemoryLayerState = field(default_factory=MemoryLayerState)
    semantic: MemoryLayerState = field(default_factory=MemoryLayerState)
    reflective: MemoryLayerState = field(default_factory=MemoryLayerState)

    def to_dict(self) -> Dict:
        return {
            "episodic": self.episodic.to_dict(),
            "semantic": self.semantic.to_dict(),
            "reflective": self.reflective.to_dict()
        }


@dataclass
class BudgetState:
    """
    Resource budget state for cost-aware decision making.

    Used in reward function: R = Quality - λ·tokens - μ·latency
    """
    remaining_tokens: int = 100000
    remaining_cost_usd: float = 10.0
    latency_budget_ms: int = 30000
    calls_remaining: int = 100

    def to_dict(self) -> Dict:
        return {
            "remaining_tokens": self.remaining_tokens,
            "remaining_cost_usd": self.remaining_cost_usd,
            "latency_budget_ms": self.latency_budget_ms,
            "calls_remaining": self.calls_remaining
        }

    def is_exhausted(self) -> bool:
        """Check if any budget constraint is violated"""
        return (
            self.remaining_tokens <= 0 or
            self.remaining_cost_usd <= 0.0 or
            self.latency_budget_ms <= 0 or
            self.calls_remaining <= 0
        )


@dataclass
class GraphState:
    """Knowledge graph state"""
    node_count: int = 0
    edge_count: int = 0
    avg_centrality: float = 0.0
    connected_components: int = 0
    last_updated: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "avg_centrality": self.avg_centrality,
            "connected_components": self.connected_components
        }


class RAEState(BaseModel):
    """
    Complete RAE system state at time t.

    Mathematical notation: s_t ∈ S

    This is the foundational state representation for:
      1. MDP formulation: Enables transition P(s_{t+1} | s_t, a_t)
      2. Reward calculation: R(s_t, a_t, s_{t+1})
      3. Policy definition: π(a_t | s_t)

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
    last_action: Optional[Dict] = Field(None, description="Last action that led to this state")

    class Config:
        arbitrary_types_allowed = True

    def to_dict(self) -> Dict:
        """Serialize state to dictionary"""
        return {
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "working_context": self.working_context.to_dict(),
            "memory_state": self.memory_state.to_dict(),
            "budget_state": self.budget_state.to_dict(),
            "graph_state": self.graph_state.to_dict(),
            "last_action": self.last_action
        }

    def compare(self, other: "RAEState") -> Dict:
        """
        Compare this state with another to compute delta.

        Useful for:
          - Transition analysis: Δs = s_{t+1} - s_t
          - Reward calculation: R depends on state changes
          - Debugging: Understand action effects
        """
        return {
            "token_delta": (
                self.budget_state.remaining_tokens -
                other.budget_state.remaining_tokens
            ),
            "cost_delta": (
                self.budget_state.remaining_cost_usd -
                other.budget_state.remaining_cost_usd
            ),
            "context_size_delta": (
                self.working_context.token_count -
                other.working_context.token_count
            ),
            "graph_nodes_delta": (
                self.graph_state.node_count -
                other.graph_state.node_count
            ),
            "time_delta_ms": (
                (self.timestamp - other.timestamp).total_seconds() * 1000
            )
        }

    def is_valid(self) -> bool:
        """
        Validate state consistency.

        Checks:
          - Budget constraints not violated
          - Context size matches token count
          - No negative values
        """
        if self.budget_state.is_exhausted():
            return False

        if self.working_context.token_count < 0:
            return False

        if len(self.working_context.content) != len(self.working_context.importance_scores):
            return False

        return True
```

#### Step 1.2: Integrate state tracking into HybridSearchService

Modify `apps/memory_api/services/hybrid_search.py`:

Add state initialization at beginning of `search()` method:

```python
async def search(
    self,
    query: str,
    tenant_id: str,
    project_id: str,
    top_k_vector: int = 5,
    graph_depth: int = 2,
    traversal_strategy: TraversalStrategy = TraversalStrategy.BFS,
    use_graph: bool = True,
    filters: Optional[Dict[str, Any]] = None,
) -> HybridSearchResult:
    """Perform hybrid search combining vector similarity and graph traversal."""

    # NEW: Initialize RAE state before search
    from apps.memory_api.core.state import RAEState, BudgetState, GraphState

    initial_state = RAEState(
        tenant_id=tenant_id,
        project_id=project_id,
        budget_state=BudgetState(
            remaining_tokens=100000,  # Default budget
            remaining_cost_usd=10.0,
            latency_budget_ms=30000
        )
    )

    logger.info(
        "hybrid_search_started_with_state",
        state=initial_state.to_dict()
    )

    # ... rest of existing search logic ...

    # NEW: Update state after search completes
    final_state = RAEState(
        tenant_id=tenant_id,
        project_id=project_id,
        budget_state=BudgetState(
            remaining_tokens=initial_state.budget_state.remaining_tokens - statistics.get("context_length", 0),
            remaining_cost_usd=initial_state.budget_state.remaining_cost_usd  # No LLM cost yet
        ),
        graph_state=GraphState(
            node_count=len(graph_nodes),
            edge_count=len(graph_edges)
        )
    )

    # Log state transition
    state_delta = final_state.compare(initial_state)
    logger.info(
        "hybrid_search_completed_state_transition",
        state_delta=state_delta
    )

    return HybridSearchResult(...)
```

#### Step 1.3: Create comprehensive tests

Create `tests/core/test_state.py`:

```python
import pytest
from datetime import datetime
from apps.memory_api.core.state import (
    RAEState, WorkingContext, MemoryState, BudgetState, GraphState
)


def test_rae_state_creation():
    """Test basic state creation"""
    state = RAEState(
        tenant_id="test",
        project_id="test-project"
    )

    assert state.tenant_id == "test"
    assert state.project_id == "test-project"
    assert state.is_valid()


def test_budget_exhaustion():
    """Test budget constraint checking"""
    state = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=0)
    )

    assert state.budget_state.is_exhausted()
    assert not state.is_valid()


def test_state_comparison():
    """Test state delta computation"""
    state1 = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=100000)
    )

    state2 = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=95000),
        timestamp=datetime.now()
    )

    delta = state2.compare(state1)

    assert delta["token_delta"] == -5000
    assert delta["time_delta_ms"] >= 0


def test_state_serialization():
    """Test state can be serialized to dict"""
    state = RAEState(
        tenant_id="test",
        project_id="test"
    )

    state_dict = state.to_dict()

    assert "tenant_id" in state_dict
    assert "working_context" in state_dict
    assert "budget_state" in state_dict
    assert state_dict["tenant_id"] == "test"
```

**Validation Criteria:**

✅ All tests pass
✅ `RAEState` can be created and serialized
✅ State tracking integrated into at least one service (HybridSearch)
✅ No performance regression (state overhead <5ms)
✅ Documentation updated with state concept

**Success Metrics:**

- [ ] `test_state.py` passes 100%
- [ ] State logged in `hybrid_search` operations
- [ ] Zero breaking changes to existing APIs
- [ ] Code review: State representation is clear and usable

---

### Iteration 2: Define Action Space and Action Abstraction

**Goal:** Formalize all RAE operations as discrete `Action` objects in action space A.

**Mathematical Concept:** Define `a_t ∈ A` (action space) with clear semantics

**Why Second:** Actions operate on states - need state (Iteration 1) before actions make sense

**Files to Create/Modify:**

1. **Create:** `apps/memory_api/core/actions.py`
2. **Create:** `apps/memory_api/core/action_executor.py`
3. **Modify:** `apps/memory_api/services/hybrid_search.py`
4. **Create:** `tests/core/test_actions.py`

**Implementation Steps:**

#### Step 2.1: Define Action classes

Create `apps/memory_api/core/actions.py`:

```python
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
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from apps.memory_api.core.state import RAEState


class ActionType(str, Enum):
    """All possible action types in RAE system"""

    # Retrieval actions
    RETRIEVE_EPISODIC = "retrieve_episodic"
    RETRIEVE_SEMANTIC = "retrieve_semantic"
    RETRIEVE_REFLECTIVE = "retrieve_reflective"
    RETRIEVE_HYBRID = "retrieve_hybrid"

    # Memory management actions
    UPDATE_MEMORY = "update_memory"
    CONSOLIDATE_MEMORIES = "consolidate_memories"
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
    """

    action_type: ActionType = Field(..., description="Type of action")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Action parameters")

    # Cost estimation (for planning and reward calculation)
    estimated_tokens: int = Field(0, description="Estimated token usage")
    estimated_cost_usd: float = Field(0.0, description="Estimated dollar cost")
    estimated_latency_ms: int = Field(0, description="Estimated latency")

    # Metadata
    created_at: Optional[str] = None
    reason: Optional[str] = Field(None, description="Why this action was selected")

    @abstractmethod
    def is_valid_for_state(self, state: RAEState) -> bool:
        """
        Check if action can be executed in given state.

        Returns True if preconditions are met.
        """
        pass

    @abstractmethod
    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        """
        Estimate resource costs for this action in given state.

        Returns dict with:
          - tokens: Expected token usage
          - cost_usd: Expected dollar cost
          - latency_ms: Expected latency
        """
        pass

    def to_dict(self) -> Dict:
        """Serialize action to dictionary"""
        return {
            "action_type": self.action_type.value,
            "parameters": self.parameters,
            "estimated_tokens": self.estimated_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_latency_ms": self.estimated_latency_ms,
            "reason": self.reason
        }


# ============================================================================
# Concrete Action Implementations
# ============================================================================


class RetrieveEpisodicAction(Action):
    """
    Retrieve recent episodic memories.

    Parameters:
      - k: Number of memories to retrieve
      - threshold: Minimum relevance threshold (0-1)
      - time_window_days: Only retrieve from last N days
    """

    action_type: ActionType = ActionType.RETRIEVE_EPISODIC

    def is_valid_for_state(self, state: RAEState) -> bool:
        # Check budget
        if state.budget_state.is_exhausted():
            return False

        # Check we have episodic memories
        if state.memory_state.episodic.count == 0:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        k = self.parameters.get("k", 10)

        # Episodic retrieval: mainly embedding computation cost
        # Assume ~100 tokens per memory
        estimated_tokens = k * 100

        return {
            "tokens": estimated_tokens,
            "cost_usd": 0.0,  # No LLM cost, just retrieval
            "latency_ms": k * 5  # ~5ms per memory retrieval
        }


class RetrieveSemanticAction(Action):
    """
    Retrieve semantically similar memories.

    Parameters:
      - k: Number of memories to retrieve
      - use_graph: Whether to use graph traversal
      - graph_depth: If using graph, how deep to traverse
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

        return {
            "tokens": estimated_tokens,
            "cost_usd": 0.0,
            "latency_ms": latency
        }


class CallLLMAction(Action):
    """
    Call LLM with current context.

    Parameters:
      - model: Model name (gpt-4o, claude-3.5-sonnet, etc.)
      - max_tokens: Maximum output tokens
      - temperature: Sampling temperature
      - system_prompt: Optional system prompt
    """

    action_type: ActionType = ActionType.CALL_LLM

    def is_valid_for_state(self, state: RAEState) -> bool:
        # Check budget
        if state.budget_state.is_exhausted():
            return False

        # Check we have context
        if state.working_context.token_count == 0:
            return False

        # Check estimated cost doesn't exceed budget
        estimated = self.estimate_cost(state)
        if estimated["cost_usd"] > state.budget_state.remaining_cost_usd:
            return False

        if estimated["tokens"] > state.budget_state.remaining_tokens:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        from apps.memory_api.cost_model import get_model_cost

        model = self.parameters.get("model", "gpt-4o-mini")
        max_tokens = self.parameters.get("max_tokens", 1000)

        # Input tokens = current context
        input_tokens = state.working_context.token_count
        output_tokens = max_tokens

        # Get model costs
        costs = get_model_cost(model)
        if costs:
            input_cost = (input_tokens / 1_000_000) * costs["input"]
            output_cost = (output_tokens / 1_000_000) * costs["output"]
            total_cost = input_cost + output_cost
        else:
            total_cost = 0.0

        # Latency estimate (very rough)
        latency = 1000 + (output_tokens * 50)  # ~50ms per output token

        return {
            "tokens": input_tokens + output_tokens,
            "cost_usd": total_cost,
            "latency_ms": latency
        }


class PruneContextAction(Action):
    """
    Prune context to reduce size.

    Parameters:
      - strategy: "importance" | "recency" | "relevance"
      - target_size: Target token count
      - min_keep: Minimum items to keep
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
            "latency_ms": 10  # Fast operation
        }


class GenerateReflectionAction(Action):
    """
    Generate reflection from memories.

    Parameters:
      - max_memories: Maximum memories to reflect on
      - min_cluster_size: Minimum cluster size for insights
      - level: "L1" | "L2" | "L3" reflection depth
    """

    action_type: ActionType = ActionType.GENERATE_REFLECTION

    def is_valid_for_state(self, state: RAEState) -> bool:
        if state.budget_state.is_exhausted():
            return False

        # Need sufficient memories to reflect on
        total_memories = (
            state.memory_state.episodic.count +
            state.memory_state.semantic.count
        )

        min_memories = self.parameters.get("min_cluster_size", 5) * 2
        if total_memories < min_memories:
            return False

        return True

    def estimate_cost(self, state: RAEState) -> Dict[str, float]:
        max_memories = self.parameters.get("max_memories", 100)
        min_cluster_size = self.parameters.get("min_cluster_size", 5)

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

        return {
            "tokens": total_tokens,
            "cost_usd": total_cost,
            "latency_ms": latency
        }


class UpdateGraphAction(Action):
    """
    Update knowledge graph with new information.

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

        return {
            "tokens": 0,
            "cost_usd": 0.0,
            "latency_ms": latency
        }
```

#### Step 2.2: Create Action Executor

Create `apps/memory_api/core/action_executor.py`:

```python
"""
Action Executor - Executes actions and tracks state transitions.

This module implements the transition function:
  s_{t+1} = T(s_t, a_t)

It also logs transitions for:
  - Reward calculation
  - Policy learning
  - Debugging
"""

import structlog
from typing import Tuple, Dict, Any
from datetime import datetime

from apps.memory_api.core.state import RAEState
from apps.memory_api.core.actions import Action, ActionType

logger = structlog.get_logger(__name__)


class ActionExecutor:
    """
    Executes actions and manages state transitions.

    Usage:
        executor = ActionExecutor()

        state = RAEState(...)
        action = RetrieveEpisodicAction(parameters={"k": 10})

        # Check if action is valid
        if executor.can_execute(action, state):
            new_state = await executor.execute(action, state)

            # Analyze transition
            transition = executor.get_last_transition()
            reward = compute_reward(transition)
    """

    def __init__(self):
        self.last_transition: Optional[Dict] = None

    def can_execute(self, action: Action, state: RAEState) -> bool:
        """
        Check if action can be executed in current state.

        Validates:
          - Action preconditions
          - Budget constraints
          - State validity
        """
        if not state.is_valid():
            logger.warning("invalid_state_for_action", state=state.to_dict())
            return False

        if not action.is_valid_for_state(state):
            logger.warning(
                "action_preconditions_not_met",
                action=action.to_dict(),
                state=state.to_dict()
            )
            return False

        # Check budget
        estimated_cost = action.estimate_cost(state)

        if estimated_cost["tokens"] > state.budget_state.remaining_tokens:
            logger.warning(
                "insufficient_token_budget",
                required=estimated_cost["tokens"],
                available=state.budget_state.remaining_tokens
            )
            return False

        if estimated_cost["cost_usd"] > state.budget_state.remaining_cost_usd:
            logger.warning(
                "insufficient_cost_budget",
                required=estimated_cost["cost_usd"],
                available=state.budget_state.remaining_cost_usd
            )
            return False

        return True

    async def execute(
        self,
        action: Action,
        state: RAEState,
        **execution_context
    ) -> Tuple[RAEState, Dict[str, Any]]:
        """
        Execute action and return new state + execution metadata.

        Args:
            action: Action to execute
            state: Current state
            execution_context: Additional context for execution (services, db, etc.)

        Returns:
            Tuple of (new_state, execution_result)

        Raises:
            ValueError: If action cannot be executed
        """
        if not self.can_execute(action, state):
            raise ValueError(f"Cannot execute action {action.action_type} in current state")

        logger.info(
            "executing_action",
            action_type=action.action_type.value,
            parameters=action.parameters,
            state=state.to_dict()
        )

        execution_start = datetime.now()

        # Execute action based on type
        if action.action_type == ActionType.RETRIEVE_EPISODIC:
            new_state, result = await self._execute_retrieve_episodic(action, state, execution_context)

        elif action.action_type == ActionType.RETRIEVE_SEMANTIC:
            new_state, result = await self._execute_retrieve_semantic(action, state, execution_context)

        elif action.action_type == ActionType.CALL_LLM:
            new_state, result = await self._execute_call_llm(action, state, execution_context)

        elif action.action_type == ActionType.PRUNE_CONTEXT:
            new_state, result = await self._execute_prune_context(action, state, execution_context)

        elif action.action_type == ActionType.GENERATE_REFLECTION:
            new_state, result = await self._execute_generate_reflection(action, state, execution_context)

        elif action.action_type == ActionType.UPDATE_GRAPH:
            new_state, result = await self._execute_update_graph(action, state, execution_context)

        else:
            raise NotImplementedError(f"Action type {action.action_type} not yet implemented")

        execution_duration = (datetime.now() - execution_start).total_seconds() * 1000

        # Record transition
        self.last_transition = {
            "state_before": state.to_dict(),
            "action": action.to_dict(),
            "state_after": new_state.to_dict(),
            "state_delta": new_state.compare(state),
            "execution_duration_ms": execution_duration,
            "execution_result": result
        }

        logger.info(
            "action_executed",
            action_type=action.action_type.value,
            duration_ms=execution_duration,
            state_delta=new_state.compare(state)
        )

        return new_state, result

    def get_last_transition(self) -> Optional[Dict]:
        """Get the last executed transition for reward calculation"""
        return self.last_transition

    # ========================================================================
    # Action-specific execution methods
    # ========================================================================

    async def _execute_retrieve_episodic(
        self, action: Action, state: RAEState, context: Dict
    ) -> Tuple[RAEState, Dict]:
        """Execute episodic memory retrieval"""
        # Import here to avoid circular dependencies
        from apps.memory_api.services.postgres_memory_retrieval import retrieve_memories

        k = action.parameters.get("k", 10)
        threshold = action.parameters.get("threshold", 0.7)

        # Call existing retrieval service
        memories = await retrieve_memories(
            tenant_id=state.tenant_id,
            project_id=state.project_id,
            k=k,
            layer="episodic",
            pool=context.get("pool")
        )

        # Update state
        new_state = state.copy(deep=True)
        new_state.working_context.content.extend([m.content for m in memories])
        new_state.working_context.token_count += sum(count_tokens(m.content) for m in memories)
        new_state.working_context.source_memory_ids.extend([m.id for m in memories])

        return new_state, {"memories_retrieved": len(memories), "memories": memories}

    async def _execute_retrieve_semantic(
        self, action: Action, state: RAEState, context: Dict
    ) -> Tuple[RAEState, Dict]:
        """Execute semantic memory retrieval"""
        # Similar to episodic but uses hybrid search
        from apps.memory_api.services.hybrid_search import HybridSearchService

        k = action.parameters.get("k", 20)
        use_graph = action.parameters.get("use_graph", False)

        search_service = context.get("hybrid_search_service")
        if not search_service:
            raise ValueError("hybrid_search_service not provided in execution context")

        result = await search_service.search(
            query=context.get("query", ""),
            tenant_id=state.tenant_id,
            project_id=state.project_id,
            top_k_vector=k,
            use_graph=use_graph
        )

        # Update state
        new_state = state.copy(deep=True)
        new_state.working_context.content.append(result.synthesized_context)
        new_state.working_context.token_count += count_tokens(result.synthesized_context)

        return new_state, {"search_result": result}

    async def _execute_call_llm(
        self, action: Action, state: RAEState, context: Dict
    ) -> Tuple[RAEState, Dict]:
        """Execute LLM call with current context"""
        from apps.memory_api.services.llm import get_llm_provider

        model = action.parameters.get("model", "gpt-4o-mini")
        max_tokens = action.parameters.get("max_tokens", 1000)

        llm_provider = get_llm_provider()

        # Build prompt from working context
        prompt = "\n\n".join(state.working_context.content)

        result = await llm_provider.generate(
            system=action.parameters.get("system_prompt", "You are a helpful assistant."),
            prompt=prompt,
            model=model,
            max_tokens=max_tokens
        )

        # Update budget
        new_state = state.copy(deep=True)
        new_state.budget_state.remaining_tokens -= result.usage.total_tokens
        new_state.budget_state.remaining_cost_usd -= result.cost_usd
        new_state.budget_state.calls_remaining -= 1

        return new_state, {"llm_result": result}

    async def _execute_prune_context(
        self, action: Action, state: RAEState, context: Dict
    ) -> Tuple[RAEState, Dict]:
        """Prune working context to target size"""
        strategy = action.parameters.get("strategy", "importance")
        target_size = action.parameters.get("target_size", 2000)

        # Sort by importance and keep top items
        if strategy == "importance":
            # Zip content with importance scores
            items = list(zip(
                state.working_context.content,
                state.working_context.importance_scores,
                state.working_context.source_memory_ids
            ))

            # Sort by importance descending
            items_sorted = sorted(items, key=lambda x: x[1], reverse=True)

            # Keep until target size reached
            pruned_content = []
            pruned_scores = []
            pruned_ids = []
            current_tokens = 0

            for content, score, mem_id in items_sorted:
                tokens = count_tokens(content)
                if current_tokens + tokens <= target_size:
                    pruned_content.append(content)
                    pruned_scores.append(score)
                    pruned_ids.append(mem_id)
                    current_tokens += tokens
                else:
                    break

            # Update state
            new_state = state.copy(deep=True)
            new_state.working_context.content = pruned_content
            new_state.working_context.importance_scores = pruned_scores
            new_state.working_context.source_memory_ids = pruned_ids
            new_state.working_context.token_count = current_tokens

            removed_count = len(state.working_context.content) - len(pruned_content)

            return new_state, {
                "items_removed": removed_count,
                "tokens_saved": state.working_context.token_count - current_tokens
            }

        else:
            raise NotImplementedError(f"Prune strategy '{strategy}' not implemented")

    async def _execute_generate_reflection(
        self, action: Action, state: RAEState, context: Dict
    ) -> Tuple[RAEState, Dict]:
        """Generate reflection from memories"""
        from apps.memory_api.services.reflection_pipeline import ReflectionPipeline
        from apps.memory_api.models.reflection_models import GenerateReflectionRequest

        pipeline = ReflectionPipeline(pool=context.get("pool"))

        request = GenerateReflectionRequest(
            tenant_id=state.tenant_id,
            project=state.project_id,
            max_memories=action.parameters.get("max_memories", 100),
            min_cluster_size=action.parameters.get("min_cluster_size", 5)
        )

        reflections, statistics = await pipeline.generate_reflections(request)

        # Update state
        new_state = state.copy(deep=True)
        new_state.memory_state.reflective.count += len(reflections)
        new_state.budget_state.remaining_cost_usd -= statistics["total_cost_usd"]

        return new_state, {"reflections": reflections, "statistics": statistics}

    async def _execute_update_graph(
        self, action: Action, state: RAEState, context: Dict
    ) -> Tuple[RAEState, Dict]:
        """Update knowledge graph"""
        from apps.memory_api.repositories.graph_repository import GraphRepository

        graph_repo = context.get("graph_repository")
        if not graph_repo:
            raise ValueError("graph_repository not provided in execution context")

        operation = action.parameters.get("operation", "add_node")

        if operation == "add_node":
            node_data = action.parameters.get("node_data")
            # Add node logic...
            result = {"node_added": True}

        elif operation == "add_edge":
            edge_data = action.parameters.get("edge_data")
            # Add edge logic...
            result = {"edge_added": True}

        else:
            raise NotImplementedError(f"Graph operation '{operation}' not implemented")

        # Update graph state
        new_state = state.copy(deep=True)
        # Graph stats would be updated by querying actual graph

        return new_state, result


def count_tokens(text: str) -> int:
    """Simple token counter (approximate)"""
    # Rough approximation: 1 token ≈ 4 characters
    return len(text) // 4
```

#### Step 2.3: Create tests

Create `tests/core/test_actions.py`:

```python
import pytest
from apps.memory_api.core.actions import (
    RetrieveEpisodicAction, CallLLMAction, PruneContextAction,
    ActionType
)
from apps.memory_api.core.state import RAEState, BudgetState, MemoryState, MemoryLayerState


def test_retrieve_episodic_action_creation():
    """Test creating retrieve episodic action"""
    action = RetrieveEpisodicAction(
        parameters={"k": 10, "threshold": 0.7}
    )

    assert action.action_type == ActionType.RETRIEVE_EPISODIC
    assert action.parameters["k"] == 10


def test_action_preconditions():
    """Test action precondition checking"""
    action = RetrieveEpisodicAction(parameters={"k": 10})

    # Valid state
    state = RAEState(
        tenant_id="test",
        project_id="test",
        memory_state=MemoryState(
            episodic=MemoryLayerState(count=100)
        )
    )

    assert action.is_valid_for_state(state)

    # Invalid state (no episodic memories)
    empty_state = RAEState(
        tenant_id="test",
        project_id="test"
    )

    assert not action.is_valid_for_state(empty_state)


def test_action_cost_estimation():
    """Test action cost estimation"""
    action = CallLLMAction(
        parameters={
            "model": "gpt-4o-mini",
            "max_tokens": 1000
        }
    )

    state = RAEState(
        tenant_id="test",
        project_id="test"
    )
    state.working_context.token_count = 2000

    cost_estimate = action.estimate_cost(state)

    assert cost_estimate["tokens"] > 0
    assert cost_estimate["cost_usd"] >= 0.0
    assert cost_estimate["latency_ms"] > 0


@pytest.mark.asyncio
async def test_action_executor():
    """Test action execution"""
    from apps.memory_api.core.action_executor import ActionExecutor

    executor = ActionExecutor()

    action = PruneContextAction(
        parameters={
            "strategy": "importance",
            "target_size": 500
        }
    )

    # Create state with large context
    state = RAEState(
        tenant_id="test",
        project_id="test"
    )
    state.working_context.content = ["memory 1", "memory 2", "memory 3"]
    state.working_context.importance_scores = [0.9, 0.5, 0.3]
    state.working_context.token_count = 1000

    # Check if can execute
    assert executor.can_execute(action, state)

    # Execute
    new_state, result = await executor.execute(action, state)

    # Verify state changed
    assert new_state.working_context.token_count < state.working_context.token_count
    assert result["tokens_saved"] > 0
```

**Validation Criteria:**

✅ All action types defined with clear semantics
✅ Each action has `is_valid_for_state()` and `estimate_cost()`
✅ `ActionExecutor` can execute at least 3 action types
✅ Tests pass 100%
✅ Actions logged in system operations

**Success Metrics:**

- [ ] `test_actions.py` passes 100%
- [ ] At least 3 concrete actions fully implemented
- [ ] Action execution logged with state transitions
- [ ] No breaking changes to existing APIs

---

### Iteration 3: Implement Reward Function and Metrics

**Goal:** Implement formal reward function `R(s_t, a_t, s_{t+1}) = Quality - λ·tokens - μ·latency`

**Mathematical Concept:** Reward as objective to maximize

**Why Third:** Need state (Iteration 1) and actions (Iteration 2) to compute rewards for transitions

**Files to Create/Modify:**

1. **Create:** `apps/memory_api/core/reward.py`
2. **Create:** `apps/memory_api/core/metrics.py`
3. **Modify:** `apps/memory_api/core/action_executor.py`
4. **Create:** `tests/core/test_reward.py`

**Implementation Steps:**

#### Step 3.1: Implement reward function

Create `apps/memory_api/core/reward.py`:

```python
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

import structlog
from typing import Dict, Any, Optional
from dataclasses import dataclass

from apps.memory_api.core.state import RAEState
from apps.memory_api.core.actions import Action

logger = structlog.get_logger(__name__)


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
    token_cost: float     # Absolute tokens used
    latency_cost: float   # Absolute milliseconds

    # Weighted components
    quality_reward: float
    token_penalty: float
    latency_penalty: float

    # Final reward
    total_reward: float

    # Metadata
    lambda_weight: float  # Token cost weight
    mu_weight: float      # Latency cost weight

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
            "mu_weight": self.mu_weight
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
        mu: float = 0.01,        # Latency weight: 1ms = 0.01 penalty
        discount_factor: float = 0.95
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
        execution_result: Optional[Dict[str, Any]] = None
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
        # Component 1: Quality
        quality_score = self._evaluate_quality(state_before, action, state_after, execution_result)

        # Component 2: Token cost
        state_delta = state_after.compare(state_before)
        token_cost = abs(state_delta["token_delta"])  # Tokens consumed

        # Component 3: Latency
        latency_cost = state_delta["time_delta_ms"]

        # Compute weighted components
        quality_reward = quality_score  # Already 0-1
        token_penalty = self.lambda_ * token_cost
        latency_penalty = self.mu * latency_cost

        # Total reward
        total_reward = quality_reward - token_penalty - latency_penalty

        components = RewardComponents(
            quality_score=quality_score,
            token_cost=token_cost,
            latency_cost=latency_cost,
            quality_reward=quality_reward,
            token_penalty=token_penalty,
            latency_penalty=latency_penalty,
            total_reward=total_reward,
            lambda_weight=self.lambda_,
            mu_weight=self.mu
        )

        logger.debug(
            "reward_computed",
            action_type=action.action_type.value,
            reward_components=components.to_dict()
        )

        return components

    def _evaluate_quality(
        self,
        state_before: RAEState,
        action: Action,
        state_after: RAEState,
        execution_result: Optional[Dict] = None
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
        from apps.memory_api.core.actions import ActionType

        action_type = action.action_type

        if action_type in [ActionType.RETRIEVE_EPISODIC, ActionType.RETRIEVE_SEMANTIC]:
            # Quality = relevance + diversity of retrieved memories
            quality = self._evaluate_retrieval_quality(execution_result)

        elif action_type == ActionType.CALL_LLM:
            # Quality = heuristic based on output length and coherence
            # (In production: user feedback, human ratings, etc.)
            quality = self._evaluate_llm_quality(execution_result)

        elif action_type == ActionType.GENERATE_REFLECTION:
            # Quality = novelty and importance scores from reflection
            quality = self._evaluate_reflection_quality(execution_result)

        elif action_type == ActionType.PRUNE_CONTEXT:
            # Quality = how much we compressed while preserving importance
            quality = self._evaluate_pruning_quality(state_before, state_after, execution_result)

        elif action_type == ActionType.UPDATE_GRAPH:
            # Quality = graph structure improvement
            quality = self._evaluate_graph_update_quality(state_before, state_after)

        else:
            # Default: neutral quality
            quality = 0.5

        return max(0.0, min(1.0, quality))  # Clamp to [0, 1]

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

        return quality

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
        output_text = llm_result.text if hasattr(llm_result, "text") else ""
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
            return avg_quality
        else:
            return 0.6  # Default if no scoring available

    def _evaluate_pruning_quality(
        self, state_before: RAEState, state_after: RAEState, execution_result: Optional[Dict]
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
        items_removed = execution_result.get("items_removed", 0)

        if tokens_saved == 0:
            return 0.0

        # Compression ratio
        compression_ratio = tokens_saved / max(1, state_before.working_context.token_count)

        # Quality = compression achieved (good pruning removes a lot)
        quality = min(1.0, compression_ratio * 2)  # Max at 50% compression

        return quality

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

#### Step 3.2: Create metrics tracking system

Create `apps/memory_api/core/metrics.py`:

```python
"""
RAE Metrics System - Track MDP performance and information bottleneck metrics.

Metrics Categories:
  1. MDP Metrics: Rewards, transitions, policy performance
  2. Information Bottleneck: I(Z;Y), I(Z;X), compression ratios
  3. Cost Metrics: Token usage, dollar cost, latency
  4. Graph Metrics: Convergence, structure quality
"""

import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field
import numpy as np

logger = structlog.get_logger(__name__)


@dataclass
class MDPMetrics:
    """Metrics for MDP performance tracking"""

    # Reward statistics
    avg_reward_per_action: Dict[str, float] = field(default_factory=dict)
    cumulative_reward: float = 0.0
    reward_history: List[float] = field(default_factory=list)

    # Transition statistics
    total_transitions: int = 0
    transitions_by_action: Dict[str, int] = field(default_factory=dict)

    # Budget tracking
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0

    # Policy performance
    avg_quality_score: float = 0.0
    budget_efficiency: float = 0.0  # Quality per dollar spent

    def to_dict(self) -> Dict:
        return {
            "avg_reward_per_action": self.avg_reward_per_action,
            "cumulative_reward": self.cumulative_reward,
            "total_transitions": self.total_transitions,
            "transitions_by_action": self.transitions_by_action,
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "avg_quality_score": self.avg_quality_score,
            "budget_efficiency": self.budget_efficiency
        }


@dataclass
class InformationBottleneckMetrics:
    """Metrics for information bottleneck performance"""

    # Mutual information estimates
    I_Z_Y: float = 0.0  # Information between context Z and output Y
    I_Z_X: float = 0.0  # Information between context Z and full memory X

    # Compression metrics
    compression_ratio: float = 0.0  # |Z| / |X|
    context_efficiency: float = 0.0  # I(Z;Y) / |Z| (information per token)

    # History
    compression_history: List[float] = field(default_factory=list)
    efficiency_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "I_Z_Y": self.I_Z_Y,
            "I_Z_X": self.I_Z_X,
            "compression_ratio": self.compression_ratio,
            "context_efficiency": self.context_efficiency,
            "avg_compression": np.mean(self.compression_history) if self.compression_history else 0.0,
            "avg_efficiency": np.mean(self.efficiency_history) if self.efficiency_history else 0.0
        }


@dataclass
class GraphMetrics:
    """Metrics for knowledge graph evolution"""

    # Structure metrics
    node_count: int = 0
    edge_count: int = 0
    avg_degree: float = 0.0
    clustering_coefficient: float = 0.0

    # Evolution metrics
    nodes_added_per_hour: float = 0.0
    edges_added_per_hour: float = 0.0

    # Convergence indicators
    spectral_gap: float = 0.0
    is_converging: bool = False

    def to_dict(self) -> Dict:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "avg_degree": self.avg_degree,
            "clustering_coefficient": self.clustering_coefficient,
            "spectral_gap": self.spectral_gap,
            "is_converging": self.is_converging
        }


class MetricsTracker:
    """
    Centralized metrics tracking for RAE system.

    Usage:
        tracker = MetricsTracker()

        # Record transition
        tracker.record_transition(
            state_before=s_t,
            action=a_t,
            state_after=s_next,
            reward=reward_components
        )

        # Get current metrics
        metrics = tracker.get_current_metrics()

        # Export for analysis
        tracker.export_to_json("metrics.json")
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics tracker.

        Args:
            window_size: Number of recent transitions to keep in memory
        """
        self.window_size = window_size

        # Metrics
        self.mdp_metrics = MDPMetrics()
        self.ib_metrics = InformationBottleneckMetrics()
        self.graph_metrics = GraphMetrics()

        # Circular buffer for recent transitions
        self.recent_transitions = deque(maxlen=window_size)

        # Start time
        self.start_time = datetime.now()

    def record_transition(
        self,
        state_before: "RAEState",
        action: "Action",
        state_after: "RAEState",
        reward: "RewardComponents"
    ):
        """
        Record a state-action-state transition with reward.

        Updates all relevant metrics.
        """
        from apps.memory_api.core.state import RAEState
        from apps.memory_api.core.actions import Action
        from apps.memory_api.core.reward import RewardComponents

        # Store transition
        transition = {
            "timestamp": datetime.now(),
            "state_before": state_before,
            "action": action,
            "state_after": state_after,
            "reward": reward
        }
        self.recent_transitions.append(transition)

        # Update MDP metrics
        self._update_mdp_metrics(action, reward)

        # Update IB metrics
        self._update_ib_metrics(state_before, state_after)

        # Update graph metrics
        self._update_graph_metrics(state_before, state_after)

        logger.debug(
            "transition_recorded",
            action_type=action.action_type.value,
            reward=reward.total_reward,
            cumulative_reward=self.mdp_metrics.cumulative_reward
        )

    def _update_mdp_metrics(self, action: "Action", reward: "RewardComponents"):
        """Update MDP-related metrics"""
        action_type = action.action_type.value

        # Update reward statistics
        self.mdp_metrics.cumulative_reward += reward.total_reward
        self.mdp_metrics.reward_history.append(reward.total_reward)

        # Keep history bounded
        if len(self.mdp_metrics.reward_history) > self.window_size:
            self.mdp_metrics.reward_history = self.mdp_metrics.reward_history[-self.window_size:]

        # Update per-action rewards
        if action_type not in self.mdp_metrics.avg_reward_per_action:
            self.mdp_metrics.avg_reward_per_action[action_type] = 0.0
            self.mdp_metrics.transitions_by_action[action_type] = 0

        count = self.mdp_metrics.transitions_by_action[action_type]
        current_avg = self.mdp_metrics.avg_reward_per_action[action_type]

        # Incremental average update
        new_avg = (current_avg * count + reward.total_reward) / (count + 1)
        self.mdp_metrics.avg_reward_per_action[action_type] = new_avg
        self.mdp_metrics.transitions_by_action[action_type] += 1

        # Update totals
        self.mdp_metrics.total_transitions += 1
        self.mdp_metrics.total_tokens_used += int(reward.token_cost)
        self.mdp_metrics.total_cost_usd += reward.token_penalty / reward.lambda_weight  # Back-calculate actual cost
        self.mdp_metrics.total_latency_ms += int(reward.latency_cost)

        # Update quality average
        count = self.mdp_metrics.total_transitions
        current_avg = self.mdp_metrics.avg_quality_score
        new_avg = (current_avg * (count - 1) + reward.quality_score) / count
        self.mdp_metrics.avg_quality_score = new_avg

        # Budget efficiency
        if self.mdp_metrics.total_cost_usd > 0:
            self.mdp_metrics.budget_efficiency = self.mdp_metrics.avg_quality_score / self.mdp_metrics.total_cost_usd

    def _update_ib_metrics(self, state_before: "RAEState", state_after: "RAEState"):
        """Update information bottleneck metrics"""
        # Estimate I(Z; Y) - how much context predicts output
        # Proxy: context diversity and relevance
        context_size = state_after.working_context.token_count
        importance_scores = state_after.working_context.importance_scores

        if context_size > 0 and importance_scores:
            # I(Z; Y) proxy: average importance * diversity
            avg_importance = np.mean(importance_scores) if importance_scores else 0.5
            diversity = np.std(importance_scores) if len(importance_scores) > 1 else 0.0

            self.ib_metrics.I_Z_Y = 0.7 * avg_importance + 0.3 * min(1.0, diversity * 2)
        else:
            self.ib_metrics.I_Z_Y = 0.0

        # Estimate I(Z; X) - how much of full memory is in context
        # Proxy: compression ratio
        total_memories = (
            state_after.memory_state.episodic.count +
            state_after.memory_state.semantic.count +
            state_after.memory_state.reflective.count
        )

        context_items = len(state_after.working_context.content)

        if total_memories > 0:
            self.ib_metrics.I_Z_X = context_items / total_memories
            self.ib_metrics.compression_ratio = 1.0 - self.ib_metrics.I_Z_X
        else:
            self.ib_metrics.I_Z_X = 0.0
            self.ib_metrics.compression_ratio = 1.0

        # Context efficiency: information per token
        if context_size > 0:
            self.ib_metrics.context_efficiency = self.ib_metrics.I_Z_Y / context_size
        else:
            self.ib_metrics.context_efficiency = 0.0

        # Record history
        self.ib_metrics.compression_history.append(self.ib_metrics.compression_ratio)
        self.ib_metrics.efficiency_history.append(self.ib_metrics.context_efficiency)

        # Keep bounded
        if len(self.ib_metrics.compression_history) > self.window_size:
            self.ib_metrics.compression_history = self.ib_metrics.compression_history[-self.window_size:]
            self.ib_metrics.efficiency_history = self.ib_metrics.efficiency_history[-self.window_size:]

    def _update_graph_metrics(self, state_before: "RAEState", state_after: "RAEState"):
        """Update graph evolution metrics"""
        self.graph_metrics.node_count = state_after.graph_state.node_count
        self.graph_metrics.edge_count = state_after.graph_state.edge_count

        # Average degree
        if self.graph_metrics.node_count > 0:
            self.graph_metrics.avg_degree = (2 * self.graph_metrics.edge_count) / self.graph_metrics.node_count

        # Growth rates
        hours_elapsed = (datetime.now() - self.start_time).total_seconds() / 3600
        if hours_elapsed > 0:
            self.graph_metrics.nodes_added_per_hour = self.graph_metrics.node_count / hours_elapsed
            self.graph_metrics.edges_added_per_hour = self.graph_metrics.edge_count / hours_elapsed

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics summary"""
        return {
            "mdp": self.mdp_metrics.to_dict(),
            "information_bottleneck": self.ib_metrics.to_dict(),
            "graph": self.graph_metrics.to_dict(),
            "session": {
                "duration_minutes": (datetime.now() - self.start_time).total_seconds() / 60,
                "transitions_count": self.mdp_metrics.total_transitions,
                "avg_reward": np.mean(self.mdp_metrics.reward_history) if self.mdp_metrics.reward_history else 0.0
            }
        }

    def export_to_json(self, filepath: str):
        """Export metrics to JSON file"""
        import json

        metrics = self.get_current_metrics()

        with open(filepath, 'w') as f:
            json.dump(metrics, f, indent=2)

        logger.info("metrics_exported", filepath=filepath)

    def get_best_actions(self, top_k: int = 5) -> List[Dict]:
        """
        Get top-k actions by average reward.

        Returns list of (action_type, avg_reward, count) tuples.
        """
        actions = [
            {
                "action_type": action_type,
                "avg_reward": avg_reward,
                "count": self.mdp_metrics.transitions_by_action[action_type]
            }
            for action_type, avg_reward in self.mdp_metrics.avg_reward_per_action.items()
        ]

        actions_sorted = sorted(actions, key=lambda x: x["avg_reward"], reverse=True)

        return actions_sorted[:top_k]

    def get_worst_actions(self, bottom_k: int = 5) -> List[Dict]:
        """Get bottom-k actions by average reward"""
        actions = [
            {
                "action_type": action_type,
                "avg_reward": avg_reward,
                "count": self.mdp_metrics.transitions_by_action[action_type]
            }
            for action_type, avg_reward in self.mdp_metrics.avg_reward_per_action.items()
        ]

        actions_sorted = sorted(actions, key=lambda x: x["avg_reward"])

        return actions_sorted[:bottom_k]
```

#### Step 3.3: Integrate reward computation into ActionExecutor

Modify `apps/memory_api/core/action_executor.py`, add to the `execute()` method:

```python
async def execute(
    self,
    action: Action,
    state: RAEState,
    **execution_context
) -> Tuple[RAEState, Dict[str, Any]]:
    """Execute action and return new state + execution metadata."""

    # ... existing execution logic ...

    # NEW: Compute reward for transition
    from apps.memory_api.core.reward import RewardFunction

    reward_fn = execution_context.get("reward_function")
    if not reward_fn:
        reward_fn = RewardFunction()  # Use default hyperparameters

    reward = reward_fn.compute_reward(
        state_before=state,
        action=action,
        state_after=new_state,
        execution_result=result
    )

    # NEW: Record in metrics tracker
    metrics_tracker = execution_context.get("metrics_tracker")
    if metrics_tracker:
        metrics_tracker.record_transition(
            state_before=state,
            action=action,
            state_after=new_state,
            reward=reward
        )

    # Add reward to transition record
    self.last_transition["reward"] = reward.to_dict()

    logger.info(
        "action_executed_with_reward",
        action_type=action.action_type.value,
        reward=reward.total_reward,
        quality=reward.quality_score,
        token_cost=reward.token_cost
    )

    return new_state, result
```

#### Step 3.4: Create tests

Create `tests/core/test_reward.py`:

```python
import pytest
from apps.memory_api.core.reward import RewardFunction, RewardComponents
from apps.memory_api.core.state import RAEState, BudgetState
from apps.memory_api.core.actions import RetrieveEpisodicAction, CallLLMAction


def test_reward_function_creation():
    """Test creating reward function with hyperparameters"""
    reward_fn = RewardFunction(lambda_=0.001, mu=0.01)

    assert reward_fn.lambda_ == 0.001
    assert reward_fn.mu == 0.01
    assert reward_fn.gamma == 0.95


def test_reward_computation():
    """Test basic reward computation"""
    reward_fn = RewardFunction(lambda_=0.001, mu=0.01)

    state_before = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=100000)
    )

    state_after = RAEState(
        tenant_id="test",
        project_id="test",
        budget_state=BudgetState(remaining_tokens=99000)  # Used 1000 tokens
    )

    action = RetrieveEpisodicAction(parameters={"k": 10})

    execution_result = {
        "memories_retrieved": 10
    }

    reward = reward_fn.compute_reward(
        state_before=state_before,
        action=action,
        state_after=state_after,
        execution_result=execution_result
    )

    assert isinstance(reward, RewardComponents)
    assert 0.0 <= reward.quality_score <= 1.0
    assert reward.token_cost == 1000
    assert reward.total_reward < reward.quality_reward  # Penalty reduces total


def test_high_quality_high_reward():
    """Test that high quality actions get high reward"""
    reward_fn = RewardFunction()

    state_before = RAEState(tenant_id="test", project_id="test")
    state_after = RAEState(tenant_id="test", project_id="test")

    action = RetrieveEpisodicAction(parameters={"k": 10})

    # High quality result
    execution_result = {
        "memories_retrieved": 20,  # Retrieved many memories
        "avg_relevance": 0.9       # High relevance
    }

    reward = reward_fn.compute_reward(
        state_before, action, state_after, execution_result
    )

    assert reward.quality_score > 0.7
    assert reward.total_reward > 0


def test_metrics_tracker():
    """Test metrics tracking"""
    from apps.memory_api.core.metrics import MetricsTracker

    tracker = MetricsTracker()

    # Record some transitions
    state = RAEState(tenant_id="test", project_id="test")
    action = RetrieveEpisodicAction(parameters={"k": 10})
    reward_fn = RewardFunction()

    reward = reward_fn.compute_reward(
        state, action, state, {"memories_retrieved": 10}
    )

    tracker.record_transition(state, action, state, reward)

    metrics = tracker.get_current_metrics()

    assert metrics["mdp"]["total_transitions"] == 1
    assert "avg_reward_per_action" in metrics["mdp"]
```

**Validation Criteria:**

✅ Reward function computes sensible rewards for different actions
✅ Metrics tracker records transitions and computes statistics
✅ Tests pass 100%
✅ Reward logged for all action executions
✅ Metrics can be exported for analysis

**Success Metrics:**

- [ ] `test_reward.py` passes 100%
- [ ] Rewards logged in action execution
- [ ] Metrics dashboard shows cumulative reward over time
- [ ] Best/worst actions identifiable from metrics

---

### Iteration 4: Implement Information Bottleneck for Context Selection

**Goal:** Replace heuristic context selection with information-theoretically grounded approach

**Mathematical Concept:** Context selection as information bottleneck: max I(Z;Y) - β·I(Z;X)

**Why Fourth:** Builds on state (Iteration 1), actions (Iteration 2), and metrics (Iteration 3)

**Files to Create/Modify:**

1. **Create:** `apps/memory_api/core/information_bottleneck.py`
2. **Modify:** `apps/memory_api/services/hybrid_search.py`
3. **Create:** `tests/core/test_information_bottleneck.py`

**Implementation Steps:**

#### Step 4.1: Implement information bottleneck context selector

Create `apps/memory_api/core/information_bottleneck.py`:

```python
"""
Information Bottleneck for Context Selection

Mathematical formulation:
  Minimize: I(Z; X)  [Context Z contains minimal info from full memory X]
  Maximize: I(Z; Y)  [Context Z maximally predicts output Y]

Lagrangian: L = I(Z; Y) - β·I(Z; X)

Where:
  X = Full memory (all episodic, semantic, reflective memories)
  Z = Selected context (what we pass to LLM)
  Y = Desired output (answer to query)
  β = Trade-off parameter (higher β = more compression)
"""

import numpy as np
import structlog
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = structlog.get_logger(__name__)


@dataclass
class MemoryItem:
    """Unified memory representation for IB"""
    id: str
    content: str
    embedding: np.ndarray
    importance: float
    layer: str  # episodic, semantic, reflective
    tokens: int
    metadata: Dict[str, Any]


class InformationBottleneckSelector:
    """
    Select optimal context using information bottleneck principle.

    Usage:
        selector = InformationBottleneckSelector(beta=1.0)

        selected_context = selector.select_context(
            query="What did user learn about Python?",
            full_memory=all_memories,
            max_tokens=4000
        )

        # Measure information metrics
        I_Z_Y = selector.estimate_I_Z_Y(selected_context, query)
        I_Z_X = selector.estimate_I_Z_X(selected_context, full_memory)
    """

    def __init__(self, beta: float = 1.0):
        """
        Initialize IB selector.

        Args:
            beta: Trade-off parameter
                  β < 1: Prefer relevance (less compression)
                  β = 1: Balanced
                  β > 1: Prefer compression (smaller context)
        """
        self.beta = beta

    def select_context(
        self,
        query: str,
        query_embedding: np.ndarray,
        full_memory: List[MemoryItem],
        max_tokens: int = 4000,
        min_relevance: float = 0.3
    ) -> List[MemoryItem]:
        """
        Select optimal context using information bottleneck.

        Algorithm:
          1. Compute relevance score for each memory: I(m; Y)
          2. Compute compression cost: I(m; X)
          3. Compute IB objective: I(m; Y) - β·I(m; X)
          4. Greedily select memories maximizing objective
          5. Stop at max_tokens

        Args:
            query: User query
            query_embedding: Query embedding vector
            full_memory: All available memories
            max_tokens: Maximum context size
            min_relevance: Minimum relevance threshold

        Returns:
            Selected memories optimizing IB objective
        """
        if not full_memory:
            return []

        logger.info(
            "ib_selection_started",
            full_memory_count=len(full_memory),
            max_tokens=max_tokens,
            beta=self.beta
        )

        # Step 1: Compute relevance scores I(m; Y)
        relevance_scores = self._compute_relevance_scores(
            memories=full_memory,
            query_embedding=query_embedding
        )

        # Step 2: Compute compression costs I(m; X)
        compression_costs = self._compute_compression_costs(
            memories=full_memory
        )

        # Step 3: Compute IB objective for each memory
        ib_scores = []
        for i, memory in enumerate(full_memory):
            relevance = relevance_scores[i]
            compression_cost = compression_costs[i]

            # Filter by minimum relevance
            if relevance < min_relevance:
                ib_score = -np.inf
            else:
                # IB objective: maximize relevance, minimize compression cost
                ib_score = relevance - self.beta * compression_cost

            ib_scores.append((memory, ib_score, relevance, compression_cost))

        # Step 4: Greedy selection
        # Sort by IB score descending
        ib_scores_sorted = sorted(ib_scores, key=lambda x: x[1], reverse=True)

        selected = []
        current_tokens = 0

        for memory, ib_score, relevance, comp_cost in ib_scores_sorted:
            if ib_score == -np.inf:
                continue

            if current_tokens + memory.tokens <= max_tokens:
                selected.append(memory)
                current_tokens += memory.tokens

            if current_tokens >= max_tokens:
                break

        # Log selection metrics
        I_Z_Y = self.estimate_I_Z_Y(selected, query_embedding, full_memory)
        I_Z_X = self.estimate_I_Z_X(selected, full_memory)

        logger.info(
            "ib_selection_completed",
            selected_count=len(selected),
            total_tokens=current_tokens,
            I_Z_Y=I_Z_Y,
            I_Z_X=I_Z_X,
            compression_ratio=1.0 - I_Z_X,
            ib_objective=I_Z_Y - self.beta * I_Z_X
        )

        return selected

    def _compute_relevance_scores(
        self,
        memories: List[MemoryItem],
        query_embedding: np.ndarray
    ) -> np.ndarray:
        """
        Compute I(m; Y) - relevance of memory m to output Y.

        Approximation: Cosine similarity between memory and query.
        """
        relevance_scores = []

        for memory in memories:
            # Cosine similarity
            similarity = self._cosine_similarity(
                memory.embedding,
                query_embedding
            )

            # Importance boost
            importance_boost = memory.importance * 0.2

            # Final relevance score
            relevance = 0.8 * similarity + 0.2 * importance_boost

            relevance_scores.append(relevance)

        return np.array(relevance_scores)

    def _compute_compression_costs(
        self,
        memories: List[MemoryItem]
    ) -> np.ndarray:
        """
        Compute I(m; X) - how much of full memory X is captured by m.

        Approximation: Normalized token count + layer penalty.

        Intuition:
          - Longer memories = higher I(m; X) (contain more info)
          - Reflective memories = lower I(m; X) (already compressed)
        """
        compression_costs = []

        total_tokens = sum(m.tokens for m in memories)

        for memory in memories:
            # Base cost: normalized token count
            base_cost = memory.tokens / max(1, total_tokens)

            # Layer adjustment
            if memory.layer == "reflective":
                layer_penalty = 0.5  # Reflections are compressed, lower cost
            elif memory.layer == "semantic":
                layer_penalty = 0.7  # Semantic is mid-level
            else:  # episodic
                layer_penalty = 1.0  # Episodic is raw, higher cost

            compression_cost = base_cost * layer_penalty
            compression_costs.append(compression_cost)

        return np.array(compression_costs)

    def estimate_I_Z_Y(
        self,
        selected_context: List[MemoryItem],
        query_embedding: np.ndarray,
        full_memory: List[MemoryItem]
    ) -> float:
        """
        Estimate I(Z; Y) - mutual information between context and output.

        Higher is better (more relevant context).

        Approximation:
          - Average relevance of selected memories
          - Diversity bonus (diverse context = more information)
        """
        if not selected_context:
            return 0.0

        # Average relevance
        relevance_scores = self._compute_relevance_scores(
            selected_context,
            query_embedding
        )
        avg_relevance = np.mean(relevance_scores)

        # Diversity: pairwise cosine distance
        embeddings = np.array([m.embedding for m in selected_context])
        diversity = self._compute_diversity(embeddings)

        # Combined I(Z; Y)
        I_Z_Y = 0.7 * avg_relevance + 0.3 * diversity

        return float(I_Z_Y)

    def estimate_I_Z_X(
        self,
        selected_context: List[MemoryItem],
        full_memory: List[MemoryItem]
    ) -> float:
        """
        Estimate I(Z; X) - mutual information between context and full memory.

        Lower is better (more compression).

        Approximation: Ratio of selected to full memory size.
        """
        if not full_memory:
            return 0.0

        selected_tokens = sum(m.tokens for m in selected_context)
        total_tokens = sum(m.tokens for m in full_memory)

        I_Z_X = selected_tokens / max(1, total_tokens)

        return float(I_Z_X)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)

        # Clamp to [0, 1] (convert from [-1, 1])
        similarity = (similarity + 1) / 2

        return float(similarity)

    def _compute_diversity(self, embeddings: np.ndarray) -> float:
        """
        Compute diversity of embedding set.

        Higher diversity = more information coverage.

        Method: Average pairwise cosine distance.
        """
        if len(embeddings) <= 1:
            return 0.0

        # Compute pairwise distances
        distances = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                similarity = self._cosine_similarity(embeddings[i], embeddings[j])
                distance = 1.0 - similarity
                distances.append(distance)

        if not distances:
            return 0.0

        avg_distance = np.mean(distances)

        return float(avg_distance)

    def adaptive_beta(
        self,
        query_complexity: float,
        budget_remaining: float,
        user_preference: str = "balanced"
    ) -> float:
        """
        Adaptively set β based on context.

        Args:
            query_complexity: 0-1 score of query complexity
            budget_remaining: 0-1 ratio of remaining budget
            user_preference: "quality" | "balanced" | "efficiency"

        Returns:
            Optimal β value
        """
        # Base β from user preference
        if user_preference == "quality":
            base_beta = 0.5  # Less compression
        elif user_preference == "efficiency":
            base_beta = 2.0  # More compression
        else:  # balanced
            base_beta = 1.0

        # Adjust for query complexity
        if query_complexity > 0.7:
            # Complex query needs rich context
            base_beta *= 0.7
        elif query_complexity < 0.3:
            # Simple query can use compressed context
            base_beta *= 1.3

        # Adjust for budget
        if budget_remaining < 0.2:
            # Low budget, compress more
            base_beta *= 1.5
        elif budget_remaining > 0.8:
            # High budget, less compression
            base_beta *= 0.8

        return base_beta
```

#### Step 4.2: Integrate into HybridSearchService

Modify `apps/memory_api/services/hybrid_search.py`:

Add IB-based context selection:

```python
async def search(
    self,
    query: str,
    tenant_id: str,
    project_id: str,
    top_k_vector: int = 5,
    graph_depth: int = 2,
    use_information_bottleneck: bool = True,  # NEW parameter
    beta: float = 1.0,  # NEW parameter
    **kwargs
) -> HybridSearchResult:
    """Perform hybrid search with optional IB-based selection"""

    # ... existing vector search logic ...

    # NEW: If IB enabled, use IB selector instead of simple top-k
    if use_information_bottleneck:
        from apps.memory_api.core.information_bottleneck import (
            InformationBottleneckSelector,
            MemoryItem
        )

        # Convert results to MemoryItem format
        memory_items = [
            MemoryItem(
                id=str(result.id),
                content=result.content,
                embedding=result.embedding if hasattr(result, 'embedding') else np.zeros(384),
                importance=result.score,
                layer="episodic",  # or infer from result
                tokens=len(result.content) // 4,  # Rough estimate
                metadata=result.metadata or {}
            )
            for result in vector_results
        ]

        # Select using IB
        ib_selector = InformationBottleneckSelector(beta=beta)
        query_embedding = self.embedding_service.generate_embeddings([query])[0]

        selected_memories = ib_selector.select_context(
            query=query,
            query_embedding=query_embedding,
            full_memory=memory_items,
            max_tokens=4000
        )

        logger.info(
            "information_bottleneck_selection",
            full_count=len(memory_items),
            selected_count=len(selected_memories),
            beta=beta
        )

        # Use selected memories for synthesis
        vector_results = [
            result for result in vector_results
            if str(result.id) in [m.id for m in selected_memories]
        ]

    # ... rest of existing logic ...
```

#### Step 4.3: Create tests

Create `tests/core/test_information_bottleneck.py`:

```python
import pytest
import numpy as np
from apps.memory_api.core.information_bottleneck import (
    InformationBottleneckSelector,
    MemoryItem
)


def create_mock_memory(id: str, tokens: int, relevance: float) -> MemoryItem:
    """Helper to create mock memory"""
    embedding = np.random.randn(384)
    # Encode relevance in embedding (for testing)
    embedding = embedding * relevance

    return MemoryItem(
        id=id,
        content=f"Memory {id}",
        embedding=embedding,
        importance=0.5,
        layer="episodic",
        tokens=tokens,
        metadata={}
    )


def test_ib_selector_creation():
    """Test creating IB selector"""
    selector = InformationBottleneckSelector(beta=1.0)
    assert selector.beta == 1.0


def test_ib_selection_basic():
    """Test basic IB selection"""
    selector = InformationBottleneckSelector(beta=1.0)

    # Create mock memories
    memories = [
        create_mock_memory("1", 100, 0.9),  # High relevance
        create_mock_memory("2", 100, 0.5),  # Medium relevance
        create_mock_memory("3", 100, 0.2),  # Low relevance
    ]

    query_embedding = np.random.randn(384)

    selected = selector.select_context(
        query="test query",
        query_embedding=query_embedding,
        full_memory=memories,
        max_tokens=200  # Only room for 2 memories
    )

    # Should select top 2 by relevance
    assert len(selected) <= 2
    assert sum(m.tokens for m in selected) <= 200


def test_ib_compression_vs_relevance():
    """Test beta trade-off"""
    # Low beta: prefer relevance
    selector_low_beta = InformationBottleneckSelector(beta=0.5)

    # High beta: prefer compression
    selector_high_beta = InformationBottleneckSelector(beta=2.0)

    memories = [create_mock_memory(str(i), 100, 0.6) for i in range(10)]
    query_embedding = np.random.randn(384)

    selected_low_beta = selector_low_beta.select_context(
        "test", query_embedding, memories, max_tokens=500
    )

    selected_high_beta = selector_high_beta.select_context(
        "test", query_embedding, memories, max_tokens=500
    )

    # Low beta should select more (less compression)
    # High beta should select fewer (more compression)
    # (This is probabilistic due to random embeddings, but generally holds)


def test_mutual_information_estimation():
    """Test I(Z;Y) and I(Z;X) estimation"""
    selector = InformationBottleneckSelector(beta=1.0)

    full_memory = [create_mock_memory(str(i), 100, 0.5) for i in range(10)]
    selected = full_memory[:3]  # Select 30%

    query_embedding = np.random.randn(384)

    I_Z_Y = selector.estimate_I_Z_Y(selected, query_embedding, full_memory)
    I_Z_X = selector.estimate_I_Z_X(selected, full_memory)

    assert 0.0 <= I_Z_Y <= 1.0
    assert 0.0 <= I_Z_X <= 1.0

    # Selected 30% of memory, so I(Z;X) should be ~0.3
    assert 0.2 <= I_Z_X <= 0.4


def test_adaptive_beta():
    """Test adaptive beta tuning"""
    selector = InformationBottleneckSelector()

    # Complex query, high budget -> low beta
    beta1 = selector.adaptive_beta(
        query_complexity=0.9,
        budget_remaining=0.9,
        user_preference="quality"
    )

    # Simple query, low budget -> high beta
    beta2 = selector.adaptive_beta(
        query_complexity=0.2,
        budget_remaining=0.2,
        user_preference="efficiency"
    )

    assert beta1 < beta2  # More compression when simple and low budget
```

**Validation Criteria:**

✅ IB selector produces sensible context selections
✅ Higher β leads to smaller contexts (more compression)
✅ I(Z;Y) and I(Z;X) metrics computed correctly
✅ Tests pass 100%
✅ IB metrics logged and trackable

**Success Metrics:**

- [ ] `test_information_bottleneck.py` passes 100%
- [ ] IB selection integrated into HybridSearch
- [ ] Metrics show I(Z;Y) > 0.7 and I(Z;X) < 0.3 (good compression + relevance)
- [ ] Context selection demonstrably better than baseline

---

### Iteration 5: Formalize Graph Update Operator

**Goal:** Implement formal graph evolution: `G_{t+1} = T(G_t, o_t, a_t)`

**Mathematical Concept:** Deterministic graph transformation operator

**Why Fifth:** Final piece - formalizes memory structure evolution

**Files to Create/Modify:**

1. **Create:** `apps/memory_api/core/graph_operator.py`
2. **Modify:** `apps/memory_api/repositories/graph_repository.py`
3. **Create:** `tests/core/test_graph_operator.py`

**Implementation Steps:**

#### Step 5.1: Implement graph update operator

Create `apps/memory_api/core/graph_operator.py`:

```python
"""
Knowledge Graph Update Operator

Mathematical formulation:
  G_{t+1} = T(G_t, o_t, a_t)

Where:
  G_t = (V_t, E_t) - Graph at time t
  o_t = Observation (new memory, entity extraction result, etc.)
  a_t = Action (add_node, add_edge, merge_nodes, prune, etc.)
  T = Deterministic transformation function

Properties to maintain:
  - Consistency: No duplicate nodes with same entity
  - Connectivity: Graph should remain connected
  - Temporal decay: Edge weights decay over time
  - Convergence: Graph should stabilize over time
"""

import structlog
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np

logger = structlog.get_logger(__name__)


class GraphActionType(str, Enum):
    """Types of graph transformations"""
    ADD_NODE = "add_node"
    ADD_EDGE = "add_edge"
    UPDATE_EDGE_WEIGHT = "update_edge_weight"
    MERGE_NODES = "merge_nodes"
    PRUNE_NODE = "prune_node"
    PRUNE_EDGE = "prune_edge"
    EXTRACT_SUBGRAPH = "extract_subgraph"


@dataclass
class GraphNode:
    """Node in knowledge graph"""
    id: str
    label: str
    node_type: str  # entity, concept, event, etc.
    properties: Dict[str, Any]
    created_at: datetime
    last_updated: datetime
    importance: float  # 0-1
    centrality: float  # 0-1 (computed from graph structure)


@dataclass
class GraphEdge:
    """Edge in knowledge graph"""
    id: str
    source_id: str
    target_id: str
    relation: str
    weight: float  # 0-1
    confidence: float  # 0-1
    created_at: datetime
    last_updated: datetime
    evidence_count: int  # How many observations support this edge


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph state"""
    nodes: Dict[str, GraphNode]
    edges: Dict[str, GraphEdge]
    tenant_id: str
    project_id: str
    created_at: datetime
    last_updated: datetime

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        return self.edges.get(edge_id)

    def adjacency_matrix(self) -> np.ndarray:
        """Get adjacency matrix for graph analysis"""
        node_ids = list(self.nodes.keys())
        n = len(node_ids)
        adj = np.zeros((n, n))

        node_idx = {node_id: i for i, node_id in enumerate(node_ids)}

        for edge in self.edges.values():
            i = node_idx.get(edge.source_id)
            j = node_idx.get(edge.target_id)

            if i is not None and j is not None:
                adj[i][j] = edge.weight

        return adj

    def copy(self) -> "KnowledgeGraph":
        """Deep copy of graph"""
        import copy
        return copy.deepcopy(self)


class GraphUpdateOperator:
    """
    Implements graph transformation function T.

    Usage:
        operator = GraphUpdateOperator()

        # Load current graph
        G_t = await load_graph(tenant_id, project_id)

        # Observation: new memory with entities
        observation = {
            "memory_id": "mem_123",
            "content": "John met Alice at the conference",
            "entities": ["John", "Alice", "conference"],
            "relations": [("John", "met", "Alice"), ...]
        }

        # Apply transformation
        G_next = operator.apply(
            graph=G_t,
            action_type=GraphActionType.ADD_EDGE,
            observation=observation
        )

        # Persist
        await save_graph(G_next)
    """

    def __init__(
        self,
        edge_half_life_days: float = 30.0,
        edge_prune_threshold: float = 0.1,
        merge_similarity_threshold: float = 0.9
    ):
        """
        Initialize graph operator.

        Args:
            edge_half_life_days: Half-life for edge weight decay
            edge_prune_threshold: Below this weight, edges are pruned
            merge_similarity_threshold: Above this similarity, nodes are merged
        """
        self.edge_half_life_days = edge_half_life_days
        self.edge_prune_threshold = edge_prune_threshold
        self.merge_similarity_threshold = merge_similarity_threshold

    def apply(
        self,
        graph: KnowledgeGraph,
        action_type: GraphActionType,
        observation: Dict[str, Any],
        parameters: Optional[Dict[str, Any]] = None
    ) -> KnowledgeGraph:
        """
        Apply graph transformation: G_{t+1} = T(G_t, o_t, a_t)

        Args:
            graph: Current graph state G_t
            action_type: Type of transformation
            observation: Observation o_t (new data)
            parameters: Optional action parameters

        Returns:
            New graph state G_{t+1}
        """
        parameters = parameters or {}

        logger.info(
            "graph_transformation_started",
            action_type=action_type.value,
            nodes_before=len(graph.nodes),
            edges_before=len(graph.edges)
        )

        # Copy graph (immutable transformation)
        G_next = graph.copy()

        # Apply transformation based on action type
        if action_type == GraphActionType.ADD_NODE:
            G_next = self._add_node(G_next, observation, parameters)

        elif action_type == GraphActionType.ADD_EDGE:
            G_next = self._add_edge(G_next, observation, parameters)

        elif action_type == GraphActionType.UPDATE_EDGE_WEIGHT:
            G_next = self._update_edge_weight(G_next, observation, parameters)

        elif action_type == GraphActionType.MERGE_NODES:
            G_next = self._merge_nodes(G_next, observation, parameters)

        elif action_type == GraphActionType.PRUNE_NODE:
            G_next = self._prune_node(G_next, observation, parameters)

        elif action_type == GraphActionType.PRUNE_EDGE:
            G_next = self._prune_edge(G_next, observation, parameters)

        else:
            raise ValueError(f"Unknown action type: {action_type}")

        # Update timestamp
        G_next.last_updated = datetime.now()

        logger.info(
            "graph_transformation_completed",
            action_type=action_type.value,
            nodes_after=len(G_next.nodes),
            edges_after=len(G_next.edges),
            nodes_delta=len(G_next.nodes) - len(graph.nodes),
            edges_delta=len(G_next.edges) - len(graph.edges)
        )

        return G_next

    def _add_node(
        self,
        graph: KnowledgeGraph,
        observation: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> KnowledgeGraph:
        """Add new node to graph"""
        node_data = observation.get("node_data") or parameters.get("node_data")

        if not node_data:
            logger.warning("add_node_missing_data")
            return graph

        # Check for duplicates
        existing = self._find_duplicate_node(graph, node_data["label"])
        if existing:
            logger.info("node_already_exists", node_id=existing.id, label=existing.label)
            return graph

        # Create new node
        node = GraphNode(
            id=node_data.get("id", f"node_{len(graph.nodes)}"),
            label=node_data["label"],
            node_type=node_data.get("node_type", "entity"),
            properties=node_data.get("properties", {}),
            created_at=datetime.now(),
            last_updated=datetime.now(),
            importance=node_data.get("importance", 0.5),
            centrality=0.0  # Will be computed later
        )

        graph.nodes[node.id] = node

        logger.debug("node_added", node_id=node.id, label=node.label)

        return graph

    def _add_edge(
        self,
        graph: KnowledgeGraph,
        observation: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> KnowledgeGraph:
        """Add or strengthen edge"""
        edge_data = observation.get("edge_data") or parameters.get("edge_data")

        if not edge_data:
            logger.warning("add_edge_missing_data")
            return graph

        source_id = edge_data["source_id"]
        target_id = edge_data["target_id"]
        relation = edge_data["relation"]

        # Check nodes exist
        if source_id not in graph.nodes or target_id not in graph.nodes:
            logger.warning("edge_nodes_not_found", source=source_id, target=target_id)
            return graph

        # Check if edge already exists
        edge_id = f"{source_id}_{relation}_{target_id}"
        existing_edge = graph.edges.get(edge_id)

        if existing_edge:
            # Strengthen existing edge
            existing_edge.weight = min(1.0, existing_edge.weight + 0.1)
            existing_edge.evidence_count += 1
            existing_edge.last_updated = datetime.now()

            logger.debug("edge_strengthened", edge_id=edge_id, new_weight=existing_edge.weight)
        else:
            # Create new edge
            edge = GraphEdge(
                id=edge_id,
                source_id=source_id,
                target_id=target_id,
                relation=relation,
                weight=edge_data.get("weight", 0.7),
                confidence=edge_data.get("confidence", 0.8),
                created_at=datetime.now(),
                last_updated=datetime.now(),
                evidence_count=1
            )

            graph.edges[edge_id] = edge

            logger.debug("edge_added", edge_id=edge_id)

        return graph

    def _update_edge_weight(
        self,
        graph: KnowledgeGraph,
        observation: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> KnowledgeGraph:
        """Update edge weights with temporal decay"""
        now = datetime.now()

        edges_to_remove = []

        for edge_id, edge in graph.edges.items():
            # Temporal decay
            time_delta = (now - edge.last_updated).total_seconds() / 86400  # days
            decay = np.exp(-time_delta / self.edge_half_life_days)

            # Apply decay
            edge.weight = edge.weight * decay

            # Mark for pruning if below threshold
            if edge.weight < self.edge_prune_threshold:
                edges_to_remove.append(edge_id)

        # Remove pruned edges
        for edge_id in edges_to_remove:
            del graph.edges[edge_id]
            logger.debug("edge_pruned", edge_id=edge_id)

        logger.info("edge_weights_updated", pruned_count=len(edges_to_remove))

        return graph

    def _merge_nodes(
        self,
        graph: KnowledgeGraph,
        observation: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> KnowledgeGraph:
        """Merge duplicate nodes (entity resolution)"""
        node1_id = parameters.get("node1_id")
        node2_id = parameters.get("node2_id")

        if not node1_id or not node2_id:
            logger.warning("merge_nodes_missing_ids")
            return graph

        node1 = graph.nodes.get(node1_id)
        node2 = graph.nodes.get(node2_id)

        if not node1 or not node2:
            logger.warning("merge_nodes_not_found")
            return graph

        # Create merged node (keep node1, merge properties)
        merged_node = node1
        merged_node.properties.update(node2.properties)
        merged_node.importance = max(node1.importance, node2.importance)
        merged_node.last_updated = datetime.now()

        # Remove node2
        del graph.nodes[node2_id]

        # Redirect all edges from node2 to node1
        edges_to_update = []
        for edge_id, edge in graph.edges.items():
            if edge.source_id == node2_id:
                edges_to_update.append((edge_id, "source"))
            elif edge.target_id == node2_id:
                edges_to_update.append((edge_id, "target"))

        for edge_id, direction in edges_to_update:
            edge = graph.edges[edge_id]

            if direction == "source":
                # Update edge ID
                new_edge_id = edge_id.replace(node2_id, node1_id)
                graph.edges[new_edge_id] = edge
                del graph.edges[edge_id]

                edge.id = new_edge_id
                edge.source_id = node1_id
            else:
                new_edge_id = edge_id.replace(node2_id, node1_id)
                graph.edges[new_edge_id] = edge
                del graph.edges[edge_id]

                edge.id = new_edge_id
                edge.target_id = node1_id

        logger.info("nodes_merged", node1=node1_id, node2=node2_id, merged_id=node1_id)

        return graph

    def _prune_node(
        self,
        graph: KnowledgeGraph,
        observation: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> KnowledgeGraph:
        """Remove low-value node"""
        node_id = parameters.get("node_id")

        if not node_id or node_id not in graph.nodes:
            return graph

        # Remove node
        del graph.nodes[node_id]

        # Remove all edges connected to this node
        edges_to_remove = [
            edge_id for edge_id, edge in graph.edges.items()
            if edge.source_id == node_id or edge.target_id == node_id
        ]

        for edge_id in edges_to_remove:
            del graph.edges[edge_id]

        logger.info("node_pruned", node_id=node_id, edges_removed=len(edges_to_remove))

        return graph

    def _prune_edge(
        self,
        graph: KnowledgeGraph,
        observation: Dict[str, Any],
        parameters: Dict[str, Any]
    ) -> KnowledgeGraph:
        """Remove specific edge"""
        edge_id = parameters.get("edge_id")

        if not edge_id or edge_id not in graph.edges:
            return graph

        del graph.edges[edge_id]

        logger.debug("edge_pruned", edge_id=edge_id)

        return graph

    def _find_duplicate_node(
        self,
        graph: KnowledgeGraph,
        label: str,
        similarity_threshold: Optional[float] = None
    ) -> Optional[GraphNode]:
        """Find node with similar label (for duplicate detection)"""
        threshold = similarity_threshold or self.merge_similarity_threshold

        # Simple exact match for now
        # TODO: Use embedding similarity for semantic matching
        for node in graph.nodes.values():
            if node.label.lower() == label.lower():
                return node

        return None

    def analyze_convergence(
        self,
        graph_history: List[KnowledgeGraph]
    ) -> Dict[str, Any]:
        """
        Analyze whether graph is converging to stable structure.

        Metrics:
          - Node churn rate (additions/deletions per timestep)
          - Edge churn rate
          - Spectral gap (stability indicator from adjacency matrix)
          - Clustering coefficient variance

        Returns:
            Convergence metrics
        """
        if len(graph_history) < 2:
            return {"is_converging": False, "reason": "insufficient_history"}

        # Node churn
        node_counts = [len(g.nodes) for g in graph_history]
        node_deltas = [abs(node_counts[i+1] - node_counts[i]) for i in range(len(node_counts)-1)]
        node_churn = np.mean(node_deltas) if node_deltas else 0

        # Edge churn
        edge_counts = [len(g.edges) for g in graph_history]
        edge_deltas = [abs(edge_counts[i+1] - edge_counts[i]) for i in range(len(edge_counts)-1)]
        edge_churn = np.mean(edge_deltas) if edge_deltas else 0

        # Spectral gap (from latest graph)
        latest_graph = graph_history[-1]
        if len(latest_graph.nodes) > 1:
            adj_matrix = latest_graph.adjacency_matrix()
            try:
                eigenvalues = np.linalg.eigvals(adj_matrix)
                eigenvalues_sorted = np.sort(np.abs(eigenvalues))[::-1]

                if len(eigenvalues_sorted) >= 2:
                    spectral_gap = float(eigenvalues_sorted[0] - eigenvalues_sorted[1])
                else:
                    spectral_gap = 0.0
            except:
                spectral_gap = 0.0
        else:
            spectral_gap = 0.0

        # Convergence criteria
        is_converging = (
            node_churn < 5.0 and  # Less than 5 nodes added/removed per step
            edge_churn < 10.0 and  # Less than 10 edges added/removed per step
            spectral_gap < 0.5     # Stable eigenvalue spectrum
        )

        return {
            "is_converging": is_converging,
            "node_churn": node_churn,
            "edge_churn": edge_churn,
            "spectral_gap": spectral_gap,
            "node_count": len(latest_graph.nodes),
            "edge_count": len(latest_graph.edges)
        }
```

#### Step 5.2: Tests

Create `tests/core/test_graph_operator.py`:

```python
import pytest
from datetime import datetime
from apps.memory_api.core.graph_operator import (
    GraphUpdateOperator,
    KnowledgeGraph,
    GraphNode,
    GraphEdge,
    GraphActionType
)


def create_test_graph() -> KnowledgeGraph:
    """Create a simple test graph"""
    return KnowledgeGraph(
        nodes={
            "node1": GraphNode(
                id="node1",
                label="Alice",
                node_type="person",
                properties={},
                created_at=datetime.now(),
                last_updated=datetime.now(),
                importance=0.8,
                centrality=0.5
            ),
            "node2": GraphNode(
                id="node2",
                label="Bob",
                node_type="person",
                properties={},
                created_at=datetime.now(),
                last_updated=datetime.now(),
                importance=0.7,
                centrality=0.4
            )
        },
        edges={
            "edge1": GraphEdge(
                id="edge1",
                source_id="node1",
                target_id="node2",
                relation="knows",
                weight=0.8,
                confidence=0.9,
                created_at=datetime.now(),
                last_updated=datetime.now(),
                evidence_count=1
            )
        },
        tenant_id="test",
        project_id="test",
        created_at=datetime.now(),
        last_updated=datetime.now()
    )


def test_graph_operator_add_node():
    """Test adding a node"""
    operator = GraphUpdateOperator()
    graph = create_test_graph()

    observation = {
        "node_data": {
            "id": "node3",
            "label": "Charlie",
            "node_type": "person",
            "importance": 0.6
        }
    }

    new_graph = operator.apply(
        graph=graph,
        action_type=GraphActionType.ADD_NODE,
        observation=observation
    )

    assert len(new_graph.nodes) == 3
    assert "node3" in new_graph.nodes
    assert new_graph.nodes["node3"].label == "Charlie"


def test_graph_operator_add_edge():
    """Test adding an edge"""
    operator = GraphUpdateOperator()
    graph = create_test_graph()

    observation = {
        "edge_data": {
            "source_id": "node2",
            "target_id": "node1",
            "relation": "likes",
            "weight": 0.7
        }
    }

    new_graph = operator.apply(
        graph=graph,
        action_type=GraphActionType.ADD_EDGE,
        observation=observation
    )

    assert len(new_graph.edges) == 2


def test_graph_operator_merge_nodes():
    """Test merging duplicate nodes"""
    operator = GraphUpdateOperator()
    graph = create_test_graph()

    # Add duplicate
    graph.nodes["node3"] = GraphNode(
        id="node3",
        label="Alice",  # Duplicate of node1
        node_type="person",
        properties={},
        created_at=datetime.now(),
        last_updated=datetime.now(),
        importance=0.6,
        centrality=0.3
    )

    parameters = {
        "node1_id": "node1",
        "node2_id": "node3"
    }

    new_graph = operator.apply(
        graph=graph,
        action_type=GraphActionType.MERGE_NODES,
        observation={},
        parameters=parameters
    )

    assert len(new_graph.nodes) == 2
    assert "node3" not in new_graph.nodes
    assert "node1" in new_graph.nodes


def test_graph_convergence_analysis():
    """Test convergence analysis"""
    operator = GraphUpdateOperator()

    # Create history of graphs
    history = []

    graph = create_test_graph()
    history.append(graph.copy())

    # Add a few nodes
    for i in range(3, 6):
        observation = {
            "node_data": {
                "id": f"node{i}",
                "label": f"Person{i}",
                "node_type": "person"
            }
        }
        graph = operator.apply(graph, GraphActionType.ADD_NODE, observation)
        history.append(graph.copy())

    # Analyze
    convergence = operator.analyze_convergence(history)

    assert "is_converging" in convergence
    assert "node_churn" in convergence
    assert "spectral_gap" in convergence
```

**Validation Criteria:**

✅ Graph operator correctly applies transformations
✅ Temporal decay implemented for edges
✅ Node merging (entity resolution) works
✅ Convergence analysis produces meaningful metrics
✅ Tests pass 100%

**Success Metrics:**

- [ ] `test_graph_operator.py` passes 100%
- [ ] Graph transformations deterministic and reproducible
- [ ] Convergence metrics show stabilization over time
- [ ] No performance regression (<100ms per transformation)

---

## Validation Framework

After completing all 5 iterations, validate the entire system:

### Mathematical Validation

1. **MDP Validation:**
   - [ ] State representation captures all relevant information
   - [ ] Action space covers all system operations
   - [ ] Reward correlates with user satisfaction (if feedback available)
   - [ ] Cumulative reward increases over time (learning/improvement)

2. **Information Bottleneck Validation:**
   - [ ] I(Z;Y) > 0.7 (context is relevant)
   - [ ] I(Z;X) < 0.3 (compression achieved)
   - [ ] Higher β leads to lower I(Z;X)
   - [ ] Context efficiency > 0.001 (information per token)

3. **Graph Operator Validation:**
   - [ ] Graph converges (node churn < 5, edge churn < 10)
   - [ ] No orphaned nodes (all nodes have edges)
   - [ ] Spectral gap < 0.5 (stable structure)
   - [ ] Entity resolution reduces duplicates

### Performance Validation

1. **Latency:**
   - [ ] State creation <5ms
   - [ ] Action execution <100ms (except LLM calls)
   - [ ] Reward computation <10ms
   - [ ] IB selection <50ms
   - [ ] Graph update <100ms

2. **Cost Efficiency:**
   - [ ] Budget efficiency (quality per dollar) increases over time
   - [ ] IB selection reduces token usage by 30% vs baseline
   - [ ] Reward-guided policy uses fewer tokens for same quality

3. **Quality:**
   - [ ] Average quality score > 0.7
   - [ ] Top actions by reward are intuitively correct
   - [ ] Graph provides better retrieval than vector-only

### Integration Validation

1. **API Compatibility:**
   - [ ] All existing API endpoints still work
   - [ ] No breaking changes to request/response formats
   - [ ] Backward compatible with existing clients

2. **Test Coverage:**
   - [ ] Core state tests pass 100%
   - [ ] Core actions tests pass 100%
   - [ ] Core reward tests pass 100%
   - [ ] Core IB tests pass 100%
   - [ ] Core graph operator tests pass 100%
   - [ ] Integration tests pass >90%

3. **Documentation:**
   - [ ] All mathematical concepts documented with code mapping
   - [ ] Examples provided for each major component
   - [ ] Migration guide written for existing users

---

## Agent Execution Guidelines

This section provides instructions for AI agents performing the refactoring.

### General Principles

1. **Incremental Changes:** Complete one iteration fully before starting the next
2. **Test-Driven:** Write tests first, then implementation
3. **Preserve Functionality:** Never break existing features
4. **Log Everything:** Add detailed logging for debugging and metrics
5. **Document as You Go:** Update docstrings and comments inline

### Per-Iteration Workflow

For each iteration:

1. **Read the iteration specification completely**
2. **Create todo list** using TodoWrite tool with all steps
3. **Create new files** before modifying existing ones
4. **Run tests continuously** after each significant change
5. **Mark todos complete** only when tests pass
6. **Commit after iteration** with descriptive message

### Code Quality Standards

**Naming:**
- Use mathematical notation in comments: `s_t`, `a_t`, `R(s,a,s')`
- Use descriptive Python names: `state_before`, `action`, `reward_components`
- Prefix with math concept: `mdp_metrics`, `ib_selector`, `graph_operator`

**Documentation:**
- Every class/function must have docstring explaining:
  - Mathematical concept it implements
  - Parameters and return values
  - Example usage
- Reference relevant equations in comments

**Testing:**
- Unit tests for each function
- Integration tests for workflows
- Property tests for mathematical invariants (e.g., rewards should never increase with higher cost)

### Error Handling

**Expected Errors:**
- State validation failures → Return to previous state, log warning
- Budget exhaustion → Gracefully stop, return partial results
- Graph inconsistencies → Auto-repair (merge duplicates, remove orphans)

**Unexpected Errors:**
- Log full stack trace
- Record state/action/observation that caused error
- Add error case to test suite
- Fix root cause, not symptom

### Performance Optimization

**Only optimize after correctness:**
1. Get it working (functional correctness)
2. Get it right (mathematical correctness)
3. Get it fast (performance optimization)

**Profiling:**
- Use `cProfile` for CPU hotspots
- Use `memory_profiler` for memory leaks
- Log timing for all major operations

**Optimization Targets:**
- State operations: <5ms
- Reward computation: <10ms
- IB selection: <50ms
- Graph updates: <100ms

### Debugging Tips

**State Issues:**
- Serialize state before/after each action
- Compare state deltas
- Check invariants (e.g., token count matches content length)

**Reward Issues:**
- Log all reward components separately
- Plot reward over time
- Check quality_score is in [0, 1]

**IB Issues:**
- Log I(Z;Y) and I(Z;X) for each selection
- Verify compression_ratio = 1 - I(Z;X)
- Check beta adaptive tuning

**Graph Issues:**
- Visualize graph (use networkx + matplotlib)
- Check for isolated nodes
- Verify edge weights in [0, 1]

---

## Success Metrics

### Phase 1: Implementation Complete (After Iteration 5)

- [ ] All 5 iterations completed
- [ ] All tests pass (100% for core, >90% for integration)
- [ ] No breaking changes to existing APIs
- [ ] Documentation updated

### Phase 2: Mathematical Correctness (Week 1-2 after implementation)

- [ ] MDP metrics logged for >1000 transitions
- [ ] Cumulative reward is positive and increasing
- [ ] IB achieves I(Z;Y) > 0.7, I(Z;X) < 0.3
- [ ] Graph converges (churn < 5, spectral gap < 0.5)

### Phase 3: Performance & Quality (Week 3-4)

- [ ] Latency targets met (see Performance Validation)
- [ ] Budget efficiency improves 20% vs baseline
- [ ] User satisfaction (if measurable) increases
- [ ] Graph-enhanced retrieval outperforms vector-only

### Phase 4: Production Ready (Week 5-6)

- [ ] Load testing passed (1000 concurrent users)
- [ ] No memory leaks (24h stress test)
- [ ] Monitoring dashboards deployed
- [ ] Runbook written for operations team

---

## Conclusion

This guide provides a **complete, actionable plan** for transforming RAE into a mathematically grounded system. Each iteration is self-contained, testable, and adds incremental value.

**Key Achievements After Completion:**

1. **Formal State Space:** Every system state explicitly represented
2. **Discrete Action Space:** All operations formalized as actions
3. **Measurable Rewards:** Quality, cost, and latency quantified
4. **Information-Theoretic Context:** Justified compression with IB
5. **Deterministic Graph Evolution:** Formal memory structure dynamics

**Next Steps (Beyond This Guide):**

- **Policy Optimization:** Use reinforcement learning to learn π*
- **Adaptive Hyperparameters:** Learn λ, μ, β from user feedback
- **Multi-Objective Optimization:** Pareto-optimal policies
- **Theoretical Analysis:** Prove convergence properties
- **Empirical Validation:** A/B test against baseline

**Remember:** "Majstersztyk inżynierski, nie papierowy potwór"

Build it. Test it. Ship it. Iterate.

---

**Document Status:** Ready for Agent Execution
**Last Updated:** 2025-12-04
**Version:** 1.0
