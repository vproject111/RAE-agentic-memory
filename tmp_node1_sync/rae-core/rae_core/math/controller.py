"""Math Layer Controller - orchestrates all mathematical operations."""

# Import available functions
from typing import Any

from rae_core.math.dynamics import calculate_recency_score
from rae_core.math.policy import compute_memory_score
from rae_core.math.structure import cosine_similarity


class MathLayerController:
    """
    Controller for RAE math layer operations.

    Orchestrates:
    - Importance calculations
    - Decay functions
    - Similarity scoring
    - Quality metrics
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize controller with optional config."""
        self.config = config or {}

    def score_memory(
        self,
        memory: dict[str, Any],
        query_similarity: float = 0.5,
        weights: Any | None = None,
    ) -> float:
        """Score a memory's importance with optional weights."""
        from datetime import datetime, timezone

        # Handle missing created_at
        created_at = memory.get("created_at")
        if created_at is None:
            created_at = datetime.now(timezone.utc)

        result = compute_memory_score(
            similarity=query_similarity,
            importance=memory.get("importance", 0.5),
            last_accessed_at=memory.get("last_accessed_at"),
            created_at=created_at,  # type: ignore
            access_count=memory.get("usage_count", 0),
            weights=weights,
        )
        return float(result.final_score)


    def apply_decay(self, age_hours: float, usage_count: int = 0) -> float:
        """Apply time-based decay to importance."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        created_at = now - timedelta(hours=age_hours)

        # recency_score, age_seconds, effective_decay
        score, _, _ = calculate_recency_score(
            last_accessed_at=None,
            created_at=created_at,
            access_count=usage_count,
            now=now,
        )
        return float(score)

    def compute_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """Compute cosine similarity between embeddings."""
        try:
            return cosine_similarity(embedding1, embedding2)
        except Exception:
            # Fallback if function doesn't exist
            import math

            dot = sum(a * b for a, b in zip(embedding1, embedding2))
            mag1 = math.sqrt(sum(a * a for a in embedding1))
            mag2 = math.sqrt(sum(b * b for b in embedding2))
            return dot / (mag1 * mag2) if (mag1 * mag2) > 0 else 0.0
