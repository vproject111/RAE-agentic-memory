"""
RAE API - High-Level API Methods

This module provides high-level convenience methods for interacting with
the RAE Memory API, wrapping the enhanced RAE client.

All API modules are accessible:
- Memories
- Reflections
- Semantic Memory
- Graph Operations
- Hybrid Search
- Evaluation
- Event Triggers
- Dashboard
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from apps.memory_api.clients.rae_client import RAEClient

logger = structlog.get_logger(__name__)


class RAEAPIClient:
    """
    High-level RAE API client.

    Provides convenient methods for all RAE API operations.
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        **client_kwargs,
    ):
        """
        Initialize RAE API client.

        Args:
            base_url: Base URL for RAE API
            api_key: API key for authentication
            tenant_id: Default tenant ID
            project_id: Default project ID
            **client_kwargs: Additional arguments for RAEClient
        """
        self.client = RAEClient(
            base_url=base_url,
            api_key=api_key,
            tenant_id=tenant_id,
            project_id=project_id,
            **client_kwargs,
        )

        self.tenant_id = tenant_id
        self.project_id = project_id

        logger.info(
            "rae_api_client_initialized",
            base_url=base_url,
            tenant_id=tenant_id,
            project_id=project_id,
        )

    async def close(self):
        """Close client."""
        await self.client.close()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    # ========================================================================
    # Memory Operations
    # ========================================================================

    async def create_memory(
        self,
        content: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new memory.

        Args:
            content: Memory content
            importance: Importance score (0.0-1.0)
            tags: Optional tags
            metadata: Optional metadata
            tenant_id: Tenant ID override
            project_id: Project ID override

        Returns:
            Created memory
        """
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project": project_id or self.project_id,
            "content": content,
            "importance": importance,
            "tags": tags or [],
            "metadata": metadata or {},
        }

        return await self.client.post("/v1/memories", json_data=data)

    async def get_memory(self, memory_id: UUID) -> Dict[str, Any]:
        """Get memory by ID."""
        return await self.client.get(f"/v1/memories/{memory_id}")

    async def search_memories(
        self,
        query: str,
        k: int = 10,
        filters: Optional[Dict] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search memories.

        Args:
            query: Search query
            k: Number of results
            filters: Optional filters
            tenant_id: Tenant ID override
            project_id: Project ID override

        Returns:
            Search results
        """
        params = {
            "tenant_id": tenant_id or self.tenant_id,
            "project": project_id or self.project_id,
            "query": query,
            "k": k,
        }

        if filters:
            params.update(filters)

        return await self.client.get("/v1/memories/search", params=params)

    # ========================================================================
    # Reflection Operations
    # ========================================================================

    async def generate_reflection(
        self,
        memory_ids: Optional[List[UUID]] = None,
        cluster_id: Optional[str] = None,
        reflection_type: str = "insight",
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate reflection from memories.

        Args:
            memory_ids: Memory IDs to reflect on
            cluster_id: Cluster ID to reflect on
            reflection_type: Type of reflection
            tenant_id: Tenant ID override
            project_id: Project ID override

        Returns:
            Generated reflection
        """
        data: Dict[str, Any] = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "reflection_type": reflection_type,
        }

        if memory_ids:
            data["memory_ids"] = [str(mid) for mid in memory_ids]

        if cluster_id:
            data["cluster_id"] = cluster_id

        return await self.client.post("/v1/reflections/generate", json_data=data)

    async def get_reflection(self, reflection_id: UUID) -> Dict[str, Any]:
        """Get reflection by ID."""
        return await self.client.get(f"/v1/reflections/{reflection_id}")

    async def list_reflections(
        self,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List reflections."""
        params = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "limit": limit,
        }

        return await self.client.get("/v1/reflections", params=params)

    # ========================================================================
    # Semantic Memory Operations
    # ========================================================================

    async def extract_semantics(
        self,
        memory_id: UUID,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract semantic nodes from memory.

        Args:
            memory_id: Memory ID
            tenant_id: Tenant ID override
            project_id: Project ID override

        Returns:
            Extraction result
        """
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "memory_id": str(memory_id),
        }

        return await self.client.post("/v1/semantic/extract", json_data=data)

    async def semantic_search(
        self,
        query: str,
        k: int = 10,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        3-stage semantic search.

        Args:
            query: Search query
            k: Number of results
            tenant_id: Tenant ID override
            project_id: Project ID override

        Returns:
            Search results
        """
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "query": query,
            "k": k,
        }

        return await self.client.post("/v1/semantic/search", json_data=data)

    # ========================================================================
    # Graph Operations
    # ========================================================================

    async def create_graph_node(
        self,
        node_id: str,
        label: str,
        node_type: str,
        properties: Optional[Dict] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        **DEPRECATED - ENDPOINT DOES NOT EXIST**

        This method calls POST /v1/graph/nodes which was never implemented.

        RAE uses GraphRAG for knowledge graph management, which automatically
        extracts entities and relationships from memories.

        **Use instead:**
        - `extract_knowledge_graph()` - Automatic entity/relation extraction
        - `get_graph_nodes()` - Read existing nodes
        - `query_graph()` - Hybrid search with graph traversal

        See docs/graphrag_guide.md for details.
        """
        raise NotImplementedError(
            "POST /v1/graph/nodes endpoint does not exist. "
            "Use extract_knowledge_graph() for automatic graph construction, "
            "or get_graph_nodes() to read existing nodes. "
            "See docs/graphrag_guide.md for GraphRAG usage."
        )

    async def create_graph_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        relation_type: str,
        weight: float = 1.0,
        confidence: float = 0.8,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        **DEPRECATED - ENDPOINT DOES NOT EXIST**

        This method calls POST /v1/graph/edges which was never implemented.

        RAE uses GraphRAG for knowledge graph management, which automatically
        extracts relationships from memories.

        **Use instead:**
        - `extract_knowledge_graph()` - Automatic entity/relation extraction
        - `get_graph_edges()` - Read existing edges
        - `query_graph()` - Hybrid search with graph traversal

        See docs/graphrag_guide.md for details.
        """
        raise NotImplementedError(
            "POST /v1/graph/edges endpoint does not exist. "
            "Use extract_knowledge_graph() for automatic graph construction, "
            "or get_graph_edges() to read existing edges. "
            "See docs/graphrag_guide.md for GraphRAG usage."
        )

    async def traverse_graph(
        self,
        start_node_id: str,
        algorithm: str = "bfs",
        max_depth: int = 3,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        **DEPRECATED - ENDPOINT DOES NOT EXIST**

        This method calls POST /v1/graph/traverse which was never implemented.

        RAE uses GraphRAG for knowledge graph traversal integrated with
        semantic search.

        **Use instead:**
        - `query_graph()` - Hybrid search with automatic graph traversal
        - `get_subgraph()` - Extract subgraph from specific nodes

        See docs/graphrag_guide.md for details.
        """
        raise NotImplementedError(
            "POST /v1/graph/traverse endpoint does not exist. "
            "Use query_graph() for hybrid search with graph traversal, "
            "or get_subgraph() to extract subgraphs. "
            "See docs/graphrag_guide.md for GraphRAG usage."
        )

    # ========================================================================
    # Hybrid Search Operations
    # ========================================================================

    async def hybrid_search(
        self,
        query: str,
        k: int = 10,
        weight_profile: str = "balanced",
        enable_reranking: bool = True,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Hybrid multi-strategy search.

        Args:
            query: Search query
            k: Number of results
            weight_profile: Weight profile (balanced, quality_focused, speed_focused)
            enable_reranking: Enable LLM re-ranking
            tenant_id: Tenant ID override
            project_id: Project ID override

        Returns:
            Search results
        """
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "query": query,
            "k": k,
            "weight_profile": weight_profile,
            "enable_reranking": enable_reranking,
        }

        return await self.client.post("/v1/search/hybrid", json_data=data)

    async def analyze_query(
        self, query: str, context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze query intent.

        Args:
            query: Query to analyze
            context: Optional context

        Returns:
            Query analysis
        """
        data = {"query": query, "context": context or []}

        return await self.client.post("/v1/search/analyze", json_data=data)

    # ========================================================================
    # Evaluation Operations
    # ========================================================================

    async def evaluate_search(
        self,
        relevance_judgments: Dict,
        search_results: Dict,
        metrics: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate search results."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "relevance_judgments": relevance_judgments,
            "search_results": search_results,
            "metrics_to_compute": metrics or ["mrr", "ndcg", "precision", "recall"],
        }

        return await self.client.post("/v1/evaluation/search", json_data=data)

    async def detect_drift(
        self,
        metric_name: str,
        drift_type: str,
        baseline_start: datetime,
        baseline_end: datetime,
        current_start: datetime,
        current_end: datetime,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Detect distribution drift."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "metric_name": metric_name,
            "drift_type": drift_type,
            "baseline_start": baseline_start.isoformat(),
            "baseline_end": baseline_end.isoformat(),
            "current_start": current_start.isoformat(),
            "current_end": current_end.isoformat(),
        }

        return await self.client.post("/v1/evaluation/drift/detect", json_data=data)

    # ========================================================================
    # Event Trigger Operations
    # ========================================================================

    async def create_trigger(
        self,
        rule_name: str,
        event_types: List[str],
        actions: List[Dict],
        condition_group: Optional[Dict] = None,
        priority: int = 5,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        created_by: str = "api_client",
    ) -> Dict[str, Any]:
        """Create event trigger."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "rule_name": rule_name,
            "condition": {
                "event_types": event_types,
                "condition_group": condition_group,
            },
            "actions": actions,
            "priority": priority,
            "created_by": created_by,
        }

        return await self.client.post("/v1/triggers/create", json_data=data)

    async def emit_event(
        self,
        event_type: str,
        payload: Dict,
        tags: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Emit custom event."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "event_type": event_type,
            "payload": payload,
            "tags": tags or [],
        }

        return await self.client.post("/v1/triggers/events/emit", json_data=data)

    async def list_triggers(
        self,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """List triggers."""
        params = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "limit": limit,
        }

        return await self.client.get("/v1/triggers/list", params=params)

    # ========================================================================
    # Dashboard Operations
    # ========================================================================

    async def get_dashboard_metrics(
        self,
        period: str = "last_24h",
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get dashboard metrics."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "period": period,
        }

        return await self.client.post("/v1/dashboard/metrics", json_data=data)

    async def get_visualization(
        self,
        visualization_type: str,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Get visualization data."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "visualization_type": visualization_type,
            **kwargs,
        }

        return await self.client.post("/v1/dashboard/visualizations", json_data=data)

    async def get_system_health(
        self,
        tenant_id: Optional[str] = None,
        project_id: Optional[str] = None,
        include_sub_components: bool = True,
    ) -> Dict[str, Any]:
        """Get system health."""
        data = {
            "tenant_id": tenant_id or self.tenant_id,
            "project_id": project_id or self.project_id,
            "include_sub_components": include_sub_components,
        }

        return await self.client.post("/v1/dashboard/health", json_data=data)

    # ========================================================================
    # Client Management
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return self.client.get_stats()

    def reset_stats(self):
        """Reset statistics."""
        self.client.reset_stats()

    def invalidate_cache(
        self, method: Optional[str] = None, path: Optional[str] = None
    ):
        """Invalidate cache."""
        self.client.invalidate_cache(method, path)
