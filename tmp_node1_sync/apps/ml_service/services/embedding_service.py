"""
Embedding Service - API-based embedding generation using LiteLLM.

This service handles embedding generation for the ML microservice,
now using external APIs via LiteLLM to eliminate heavy local dependencies.
"""

from typing import List

import litellm
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingMLService:
    """
    Service for generating embeddings using LiteLLM API.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_name: str = "ollama/nomic-embed-text"):
        """
        Initialize embedding service with specified model.

        Args:
            model_name: Name of the LiteLLM model to use
        """
        if not hasattr(self, "model_name"):
            self.model_name = model_name
            logger.info("embedding_service_initialized", model_name=model_name)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts (synchronous).
        """
        if not texts:
            return []

        logger.info(
            "generating_embeddings", text_count=len(texts), model=self.model_name
        )

        try:
            response = litellm.embedding(model=self.model_name, input=texts)
            result = [d["embedding"] for d in response["data"]]

            logger.info(
                "embeddings_generated",
                text_count=len(texts),
                embedding_dim=len(result[0]) if result else 0,
            )
            return result
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Fallback to zeros if API fails
            dim = self.get_embedding_dimension()
            return [[0.0] * dim for _ in texts]

    async def generate_embeddings_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts (asynchronous).
        """
        if not texts:
            return []

        try:
            response = await litellm.aembedding(model=self.model_name, input=texts)
            return [d["embedding"] for d in response["data"]]
        except Exception as e:
            logger.error("async_embedding_generation_failed", error=str(e))
            dim = self.get_embedding_dimension()
            return [[0.0] * dim for _ in texts]

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        """
        if "nomic" in self.model_name:
            return 768
        if "text-embedding-3-small" in self.model_name:
            return 1536
        return 1536
