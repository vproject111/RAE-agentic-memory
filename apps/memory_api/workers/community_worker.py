"""Autonomous worker for knowledge graph community detection and reflective synthesis."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import structlog

from apps.memory_api.models.reflection_models import (
    SynthesizeCommunitiesResponse,
    SynthesizedCommunityItem,
)
from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.graph.community_detector import CommunityDetector, GraphCommunity
from rae_core.models.graph import EdgeType, GraphEdge
from rae_core.reflection.community_summarizer import CommunitySummarizer
from rae_core.types.enums import MemoryLayer

logger = structlog.get_logger(__name__)


class CommunitySynthesisWorker:
    """
    Autonomous worker for detecting graph communities and synthesizing
    reflective memories into MemoryLayer.REFLECTIVE.
    """

    def __init__(
        self,
        rae_service: RAECoreService,
        min_community_size: int = 3,
    ):
        self.rae_service = rae_service
        self.min_community_size = min_community_size
        self.detector = CommunityDetector(min_community_size=min_community_size)
        self.summarizer = CommunitySummarizer()

    async def fetch_graph_data(self, tenant_id: str, project: str) -> tuple[
        list[UUID],
        list[GraphEdge],
        dict[UUID, dict[str, Any]],
        dict[UUID, str],
        dict[UUID, str],
    ]:
        """
        Fetch graph nodes and edges for the given tenant and project.
        """
        nodes: list[UUID] = []
        edges: list[GraphEdge] = []
        node_properties: dict[UUID, dict[str, Any]] = {}
        node_contents: dict[UUID, str] = {}
        node_labels: dict[UUID, str] = {}

        raw_nodes: list[dict[str, Any]] = []
        raw_edges: list[dict[str, Any]] = []

        # 1. Try graph repository if available
        graph_repo = getattr(self.rae_service, "enhanced_graph_repo", None)
        if (
            not graph_repo
            and hasattr(self.rae_service, "postgres_pool")
            and self.rae_service.postgres_pool
        ):
            from apps.memory_api.repositories.graph_repository import GraphRepository

            graph_repo = GraphRepository(self.rae_service.postgres_pool)

        if (
            graph_repo
            and hasattr(graph_repo, "get_all_nodes")
            and hasattr(graph_repo, "get_all_edges")
        ):
            try:
                raw_nodes = await graph_repo.get_all_nodes(tenant_id, project)
                raw_edges = await graph_repo.get_all_edges(tenant_id, project)
            except Exception as e:
                logger.warning("failed_to_fetch_graph_from_repo", error=str(e))

        # 2. Map raw nodes into UUIDs
        node_id_to_uuid: dict[str, UUID] = {}
        for rn in raw_nodes:
            nid_val = rn.get("id") or rn.get("node_id")
            if not nid_val:
                continue
            try:
                n_uuid = UUID(str(nid_val))
            except ValueError:
                n_uuid = uuid4()
            node_id_to_uuid[str(rn.get("node_id", nid_val))] = n_uuid
            node_id_to_uuid[str(nid_val)] = n_uuid
            nodes.append(n_uuid)

            props = rn.get("properties") or {}
            node_properties[n_uuid] = props
            node_labels[n_uuid] = rn.get("label") or str(rn.get("node_id", ""))
            node_contents[n_uuid] = (
                props.get("content") or rn.get("label") or str(n_uuid)
            )

        # 3. Map raw edges into GraphEdge
        for re in raw_edges:
            src_str = str(re.get("source_node_id", ""))
            tgt_str = str(re.get("target_node_id", ""))
            src_uuid = node_id_to_uuid.get(src_str)
            tgt_uuid = node_id_to_uuid.get(tgt_str)
            if not src_uuid or not tgt_uuid:
                continue
            rel_str = str(re.get("relation", "relates_to")).lower()
            try:
                edge_type = EdgeType(rel_str)
            except ValueError:
                edge_type = EdgeType.RELATES_TO

            props = re.get("properties") or {}
            weight = float(props.get("weight", 1.0) if isinstance(props, dict) else 1.0)
            edges.append(
                GraphEdge(
                    source_id=src_uuid,
                    target_id=tgt_uuid,
                    edge_type=edge_type,
                    weight=weight,
                    tenant_id=tenant_id,
                )
            )

        return nodes, edges, node_properties, node_contents, node_labels

    async def run_synthesis(
        self,
        tenant_id: str = "default",
        project: str = "default",
        custom_nodes: list[UUID] | None = None,
        custom_edges: list[GraphEdge] | None = None,
        custom_node_contents: dict[UUID, str] | None = None,
        custom_node_labels: dict[UUID, str] | None = None,
        custom_node_props: dict[UUID, dict[str, Any]] | None = None,
    ) -> SynthesizeCommunitiesResponse:
        """
        Execute community detection and synthesize reflective memories into RAE.
        """
        if custom_nodes is not None and custom_edges is not None:
            nodes = custom_nodes
            edges = custom_edges
            node_props = custom_node_props or {}
            node_contents = custom_node_contents or {}
            node_labels = custom_node_labels or {}
        else:
            (
                nodes,
                edges,
                node_props,
                node_contents,
                node_labels,
            ) = await self.fetch_graph_data(tenant_id=tenant_id, project=project)

        if not nodes or not edges:
            logger.info(
                "community_synthesis_skipped_no_graph_data",
                tenant_id=tenant_id,
                project=project,
            )
            return SynthesizeCommunitiesResponse(
                synthesized_count=0,
                communities=[],
                message="No graph nodes or edges available for synthesis",
            )

        communities: list[GraphCommunity] = self.detector.detect_communities(
            nodes=nodes,
            edges=edges,
            node_properties=node_props,
        )

        synthesized_items: list[SynthesizedCommunityItem] = []

        for community in communities:
            synthesis = self.summarizer.summarize_community(
                community=community,
                node_contents=node_contents,
                node_labels=node_labels,
            )

            # Store into MemoryLayer.REFLECTIVE
            tags = [
                "community_synthesis",
                f"community:{community.community_id}",
                synthesis.domain,
            ]
            meta = {
                "community_id": community.community_id,
                "domain": synthesis.domain,
                "member_count": len(community.node_ids),
                "key_entities": synthesis.key_entities,
                "density": community.density,
                "synthesized_at": synthesis.synthesized_at.isoformat(),
            }

            memory_id = await self.rae_service.store_memory(
                tenant_id=tenant_id,
                project=project,
                content=synthesis.summary,
                source="community_synthesis_worker",
                importance=0.9,
                tags=tags,
                layer=MemoryLayer.REFLECTIVE.value,
                metadata=meta,
            )

            synthesized_items.append(
                SynthesizedCommunityItem(
                    community_id=community.community_id,
                    domain=synthesis.domain,
                    member_count=len(community.node_ids),
                    memory_id=str(memory_id),
                    summary=synthesis.summary,
                )
            )

        logger.info(
            "community_synthesis_complete",
            tenant_id=tenant_id,
            project=project,
            synthesized_count=len(synthesized_items),
        )

        return SynthesizeCommunitiesResponse(
            synthesized_count=len(synthesized_items),
            communities=synthesized_items,
            message=f"Successfully synthesized {len(synthesized_items)} community reflections",
        )


async def synthesize_tenant_communities(
    rae_service: RAECoreService,
    tenant_id: str = "default",
    project: str = "default",
    min_community_size: int = 3,
) -> SynthesizeCommunitiesResponse:
    """Convenience functional wrapper for community synthesis."""
    worker = CommunitySynthesisWorker(
        rae_service=rae_service, min_community_size=min_community_size
    )
    return await worker.run_synthesis(tenant_id=tenant_id, project=project)
