"""
Reranker Factory.
"""

from typing import Any

import structlog

from apps.memory_api.config import settings
from apps.memory_api.services.reranking.base import RerankingStrategy
from apps.memory_api.services.reranking.llm_strategy import LlmRerankerStrategy
from apps.memory_api.services.reranking.math_strategy import MathRerankerStrategy

logger = structlog.get_logger(__name__)


class RerankerFactory:
    """
    Factory to create the appropriate RerankingStrategy based on configuration.
    """

    @staticmethod
    def create(llm_service: Any = None) -> RerankingStrategy:
        mode = getattr(settings, "RAE_RERANKER_MODE", "math")

        logger.info("reranker_factory_create", mode=mode)

        if mode == "llm":
            if llm_service:
                return LlmRerankerStrategy(llm_service)
            else:
                logger.warning(
                    "reranker_llm_mode_requested_but_no_service", fallback="math"
                )
                # Fallback to math if LLM service not provided
                return MathRerankerStrategy()

        # Default to Math
        return MathRerankerStrategy()
