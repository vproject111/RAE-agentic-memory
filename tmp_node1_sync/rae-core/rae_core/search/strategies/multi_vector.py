"""Multi-vector search strategy using Rank Reciprocal Fusion."""

import asyncio
from typing import Any
from uuid import UUID

from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.vector import IVectorStore
from rae_core.math.fusion import reciprocal_rank_fusion
from rae_core.search.strategies import SearchStrategy


class MultiVectorSearchStrategy(SearchStrategy):
    """
    Search strategy that fuses results from multiple vector spaces.

    This strategy allows searching across embeddings from different models
    (e.g., OpenAI text-embedding-3-small and Ollama mxbai-embed-large)
    simultaneously, robustly handling different dimensions.
    """

    def __init__(
        self,
        strategies: list[tuple[IVectorStore, IEmbeddingProvider, str]],
        default_weight: float = 0.5,
    ):
        """
        Initialize multi-vector search strategy.

        Args:
            strategies: List of (vector_store, embedding_provider, layer_name) tuples.
            default_weight: Default weight for this strategy in hybrid search.
        """
        self.strategies = strategies
        self.default_weight = default_weight

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[tuple[UUID, float]]:
        """
        Execute search across all vector stores and fuse results.

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            filters: Optional filters
            limit: Maximum number of results

        Returns:
            List of (memory_id, rrf_score) tuples
        """
        tasks = []
        for store, provider, layer in self.strategies:
            tasks.append(
                self._execute_single_search(
                    store,
                    provider,
                    query,
                    tenant_id,
                    filters,
                    limit * 2,  # Fetch more for fusion
                )
            )

        # Run searches in parallel
        results_list = await asyncio.gather(*tasks)

        # Fuse results using RRF
        fused_results = reciprocal_rank_fusion(results_list)

        return fused_results[:limit]

    async def _execute_single_search(
        self,
        store: IVectorStore,
        provider: IEmbeddingProvider,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None,
        limit: int,
    ) -> list[tuple[UUID, float]]:
        """Execute a single vector search."""
        try:
            query_embedding = await provider.embed_text(query)

            # Extract basic filters
            layer = filters.get("layer") if filters else None
            score_threshold = filters.get("score_threshold", 0.0) if filters else 0.0

            return await store.search_similar(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                layer=layer,
                limit=limit,
                score_threshold=score_threshold,
            )
        except Exception as e:
            # Log error but don't fail the whole search
            # TODO: Add logging
            print(f"Vector search failed for provider: {e}")
            return []

    def get_strategy_name(self) -> str:
        return "multi_vector_fusion"

    def get_strategy_weight(self) -> float:
        return self.default_weight
