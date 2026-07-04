"""
Rank Reciprocal Fusion (RRF) Implementation.

This module provides mathematical functions for fusing ranked lists from multiple
search strategies using the Reciprocal Rank Fusion algorithm.
"""

from uuid import UUID


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[UUID, float]]], k: int = 60
) -> list[tuple[UUID, float]]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.

    RRF Score(d) = sum(1 / (k + rank(d)))

    Args:
        ranked_lists: A list of ranked lists. Each ranked list contains
                      tuples of (item_id, original_score).
                      The lists are assumed to be sorted by score descending.
        k: The constant k in the RRF formula (default: 60).

    Returns:
        A combined list of (item_id, rrf_score), sorted by rrf_score descending.
    """
    rrf_scores: dict[UUID, float] = {}

    for ranked_list in ranked_lists:
        for rank, (item_id, _) in enumerate(ranked_list):
            # rank is 0-based
            score = 1.0 / (k + rank)
            if item_id in rrf_scores:
                rrf_scores[item_id] += score
            else:
                rrf_scores[item_id] = score

    # Sort by RRF score descending
    sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_items
