"""
Math-based Reranking Strategy (MMR + Keyword Boosting).
Target: CPU / Lite Profile.
"""

from typing import Any, Dict, List

import numpy as np
from scipy.spatial.distance import cosine

from apps.memory_api.services.reranking.base import RerankingStrategy


class MathRerankerStrategy(RerankingStrategy):
    """
    Reranker that uses Maximum Marginal Relevance (MMR) and keyword boosting.
    Does not require an LLM.
    """

    def __init__(self, lambda_mult: float = 0.5, keyword_boost: float = 0.2):
        self.lambda_mult = lambda_mult
        self.keyword_boost = keyword_boost

    async def rerank(
        self, candidates: List[Dict[str, Any]], query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Apply MMR reranking and keyword boosting.
        """
        if not candidates:
            return []

        # 1. Keyword Boosting (Simple Heuristic)
        # Updates 'final_score' in place or creates a new score
        boosted_candidates = self._apply_keyword_boost(candidates, query)

        # 2. MMR Diversification
        # Requires vectors. If 'vector' is missing, fallback to simple sort.
        has_vectors = all("vector" in c for c in boosted_candidates)

        if has_vectors and len(boosted_candidates) > 1:
            try:
                # Mock query vector or retrieve it (Problem: we usually don't have query vector here)
                # If we don't have the query vector passed down, MMR is hard.
                # However, we have the initial similarity scores (v3_score).
                # We can approximate MMR using only document-document similarity.
                selected_indices = self._mmr_selection(boosted_candidates, limit)
                final_results = [boosted_candidates[i] for i in selected_indices]
                return final_results
            except Exception:
                # Fallback to simple sort if math fails
                pass

        # Fallback: Sort by boosted score
        boosted_candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
        return boosted_candidates[:limit]

    def _apply_keyword_boost(
        self, candidates: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        query_terms = set(query.lower().split())
        for cand in candidates:
            content = cand.get("content", "").lower()
            current_score = cand.get("final_score", 0.0)

            # Simple Exact Match Boost
            boost = 0.0
            for term in query_terms:
                if len(term) > 3 and term in content:
                    boost += 0.05  # Small boost per term

            # Bound boost
            boost = min(boost, self.keyword_boost)
            new_score = current_score + boost
            cand["final_score"] = new_score
            cand["smart_score"] = new_score  # For backward compatibility and debugging

        return candidates

    def _mmr_selection(self, candidates: List[Dict[str, Any]], limit: int) -> List[int]:
        """
        Selects indices using MMR algorithm.

        MMR = ArgMax [ lambda * Sim(Di, Q) - (1-lambda) * Max(Sim(Di, Dj)) ]

        Since we might not have Q vector, we use 'final_score' as proxy for Sim(Di, Q).
        We calculate Sim(Di, Dj) using the 'vector' field in candidates.
        """
        # Extract vectors
        vectors = np.array([c["vector"] for c in candidates])
        scores = np.array([c.get("final_score", 0.0) for c in candidates])

        selected_indices: List[int] = []
        candidate_indices = list(range(len(candidates)))

        while len(selected_indices) < limit and candidate_indices:
            best_score = -float("inf")
            best_idx = -1

            for idx in candidate_indices:
                # Relevance part (Sim(Di, Q))
                relevance = scores[idx]

                # Diversity part (Max(Sim(Di, Dj)))
                diversity = 0.0
                if selected_indices:
                    # Calculate sim with already selected
                    # cosine distance = 1 - sim => sim = 1 - dist
                    sims = [
                        1 - cosine(vectors[idx], vectors[sel_idx])
                        for sel_idx in selected_indices
                    ]
                    diversity = max(sims)

                mmr_score = (self.lambda_mult * relevance) - (
                    (1 - self.lambda_mult) * diversity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx != -1:
                selected_indices.append(best_idx)
                candidate_indices.remove(best_idx)
            else:
                break

        return selected_indices
