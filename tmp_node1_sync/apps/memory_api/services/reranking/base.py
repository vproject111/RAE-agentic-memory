"""
Base Reranking Strategy Interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class RerankingStrategy(ABC):
    """
    Abstract base class for reranking strategies.
    """

    @abstractmethod
    async def rerank(
        self, candidates: List[Dict[str, Any]], query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Re-rank a list of candidate memories.

        Args:
            candidates: List of memory dicts (must contain 'embedding' if using math strategy).
            query: The user query string.
            limit: Number of results to return.

        Returns:
            Re-ordered and trimmed list of candidates.
        """
        pass
