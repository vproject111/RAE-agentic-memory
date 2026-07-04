"""
Entity Resolution Service - Orchestrates deduplication and merging of knowledge graph nodes.

Implements Pillar 1 of the optimization plan:
- Semantic Clustering (delegated to ML Service)
- Janitor Agent (LLM-based conflict resolution)
- Database merging operations

This service orchestrates the resolution process while delegating
heavy ML operations to the ML microservice.
"""

from typing import Dict, List, Optional, cast

import structlog
from pydantic import BaseModel, Field

from apps.memory_api.config import settings
from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.llm import get_llm_provider
from apps.memory_api.services.ml_service_client import MLServiceClient
from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


class MergeDecision(BaseModel):
    should_merge: bool = Field(
        ...,
        description="Whether the entities represent the same concept and should be merged.",
    )
    canonical_name: str = Field(
        ..., description="The canonical name to use for the merged entity."
    )
    reasoning: str = Field(..., description="Reasoning for the decision.")


class EntityResolutionService:
    """
    Orchestrator for entity resolution process.

    Coordinates between ML Service (clustering), LLM (janitor decisions),
    and database (merging operations).
    """

    def __init__(
        self,
        rae_service: "RAECoreService",
        ml_client: Optional[MLServiceClient] = None,
        graph_repository: Optional[GraphRepository] = None,
    ):
        self.rae_service = rae_service
        self.pool = rae_service.postgres_pool
        self.graph_repo = graph_repository or GraphRepository(self.pool)
        self.llm_provider = get_llm_provider()
        self.ml_client = ml_client or MLServiceClient()
        self.similarity_threshold_high = 0.95
        self.similarity_threshold_low = 0.85

    async def run_clustering_and_merging(self, project_id: str, tenant_id: str):
        """
        Main entry point for entity resolution.

        Process:
        1. Fetch all nodes for the project from database
        2. Call ML Service for clustering
        3. Process each cluster (auto-merge or ask LLM)
        4. Execute merges in database
        """
        logger.info(
            "starting_entity_resolution", project_id=project_id, tenant_id=tenant_id
        )

        # Fetch nodes from database
        nodes = await self._fetch_nodes(project_id, tenant_id)
        if len(nodes) < 2:
            logger.info("not_enough_nodes_for_clustering", count=len(nodes))
            return

        # Call ML Service for clustering
        try:
            result = await self.ml_client.resolve_entities(
                nodes=[{"id": str(n["id"]), "label": n["label"]} for n in nodes],
                similarity_threshold=self.similarity_threshold_low,
            )

            merge_groups = result.get("merge_groups", [])
            statistics = result.get("statistics", {})

            logger.info(
                "ml_service_clustering_completed",
                groups_found=len(merge_groups),
                statistics=statistics,
            )

        except Exception as e:
            logger.exception("ml_service_clustering_failed", error=str(e))
            return

        # Process each merge group
        for group_ids in merge_groups:
            # Find nodes in this group
            group_nodes = [n for n in nodes if str(n["id"]) in group_ids]

            if len(group_nodes) < 2:
                continue

            await self._process_group(group_nodes, project_id, tenant_id)

    async def _process_group(self, nodes: List[Dict], project_id: str, tenant_id: str):
        """
        Process a group of similar nodes.

        For high similarity (>0.95): auto-merge
        For medium similarity (0.85-0.95): ask Janitor Agent
        """
        names = [n["label"] for n in nodes]

        # For now, we'll ask the Janitor Agent for all groups
        # In future, we could get similarity scores from ML service to auto-merge high confidence groups
        logger.info("asking_janitor_agent", names=names)

        decision = await self._ask_janitor(names)

        if decision.should_merge:
            logger.info(
                "janitor_approved_merge", names=names, canonical=decision.canonical_name
            )
            await self._merge_nodes(
                nodes, project_id, tenant_id, canonical_name=decision.canonical_name
            )
        else:
            logger.info(
                "janitor_rejected_merge", names=names, reason=decision.reasoning
            )

    async def _ask_janitor(self, names: List[str]) -> MergeDecision:
        prompt = f"""
        Analyze the following list of entity names from a knowledge graph:
        {names}

        Decide if these entities refer to the exact same concept/thing and should be merged.
        Examples:
        - "Apple Inc." and "Apple Company" -> Merge (True)
        - "Java" (island) and "Java" (language) -> Do NOT Merge (False)
        - "Jan Kowalski" and "Jan K." -> Likely Merge (True) if context supports it, but here assume Yes if it looks obvious.

        If they should be merged, choose the best canonical name (e.g. the most complete or formal one).
        """

        try:
            result = await self.llm_provider.generate_structured(
                system="You are the 'Janitor Agent' responsible for data quality in a knowledge graph.",
                prompt=prompt,
                model=settings.EXTRACTION_MODEL,  # Cheap model
                response_model=MergeDecision,
            )
            return cast(MergeDecision, result)
        except Exception as e:
            logger.error("janitor_agent_failed", error=str(e))
            # Default to not merging if unsure
            return MergeDecision(
                should_merge=False, canonical_name="", reasoning="Error"
            )

    async def _merge_nodes(
        self,
        nodes: List[Dict],
        project_id: str,
        tenant_id: str,
        canonical_name: Optional[str] = None,
    ):
        """
        Merges multiple nodes into one using repository pattern.

        Process:
        1. Pick a target node (or rename if canonical name provided)
        2. Update target node label if needed
        3. Move edges from source nodes to target node
        4. Delete source nodes

        Args:
            nodes: List of nodes to merge
            project_id: Project identifier
            tenant_id: Tenant identifier
            canonical_name: Optional canonical name for merged entity
        """
        if not nodes:
            return

        # Pick target node: The one with the canonical name if present, or the first one,
        # or the one with longest label (heuristic)
        if canonical_name:
            # Find if any node already has this name
            target_node = next((n for n in nodes if n["label"] == canonical_name), None)
            if not target_node:
                # Rename the first node
                target_node = nodes[0]
                # Update label using repository
                await self.graph_repo.update_node_label(
                    node_internal_id=target_node["id"], new_label=canonical_name
                )
                target_node["label"] = canonical_name  # Update local reference
        else:
            # Heuristic: longest name is usually more descriptive
            target_node = max(nodes, key=lambda n: len(n["label"]))

        sources = [n for n in nodes if n["id"] != target_node["id"]]

        # Process each source node
        for source in sources:
            # Move edges from source to target using repository
            await self.graph_repo.merge_node_edges(
                source_node_id=source["id"], target_node_id=target_node["id"]
            )

            # Delete remaining edges (handles duplicates that couldn't be moved)
            await self.graph_repo.delete_node_edges(node_internal_id=source["id"])

            # Delete source node
            await self.graph_repo.delete_node(node_internal_id=source["id"])

        logger.info(
            "nodes_merged",
            target=target_node["label"],
            merged_count=len(sources),
            target_id=target_node["id"],
        )

    async def _fetch_nodes(self, project_id: str, tenant_id: str) -> List[Dict]:
        """
        Fetch all nodes for a project using repository pattern.

        Args:
            project_id: Project identifier
            tenant_id: Tenant identifier

        Returns:
            List of node dictionaries
        """
        return await self.graph_repo.get_all_nodes(
            tenant_id=tenant_id, project_id=project_id
        )
