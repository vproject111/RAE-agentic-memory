import math
from datetime import datetime, timezone
from typing import List

from ..models import ScoredMemoryRecord


def calculate_recency_score(
    memory: ScoredMemoryRecord, half_life_hours: int = 24
) -> float:
    """
    Calculates a recency score for a memory using exponential decay.
    The score is 1 for a brand new memory and decays to 0.5 after half_life_hours.
    """
    now = datetime.now(timezone.utc)
    # Ensure the memory timestamp is timezone-aware
    memory_ts = (
        memory.timestamp
        if memory.timestamp.tzinfo
        else memory.timestamp.replace(tzinfo=timezone.utc)
    )

    time_diff_hours = (now - memory_ts).total_seconds() / 3600

    if time_diff_hours < 0:  # Should not happen, but as a safeguard
        return 1.0

    decay_rate = math.log(0.5) / half_life_hours
    return math.exp(decay_rate * time_diff_hours)


def calculate_usage_score(memory: ScoredMemoryRecord) -> float:
    """
    Calculates a score based on the memory's usage count, normalized with a logarithm.
    """
    return math.log1p(memory.usage_count)


def calculate_final_score(memory: ScoredMemoryRecord) -> float:
    """
    Combines various scores into a single final score for ranking.
    The weights are currently hardcoded but could be made configurable.
    """
    weights = {
        "semantic": 0.6,
        "recency": 0.1,
        "importance": 0.2,
        "usage": 0.1,
    }

    # Normalize semantic score (assuming it's in range [0,1] from vector search)
    semantic_score = memory.score

    recency_score = calculate_recency_score(memory)
    importance_score = memory.importance
    usage_score = calculate_usage_score(memory)

    final_score = (
        semantic_score * weights["semantic"]
        + recency_score * weights["recency"]
        + importance_score * weights["importance"]
        + usage_score * weights["usage"]
    )
    return float(final_score)


def rescore_memories(memories: List[ScoredMemoryRecord]) -> List[ScoredMemoryRecord]:
    """
    Takes a list of scored memories, recalculates their scores based on multiple heuristics,
    and returns the list sorted by the new final score.
    """
    if not memories:
        return []

    for memory in memories:
        memory.score = calculate_final_score(memory)

    # Sort by the new final score in descending order
    return sorted(memories, key=lambda m: m.score, reverse=True)
