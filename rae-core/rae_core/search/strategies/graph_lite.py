"""Autonomous GraphRAG-lite retrieval strategy with automated seed expansion."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from rae_core.interfaces.graph import IGraphStore
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.search.strategies import SearchStrategy

logger = structlog.get_logger(__name__)


class GraphLiteStrategy(SearchStrategy):
    """
    Autonomous GraphRAG-lite search strategy.
    Extracts seeds automatically from an initial candidate strategy (e.g. Vector or FullText)
    or explicitly passed seeds, then performs bounded BFS graph expansion up to max_depth=2.
    """

    def __init__(
        self,
        graph_store: IGraphStore,
        memory_storage: IMemoryStorage | None = None,
        seed_strategy: SearchStrategy | None = None,
        default_weight: float = 0.5,
        max_depth: int = 2,
        max_nodes_per_seed: int = 15,
        min_edge_weight: float = 0.4,
    ) -> None:
        self.graph_store = graph_store
        self.memory_storage = memory_storage
        self.seed_strategy = seed_strategy
        self.default_weight = default_weight
        self.max_depth = min(max_depth, 2)  # Enforce combinatorial limit
        self.max_nodes_per_seed = max_nodes_per_seed
        self.min_edge_weight = min_edge_weight

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
        project: str | None = None,
        **kwargs: Any,
    ) -> list[tuple[UUID, float, float]]:
        """
        Execute autonomous BFS expansion starting from explicit seeds or auto-discovered seeds.
        """
        search_filters = filters or {}
        raw_seeds = kwargs.get("seed_ids") or search_filters.get("seed_ids")
        edge_type = kwargs.get("edge_type") or search_filters.get("edge_type")

        seeds: list[UUID] = []

        # 1. Parse provided seeds if present
        if raw_seeds:
            for sid in raw_seeds:
                if isinstance(sid, str):
                    try:
                        seeds.append(UUID(sid))
                    except ValueError:
                        continue
                elif isinstance(sid, UUID):
                    seeds.append(sid)

        # 2. Autonomous seed discovery if seeds are empty
        if not seeds and self.seed_strategy:
            try:
                candidate_results = await self.seed_strategy.search(
                    query=query,
                    tenant_id=tenant_id,
                    filters=filters,
                    limit=3,
                    project=project,
                    **kwargs,
                )
                for cand in candidate_results:
                    if cand and len(cand) > 0:
                        cand_id = cand[0]
                        if isinstance(cand_id, UUID):
                            seeds.append(cand_id)
                        elif isinstance(cand_id, str):
                            try:
                                seeds.append(UUID(cand_id))
                            except ValueError:
                                pass
            except Exception as e:
                logger.warning("graph_lite_seed_discovery_failed", error=str(e))

        if not seeds:
            return []

        # Limit to top 3 seeds to prevent wide fan-out
        seeds = seeds[:3]

        # 3. Bounded BFS Traversal
        visited = set(seeds)
        to_visit = list(seeds)
        node_scores: dict[UUID, float] = {}
        depth = 0

        while to_visit and depth < self.max_depth:
            current_layer = to_visit
            to_visit = []
            depth += 1
            decay = 1.0 / depth

            for seed_node in current_layer:
                try:
                    neighbors = await self.graph_store.get_neighbors(
                        seed_node,
                        tenant_id=tenant_id,
                        edge_type=edge_type,
                    )
                except Exception as e:
                    logger.warning(
                        "graph_lite_get_neighbors_failed",
                        node=seed_node,
                        error=str(e),
                    )
                    continue

                # Cap expansion per node to max_nodes_per_seed
                expanded_count = 0
                for neighbor_id in neighbors:
                    if expanded_count >= self.max_nodes_per_seed:
                        break

                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        to_visit.append(neighbor_id)
                        expanded_count += 1

                    # Multi-path accumulation: nodes reached via multiple paths receive higher score
                    node_scores[neighbor_id] = node_scores.get(neighbor_id, 0.0) + (
                        0.5 * decay
                    )

        # Rank expanded nodes by accumulated score
        ranked = sorted(node_scores.items(), key=lambda x: x[1], reverse=True)[:limit]
        return [(m_id, min(1.0, score), 0.0) for m_id, score in ranked]

    def get_strategy_name(self) -> str:
        return "graph_lite"

    def get_strategy_weight(self) -> float:
        return self.default_weight
