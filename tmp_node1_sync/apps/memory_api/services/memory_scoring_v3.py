"""
Memory Scoring V3 - Hybrid Math (Iteration 1)

This module implements the "Soft Hybrid" scoring strategy described in
Hybrid Math v3 Plan. It extends Math v2 by adding:
- Graph Centrality
- Diversity (penalizing similarity between results)
- Information Density

Formula:
    score = w1*relevance + w2*importance + w3*recency +
            w4*graph_centrality + w5*diversity + w6*density
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class ScoringWeightsV3:
    """
    Weights for Hybrid Math v3 scoring components.

    Weights should sum to 1.0.
    """

    w1_relevance: float = 0.40
    w2_importance: float = 0.20
    w3_recency: float = 0.10
    w4_centrality: float = 0.10
    w5_diversity: float = 0.10
    w6_density: float = 0.10

    def __post_init__(self):
        total = sum(
            [
                self.w1_relevance,
                self.w2_importance,
                self.w3_recency,
                self.w4_centrality,
                self.w5_diversity,
                self.w6_density,
            ]
        )
        if not math.isclose(total, 1.0, rel_tol=1e-5):
            logger.warning(
                "scoring_weights_v3_not_normalized",
                total=total,
                weights=self.__dict__,
            )


@dataclass
class DecayConfig:
    """Configuration for recency decay (reused from v2 logic)."""

    base_decay_rate: float = 0.001
    access_count_boost: bool = True
    min_decay_rate: float = 0.0001
    max_decay_rate: float = 0.01


@dataclass
class MemoryScoreResultV3:
    """Result of memory scoring with full component breakdown."""

    final_score: float

    # Sub-scores
    score_relevance: float
    score_importance: float
    score_recency: float
    score_centrality: float
    score_diversity: float
    score_density: float

    # Metadata
    memory_id: str


# ============================================================================
# Core Logic
# ============================================================================


def compute_batch_scores_v3(
    memories: List[Dict[str, Any]],
    similarity_scores: List[float],
    embeddings: Optional[List[List[float]]] = None,
    now: Optional[datetime] = None,
    weights: Optional[ScoringWeightsV3] = None,
    decay_config: Optional[DecayConfig] = None,
) -> List[MemoryScoreResultV3]:
    """
    Compute scores for a batch of memories using Math v3 logic.
    """
    if weights is None:
        weights = ScoringWeightsV3()
    if decay_config is None:
        decay_config = DecayConfig()
    if now is None:
        now = datetime.now(timezone.utc)

    results = []

    # Pre-calculate diversity if embeddings are available
    diversity_scores = (
        _calculate_batch_diversity(embeddings) if embeddings else [1.0] * len(memories)
    )

    for i, (memory, similarity) in enumerate(zip(memories, similarity_scores)):
        # Extract standard fields
        access_count = memory.get("usage_count") or memory.get("access_count") or 0
        created_at = _ensure_utc(memory["created_at"])
        last_accessed_at = memory.get("last_accessed_at")
        if last_accessed_at:
            last_accessed_at = _ensure_utc(last_accessed_at)

        # 1. Relevance (w1)
        score_relevance = max(0.0, min(1.0, similarity))

        # 2. Importance (w2)
        # Use 'importance' field from DB, default to 0.5
        score_importance = max(0.0, min(1.0, memory.get("importance", 0.5)))

        # 3. Recency (w3)
        score_recency = _calculate_recency(
            last_accessed_at, created_at, access_count, now, decay_config
        )

        # 4. Graph Centrality (w4)
        # Looking for 'graph_centrality' in memory record
        # If missing, check metadata, else default to importance (heuristic fallback)
        centrality_raw = memory.get("graph_centrality")
        if centrality_raw is None:
            centrality_raw = memory.get("metadata", {}).get("graph_centrality", 0.0)
        score_centrality = max(0.0, min(1.0, float(centrality_raw)))

        # 5. Diversity (w5)
        score_diversity = diversity_scores[i]

        # 6. Density (w6)
        # Heuristic: 'token_count' normalized or 'content' length
        score_density = _calculate_density(memory)

        # Weighted Sum
        final_score = (
            weights.w1_relevance * score_relevance
            + weights.w2_importance * score_importance
            + weights.w3_recency * score_recency
            + weights.w4_centrality * score_centrality
            + weights.w5_diversity * score_diversity
            + weights.w6_density * score_density
        )

        final_score = max(0.0, min(1.0, final_score))

        results.append(
            MemoryScoreResultV3(
                final_score=final_score,
                score_relevance=score_relevance,
                score_importance=score_importance,
                score_recency=score_recency,
                score_centrality=score_centrality,
                score_diversity=score_diversity,
                score_density=score_density,
                memory_id=str(memory.get("id", "unknown")),
            )
        )

    return results


def _calculate_recency(
    last_accessed_at: Optional[datetime],
    created_at: datetime,
    access_count: int,
    now: datetime,
    decay_config: DecayConfig,
) -> float:
    """Calculate recency score (same logic as v2)."""
    time_ref = last_accessed_at if last_accessed_at else created_at
    time_diff = (now - time_ref).total_seconds()

    if time_diff < 0:
        return 1.0

    if decay_config.access_count_boost and access_count > 0:
        effective_decay = decay_config.base_decay_rate / (
            math.log(1 + access_count) + 1
        )
    else:
        effective_decay = decay_config.base_decay_rate

    effective_decay = max(
        decay_config.min_decay_rate, min(decay_config.max_decay_rate, effective_decay)
    )

    return max(0.0, min(1.0, math.exp(-effective_decay * time_diff)))


def _calculate_batch_diversity(embeddings: List[List[float]]) -> List[float]:
    """
    Calculate diversity score for each item in batch.
    Score = 1.0 - (average cosine similarity to other items).
    Higher score = more unique.
    """
    n = len(embeddings)
    if n <= 1:
        return [1.0] * n

    import numpy as np

    # Simple O(N^2) implementation - fine for batch_size ~50
    try:
        vecs = np.array(embeddings)
        # Normalize vectors
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # Avoid div by zero
        vecs_norm = vecs / norms

        # Similarity matrix
        sim_matrix = np.dot(vecs_norm, vecs_norm.T)

        scores = []
        for i in range(n):
            # Average similarity to others (exclude self at index i)
            others_sim = (np.sum(sim_matrix[i]) - sim_matrix[i, i]) / (n - 1)
            # Diversity = 1 - similarity
            # Ensure bounded [0, 1]
            diversity = 1.0 - max(0.0, min(1.0, others_sim))
            scores.append(diversity)

        return scores

    except ImportError:
        logger.warning("numpy_missing_for_diversity_check")
        return [1.0] * n
    except Exception as e:
        logger.error("diversity_calculation_failed", error=str(e))
        return [1.0] * n


def _calculate_density(memory: Dict[str, Any]) -> float:
    """
    Calculate information density score.

    Heuristic:
    - If token_count exists: token_count / 1000 (normalized up to 1k tokens)
    - Else: content length / 4000
    """
    metadata = memory.get("metadata", {})
    token_count = metadata.get("token_count")

    if token_count:
        # Assume sweet spot is around 100-500 tokens.
        # Too short (<10) is bad. Too long (>1000) might be dilute.
        # For now, linear normalization up to 500 tokens.
        return min(1.0, float(token_count) / 500.0)

    content = memory.get("content", "")
    length = len(content)
    if length == 0:
        return 0.0

    # Fallback: 1 char approx 0.25 tokens
    # 500 tokens * 4 = 2000 chars
    return min(1.0, length / 2000.0)


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
