"""Memory retrieval delegate for RAECoreService."""

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import UUID

import structlog

from rae_core.models.evidence_package import EvidencePackage
from rae_core.models.search import SearchResponse, SearchResult, SearchStrategy

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class MemoryRetrievalDelegate:
    """Handles multi-strategy retrieval, hybrid querying, and evidence assembly."""

    def __init__(self, service: "RAECoreService"):
        self.service = service

    async def get_memory(
        self, memory_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
        try:
            mem_uuid = UUID(memory_id)
        except ValueError:
            return None

        return await self.service.postgres_adapter.get_memory(mem_uuid, tenant_id)

    async def list_memories(
        self,
        tenant_id: str,
        layer: Optional[str] = None,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List memories for a specific layer and project (agent)."""
        return await self.service.postgres_adapter.list_memories(
            tenant_id=tenant_id,
            agent_id=agent_id,
            project=project,
            layer=layer,
            tags=tags,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    async def count_memories(
        self,
        tenant_id: str,
        layer: str,
        project: str,
        agent_id: str | None = None,
    ) -> int:
        """Count memories for a layer and project."""
        return cast(
            int,
            await self.service.postgres_adapter.count_memories(
                tenant_id=tenant_id, agent_id=agent_id, layer=layer
            ),
        )

    async def query_memories(
        self,
        tenant_id: str,
        project: str,
        query: str,
        k: int = 10,
        layers: Optional[list] = None,
        filters: Optional[dict] = None,
    ) -> SearchResponse:
        """Query memories across layers with dynamic weights."""
        start_time = time.time()

        weights = None
        if self.service.tuning_service:
            try:
                weights = await self.service.tuning_service.get_current_weights(
                    str(tenant_id)
                )
            except Exception as e:
                logger.warning("failed_to_get_tuning_weights", error=str(e))

        if self.service.szubar_mode:
            from rae_core.math.structure import ScoringWeights

            weights = ScoringWeights.szubar_profile()
            logger.debug("using_szubar_weights_for_query")

        target_layer = (layers[0] if layers else None) or (filters or {}).get("layer")
        raw_results = await self.service.engine.search_memories(
            query=query,
            tenant_id=str(tenant_id),
            agent_id="default",
            project=project,
            layer=target_layer,
            top_k=k,
            filters=filters,
            custom_weights=weights,
        )

        results_list = []
        for res in raw_results:
            metadata_val = res.get("metadata", {})
            if isinstance(metadata_val, str):
                try:
                    import json

                    metadata_val = json.loads(metadata_val)
                except Exception:
                    metadata_val = {}

            raw_score = (
                res.get("math_score")
                if res.get("math_score") is not None
                else res.get("search_score", 0.0)
            )
            safe_score = max(0.0, float(raw_score))

            results_list.append(
                SearchResult(
                    memory_id=str(res.get("id")),
                    content=res.get("content", ""),
                    human_label=res.get("human_label"),
                    score=safe_score,
                    strategy_used=SearchStrategy.HYBRID,
                    metadata=metadata_val,
                )
            )

        return SearchResponse(
            results=results_list,
            query=query,
            strategy=SearchStrategy.HYBRID,
            total_found=len(results_list),
            execution_time_ms=(time.time() - start_time) * 1000,
        )

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        project: Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 10,
        enable_reranking: bool = False,
        filters: Optional[dict] = None,
        auto_route: bool = False,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search memories across layers using RAE Core Engine."""
        weights = None
        if self.service.tuning_service:
            try:
                weights = await self.service.tuning_service.get_current_weights(
                    str(tenant_id)
                )
            except Exception as e:
                logger.warning("failed_to_get_tuning_weights", error=str(e))

        if self.service.szubar_mode:
            from rae_core.math.structure import ScoringWeights

            weights = ScoringWeights.szubar_profile()

        return await self.service.engine.search_memories(
            query=query,
            tenant_id=str(tenant_id),
            agent_id="default",
            project=project,
            layer=layer,
            top_k=limit,
            filters=filters,
            custom_weights=weights,
            enable_reranking=enable_reranking,
            auto_route=auto_route,
            **kwargs,
        )

    async def search_evidence(
        self,
        query: str,
        tenant_id: str = "default",
        project: Optional[str] = None,
        agent_id: Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 10,
        strategies: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        auto_route: bool = False,
        enable_reranking: bool = False,
        force_2pass: bool = False,
        filters: Optional[dict] = None,
        **kwargs: Any,
    ) -> EvidencePackage:
        """Search memories across layers returning an auditable EvidencePackage."""
        weights: Any = custom_weights
        if not weights and self.service.tuning_service:
            try:
                weights = await self.service.tuning_service.get_current_weights(
                    str(tenant_id)
                )
            except Exception as e:
                logger.warning("failed_to_get_tuning_weights", error=str(e))

        if not weights and self.service.szubar_mode:
            from rae_core.math.structure import ScoringWeights

            weights = ScoringWeights.szubar_profile()

        return cast(
            EvidencePackage,
            await self.service.engine.search_evidence(
                query=query,
                tenant_id=str(tenant_id),
                project=project,
                agent_id=agent_id or "default",
                layer=layer,
                limit=limit,
                strategies=strategies,
                strategy_weights=weights,
                filters=filters,
                auto_route=auto_route,
                enable_reranking=enable_reranking,
                force_2pass=force_2pass,
                **kwargs,
            ),
        )

    async def get_session_context(
        self,
        session_id: str,
        tenant_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve all memories associated with a specific session."""
        sql = """
            SELECT *
            FROM memories
            WHERE tenant_id = $1
                AND session_id = $2
            ORDER BY timestamp ASC
            LIMIT $3
        """
        records = await self.service.db.fetch(sql, tenant_id, session_id, limit)
        return [dict(r) for r in records]

    async def list_memories_for_graph_extraction(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List memories that are pending graph extraction."""
        records = await self.service.db.fetch(
            """
            SELECT DISTINCT tenant_id, ARRAY_AGG(id) as memory_ids
            FROM memories m
            WHERE layer = 'episodic'
                AND NOT EXISTS (
                    SELECT 1 FROM knowledge_graph_edges ke
                    WHERE ke.tenant_id = m.tenant_id
                    AND (ke.source_node_id IN (SELECT id FROM knowledge_graph_nodes WHERE node_id = m.id::text)
                            OR ke.target_node_id IN (SELECT id FROM knowledge_graph_nodes WHERE node_id = m.id::text))
                )
            GROUP BY tenant_id
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in records]
