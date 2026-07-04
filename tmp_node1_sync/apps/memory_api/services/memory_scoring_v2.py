"""
Memory Scoring V2 - Unified Relevance + Importance + Recency

This module provides a backward-compatible wrapper around rae_core.math
for the unified memory scoring function described in RAE v1 Implementation Plan.

The actual implementation now lives in rae_core.math as pure mathematical
functions, allowing them to be used independently of the FastAPI application.

This module now serves as:
1. A compatibility layer for existing code
2. An integration point for logging (via structlog)
3. The service layer that bridges rae_core (pure math) and apps/memory_api (infrastructure)

Mathematical formulation (implemented in rae_core.math):
    score = alpha * similarity + beta * importance + gamma * recency

Where:
- Relevance (similarity): Vector cosine similarity (0.0-1.0)
- Importance: LLM-driven or manual importance score (0.0-1.0)
- Recency: Time-based decay with access count consideration

See rae_core.math for detailed mathematical documentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

# Import pure math functions from rae_core
from rae_core.math import DecayConfig, MemoryScoreResult, ScoringWeights
from rae_core.math import compute_batch_scores as _compute_batch_scores
from rae_core.math import compute_memory_score as _compute_memory_score
from rae_core.math import rank_memories_by_score as _rank_memories_by_score

logger = structlog.get_logger(__name__)

# Re-export for backward compatibility
__all__ = [
    "ScoringWeights",
    "DecayConfig",
    "MemoryScoreResult",
    "compute_memory_score",
    "compute_batch_scores",
    "rank_memories_by_score",
]


# ============================================================================
# Service Layer Functions (with logging)
# ============================================================================
#
# These wrap the pure math functions from rae_core.math and add:
# - Structured logging for observability
# - Application-specific context
# - Integration with FastAPI services
#


def compute_memory_score(
    similarity: float,
    importance: float,
    last_accessed_at: Optional[datetime],
    created_at: datetime,
    access_count: int = 0,
    now: Optional[datetime] = None,
    weights: Optional[ScoringWeights] = None,
    decay_config: Optional[DecayConfig] = None,
    memory_id: Optional[str] = None,
) -> MemoryScoreResult:
    """
    Compute unified memory score combining relevance, importance, and recency.

    This is a service-layer wrapper that adds logging around the pure math
    function from rae_core.math.policy.compute_memory_score().

    For mathematical details, see: rae_core.math.policy.compute_memory_score

    Args:
        similarity: Relevance score from vector similarity (0.0-1.0)
        importance: Importance score (0.0-1.0)
        last_accessed_at: Last access timestamp (None = never accessed)
        created_at: Creation timestamp
        access_count: Number of times memory was accessed
        now: Current time (defaults to UTC now)
        weights: Custom scoring weights (defaults to ScoringWeights())
        decay_config: Custom decay configuration (defaults to DecayConfig())
        memory_id: Optional memory ID for logging

    Returns:
        MemoryScoreResult with final score and component breakdown

    Example:
        >>> from datetime import datetime, timezone
        >>> score = compute_memory_score(
        ...     similarity=0.85,
        ...     importance=0.7,
        ...     last_accessed_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...     created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...     access_count=5,
        ...     now=datetime(2024, 1, 8, tzinfo=timezone.utc)
        ... )
        >>> print(f"Final score: {score.final_score:.3f}")
        Final score: 0.783
    """
    # Delegate to pure math function
    result = _compute_memory_score(
        similarity=similarity,
        importance=importance,
        last_accessed_at=last_accessed_at,
        created_at=created_at,
        access_count=access_count,
        now=now,
        weights=weights,
        decay_config=decay_config,
        memory_id=memory_id,
    )

    # Log for observability (service layer responsibility)
    logger.debug(
        "memory_score_computed",
        memory_id=memory_id,
        final_score=round(result.final_score, 4),
        components={
            "relevance": round(result.relevance_score, 4),
            "importance": round(result.importance_score, 4),
            "recency": round(result.recency_score, 4),
        },
        age_seconds=int(result.age_seconds),
        access_count=result.access_count,
        effective_decay_rate=round(result.effective_decay_rate, 6),
    )

    return result


def compute_batch_scores(
    memories: List[Dict[str, Any]],
    similarity_scores: List[float],
    now: Optional[datetime] = None,
    weights: Optional[ScoringWeights] = None,
    decay_config: Optional[DecayConfig] = None,
) -> List[MemoryScoreResult]:
    """
    Compute scores for a batch of memories.

    Service-layer wrapper with logging around rae_core.math.policy.compute_batch_scores().

    For mathematical details, see: rae_core.math.policy.compute_batch_scores

    Args:
        memories: List of memory dicts with keys: id, importance,
                  last_accessed_at, created_at, usage_count (or access_count)
        similarity_scores: Corresponding similarity scores for each memory
        now: Current time
        weights: Scoring weights
        decay_config: Decay configuration

    Returns:
        List of MemoryScoreResult objects, one per memory

    Example:
        >>> memories = [
        ...     {
        ...         "id": "mem1",
        ...         "importance": 0.8,
        ...         "last_accessed_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...         "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...         "usage_count": 10,
        ...     },
        ... ]
        >>> similarities = [0.9]
        >>> results = compute_batch_scores(memories, similarities)
    """
    logger.debug(
        "batch_scoring_started",
        num_memories=len(memories),
        num_similarities=len(similarity_scores),
    )

    # Delegate to pure math function
    results = _compute_batch_scores(
        memories=memories,
        similarity_scores=similarity_scores,
        now=now,
        weights=weights,
        decay_config=decay_config,
    )

    logger.debug(
        "batch_scoring_completed",
        num_results=len(results),
        avg_score=(
            sum(r.final_score for r in results) / len(results) if results else 0.0
        ),
    )

    return results


def rank_memories_by_score(
    memories: List[Dict[str, Any]], score_results: List[MemoryScoreResult]
) -> List[Dict[str, Any]]:
    """
    Rank memories by their computed scores.

    Service-layer wrapper around rae_core.math.policy.rank_memories_by_score().

    For details, see: rae_core.math.policy.rank_memories_by_score

    Args:
        memories: Original memory records
        score_results: Corresponding score results

    Returns:
        List of memories sorted by score (descending), with 'final_score' added
    """
    # Delegate to pure math function
    return _rank_memories_by_score(memories, score_results)
