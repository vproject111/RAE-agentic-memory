"""
Community Detection and Summarization - Pillar 2: Wisdom.

Implements:
- Community Detection (Leiden/Louvain via networkx/community)
- Community Summarization (LLM)
- Super-Node Creation
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

import networkx as nx
import structlog
from pydantic import BaseModel, Field

from apps.memory_api.config import settings
from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.llm import get_llm_provider
from apps.memory_api.services.rae_core_service import RAECoreService

try:  # pragma: no cover - import guarded
    import community.community_louvain as community_louvain

    COMMUNITY_DETECTION_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    community_louvain = None  # type: ignore[assignment]
    COMMUNITY_DETECTION_AVAILABLE = False

if TYPE_CHECKING:  # poprawne typy dla mypy
    import community.community_louvain as _cl  # noqa: F401

logger = structlog.get_logger(__name__)


class CommunitySummary(BaseModel):
    summary: str = Field(
        ...,
        description="A high-level synthesis of the information contained in the community.",
    )
    themes: List[str] = Field(
        ..., description="Key themes or topics in this community."
    )
    title: str = Field(..., description="A short title for this community/cluster.")


class CommunityDetectionService:
    def __init__(
        self,
        rae_service: "RAECoreService",
        graph_repository: Optional[GraphRepository] = None,
    ):
        self.rae_service = rae_service
        self.pool = rae_service.postgres_pool
        self.graph_repo = graph_repository or GraphRepository(self.pool)
        self.llm_provider = get_llm_provider()

    def _ensure_available(self) -> None:
        """Ensure community detection library is available."""
        if not COMMUNITY_DETECTION_AVAILABLE:
            raise RuntimeError(
                "Community detection requires 'python-louvain' "
                "(`pip install python-louvain`)."
            )

    async def run_community_detection_and_summarization(
        self, project_id: str, tenant_id: str
    ):
        """
        1. Load Graph from DB.
        2. Run Community Detection (Louvain).
        3. For each community, generate summary.
        4. Store summary as 'Super-Node'.
        """
        self._ensure_available()
        logger.info(
            "starting_community_detection", project_id=project_id, tenant_id=tenant_id
        )

        # 1. Load Graph
        graph = await self._load_graph_from_db(project_id, tenant_id)
        if len(graph.nodes) < 5:
            logger.info("graph_too_small_for_communities", node_count=len(graph.nodes))
            return

        # 2. Detect Communities
        # Using Louvain algorithm for community detection
        # Partition is a dict: {node: community_id}
        partition = community_louvain.best_partition(graph)

        # Group nodes by community
        communities: Dict[int, List[Any]] = {}
        for node, community_id in partition.items():
            if community_id not in communities:
                communities[community_id] = []
            communities[community_id].append(node)

        logger.info("communities_detected", count=len(communities))

        # 3. & 4. Summarize and Store
        for community_id, node_ids in communities.items():
            # Only process communities of a certain size
            if len(node_ids) < 3:
                continue

            await self._process_community(
                community_id, node_ids, graph, project_id, tenant_id
            )

    async def _process_community(
        self,
        community_id: int,
        node_ids: List[Any],
        graph: nx.Graph,
        project_id: str,
        tenant_id: str,
    ):
        # Gather information about the community
        # Nodes and their immediate edges/relationships within the community
        nodes_info = []
        for node_id in node_ids:
            # We used internal DB IDs for graph nodes, but we need labels for LLM
            # Let's assume graph nodes are keyed by 'label' or we have a mapping.
            # In _load_graph_from_db, I will set node 'label' attribute.
            label = graph.nodes[node_id].get("label", str(node_id))
            nodes_info.append(label)

        # Get edges inside the community
        edges_info = []
        subgraph = graph.subgraph(node_ids)
        for u, v, data in subgraph.edges(data=True):
            u_label = graph.nodes[u].get("label", str(u))
            v_label = graph.nodes[v].get("label", str(v))
            relation = data.get("relation", "RELATED_TO")
            edges_info.append(f"{u_label} --[{relation}]--> {v_label}")

        description = f"Nodes: {', '.join(nodes_info)}\nRelationships:\n{chr(10).join(edges_info[:50])}"  # Limit edges to fit context

        # Generate Summary
        summary = await self._generate_summary(description)

        # Store as Super-Node
        await self._store_super_node(
            community_id, summary, node_ids, project_id, tenant_id
        )

    async def _generate_summary(self, description: str) -> CommunitySummary:
        prompt = f"""
        Analyze the following community of entities and relationships from a knowledge graph:

        {description}

        Synthesize this information into a high-level summary.
        Instead of listing facts, generalize them.
        Example: Instead of "User likes sushi", "User likes ramen", say "User prefers Japanese cuisine".

        Provide a Title, a Summary, and a list of Key Themes.
        """

        try:
            # Use the "Sage" model (Synthesis Model)
            result = await self.llm_provider.generate_structured(
                system="You are a Wisdom Engine responsible for synthesizing knowledge.",
                prompt=prompt,
                model=settings.SYNTHESIS_MODEL,
                response_model=CommunitySummary,
            )
            return cast(CommunitySummary, result)
        except Exception as e:
            logger.error("community_summarization_failed", error=str(e))
            return CommunitySummary(
                summary="Extraction failed", themes=[], title="Unknown Community"
            )

    async def _store_super_node(
        self,
        community_id: int,
        summary: CommunitySummary,
        member_node_ids: List[int],
        project_id: str,
        tenant_id: str,
    ):
        """
        Store the summary as a special community super-node using repository pattern.

        Args:
            community_id: Community identifier
            summary: Summary generated by LLM
            member_node_ids: List of member node IDs in this community
            project_id: Project identifier
            tenant_id: Tenant identifier
        """
        node_label = f"Community: {summary.title}"
        properties = {
            "type": "community",
            "summary": summary.summary,
            "themes": summary.themes,
            "community_id": community_id,
            "member_count": len(member_node_ids),
        }

        # Create unique node_id for super-node
        super_node_id = f"community_{project_id}_{community_id}"

        # Use repository upsert (insert or update)
        internal_id = await self.graph_repo.upsert_node(
            tenant_id=tenant_id,
            project_id=project_id,
            node_id=super_node_id,
            label=node_label,
            properties=properties,
        )

        logger.info(
            "super_node_stored",
            community_id=community_id,
            internal_id=internal_id,
            member_count=len(member_node_ids),
        )

    async def _load_graph_from_db(self, project_id: str, tenant_id: str) -> nx.Graph:
        """
        Load knowledge graph from database into NetworkX Graph using repository pattern.

        Args:
            project_id: Project identifier
            tenant_id: Tenant identifier

        Returns:
            NetworkX Graph with nodes and edges
        """
        G = nx.Graph()

        # Load nodes using repository
        nodes = await self.graph_repo.get_all_nodes(
            tenant_id=tenant_id, project_id=project_id
        )

        for node in nodes:
            G.add_node(node["id"], label=node["label"])

        # Load edges using repository
        edges = await self.graph_repo.get_all_edges(
            tenant_id=tenant_id, project_id=project_id
        )

        for edge in edges:
            source_id = edge["source_node_id"]
            target_id = edge["target_node_id"]
            if G.has_node(source_id) and G.has_node(target_id):
                G.add_edge(source_id, target_id, relation=edge["relation"])

        logger.info(
            "graph_loaded_from_db",
            project_id=project_id,
            nodes_count=len(G.nodes),
            edges_count=len(G.edges),
        )

        return G
