"""Hybrid search engine implementation."""

import math
import os
from typing import Any
from uuid import UUID

import structlog

from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.reranking import IReranker
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.math.fusion import FusionStrategy
from rae_core.math.metadata_injector import MetadataInjector
from rae_core.models.evidence_package import EvidenceItem, EvidencePackage
from rae_core.search.router import RoutingPlan, StrategyRouter
from rae_core.search.strategies import SearchStrategy
from rae_core.search.sufficiency_gate import EvidenceSufficiencyGate

logger = structlog.get_logger(__name__)


class EmeraldReranker(IReranker):
    """Emerald Reranker v1 - Semantic Cross-Validation."""

    def __init__(self, embedding_provider: Any, memory_storage: Any):
        self.embedding_provider = embedding_provider
        self.memory_storage = memory_storage

    async def rerank(
        self,
        query: str,
        candidates: list[tuple[UUID, float, float]],
        tenant_id: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[tuple[UUID, float, float]]:
        if self.embedding_provider is None or self.memory_storage is None:
            return candidates[:limit]

        try:
            query_emb = await self.embedding_provider.embed_text(
                query, task_type="search_query"
            )
            reranked: list[tuple[UUID, float, float]] = []

            for item in candidates:
                m_id, original_score, importance, audit_log = (
                    self._unpack_candidate_with_audit(item)
                )

                # Get full content for deep comparison
                memory = await self.memory_storage.get_memory(m_id, tenant_id)
                if not memory:
                    reranked.append((m_id, original_score, importance, audit_log))
                    continue

                # Semantic Scoring (Emerald Logic)
                memory_emb = await self.embedding_provider.embed_text(
                    memory.content, task_type="search_document"
                )

                # Manual Cosine Similarity (No external dependencies needed here)
                v1 = query_emb
                v2 = memory_emb
                dot = sum(a * b for a, b in zip(v1, v2))
                mag1 = math.sqrt(sum(a * a for a in v1))
                mag2 = math.sqrt(sum(a * a for a in v2))
                semantic_score = dot / (mag1 * mag2) if (mag1 * mag2) > 0 else 0.0

                # Synergy Score: 70% Semantic, 30% Original Rank
                final_score = (semantic_score * 0.7) + (original_score * 0.3)
                audit_log["emerald_semantic"] = semantic_score
                reranked.append((m_id, final_score, importance, audit_log))

            return sorted(reranked, key=lambda x: x[1], reverse=True)[:limit]
        except Exception as e:
            logger.error("rerank_failed", error=str(e))
            return candidates[:limit]

    def _unpack_candidate_with_audit(
        self, item: tuple
    ) -> tuple[UUID, float, float, dict]:
        """Safely unpack candidate tuple with audit log (4 values)."""
        if len(item) == 4:
            return item[0], item[1], item[2], item[3]
        elif len(item) == 3:
            return item[0], item[1], item[2], {}
        elif len(item) == 2:
            return item[0], item[1], 0.0, {}
        else:
            raise ValueError(f"Invalid candidate tuple length: {len(item)}")

    def _unpack_candidate(self, item: tuple) -> tuple[UUID, float, float]:
        """Safely unpack candidate tuple (handles 2, 3, or 4 values)."""
        if len(item) == 4:
            return item[0], item[1], item[2]
        elif len(item) == 3:
            return item[0], item[1], item[2]
        elif len(item) == 2:
            return item[0], item[1], 0.0
        else:
            raise ValueError(f"Invalid candidate tuple length: {len(item)}")


class HybridSearchEngine:
    """
    Orchestrates multiple search strategies (Vector + FullText) and fuses them using LogicGateway.
    """

    def __init__(
        self,
        strategies: dict[str, SearchStrategy],
        embedding_provider: IEmbeddingProvider | None = None,
        memory_storage: IMemoryStorage | None = None,
        reranker: IReranker | None = None,
        graph_store: Any | None = None,
        math_controller: Any | None = None,
        cache: Any | None = None,
        router: StrategyRouter | None = None,
    ):
        self.strategies = strategies
        self.embedding_provider = embedding_provider
        self.memory_storage = memory_storage
        self.graph_store = graph_store
        self._reranker = reranker
        self.math_controller = math_controller
        self.cache = cache
        self.router = router or StrategyRouter()
        self.injector = MetadataInjector()

        # Initialize Fusion Strategy (LogicGateway wrapper)
        config = self.math_controller.config if self.math_controller else {}
        self.fusion_strategy = FusionStrategy(config)
        if hasattr(self.fusion_strategy, "gateway"):
            self.fusion_strategy.gateway.storage = memory_storage
            self.fusion_strategy.gateway.graph_store = graph_store

    async def search(
        self,
        query: str,
        tenant_id: str,
        agent_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        enable_reranking: bool = False,
        math_controller: Any = None,
        **kwargs: Any,
    ) -> list[tuple[UUID, float, float]]:
        """
        Execute search across active strategies and fuse results.
        Supports System 7.2 gateway_config override.
        """
        # Intelligent routing support (Iteration 5)
        auto_route = kwargs.get(
            "auto_route",
            os.getenv("RAE_QUERY_ROUTING_ENABLED", "false").lower()
            in ("1", "true", "yes", "on"),
        )
        if auto_route and strategies is None:
            available = list(self.strategies.keys())
            routing_plan = self.router.route(query, available_strategies=available)
            active_strategies = routing_plan.active_strategies
            if strategy_weights is None:
                strategy_weights = routing_plan.strategy_weights
        else:
            active_strategies = strategies or list(self.strategies.keys())

        weights = {}
        for name in active_strategies:
            if strategy_weights and name in strategy_weights:
                weights[name] = strategy_weights[name]
            elif name in self.strategies:
                strat = self.strategies[name]
                if hasattr(strat, "get_strategy_weight"):
                    weights[name] = strat.get_strategy_weight()
                else:
                    weights[name] = 1.0

        # Extract Gateway Config Override (System 7.2)
        gateway_config = kwargs.get("gateway_config")

        # SYSTEM 43.0: No Enrichment. Enrichment dilutes technical signal.
        enriched_query = query

        # 1. PARALLEL EXECUTION (Full Spectrum Synergy)
        strategy_results: dict[str, list[tuple[UUID, float, float]]] = {}

        async def run_strategies():
            tasks = []
            task_names = []
            for name in active_strategies:
                if name not in self.strategies:
                    continue

                strategy = self.strategies[name]
                task_names.append(name)

                # Split-Brain Querying: Vector gets enriched, FullText gets precise
                target_query = enriched_query if name == "vector" else query

                tasks.append(
                    strategy.search(
                        query=target_query,
                        tenant_id=tenant_id,
                        filters=filters,
                        limit=limit,
                        **kwargs,
                    )
                )

            if not tasks:
                return {}

            import asyncio

            all_results = await asyncio.gather(*tasks, return_exceptions=True)

            results_dict = {}
            for name, results in zip(task_names, all_results):
                if isinstance(results, Exception):
                    logger.error("strategy_failed", name=name, error=str(results))
                    results_dict[name] = []
                else:
                    results_dict[name] = [
                        (r[0], r[1], r[2] if len(r) > 2 else 0.0) for r in results
                    ]
            return results_dict

        # Run all strategies in parallel
        strategy_results = await run_strategies()

        if not strategy_results:
            logger.warning("no_active_strategies_for_search")

        # 2. FUSION (LogicGateway)
        # Fetch contents for reranking
        all_ids = set()
        for results in strategy_results.values():
            for r in results:
                all_ids.add(r[0])  # m_id

        memory_data = {}
        if all_ids and hasattr(self.memory_storage, "get_memories_batch"):
            try:
                mems = await self.memory_storage.get_memories_batch(
                    list(all_ids), tenant_id
                )
                for mem in mems:
                    # Store full memory object instead of just content
                    memory_data[mem["id"]] = mem
            except Exception as e:
                logger.warning("batch_fetch_failed", error=str(e))

        # Note: We pass 'gateway_config' to fuse if supported
        # SYSTEM 41.1: We pass the ORIGINAL query to LogicGateway (Resonance/Neural)
        fused_results = await self.fusion_strategy.fuse(
            strategy_results,
            weights,
            query=query,
            config_override=gateway_config,
            memory_contents=memory_data,
        )

        # 3. OPTIONAL RERANKING
        if enable_reranking and len(fused_results) > 1:
            # Skip if LogicGateway already reranked (Neural Scalpel active)
            if (
                hasattr(self.fusion_strategy, "gateway")
                and self.fusion_strategy.gateway.reranker
            ):
                return fused_results[:limit]

            reranker = self._reranker
            if reranker is None and self.embedding_provider and self.memory_storage:
                reranker = EmeraldReranker(self.embedding_provider, self.memory_storage)

            if reranker:
                logger.info("reranking_activated", count=len(fused_results[:20]))
                # SYSTEM 41.1: Use original query for reranking
                return await reranker.rerank(
                    query, fused_results[:20], tenant_id, limit=limit
                )

        return fused_results[:limit]

    def get_available_strategies(self) -> list[str]:
        """Get list of available strategy names."""
        return list(self.strategies.keys())

    async def rerank(
        self,
        query: str,
        candidates: list[tuple[UUID, float]],
        tenant_id: str = "default",
        limit: int = 10,
        **kwargs: Any,
    ) -> list[tuple[UUID, float]]:
        """Rerank candidates using configured reranker."""
        if not self._reranker:
            return candidates[:limit]
        return await self._reranker.rerank(
            query, candidates, tenant_id, limit=limit, **kwargs
        )

    async def search_single_strategy(
        self,
        strategy_name: str,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        use_cache: bool = True,
        **kwargs: Any,
    ) -> list[tuple[UUID, float]]:
        """Search using a single strategy with optional caching."""
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
                return [(r[0], r[1]) for r in cached_result][:limit]

        # Execute strategy
        results = await strategy.search(
            query=query,
            tenant_id=tenant_id,
            filters=filters,
            limit=limit,
            **kwargs,
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

        return [(r[0], r[1]) for r in results][:limit]

    async def search_evidence(
        self,
        query: str,
        tenant_id: str,
        agent_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        enable_reranking: bool = False,
        math_controller: Any = None,
        **kwargs: Any,
    ) -> EvidencePackage:
        """
        Execute search and assemble results into an auditable EvidencePackage.
        Guarantees 100% ID and score parity with search() candidates.
        """
        auto_route = kwargs.get(
            "auto_route",
            os.getenv("RAE_QUERY_ROUTING_ENABLED", "false").lower()
            in ("1", "true", "yes", "on"),
        )
        routing_plan: RoutingPlan | None = None
        if auto_route and strategies is None:
            available = list(self.strategies.keys())
            routing_plan = self.router.route(query, available_strategies=available)
            active_strategies = routing_plan.active_strategies
            if strategy_weights is None:
                strategy_weights = routing_plan.strategy_weights
        else:
            active_strategies = strategies or list(self.strategies.keys())

        candidates = await self.search(
            query=query,
            tenant_id=tenant_id,
            agent_id=agent_id,
            filters=filters,
            limit=limit,
            strategies=active_strategies,
            strategy_weights=strategy_weights,
            enable_reranking=enable_reranking,
            math_controller=math_controller,
            **kwargs,
        )

        items: list[EvidenceItem] = []

        candidate_ids = [c[0] for c in candidates if len(c) > 0]
        memory_map: dict[UUID, Any] = {}

        if candidate_ids and hasattr(self.memory_storage, "get_memories_batch"):
            try:
                mems = await self.memory_storage.get_memories_batch(
                    candidate_ids, tenant_id
                )
                for mem in mems:
                    m_id = (
                        mem.get("id")
                        if isinstance(mem, dict)
                        else getattr(mem, "id", None)
                    )
                    if m_id:
                        if isinstance(m_id, str):
                            try:
                                m_id = UUID(m_id)
                            except ValueError:
                                pass
                        memory_map[m_id] = mem
            except Exception as e:
                logger.warning("evidence_batch_fetch_failed", error=str(e))

        for cand in candidates:
            m_id = cand[0]
            m_uid: UUID | None = None
            if isinstance(m_id, UUID):
                m_uid = m_id
            elif isinstance(m_id, str):
                try:
                    m_uid = UUID(m_id)
                except ValueError:
                    pass

            score = float(cand[1]) if len(cand) > 1 else 0.0
            mem_data = memory_map.get(m_uid) if m_uid else None

            content = ""
            envelope = None
            trust_score = 1.0

            if isinstance(mem_data, dict):
                content = mem_data.get("content", "")
                envelope = mem_data.get("envelope")
                trust_score = mem_data.get("importance", 1.0)
            elif mem_data is not None:
                content = getattr(mem_data, "content", "")
                envelope = getattr(mem_data, "envelope", None)
                trust_score = getattr(mem_data, "importance", 1.0)

            item = EvidenceItem.from_memory_and_score(
                memory_id=m_id,
                content=content,
                score=score,
                strategy="hybrid_fused",
                trust_score=trust_score,
                envelope=envelope,
            )
            items.append(item)

        avg_score = (
            float(sum(i.relevance_score for i in items) / len(items)) if items else 0.0
        )

        package = EvidencePackage(
            query=query,
            tenant_id=tenant_id,
            items=items,
            strategies_used=active_strategies,
            confidence_score=avg_score,
        )

        # Iteration 3: Evidence Sufficiency Gate evaluation
        gate = EvidenceSufficiencyGate()
        assessment = gate.evaluate(package)
        package.metadata["sufficiency_assessment"] = assessment.model_dump()
        package.confidence_score = assessment.composite_score
        package.missing_aspects = assessment.missing_aspects

        if routing_plan:
            package.metadata["routing_plan"] = routing_plan.model_dump()

        return package


class NoiseAwareSearchEngine(HybridSearchEngine):
    """Noise-aware search engine that adjusts retrieval based on noise level.

    Under high noise conditions (>0.5), this engine:
    1. Boosts weight of recent memories (recency bias)
    2. Boosts weight of high-confidence memories
    3. Reduces influence of potentially corrupted older data
    """

    def __init__(
        self,
        strategies: dict[str, SearchStrategy],
        embedding_provider: IEmbeddingProvider | None = None,
        memory_storage: IMemoryStorage | None = None,
        reranker: IReranker | None = None,
        graph_store: Any | None = None,
        math_controller: Any | None = None,
        noise_threshold: float = 0.5,
        recency_boost_factor: float = 1.5,
        confidence_boost_factor: float = 1.3,
    ):
        super().__init__(
            strategies=strategies,
            embedding_provider=embedding_provider,
            memory_storage=memory_storage,
            reranker=reranker,
            graph_store=graph_store,
            math_controller=math_controller,
        )
        self.noise_threshold = noise_threshold
        self.recency_boost_factor = recency_boost_factor
        self.confidence_boost_factor = confidence_boost_factor

    def _apply_noise_aware_boost(
        self,
        results: list[tuple[UUID, float, float]],
        memory_metadata: dict[UUID, dict[str, Any]],
        noise_level: float,
    ) -> list[tuple[UUID, float, float]]:
        if noise_level <= self.noise_threshold:
            return results

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        boosted_results = []

        for item in results:
            m_id, original_score, importance = self._unpack_candidate(item)
            metadata = memory_metadata.get(m_id, {})

            created_at = metadata.get("created_at")
            recency_boost = 0.0
            if created_at:
                if isinstance(created_at, str):
                    try:
                        created_at = datetime.fromisoformat(created_at)
                    except ValueError:
                        created_at = None
                if created_at:
                    age_days = (now - created_at).days
                    recency_boost = 1.0 / (1.0 + age_days / 7.0)

            confidence = metadata.get("confidence_score", 0.5)
            confidence_boost = confidence

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

            boosted_score = (
                original_score * final_recency_boost * final_confidence_boost
            )
            boosted_results.append((m_id, boosted_score, importance))

        boosted_results.sort(key=lambda x: x[1], reverse=True)
        return boosted_results

    async def search(
        self,
        query: str,
        tenant_id: str,
        agent_id: str | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        strategies: list[str] | None = None,
        strategy_weights: dict[str, float] | None = None,
        enable_reranking: bool = False,
        math_controller: Any = None,
        noise_level: float = 0.0,
        memory_metadata: dict[UUID, dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> list[tuple[UUID, float, float]]:
        base_results = await super().search(
            query=query,
            tenant_id=tenant_id,
            agent_id=agent_id,
            filters=filters,
            limit=limit * 2,
            strategies=strategies,
            strategy_weights=strategy_weights,
            enable_reranking=enable_reranking,
            math_controller=math_controller,
            **kwargs,
        )

        if memory_metadata and noise_level > 0.0:
            boosted_results = self._apply_noise_aware_boost(
                results=base_results,
                memory_metadata=memory_metadata,
                noise_level=noise_level,
            )
            return boosted_results[:limit]

        return base_results[:limit]
