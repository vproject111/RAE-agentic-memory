"""Vector-based semantic search strategy."""

from typing import Any
from uuid import UUID

from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.vector import IVectorStore
from rae_core.search.strategies import SearchStrategy


class VectorSearchStrategy(SearchStrategy):
    """Semantic search using vector embeddings.

    Uses cosine similarity between query embedding and memory embeddings
    to find semantically similar memories.
    """

    def __init__(
        self,
        vector_store: IVectorStore,
        embedding_provider: IEmbeddingProvider,
        default_weight: float = 0.4,
    ):
        """Initialize vector search strategy.

        Args:
            vector_store: Vector store implementation
            embedding_provider: Embedding provider for query encoding
            default_weight: Default weight in hybrid search (0.0-1.0)
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.default_weight = default_weight

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[tuple[UUID, float]]:
        """Execute semantic search.

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            filters: Optional filters (layer, agent_id, score_threshold, etc.)
            limit: Maximum number of results

        Returns:
            List of (memory_id, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = await self.embedding_provider.embed_text(query)

        # Extract filters
        layer = filters.get("layer") if filters else None
        agent_id = filters.get("agent_id") if filters else None
        score_threshold = filters.get("score_threshold", 0.0) if filters else 0.0

        # Search similar vectors
        results = await self.vector_store.search_similar(
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            layer=layer,
            agent_id=agent_id,
            limit=limit,
            score_threshold=score_threshold,
        )

        return results

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "vector"

    def get_strategy_weight(self) -> float:
        """Return default weight for hybrid fusion."""
        return self.default_weight
