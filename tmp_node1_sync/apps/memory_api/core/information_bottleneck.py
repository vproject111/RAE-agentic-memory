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

Usage:
    selector = InformationBottleneckSelector(beta=1.0)

    selected_context = selector.select_context(
        query="What did user learn about Python?",
        query_embedding=query_emb,
        full_memory=all_memories,
        max_tokens=4000
    )

    # Measure information metrics
    I_Z_Y = selector.estimate_I_Z_Y(selected_context, query_emb, full_memory)
    I_Z_X = selector.estimate_I_Z_X(selected_context, full_memory)
"""

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import structlog

from apps.memory_api.observability.rae_tracing import get_tracer

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


@dataclass
class MemoryItem:
    """Unified memory representation for IB selection"""

    id: str
    content: str
    embedding: np.ndarray
    importance: float
    layer: str  # episodic, semantic, reflective, working, ltm
    tokens: int
    metadata: Dict[str, Any]


class InformationBottleneckSelector:
    """
    Select optimal context using information bottleneck principle.

    Algorithm:
      1. Compute relevance score for each memory: I(m; Y) ≈ cosine_similarity(m, query)
      2. Compute compression cost: I(m; X) ≈ tokens/total_tokens
      3. Compute IB objective: I(m; Y) - β·I(m; X)
      4. Greedily select memories maximizing objective
      5. Stop at max_tokens

    Mathematical Justification:
      - I(Z;Y) measures how much context helps predict output
      - I(Z;X) measures how much of full memory is captured
      - Optimal context maximizes I(Z;Y) while minimizing I(Z;X)
      - β controls compression: higher β = smaller context
    """

    def __init__(self, beta: float = 1.0):
        """
        Initialize IB selector.

        Args:
            beta: Trade-off parameter
                  β < 1: Prefer relevance (lower compression)
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
        min_relevance: float = 0.3,
    ) -> List[MemoryItem]:
        """
        Select optimal context using information bottleneck.

        Args:
            query: User query
            query_embedding: Query embedding vector
            full_memory: All available memories
            max_tokens: Maximum context size
            min_relevance: Minimum relevance threshold

        Returns:
            Selected memories optimizing IB objective
        """
        with tracer.start_as_current_span(
            "rae.information_bottleneck.select_context"
        ) as span:
            if not full_memory:
                span.set_attribute("rae.ib.full_memory_count", 0)
                span.set_attribute("rae.outcome.label", "empty_memory")
                return []

            span.set_attribute("rae.ib.full_memory_count", len(full_memory))
            span.set_attribute("rae.ib.max_tokens", max_tokens)
            span.set_attribute("rae.ib.beta", self.beta)
            span.set_attribute("rae.ib.min_relevance", min_relevance)

            logger.info(
                "ib_selection_started",
                full_memory_count=len(full_memory),
                max_tokens=max_tokens,
                beta=self.beta,
            )

            # Step 1: Compute relevance scores I(m; Y)
            relevance_scores = self._compute_relevance_scores(
                memories=full_memory, query_embedding=query_embedding
            )
            span.set_attribute("rae.ib.avg_relevance", float(np.mean(relevance_scores)))

            # Step 2: Compute compression costs I(m; X)
            compression_costs = self._compute_compression_costs(memories=full_memory)
            span.set_attribute(
                "rae.ib.avg_compression_cost", float(np.mean(compression_costs))
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
            compression_ratio = 1.0 - I_Z_X
            ib_objective = I_Z_Y - self.beta * I_Z_X

            span.set_attribute("rae.ib.selected_count", len(selected))
            span.set_attribute("rae.ib.total_tokens", current_tokens)
            span.set_attribute("rae.ib.I_Z_Y", I_Z_Y)
            span.set_attribute("rae.ib.I_Z_X", I_Z_X)
            span.set_attribute("rae.ib.compression_ratio", compression_ratio)
            span.set_attribute("rae.ib.objective", ib_objective)
            span.set_attribute("rae.outcome.label", "success")

            logger.info(
                "ib_selection_completed",
                selected_count=len(selected),
                total_tokens=current_tokens,
                I_Z_Y=I_Z_Y,
                I_Z_X=I_Z_X,
                compression_ratio=compression_ratio,
                ib_objective=ib_objective,
            )

            return selected

    def _compute_relevance_scores(
        self, memories: List[MemoryItem], query_embedding: np.ndarray
    ) -> np.ndarray:
        """
        Compute I(m; Y) - relevance of memory m to output Y.

        Approximation: Cosine similarity between memory and query.

        Args:
            memories: List of memory items
            query_embedding: Query embedding vector

        Returns:
            Array of relevance scores [0, 1]
        """
        relevance_scores = []

        for memory in memories:
            # Cosine similarity
            similarity = self._cosine_similarity(memory.embedding, query_embedding)

            # Importance boost
            importance_boost = memory.importance * 0.2

            # Final relevance score
            relevance = 0.8 * similarity + 0.2 * importance_boost

            relevance_scores.append(relevance)

        return np.array(relevance_scores)

    def _compute_compression_costs(self, memories: List[MemoryItem]) -> np.ndarray:
        """
        Compute I(m; X) - how much of full memory X is captured by m.

        Approximation: Normalized token count + layer penalty.

        Intuition:
          - Longer memories = higher I(m; X) (contain more info)
          - Reflective memories = lower I(m; X) (already compressed)

        Args:
            memories: List of memory items

        Returns:
            Array of compression costs [0, 1]
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
            elif memory.layer == "ltm":
                layer_penalty = 0.6  # LTM is consolidated
            elif memory.layer == "working":
                layer_penalty = 0.9  # Working memory is recent but raw
            else:  # episodic
                layer_penalty = 1.0  # Episodic is raw, higher cost

            compression_cost = base_cost * layer_penalty
            compression_costs.append(compression_cost)

        return np.array(compression_costs)

    def estimate_I_Z_Y(
        self,
        selected_context: List[MemoryItem],
        query_embedding: np.ndarray,
        full_memory: List[MemoryItem],
    ) -> float:
        """
        Estimate I(Z; Y) - mutual information between context and output.

        Higher is better (more relevant context).

        Approximation:
          - Average relevance of selected memories
          - Diversity bonus (diverse context = more information)

        Args:
            selected_context: Selected context memories
            query_embedding: Query embedding
            full_memory: Full memory set (for reference)

        Returns:
            Estimated I(Z;Y) in [0, 1]
        """
        if not selected_context:
            return 0.0

        # Average relevance
        relevance_scores = self._compute_relevance_scores(
            selected_context, query_embedding
        )
        avg_relevance = np.mean(relevance_scores)

        # Diversity: pairwise cosine distance
        embeddings = np.array([m.embedding for m in selected_context])
        diversity = self._compute_diversity(embeddings)

        # Combined I(Z; Y)
        I_Z_Y = 0.7 * avg_relevance + 0.3 * diversity

        return float(I_Z_Y)

    def estimate_I_Z_X(
        self, selected_context: List[MemoryItem], full_memory: List[MemoryItem]
    ) -> float:
        """
        Estimate I(Z; X) - mutual information between context and full memory.

        Lower is better (more compression).

        Approximation: Ratio of selected to full memory size.

        Args:
            selected_context: Selected context memories
            full_memory: Full memory set

        Returns:
            Estimated I(Z;X) in [0, 1]
        """
        if not full_memory:
            return 0.0

        selected_tokens = sum(m.tokens for m in selected_context)
        total_tokens = sum(m.tokens for m in full_memory)

        I_Z_X = selected_tokens / max(1, total_tokens)

        return float(I_Z_X)

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Similarity in [0, 1]
        """
        # Handle zero vectors
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        similarity = dot_product / (norm1 * norm2)

        # Convert from [-1, 1] to [0, 1]
        similarity = (similarity + 1) / 2

        return float(np.clip(similarity, 0.0, 1.0))

    def _compute_diversity(self, embeddings: np.ndarray) -> float:
        """
        Compute diversity of embedding set.

        Higher diversity = more information coverage.

        Method: Average pairwise cosine distance.

        Args:
            embeddings: Array of embedding vectors

        Returns:
            Diversity score in [0, 1]
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
        user_preference: str = "balanced",
    ) -> float:
        """
        Adaptively set β based on context.

        Strategy:
          - Complex queries need rich context → lower β
          - Low budget requires compression → higher β
          - User preference overrides

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
            # High budget, lower compression
            base_beta *= 0.8

        logger.debug(
            "adaptive_beta_computed",
            base_beta=base_beta,
            query_complexity=query_complexity,
            budget_remaining=budget_remaining,
            user_preference=user_preference,
        )

        return base_beta

    def compute_ib_objective(
        self,
        selected_context: List[MemoryItem],
        query_embedding: np.ndarray,
        full_memory: List[MemoryItem],
    ) -> Dict[str, float]:
        """
        Compute full information bottleneck objective.

        L = I(Z;Y) - β·I(Z;X)

        Args:
            selected_context: Selected context
            query_embedding: Query embedding
            full_memory: Full memory

        Returns:
            Dictionary with I_Z_Y, I_Z_X, and objective value
        """
        I_Z_Y = self.estimate_I_Z_Y(selected_context, query_embedding, full_memory)
        I_Z_X = self.estimate_I_Z_X(selected_context, full_memory)

        objective = I_Z_Y - self.beta * I_Z_X

        return {
            "I_Z_Y": I_Z_Y,
            "I_Z_X": I_Z_X,
            "beta": self.beta,
            "objective": objective,
            "compression_ratio": 1.0 - I_Z_X,
            "context_efficiency": I_Z_Y
            / max(1, sum(m.tokens for m in selected_context)),
        }
