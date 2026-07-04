"""
RAE Math - Scoring Policy

This module implements the unified memory scoring policy that combines:
- Relevance (semantic similarity)
- Importance (content value)
- Recency (temporal dynamics)

These are pure mathematical functions that compose the core components
into final memory scores for retrieval ranking.

Mathematical Foundation:
    Unified Memory Score:
        S(m, q, t) = α·sim(m, q) + β·imp(m) + γ·rec(m, t)

    Where:
        - m = memory
        - q = query
        - t = current time
        - sim(m, q) = cosine similarity (relevance)
        - imp(m) = importance score
        - rec(m, t) = recency score (exponential decay)
        - α, β, γ = weights (sum to 1.0)

    This creates a multi-objective ranking that balances:
        1. Semantic relevance to current context
        2. Intrinsic importance of content
        3. Temporal relevance (recent = more relevant)

License: Apache-2.0
Author: Grzegorz Leśniowski <lesniowskig@gmail.com>
"""

from datetime import datetime, timezone
from typing import Any

from rae_core.math.dynamics import calculate_recency_score
from rae_core.math.structure import DecayConfig, MemoryScoreResult, ScoringWeights


def compute_memory_score(
    similarity: float,
    importance: float,
    last_accessed_at: datetime | None,
    created_at: datetime,
    access_count: int = 0,
    now: datetime | None = None,
    weights: ScoringWeights | None = None,
    decay_config: DecayConfig | None = None,
    memory_id: str | None = None,
) -> MemoryScoreResult:
    """
    Compute unified memory score combining relevance, importance, and recency.

    This is the core scoring function implementing RAE's unified scoring formula:
        score = alpha * similarity + beta * importance + gamma * recency_component

    Where recency_component considers:
    - Time since last access (or creation)
    - Access count (more accessed = slower decay)
    - Configurable decay rate

    Args:
        similarity: Relevance score from vector similarity (0.0-1.0)
        importance: Importance score (0.0-1.0)
        last_accessed_at: Last access timestamp (None = never accessed)
        created_at: Creation timestamp
        access_count: Number of times memory was accessed
        now: Current time (defaults to UTC now)
        weights: Custom scoring weights (defaults to ScoringWeights())
        decay_config: Custom decay configuration (defaults to DecayConfig())
        memory_id: Optional memory ID for logging/debugging

    Returns:
        MemoryScoreResult with final score and component breakdown

    Mathematical Properties:
        - All component scores are in [0, 1]
        - Final score is in [0, 1]
        - Weights determine relative importance of components
        - Default weights: α=0.5, β=0.3, γ=0.2

    Example:
        >>> from datetime import datetime, timedelta, timezone
        >>> now = datetime.now(timezone.utc)
        >>> created = now - timedelta(minutes=10)
        >>>
        >>> # High similarity, high importance, recent creation
        >>> score = compute_memory_score(
        ...     similarity=0.85,
        ...     importance=0.7,
        ...     last_accessed_at=None,
        ...     created_at=created,
        ...     access_count=5,
        ...     now=now
        ... )
        >>> print(f"Final score: {score.final_score:.3f}")
        Final score: 0.783
        >>> print(f"Components: rel={score.relevance_score:.3f}, "
        ...       f"imp={score.importance_score:.3f}, rec={score.recency_score:.3f}")
        Components: rel=0.850, imp=0.700, rec=0.773

    Implementation Notes:
        - Similarity and importance are clamped to [0, 1]
        - Recency uses exponential decay with access count adjustment
        - Final score is weighted combination, clamped to [0, 1]
    """
    # Initialize configs with defaults if not provided
    if weights is None:
        weights = ScoringWeights()
    if decay_config is None:
        decay_config = DecayConfig()
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Relevance component (normalized similarity)
    relevance_score = max(0.0, min(1.0, similarity))

    # 2. Importance component (already normalized)
    importance_score = max(0.0, min(1.0, importance))

    # 3. Recency component (exponential decay with access count adjustment)
    recency_score, age_seconds, effective_decay = calculate_recency_score(
        last_accessed_at=last_accessed_at,
        created_at=created_at,
        access_count=access_count,
        now=now,
        decay_config=decay_config,
    )

    # 4. Weighted combination
    final_score = (
        weights.alpha * relevance_score
        + weights.beta * importance_score
        + weights.gamma * recency_score
    )

    # Ensure final score is in [0, 1]
    final_score = max(0.0, min(1.0, final_score))

    return MemoryScoreResult(
        final_score=final_score,
        relevance_score=relevance_score,
        importance_score=importance_score,
        recency_score=recency_score,
        memory_id=memory_id or "unknown",
        age_seconds=age_seconds,
        access_count=access_count,
        effective_decay_rate=effective_decay,
    )


def compute_batch_scores(
    memories: list[dict[str, Any]],
    similarity_scores: list[float],
    now: datetime | None = None,
    weights: ScoringWeights | None = None,
    decay_config: DecayConfig | None = None,
) -> list[MemoryScoreResult]:
    """
    Compute scores for a batch of memories.

    Efficiently processes multiple memories with their corresponding similarity scores.
    This is the typical use case for memory retrieval ranking.

    Args:
        memories: List of memory dicts with keys:
            - id: Memory identifier
            - importance: Importance score (0.0-1.0)
            - last_accessed_at: Last access timestamp (optional)
            - created_at: Creation timestamp
            - usage_count or access_count: Access count (optional, default 0)
        similarity_scores: Corresponding similarity scores for each memory
        now: Current time (defaults to UTC now)
        weights: Scoring weights (defaults to ScoringWeights())
        decay_config: Decay configuration (defaults to DecayConfig())

    Returns:
        List of MemoryScoreResult objects, one per memory

    Raises:
        ValueError: If memories and similarity_scores have different lengths

    Example:
        >>> from datetime import datetime, timezone
        >>> memories = [
        ...     {
        ...         "id": "mem1",
        ...         "importance": 0.8,
        ...         "last_accessed_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...         "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        ...         "usage_count": 10,
        ...     },
        ...     {
        ...         "id": "mem2",
        ...         "importance": 0.6,
        ...         "last_accessed_at": None,
        ...         "created_at": datetime(2024, 1, 5, tzinfo=timezone.utc),
        ...         "usage_count": 2,
        ...     },
        ... ]
        >>> similarities = [0.9, 0.7]
        >>> results = compute_batch_scores(memories, similarities)
        >>> sorted_results = sorted(results, key=lambda r: r.final_score, reverse=True)
        >>> print(f"Top memory: {sorted_results[0].memory_id} "
        ...       f"(score: {sorted_results[0].final_score:.3f})")
        Top memory: mem1 (score: 0.850)
    """
    if len(memories) != len(similarity_scores):
        raise ValueError(
            f"Length mismatch: {len(memories)} memories but "
            f"{len(similarity_scores)} similarity scores"
        )

    results = []
    for memory, similarity in zip(memories, similarity_scores):
        # Extract fields (handle both usage_count and access_count)
        access_count = memory.get("usage_count") or memory.get("access_count") or 0

        result = compute_memory_score(
            similarity=similarity,
            importance=memory.get("importance", 0.5),
            last_accessed_at=memory.get("last_accessed_at"),
            created_at=memory["created_at"],
            access_count=access_count,
            now=now,
            weights=weights,
            decay_config=decay_config,
            memory_id=str(memory.get("id", "unknown")),
        )
        results.append(result)

    return results


def rank_memories_by_score(
    memories: list[dict[str, Any]], score_results: list[MemoryScoreResult]
) -> list[dict[str, Any]]:
    """
    Rank memories by their computed scores.

    Combines original memory records with their scores and sorts by
    final_score descending (highest score first).

    Args:
        memories: Original memory records
        score_results: Corresponding score results from compute_batch_scores()

    Returns:
        List of memories sorted by score (descending), with 'final_score' field added

    Raises:
        ValueError: If memories and score_results have different lengths

    Example:
        >>> memories = [
        ...     {"id": "mem1", "content": "...", "importance": 0.8},
        ...     {"id": "mem2", "content": "...", "importance": 0.6},
        ... ]
        >>> score_results = [...]  # From compute_batch_scores()
        >>> ranked = rank_memories_by_score(memories, score_results)
        >>> print(f"Top memory: {ranked[0]['id']} (score: {ranked[0]['final_score']:.3f})")
        Top memory: mem1 (score: 0.850)
    """
    if len(memories) != len(score_results):
        raise ValueError(
            f"Length mismatch: {len(memories)} memories but "
            f"{len(score_results)} score results"
        )

    # Combine memories with scores
    ranked = []
    for memory, score_result in zip(memories, score_results):
        memory_with_score = {**memory, "final_score": score_result.final_score}
        ranked.append(memory_with_score)

    # Sort by final_score descending
    ranked.sort(key=lambda m: m["final_score"], reverse=True)

    return ranked


def compute_score_with_custom_weights(
    similarity: float,
    importance: float,
    recency: float,
    alpha: float,
    beta: float,
    gamma: float,
) -> float:
    """
    Compute weighted score with custom weights (utility function).

    This is a simplified version for custom weight experimentation.

    Args:
        similarity: Relevance score (0.0-1.0)
        importance: Importance score (0.0-1.0)
        recency: Recency score (0.0-1.0)
        alpha: Relevance weight
        beta: Importance weight
        gamma: Recency weight

    Returns:
        Weighted score (0.0-1.0)

    Example:
        >>> # Emphasize recency heavily
        >>> score = compute_score_with_custom_weights(
        ...     similarity=0.8,
        ...     importance=0.7,
        ...     recency=0.9,
        ...     alpha=0.2,
        ...     beta=0.2,
        ...     gamma=0.6
        ... )
        >>> print(f"Score: {score:.3f}")
        Score: 0.840
    """
    score = alpha * similarity + beta * importance + gamma * recency
    return max(0.0, min(1.0, score))


def compute_coherence_reward(
    path_steps: list[str],
    episodic_memories: list[dict[str, Any]],
    semantic_memories: list[dict[str, Any]],
) -> float:
    """
    Compute coherence reward for a reasoning path.

    Higher reward if path is consistent with multiple memory layers.
    This encourages reasoning that aligns across episodic and semantic memory.

    Args:
        path_steps: List of reasoning step descriptions
        episodic_memories: Recent episodic memories for validation
        semantic_memories: Semantic knowledge for validation

    Returns:
        Coherence reward (0.0-1.0), higher is better

    Mathematical Properties:
        - Reward = (episodic_support + semantic_support) / (path_length + 1)
        - episodic_support = count of episodic memories aligned with path
        - semantic_support = count of semantic memories aligned with path
        - Normalized by path length to prevent bias toward longer paths

    Example:
        >>> episodic = [
        ...     {"content": "User logged in at 10am"},
        ...     {"content": "User accessed dashboard"},
        ... ]
        >>> semantic = [
        ...     {"content": "Dashboard requires authentication"},
        ... ]
        >>> path = ["User logged in", "User accessed dashboard"]
        >>> reward = compute_coherence_reward(path, episodic, semantic)
        >>> print(f"Coherence: {reward:.3f}")
        Coherence: 0.667

    Implementation Notes:
        - Simple alignment check: memory content appears in step
        - Could be enhanced with semantic similarity scoring
        - Returns 0.0 if path is empty
    """
    if not path_steps:
        return 0.0

    episodic_support = 0
    semantic_support = 0

    # Check alignment with episodic memories
    for memory in episodic_memories:
        memory_content = memory.get("content", "").lower()
        if not memory_content:
            continue

        # Check if any path step aligns with this memory
        for step in path_steps:
            if memory_content in step.lower() or step.lower() in memory_content:
                episodic_support += 1
                break  # Count each memory only once

    # Check alignment with semantic memories
    for memory in semantic_memories:
        memory_content = memory.get("content", "").lower()
        if not memory_content:
            continue

        # Check if any path step aligns with this memory
        for step in path_steps:
            if memory_content in step.lower() or step.lower() in memory_content:
                semantic_support += 1
                break  # Count each memory only once

    # Compute reward normalized by path length
    # +1 to avoid division by zero and prevent bias toward very short paths
    total_support = episodic_support + semantic_support
    reward = total_support / (len(path_steps) + 1)

    return max(0.0, min(1.0, reward))


def compute_reasoning_score_with_coherence(
    base_score: float,
    coherence_reward: float,
    coherence_weight: float = 0.3,
) -> float:
    """
    Combine base reasoning score with coherence reward.

    Args:
        base_score: Base reasoning score (0.0-1.0)
        coherence_reward: Coherence reward from compute_coherence_reward()
        coherence_weight: Weight for coherence component (default: 0.3)

    Returns:
        Combined score (0.0-1.0)

    Example:
        >>> base = 0.7
        >>> coherence = 0.8
        >>> score = compute_reasoning_score_with_coherence(base, coherence)
        >>> print(f"Combined: {score:.3f}")
        Combined: 0.730
    """
    # Weighted combination: (1 - w) * base + w * coherence
    combined = (
        1.0 - coherence_weight
    ) * base_score + coherence_weight * coherence_reward
    return max(0.0, min(1.0, combined))
