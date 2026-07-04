"""Hybrid search engine that orchestrates multiple search strategies."""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from rae_core.search.cache import SearchCache
from rae_core.search.strategies import SearchStrategy


class HybridSearchEngine:
    """Hybrid search engine combining multiple strategies.

    Implements Reciprocal Rank Fusion (RRF) to combine results
    from multiple search strategies (vector, graph, sparse, fulltext).
    """

    def __init__(
        self,
        strategies: dict[str, SearchStrategy],
        cache: SearchCache | None = None,
        rrf_k: int = 60,
    ):
        """Initialize hybrid search engine.

        Args:
            strategies: Dictionary of strategy_name -> strategy instance
            cache: Optional search cache
            rrf_k: RRF constant (typically 60)
        """
        self.strategies = strategies
        self.cache = cache
        self.rrf_k = rrf_k

    def _reciprocal_rank_fusion(
        self,
        strategy_results: dict[str, list[tuple[UUID, float]]],
        strategy_weights: dict[str, float],
    ) -> list[tuple[UUID, float]]:
        """Combine multiple result sets using Reciprocal Rank Fusion.

        RRF Formula: score(d) = Σ weight_s / (k + rank_s(d))
        where k is a constant (typically 60) and rank_s(d) is the rank
        of document d in strategy s.

        Args:
            strategy_results: Results from each strategy
            strategy_weights: Weight for each strategy

        Returns:
            Fused results sorted by combined score
        """
        # Build unified score map
        unified_scores: dict[UUID, float] = {}

        for strategy_name, results in strategy_results.items():
            weight = strategy_weights.get(strategy_name, 1.0)

            for rank, (memory_id, _) in enumerate(results, start=1):
                # RRF score contribution
                rrf_score = weight / (self.rrf_k + rank)

                if memory_id in unified_scores:
                    unified_scores[memory_id] += rrf_score
                else:
                    unified_scores[memory_id] = rrf_score

        # Convert to sorted list
        fused_results = sorted(
            unified_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return fused_results

    async def search(
        self,
        query: str,
        tenant_id: str,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[tuple[UUID, float]]:
        """Execute hybrid search across multiple strategies.

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            strategies: List of strategy names to use (all if None)
            strategy_weights: Custom weights for strategies (uses defaults if None)
            filters: Optional filters passed to all strategies
            limit: Maximum number of results
            use_cache: Whether to use cache for results

        Returns:
            List of (memory_id, fused_score) tuples
        """
        # Determine which strategies to use
        active_strategies = strategies or list(self.strategies.keys())

        # Determine weights
        weights = strategy_weights or {}
        for strategy_name in active_strategies:
            if strategy_name not in weights:
                strategy = self.strategies.get(strategy_name)
                if strategy:
                    weights[strategy_name] = strategy.get_strategy_weight()

        # Collect results from each strategy
        strategy_results: dict[str, list[tuple[UUID, float]]] = {}

        for strategy_name in active_strategies:
            strategy = self.strategies.get(strategy_name)
            if not strategy:
                continue

            # Check cache first
            cached_result = None
            if use_cache and self.cache:
                cached_result = await self.cache.get(
                    query=query,
                    tenant_id=tenant_id,
                    strategy=strategy_name,
                    filters=filters,
                )

            if cached_result is not None:
                strategy_results[strategy_name] = cached_result
            else:
                # Execute strategy
                results = await strategy.search(
                    query=query,
                    tenant_id=tenant_id,
                    filters=filters,
                    limit=limit * 2,  # Fetch more for fusion
                )
                strategy_results[strategy_name] = results

                # Cache results
                if use_cache and self.cache:
                    await self.cache.set(
                        query=query,
                        tenant_id=tenant_id,
                        strategy=strategy_name,
                        results=results,
                        filters=filters,
                    )

        # Fuse results using RRF
        fused_results = self._reciprocal_rank_fusion(
            strategy_results=strategy_results,
            strategy_weights=weights,
        )

        return fused_results[:limit]

    async def search_single_strategy(
        self,
        strategy_name: str,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[tuple[UUID, float]]:
        """Execute search using a single strategy.

        Args:
            strategy_name: Name of strategy to use
            query: Search query text
            tenant_id: Tenant identifier
            filters: Optional filters
            limit: Maximum number of results
            use_cache: Whether to use cache

        Returns:
            List of (memory_id, score) tuples
        """
        strategy = self.strategies.get(strategy_name)
        if not strategy:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        # Check cache
        if use_cache and self.cache:
            cached_result = await self.cache.get(
                query=query,
                tenant_id=tenant_id,
                strategy=strategy_name,
                filters=filters,
            )
            if cached_result is not None:
                return cached_result[:limit]

        # Execute strategy
        results = await strategy.search(
            query=query,
            tenant_id=tenant_id,
            filters=filters,
            limit=limit,
        )

        # Cache results
        if use_cache and self.cache:
            await self.cache.set(
                query=query,
                tenant_id=tenant_id,
                strategy=strategy_name,
                results=results,
                filters=filters,
            )

        return results

    def get_available_strategies(self) -> list[str]:
        """Get list of available strategy names."""
        return list(self.strategies.keys())

    async def rerank(
        self,
        query: str,
        results: list[tuple[UUID, float]],
    ) -> list[tuple[UUID, float]]:
        """Rerank search results.

        Placeholder implementation that returns results as-is.
        Should be overridden or extended to use a real reranker.

        Args:
            query: Search query
            results: Results to rerank

        Returns:
            Reranked results
        """
        return results


class NoiseAwareSearchEngine(HybridSearchEngine):
    """Noise-aware search engine that adjusts retrieval based on noise level.

    Under high noise conditions (>0.5), this engine:
    1. Boosts weight of recent memories (recency bias)
    2. Boosts weight of high-confidence memories
    3. Reduces influence of potentially corrupted older data

    This improves RST (Retrieval under Stress Test) performance by
    preferring verified, recent data when noise is high.
    """

    def __init__(
        self,
        strategies: dict[str, SearchStrategy],
        cache: SearchCache | None = None,
        rrf_k: int = 60,
        noise_threshold: float = 0.5,
        recency_boost_factor: float = 1.5,
        confidence_boost_factor: float = 1.3,
    ):
        """Initialize noise-aware search engine.

        Args:
            strategies: Dictionary of strategy_name -> strategy instance
            cache: Optional search cache
            rrf_k: RRF constant (typically 60)
            noise_threshold: Noise level above which to activate boosting
            recency_boost_factor: Multiplier for recent memory scores
            confidence_boost_factor: Multiplier for high-confidence scores
        """
        super().__init__(strategies=strategies, cache=cache, rrf_k=rrf_k)
        self.noise_threshold = noise_threshold
        self.recency_boost_factor = recency_boost_factor
        self.confidence_boost_factor = confidence_boost_factor

    def _apply_noise_aware_boost(
        self,
        results: list[tuple[UUID, float]],
        memory_metadata: dict[UUID, dict[str, Any]],
        noise_level: float,
    ) -> list[tuple[UUID, float]]:
        """Apply noise-aware boosting to search results.

        Args:
            results: Original search results (memory_id, score)
            memory_metadata: Metadata for each memory (timestamp, confidence, etc.)
            noise_level: Current noise level (0.0-1.0)

        Returns:
            Boosted results sorted by new scores
        """
        if noise_level <= self.noise_threshold:
            # No boosting needed under low noise
            return results

        now = datetime.now(timezone.utc)
        boosted_results = []

        for memory_id, base_score in results:
            metadata = memory_metadata.get(memory_id, {})

            # Calculate recency boost
            created_at = metadata.get("created_at")
            recency_boost = 0.0
            if created_at:
                age_days = (now - created_at).days
                # Exponential decay: 1.0 for today, 0.5 for 7 days, ~0 for 30+ days
                recency_boost = 1.0 / (1.0 + age_days / 7.0)

            # Calculate confidence boost
            confidence = metadata.get("confidence_score", 0.5)
            confidence_boost = confidence  # Already 0-1

            # Apply boosts (scaled by noise level)
            noise_intensity = (noise_level - self.noise_threshold) / (
                1.0 - self.noise_threshold
            )

            final_recency_boost = (
                1.0
                + (self.recency_boost_factor - 1.0) * recency_boost * noise_intensity
            )
            final_confidence_boost = (
                1.0
                + (self.confidence_boost_factor - 1.0)
                * confidence_boost
                * noise_intensity
            )

            # Combine boosts multiplicatively
            boosted_score = base_score * final_recency_boost * final_confidence_boost

            boosted_results.append((memory_id, boosted_score))

        # Re-sort by boosted scores
        boosted_results.sort(key=lambda x: x[1], reverse=True)

        return boosted_results

    async def search(
        self,
        query: str,
        tenant_id: str,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        use_cache: bool = True,
        noise_level: float = 0.0,
        memory_metadata: dict[UUID, dict[str, Any]] | None = None,
    ) -> list[tuple[UUID, float]]:
        """Execute noise-aware hybrid search.

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            strategies: List of strategy names to use
            strategy_weights: Custom weights for strategies
            filters: Optional filters
            limit: Maximum number of results
            use_cache: Whether to use cache
            noise_level: Current noise level (0.0-1.0)
            memory_metadata: Metadata for memories (for boosting)

        Returns:
            List of (memory_id, score) tuples with noise-aware adjustments
        """
        # Execute base hybrid search
        base_results = await super().search(
            query=query,
            tenant_id=tenant_id,
            strategies=strategies,
            strategy_weights=strategy_weights,
            filters=filters,
            limit=limit * 2,  # Fetch more for post-processing
            use_cache=use_cache,
        )

        # Apply noise-aware boosting if metadata provided
        if memory_metadata and noise_level > 0.0:
            boosted_results = self._apply_noise_aware_boost(
                results=base_results,
                memory_metadata=memory_metadata,
                noise_level=noise_level,
            )
            return boosted_results[:limit]

        return base_results[:limit]
