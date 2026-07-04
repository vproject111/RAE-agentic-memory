"""
Smart Re-Ranker (Strategy Pattern Implementation)

This module delegates the re-ranking logic to the configured strategy (Math vs. LLM).
It serves as the main entry point for the application to request reranking.
"""

import time
from typing import Any, Dict, List, Optional

import structlog

from apps.memory_api.config import settings
from apps.memory_api.services.reranking.factory import RerankerFactory

logger = structlog.get_logger(__name__)


class SmartReranker:
    """
    Smart Re-Ranker service.

    Acts as a facade for the underlying RerankingStrategy.
    """

    def __init__(self, llm_service: Optional[Any] = None):
        """
        Initialize the Reranker with a specific strategy.

        Args:
            llm_service: Optional LLM service instance (required for 'llm' mode).
        """
        self.strategy = RerankerFactory.create(llm_service)

    async def rerank(
        self, candidates: List[Dict[str, Any]], query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Re-rank a list of candidate memories using the active strategy.

        Args:
            candidates: List of memories (dict).
            query: The user query.
            limit: Number of items to return.

        Returns:
            Re-ranked and trimmed list of memories.
        """
        if not settings.ENABLE_SMART_RERANKER:
            return candidates[:limit]

        if not candidates:
            return []

        start_time = time.perf_counter()

        try:
            results = await self.strategy.rerank(candidates, query, limit)

            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(
                "smart_reranking_complete",
                count_in=len(candidates),
                count_out=len(results),
                strategy=settings.RAE_RERANKER_MODE,
                elapsed_ms=elapsed,
            )
            return results

        except Exception as e:
            logger.error("smart_reranker_failed", error=str(e))
            # Fail safe: return original top-k
            return candidates[:limit]
