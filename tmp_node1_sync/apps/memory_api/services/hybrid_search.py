"""
Hybrid Search Service - Enterprise-grade search combining vector similarity and graph traversal.

This module implements advanced hybrid search capabilities that merge:
- Vector similarity search (semantic search)
- Knowledge graph traversal (relationship-based discovery)
- Context synthesis (merging results into coherent context)
- Relevance reranking (scoring combined results)

This approach provides richer, more contextual search results by leveraging
both the semantic similarity of content and the structural relationships
between entities in the knowledge graph.
"""

from typing import Any, Dict, List, Optional, Tuple, cast

import structlog
from pydantic import BaseModel, Field

from apps.memory_api.models import ScoredMemoryRecord
from apps.memory_api.models.graph import GraphEdge, GraphNode, TraversalStrategy
from apps.memory_api.repositories.graph_repository import GraphRepository
from apps.memory_api.services.embedding import get_embedding_service
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.vector_store import get_vector_store

logger = structlog.get_logger(__name__)


class HybridSearchResult(BaseModel):
    """Complete result from hybrid search operation."""

    vector_matches: List[ScoredMemoryRecord] = Field(
        default_factory=list, description="Results from vector similarity search"
    )
    graph_nodes: List[GraphNode] = Field(
        default_factory=list, description="Nodes discovered via graph traversal"
    )
    graph_edges: List[GraphEdge] = Field(
        default_factory=list, description="Edges discovered via graph traversal"
    )
    synthesized_context: str = Field(
        default="", description="Merged context from all sources"
    )
    graph_enabled: bool = Field(
        default=False, description="Whether graph traversal was enabled for this search"
    )
    statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Search statistics"
    )


class HybridSearchService:
    """
    Enterprise-grade hybrid search service.

    Combines vector similarity search with knowledge graph traversal to provide
    comprehensive, context-rich search results.

    Features:
    - Configurable search strategies
    - Multiple traversal algorithms (BFS/DFS)
    - Context synthesis from multiple sources
    - Performance metrics and logging
    - Relevance scoring
    - Full Dependency Injection for testability
    """

    def __init__(
        self,
        rae_service: RAECoreService,
        graph_repo: Optional[GraphRepository] = None,
    ):
        """
        Initialize hybrid search service.

        Args:
            rae_service: RAECoreService instance
            graph_repo: Optional GraphRepository instance
        """
        self.rae_service = rae_service
        self.pool = rae_service.postgres_pool
        self.graph_repository = graph_repo or GraphRepository(self.pool)
        self.embedding_service = get_embedding_service()

    async def search(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        top_k_vector: int = 5,
        graph_depth: int = 2,
        traversal_strategy: TraversalStrategy = TraversalStrategy.BFS,
        use_graph: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        use_information_bottleneck: bool = False,  # NEW: Enable IB-based context selection
        beta: float = 1.0,  # NEW: IB trade-off parameter
    ) -> HybridSearchResult:
        """
        Perform hybrid search combining vector similarity and graph traversal.

        Process:
        1. Vector search - find semantically similar memories
        2. Map memories to graph nodes
        3. Graph traversal - discover related entities
        4. Context synthesis - merge all information
        5. Relevance ranking - score and order results

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            project_id: Project identifier
            top_k_vector: Number of vector search results (default: 5)
            graph_depth: Maximum graph traversal depth (default: 2)
            traversal_strategy: BFS or DFS traversal (default: BFS)
            use_graph: Enable graph traversal (default: True)
            filters: Optional filters for vector search

        Returns:
            HybridSearchResult with vector matches, graph data, and synthesized context

        Raises:
            RuntimeError: If search operation fails
        """
        logger.info(
            "hybrid_search_started",
            tenant_id=tenant_id,
            project_id=project_id,
            query_length=len(query),
            use_graph=use_graph,
        )

        # Initialize RAE state before search (MDP formulation: s_t)
        from apps.memory_api.core.state import BudgetState, GraphState, RAEState

        initial_state = RAEState(
            tenant_id=tenant_id,
            project_id=project_id,
            budget_state=BudgetState(
                remaining_tokens=100000,  # Default budget
                remaining_cost_usd=10.0,
                latency_budget_ms=30000,
                calls_remaining=100,
            ),
        )

        logger.info("hybrid_search_state_initialized", state=initial_state.to_dict())

        try:
            # Phase 1: Vector similarity search
            vector_results = await self._vector_search(
                query=query,
                tenant_id=tenant_id,
                project_id=project_id,
                top_k=top_k_vector,
                filters=filters,
            )

            logger.info("vector_search_completed", results_count=len(vector_results))

            # NEW: Information Bottleneck-based context selection (Iteration 4)
            if use_information_bottleneck and vector_results:
                import numpy as np

                from apps.memory_api.core.information_bottleneck import (
                    InformationBottleneckSelector,
                    MemoryItem,
                )

                logger.info(
                    "ib_selection_enabled",
                    beta=beta,
                    full_results_count=len(vector_results),
                )

                # Generate query embedding
                query_embedding = (
                    await self.embedding_service.generate_embeddings_async([query])
                )
                query_emb = np.array(query_embedding[0])

                # Convert vector results to MemoryItem format
                memory_items = []
                for result in vector_results:
                    # Get embedding (if available)
                    embedding = (
                        np.array(result.embedding)
                        if hasattr(result, "embedding") and result.embedding
                        else np.zeros(384)
                    )

                    memory_item = MemoryItem(
                        id=str(result.id),
                        content=result.content,
                        embedding=embedding,
                        importance=(
                            float(result.score) if hasattr(result, "score") else 0.7
                        ),
                        layer=result.layer if hasattr(result, "layer") else "episodic",
                        tokens=len(result.content) // 4,  # Rough token estimate
                        metadata=result.metadata if hasattr(result, "metadata") else {},
                    )
                    memory_items.append(memory_item)

                # Apply Information Bottleneck selection
                ib_selector = InformationBottleneckSelector(beta=beta)
                selected_memories = ib_selector.select_context(
                    query=query,
                    query_embedding=query_emb,
                    full_memory=memory_items,
                    max_tokens=4000,
                )

                # Convert back to ScoredMemoryRecord format
                selected_ids = {m.id for m in selected_memories}
                vector_results = [
                    r for r in vector_results if str(r.id) in selected_ids
                ]

                logger.info(
                    "ib_selection_completed",
                    full_count=len(memory_items),
                    selected_count=len(selected_memories),
                    compression_ratio=(
                        len(selected_memories) / len(memory_items)
                        if memory_items
                        else 0.0
                    ),
                )

            # If graph traversal disabled, return vector results only
            if not use_graph:
                synthesized = self._synthesize_vector_only(vector_results)
                return HybridSearchResult(
                    vector_matches=vector_results,
                    synthesized_context=synthesized,
                    graph_enabled=False,
                    statistics={"vector_results": len(vector_results)},
                )

            # Phase 2: Map vector results to graph nodes
            start_node_ids = await self._map_memories_to_nodes(
                memory_results=vector_results,
                tenant_id=tenant_id,
                project_id=project_id,
            )

            logger.info("mapped_to_graph_nodes", start_nodes_count=len(start_node_ids))

            # If no graph nodes found, return vector results only
            if not start_node_ids:
                synthesized = self._synthesize_vector_only(vector_results)
                return HybridSearchResult(
                    vector_matches=vector_results,
                    synthesized_context=synthesized,
                    graph_enabled=True,
                    statistics={
                        "vector_results": len(vector_results),
                        "graph_nodes_found": 0,
                    },
                )

            # Phase 3: Graph traversal
            graph_nodes, graph_edges = await self._traverse_graph(
                start_node_ids=start_node_ids,
                tenant_id=tenant_id,
                project_id=project_id,
                depth=graph_depth,
                strategy=traversal_strategy,
            )

            logger.info(
                "graph_traversal_completed",
                nodes_discovered=len(graph_nodes),
                edges_discovered=len(graph_edges),
            )

            # Phase 4: Context synthesis
            synthesized_context = await self._synthesize_context(
                vector_results=vector_results,
                graph_nodes=graph_nodes,
                graph_edges=graph_edges,
                query=query,
            )

            # Phase 5: Compile statistics
            statistics = {
                "vector_results": len(vector_results),
                "graph_nodes": len(graph_nodes),
                "graph_edges": len(graph_edges),
                "graph_depth": graph_depth,
                "traversal_strategy": traversal_strategy.value,
                "context_length": len(synthesized_context),
            }

            logger.info(
                "hybrid_search_completed",
                tenant_id=tenant_id,
                project_id=project_id,
                statistics=statistics,
            )

            # Update RAE state after search completes (MDP formulation: s_{t+1})
            final_state = RAEState(
                tenant_id=tenant_id,
                project_id=project_id,
                budget_state=BudgetState(
                    # Context tokens used (approximation)
                    remaining_tokens=initial_state.budget_state.remaining_tokens
                    - int(statistics.get("context_length", 0)),
                    # No direct LLM cost in search
                    remaining_cost_usd=initial_state.budget_state.remaining_cost_usd,
                    latency_budget_ms=initial_state.budget_state.latency_budget_ms,
                    calls_remaining=initial_state.budget_state.calls_remaining,
                ),
                graph_state=GraphState(
                    node_count=len(graph_nodes),
                    edge_count=len(graph_edges),
                    connected_components=1,  # TODO: compute from graph
                ),
            )

            # Log state transition (Δs = s_{t+1} - s_t)
            state_delta = final_state.compare(initial_state)
            logger.info(
                "hybrid_search_state_transition",
                tenant_id=tenant_id,
                state_delta=state_delta,
            )

            return HybridSearchResult(
                vector_matches=vector_results,
                graph_nodes=graph_nodes,
                graph_edges=graph_edges,
                synthesized_context=synthesized_context,
                graph_enabled=True,
                statistics=statistics,
            )

        except Exception as e:
            logger.exception(
                "hybrid_search_failed",
                tenant_id=tenant_id,
                project_id=project_id,
                error=str(e),
            )
            raise RuntimeError(f"Hybrid search failed: {e}")

    async def _vector_search(
        self,
        query: str,
        tenant_id: str,
        project_id: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[ScoredMemoryRecord]:
        """
        Perform vector similarity search.
        Supports Multi-Vector Fusion (OpenAI + Ollama) if configured.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            project_id: Project identifier
            top_k: Number of results
            filters: Optional search filters

        Returns:
            List of scored memory records
        """
        from apps.memory_api.config import settings
        from rae_core.math.fusion import reciprocal_rank_fusion

        # Build filters
        query_filters = {
            "must": [
                {"key": "tenant_id", "match": {"value": tenant_id}},
                {"key": "project", "match": {"value": project_id}},
            ]
        }

        if filters:
            for key, value in filters.items():
                if key == "tags" and isinstance(value, list):
                    query_filters["must"].append(
                        {"key": "tags", "match": {"any": value}}
                    )

        vector_store = get_vector_store(pool=self.pool)

        # Check active models for Multi-Vector Fusion
        active_searches = []

        # 1. OpenAI (1536 dim)
        if settings.OPENAI_API_KEY:
            active_searches.append(
                {
                    "name": "openai",
                    "model": "text-embedding-3-small",
                    "vector_name": "openai",
                }
            )

        # 2. Ollama (384 dim - or configured local)
        # Always try local/ollama as fallback or secondary
        active_searches.append(
            {
                "name": "ollama",
                "model": (
                    "ollama/all-minilm"
                    if settings.RAE_LLM_BACKEND == "ollama"
                    else "ollama/nomic-embed-text"
                ),
                "vector_name": "ollama",
            }
        )

        # If we have multiple models, execute parallel search
        import asyncio

        search_tasks = []

        for search_cfg in active_searches:
            search_tasks.append(
                self._execute_single_vector_search(
                    vector_store,
                    query,
                    search_cfg["model"],
                    search_cfg["vector_name"],
                    top_k * 2,  # Fetch more for fusion
                    query_filters,
                )
            )

        # Execute all searches
        results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Convert to format for RRF: List[Tuple[UUID, float]]
        rrf_inputs = []
        record_map = {}  # ID -> MemoryRecord

        for i, res in enumerate(results_lists):
            if isinstance(res, BaseException) or not res:
                if isinstance(res, BaseException):
                    logger.warning(f"Vector search strategy {i} failed: {res}")
                continue

            # Mypy now knows res is a list due to the check above (mostly)
            # but safer to cast for strict mode
            from typing import cast

            results = cast(List[ScoredMemoryRecord], res)

            # Process results for this strategy
            strategy_ranked_list = []
            for record in results:
                # Assuming record is ScoredMemoryRecord
                strategy_ranked_list.append((record.id, record.score))
                record_map[str(record.id)] = record

            rrf_inputs.append(strategy_ranked_list)

        if not rrf_inputs:
            logger.warning("All vector searches failed or returned empty.")
            return []

        # Fuse results
        fused_ranked = reciprocal_rank_fusion(rrf_inputs)

        # Reconstruct ScoredMemoryRecords
        final_results = []
        for uuid_id, rrf_score in fused_ranked[:top_k]:
            str_id = str(uuid_id)
            if str_id in record_map:
                rec = record_map[str_id]
                # Update score to RRF score (or keep original? RRF score is safer for ranking)
                # But RRF score is small (0.02 range). We might want to normalize.
                # For now, let's use the RRF score.
                rec.score = rrf_score
                rec.source = "multi_vector_fusion"
                final_results.append(rec)

        # --- Pillar 2 Implementation: Hybrid Search with Super-Nodes ---
        # Search specifically for "community" nodes (Super-Nodes) in the graph
        # that might be relevant to the query.
        # This is a basic implementation that text-matches the query against super-node labels/summaries.
        # Ideally, Super-Nodes should also have vector embeddings in a separate collection or marked index.
        # For now, we search for them using SQL fuzzy match or just append them if found in the vector results
        # (if vector store indexes graph nodes too).

        # Assumption: "Super-Nodes" are stored in knowledge_graph_nodes with type='community'.
        # We perform a side-query to DB to find relevant communities.

        # Note: This is an additive search step.
        relevant_communities = await self._find_relevant_communities(
            query, tenant_id, project_id
        )

        # Create synthetic memory records for these communities so they are included in the synthesis
        for comm in relevant_communities:
            # Check if this community is already in results (unlikely if vector store doesn't index them)
            # Create a high-scoring record
            synthetic_record = ScoredMemoryRecord(
                id=str(comm["id"]),
                content=f"COMMUNITY WISDOM: {comm['label']}. Summary: {comm['properties'].get('summary', '')}",
                score=0.95,  # Give high priority to wisdom
                source="community_wisdom",
                tags=["wisdom", "community"],
                metadata=comm["properties"],
            )
            # Prepend to results
            final_results.insert(0, synthetic_record)

        return final_results

    async def _execute_single_vector_search(
        self,
        vector_store: Any,
        query: str,
        model_name: str,
        vector_name: str,
        top_k: int,
        filters: Dict,
    ) -> List[ScoredMemoryRecord]:
        """Helper to execute a single vector search safely."""
        try:
            # Generate embedding
            embeddings = await self.embedding_service.generate_embeddings_for_model(
                [query], model_name
            )
            query_embedding = embeddings[0]

            # Check for zero embedding (failed)
            if all(v == 0.0 for v in query_embedding):
                return []

            # Query store
            # Check if vector_store supports vector_name (QdrantStore does)
            # We use a safer check that handles Mocks and real objects
            supports_vector_name = False
            if hasattr(vector_store, "query"):
                import inspect

                try:
                    sig = inspect.signature(vector_store.query)
                    supports_vector_name = "vector_name" in sig.parameters
                except (ValueError, TypeError):
                    # Fallback for objects that don't support signature (some C extensions or mocks)
                    # For mocks, we assume they can handle the parameter if configured
                    from unittest.mock import Mock

                    if isinstance(vector_store.query, Mock):
                        supports_vector_name = True

            if supports_vector_name:
                result = await vector_store.query(
                    query_embedding, top_k, filters, vector_name=vector_name
                )
                return cast(List[ScoredMemoryRecord], result)
            else:
                # Fallback for stores that don't support vector_name (e.g. PGVector)
                # Only use if this is the "default" or primary search
                if vector_name in [
                    "dense",
                    "default",
                    "ollama",
                ]:  # Assuming simple stores use default
                    result = await vector_store.query(query_embedding, top_k, filters)
                    return cast(List[ScoredMemoryRecord], result)
                return []
        except Exception as e:
            logger.warning(f"Single vector search failed for {vector_name}: {e}")
            return []

    async def _find_relevant_communities(
        self, query: str, tenant_id: str, project_id: str
    ) -> List[Dict]:
        """
        Find community nodes relevant to the query.

        Delegates to GraphRepository for database access.
        """
        return await self.graph_repository.find_relevant_communities(
            query=query, tenant_id=tenant_id, project_id=project_id, limit=3
        )

    async def _map_memories_to_nodes(
        self, memory_results: List[ScoredMemoryRecord], tenant_id: str, project_id: str
    ) -> List[str]:
        """
        Map memory content to knowledge graph nodes.

        This attempts to find graph nodes that correspond to the
        content of retrieved memories by matching entity names.

        Delegates to GraphRepository for database access.

        Args:
            memory_results: Vector search results
            tenant_id: Tenant identifier
            project_id: Project identifier

        Returns:
            List of node IDs to use as traversal starting points
        """
        if not memory_results:
            return []

        # Find nodes linked to these memories through content matching
        node_ids = []

        for memory in memory_results:
            # Look for nodes that match entities mentioned in the memory
            matched_nodes = await self.graph_repository.find_nodes_by_content_match(
                content=memory.content,
                tenant_id=tenant_id,
                project_id=project_id,
                limit=5,
            )
            node_ids.extend(matched_nodes)

        # Return unique node IDs
        return list(set(node_ids))

    async def _traverse_graph(
        self,
        start_node_ids: List[str],
        tenant_id: str,
        project_id: str,
        depth: int,
        strategy: TraversalStrategy,
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Traverse the knowledge graph starting from given nodes.

        Delegates to GraphRepository for actual graph traversal operations.

        Args:
            start_node_ids: Starting node IDs
            tenant_id: Tenant identifier
            project_id: Project identifier
            depth: Maximum traversal depth
            strategy: Traversal strategy (BFS or DFS)

        Returns:
            Tuple of (discovered nodes, discovered edges)
        """
        if strategy == TraversalStrategy.BFS:
            return await self.graph_repository.traverse_graph_bfs(
                start_node_ids, tenant_id, project_id, depth
            )
        else:
            return await self.graph_repository.traverse_graph_dfs(
                start_node_ids, tenant_id, project_id, depth
            )

    async def _synthesize_context(
        self,
        vector_results: List[ScoredMemoryRecord],
        graph_nodes: List[GraphNode],
        graph_edges: List[GraphEdge],
        query: str,
    ) -> str:
        """
        Synthesize unified context from vector and graph results.

        Args:
            vector_results: Vector search results
            graph_nodes: Discovered graph nodes
            graph_edges: Discovered graph edges
            query: Original search query

        Returns:
            Synthesized context string
        """
        context_parts = []

        # Section 1: Query context
        context_parts.append(f"# Search Query\n{query}\n")

        # Section 2: Vector search results
        if vector_results:
            context_parts.append("# Relevant Memories (Vector Search)\n")
            for i, result in enumerate(vector_results, 1):
                context_parts.append(
                    f"{i}. [Score: {result.score:.3f}] {result.content}\n"
                    f"   Source: {result.source} | Tags: {', '.join(result.tags or [])}\n"
                )

        # Section 3: Knowledge graph context
        if graph_nodes:
            context_parts.append("\n# Related Entities (Knowledge Graph)\n")

            # Group nodes by depth
            nodes_by_depth: Dict[int, List[GraphNode]] = {}
            for node in graph_nodes:
                depth = node.depth
                if depth not in nodes_by_depth:
                    nodes_by_depth[depth] = []
                nodes_by_depth[depth].append(node)

            for depth in sorted(nodes_by_depth.keys()):
                context_parts.append(f"\nDepth {depth}:\n")
                for node in nodes_by_depth[depth]:
                    context_parts.append(f"  - {node.label}\n")

        # Section 4: Relationships
        if graph_edges:
            context_parts.append("\n# Relationships\n")

            # Group edges by relation type
            edges_by_relation: Dict[str, List[GraphEdge]] = {}
            for edge in graph_edges:
                relation = edge.relation
                if relation not in edges_by_relation:
                    edges_by_relation[relation] = []
                edges_by_relation[relation].append(edge)

            for relation, edges in edges_by_relation.items():
                context_parts.append(f"\n{relation}:\n")
                for edge in edges[:10]:  # Limit to 10 per relation
                    # Find node labels
                    source_node = next(
                        (n for n in graph_nodes if n.id == edge.source_id), None
                    )
                    target_node = next(
                        (n for n in graph_nodes if n.id == edge.target_id), None
                    )

                    if source_node and target_node:
                        context_parts.append(
                            f"  {source_node.label} → {target_node.label}\n"
                        )

        return "\n".join(context_parts)

    def _synthesize_vector_only(self, vector_results: List[ScoredMemoryRecord]) -> str:
        """
        Synthesize context from vector results only.

        Args:
            vector_results: Vector search results

        Returns:
            Synthesized context string
        """
        if not vector_results:
            return "No results found."

        context_parts = ["# Search Results\n"]

        for i, result in enumerate(vector_results, 1):
            context_parts.append(
                f"{i}. [Score: {result.score:.3f}] {result.content}\n"
                f"   Source: {result.source} | Tags: {', '.join(result.tags or [])}\n"
            )

        return "\n".join(context_parts)
