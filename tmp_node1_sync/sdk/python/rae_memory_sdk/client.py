from typing import Any, Dict, List, Optional, cast

import httpx
import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

from .models import (
    DeleteMemoryResponse,
    QueryMemoryRequest,
    QueryMemoryResponse,
    StoreMemoryRequest,
    StoreMemoryResponse,
)

logger = structlog.get_logger(__name__)


class RAEClientConfig(BaseSettings):
    """
    Configuration settings for the RAE Memory Client.
    """

    RAE_API_URL: str = "http://localhost:8000"
    RAE_API_KEY: str = "your-rae-api-key"
    RAE_TENANT_ID: str = "default-tenant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields from .env file
    )


class MemoryClient:
    """
    Enterprise-grade client for interacting with the RAE Memory API.

    Supports both synchronous and asynchronous operations.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant_id: Optional[str] = None,
        session_id: Optional[str] = None,
        config: Optional[RAEClientConfig] = None,
    ):
        if config:
            self.config = config
        else:
            self.config = RAEClientConfig(
                RAE_API_URL=api_url or RAEClientConfig().RAE_API_URL,
                RAE_API_KEY=api_key or RAEClientConfig().RAE_API_KEY,
                RAE_TENANT_ID=tenant_id or RAEClientConfig().RAE_TENANT_ID,
            )

        self.session_id = session_id
        self._http_client = httpx.Client(base_url=self.config.RAE_API_URL)
        self._async_http_client = httpx.AsyncClient(base_url=self.config.RAE_API_URL)
        self._headers = {
            "X-API-Key": self.config.RAE_API_KEY,
            "X-Tenant-Id": self.config.RAE_TENANT_ID,
            "Content-Type": "application/json",
        }
        if self.session_id:
            self._headers["X-Session-Id"] = self.session_id

    def _request(self, method: str, url: str, **kwargs) -> Any:
        """Synchronous HTTP request wrapper."""
        try:
            response = self._http_client.request(
                method, url, headers=self._headers, **kwargs
            )
            response.raise_for_status()
            return cast(Any, response.json())
        except httpx.HTTPStatusError as e:
            logger.error(
                "http_error",
                url=url,
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except httpx.RequestError as e:
            logger.error("request_error", url=url, error=str(e))
            raise

    async def _async_request(self, method: str, url: str, **kwargs) -> Any:
        """Asynchronous HTTP request wrapper."""
        try:
            response = await self._async_http_client.request(
                method, url, headers=self._headers, **kwargs
            )
            response.raise_for_status()
            return cast(Any, response.json())
        except httpx.HTTPStatusError as e:
            logger.error(
                "async_http_error",
                url=url,
                status_code=e.response.status_code,
                response_text=e.response.text,
            )
            raise
        except httpx.RequestError as e:
            logger.error("async_request_error", url=url, error=str(e))
            raise

    def store(self, memory: StoreMemoryRequest) -> StoreMemoryResponse:
        """
        Stores a new memory record.
        """
        if not memory.session_id and self.session_id:
            memory.session_id = self.session_id

        response_data = self._request(
            "POST", "/memory/store", json=memory.model_dump(exclude_none=True)
        )
        return StoreMemoryResponse(**response_data)

    def query(
        self, query_text: str, k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> QueryMemoryResponse:
        """
        Queries the memory for relevant records.
        """
        request_body = QueryMemoryRequest(query_text=query_text, k=k, filters=filters)
        response_data = self._request(
            "POST", "/memory/query", json=request_body.model_dump(exclude_none=True)
        )
        return QueryMemoryResponse(**response_data)

    def delete(self, memory_id: str) -> DeleteMemoryResponse:
        """
        Deletes a memory record by its ID.
        """
        response_data = self._request("DELETE", f"/memory/delete?memory_id={memory_id}")
        return DeleteMemoryResponse(**response_data)

    # GraphRAG Methods

    def extract_knowledge_graph(
        self,
        project_id: str,
        limit: int = 50,
        min_confidence: float = 0.5,
        auto_store: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract knowledge graph from episodic memories.

        Args:
            project_id: Project identifier
            limit: Maximum number of memories to process
            min_confidence: Minimum confidence threshold for triples
            auto_store: Whether to automatically store extracted triples

        Returns:
            Dict containing extracted triples, entities, and statistics
        """
        request_body: Dict[str, Any] = {
            "project_id": project_id,
            "limit": limit,
            "min_confidence": min_confidence,
            "auto_store": auto_store,
        }
        return cast(
            Dict[str, Any],
            self._request("POST", "/v1/graph/extract", json=request_body),
        )

    def query_graph(
        self,
        project_id: str,
        query: str,
        limit: int = 20,
        similarity_threshold: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Query the knowledge graph for relevant nodes and edges.

        Args:
            project_id: Project identifier
            query: Search query
            limit: Maximum items to return
            similarity_threshold: Minimum similarity for nodes

        Returns:
            Dict with matching nodes and edges
        """
        request_body: Dict[str, Any] = {
            "query": query,
            "project_id": project_id,
            "limit": limit,
            "similarity_threshold": similarity_threshold,
        }
        return cast(
            Dict[str, Any], self._request("POST", "/v1/graph/query", json=request_body)
        )

    def get_graph_stats(self, project_id: str) -> Dict[str, Any]:
        """
        Get knowledge graph statistics.

        Args:
            project_id: Project identifier

        Returns:
            Dict with node/edge counts and distribution
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/graph/stats?project_id={project_id}"),
        )

    def get_graph_nodes(
        self,
        project_id: str,
        limit: int = 100,
        use_pagerank: bool = False,
        min_pagerank_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve graph nodes with optional PageRank filtering.

        Args:
            project_id: Project identifier
            limit: Maximum nodes to return
            use_pagerank: Enable PageRank filtering
            min_pagerank_score: Minimum PageRank threshold

        Returns:
            List of node dictionaries
        """
        params = {
            "project_id": project_id,
            "limit": limit,
            "use_pagerank": use_pagerank,
            "min_pagerank_score": min_pagerank_score,
        }
        return cast(
            List[Dict[str, Any]], self._request("GET", "/v1/graph/nodes", params=params)
        )

    def get_graph_edges(
        self, project_id: str, limit: int = 100, relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve graph edges with optional relation filtering.

        Args:
            project_id: Project identifier
            limit: Maximum edges to return
            relation: Filter by relation type

        Returns:
            List of edge dictionaries
        """
        params = {"project_id": project_id, "limit": limit}
        if relation:
            params["relation"] = relation
        return cast(
            List[Dict[str, Any]], self._request("GET", "/v1/graph/edges", params=params)
        )

    def get_subgraph(
        self, project_id: str, node_ids: List[str], depth: int = 1
    ) -> Dict[str, Any]:
        """
        Retrieve a subgraph starting from specific nodes.

        Args:
            project_id: Project identifier
            node_ids: List of starting node IDs
            depth: Maximum traversal depth

        Returns:
            Dict with nodes, edges, and statistics
        """
        request_body: Dict[str, Any] = {"node_ids": node_ids, "depth": depth}
        return cast(
            Dict[str, Any],
            self._request(
                "POST", f"/v1/graph/subgraph?project_id={project_id}", json=request_body
            ),
        )

    # Agent Methods

    def execute_agent(
        self, tenant_id: str, project: str, prompt: str
    ) -> Dict[str, Any]:
        """
        Execute an AI agent task with full memory retrieval and context management.

        This orchestrates:
        1. Retrieval of cached semantic & reflective context
        2. Vector search for episodic memories
        3. Reranking of retrieved memories
        4. LLM inference with full context
        5. Automatic reflection generation
        6. Cost tracking

        Args:
            tenant_id: Tenant identifier
            project: Project identifier
            prompt: Agent task prompt

        Returns:
            Dict with answer, used_memories, and cost breakdown
        """
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project": project,
            "prompt": prompt,
        }
        return cast(
            Dict[str, Any],
            self._request("POST", "/v1/agent/execute", json=request_body),
        )

    # Governance Methods

    def get_governance_overview(self, days: int = 30) -> Dict[str, Any]:
        """
        Get system-wide governance overview (admin only).

        Args:
            days: Number of days to analyze

        Returns:
            Dict with cross-tenant governance metrics
        """
        return cast(
            Dict[str, Any], self._request("GET", f"/v1/governance/overview?days={days}")
        )

    def get_tenant_governance(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get comprehensive governance statistics for a tenant.

        Args:
            tenant_id: Tenant identifier
            days: Number of days to analyze

        Returns:
            Dict with tenant-specific metrics
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/governance/tenant/{tenant_id}?days={days}"),
        )

    def get_tenant_budget(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get current budget status and projections for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Dict with budget limits, current usage, projections, and alerts
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/governance/tenant/{tenant_id}/budget"),
        )

    # ISO/IEC 42001 Compliance Methods

    def request_approval(
        self,
        tenant_id: str,
        project_id: str,
        operation_type: str,
        operation_description: str,
        risk_level: str,
        resource_type: str,
        resource_id: str,
        requested_by: str,
        required_approvers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Request approval for a high-risk operation.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            operation_type: Type of operation (e.g., "delete", "export", "modify")
            operation_description: Human-readable description of the operation
            risk_level: Risk level (none, low, medium, high, critical)
            resource_type: Type of resource being operated on
            resource_id: ID of the resource
            requested_by: User ID who requested the operation
            required_approvers: Optional list of specific approvers required
            metadata: Optional additional metadata

        Returns:
            Dict with request_id, status, risk_level, expires_at, min_approvals
        """
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "operation_type": operation_type,
            "operation_description": operation_description,
            "risk_level": risk_level,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "requested_by": requested_by,
        }
        if required_approvers:
            request_body["required_approvers"] = required_approvers
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            self._request("POST", "/v1/compliance/approvals", json=request_body),
        )

    def check_approval_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check the status of an approval request.

        Args:
            request_id: UUID of the approval request

        Returns:
            Dict with full approval details including status, approvers, and timestamps
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/compliance/approvals/{request_id}"),
        )

    def process_approval_decision(
        self,
        request_id: str,
        approved: bool,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Approve or reject an approval request.

        Args:
            request_id: UUID of the approval request
            approved: True to approve, False to reject
            approver_id: User ID of the approver
            reason: Optional reason for the decision

        Returns:
            Dict with confirmation and updated status
        """
        request_body: Dict[str, Any] = {
            "approved": approved,
            "approver_id": approver_id,
        }
        if reason:
            request_body["reason"] = reason

        return cast(
            Dict[str, Any],
            self._request(
                "POST",
                f"/v1/compliance/approvals/{request_id}/decide",
                json=request_body,
            ),
        )

    def create_decision_context(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        sources: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create decision context for provenance tracking.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Original query that led to the decision
            sources: List of context sources with metadata
            metadata: Optional additional metadata

        Returns:
            Dict with context_id and quality metrics
        """
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "query": query,
            "sources": sources,
        }
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            self._request(
                "POST", "/v1/compliance/provenance/context", json=request_body
            ),
        )

    def record_decision(
        self,
        tenant_id: str,
        project_id: str,
        context_id: str,
        decision: str,
        decision_type: str,
        confidence: float,
        human_approved: bool = False,
        approver_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a decision with full provenance.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            context_id: ID of the decision context
            decision: The decision made
            decision_type: Type of decision (e.g., "classification", "recommendation")
            confidence: Confidence score (0.0 to 1.0)
            human_approved: Whether a human approved this decision
            approver_id: Optional ID of human approver
            metadata: Optional additional metadata

        Returns:
            Dict with decision_id and confirmation
        """
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "context_id": context_id,
            "decision": decision,
            "decision_type": decision_type,
            "confidence": confidence,
            "human_approved": human_approved,
        }
        if approver_id:
            request_body["approver_id"] = approver_id
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            self._request(
                "POST", "/v1/compliance/provenance/decision", json=request_body
            ),
        )

    def get_decision_lineage(self, decision_id: str) -> Dict[str, Any]:
        """
        Get full provenance lineage for a decision.

        Args:
            decision_id: UUID of the decision

        Returns:
            Dict with query, context, sources, and decision details
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/compliance/provenance/lineage/{decision_id}"),
        )

    def get_all_circuit_breakers(self) -> List[Dict[str, Any]]:
        """
        Get status of all circuit breakers.

        Returns:
            List of circuit breaker states with metrics
        """
        return cast(
            List[Dict[str, Any]],
            self._request("GET", "/v1/compliance/circuit-breakers"),
        )

    def get_circuit_breaker_state(self, name: str) -> Dict[str, Any]:
        """
        Get status of a specific circuit breaker.

        Args:
            name: Name of the circuit breaker (e.g., "database", "vector_store", "llm_service")

        Returns:
            Dict with state, failure count, and metrics
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/compliance/circuit-breakers/{name}"),
        )

    def reset_circuit_breaker(self, name: str) -> Dict[str, Any]:
        """
        Reset a circuit breaker (admin only).

        Args:
            name: Name of the circuit breaker to reset

        Returns:
            Dict with confirmation message
        """
        return cast(
            Dict[str, Any],
            self._request("POST", f"/v1/compliance/circuit-breakers/{name}/reset"),
        )

    def list_policies(
        self,
        tenant_id: str,
        policy_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List governance policies.

        Args:
            tenant_id: Tenant identifier
            policy_type: Optional filter by policy type
            status: Optional filter by status

        Returns:
            Dict with policies list
        """
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if policy_type:
            params["policy_type"] = policy_type
        if status:
            params["status"] = status

        return cast(
            Dict[str, Any],
            self._request("GET", "/v1/compliance/policies", params=params),
        )

    def create_policy(
        self,
        tenant_id: str,
        policy_id: str,
        policy_type: str,
        rules: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new governance policy.

        Args:
            tenant_id: Tenant identifier
            policy_id: Unique policy identifier
            policy_type: Type of policy (data_retention, access_control, etc.)
            rules: Policy rules as dict
            created_by: User who created the policy
            description: Optional policy description
            metadata: Optional additional metadata

        Returns:
            Dict with version_id and confirmation
        """
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "policy_id": policy_id,
            "policy_type": policy_type,
            "rules": rules,
            "created_by": created_by,
        }
        if description:
            request_body["description"] = description
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            self._request("POST", "/v1/compliance/policies", json=request_body),
        )

    def activate_policy(
        self, policy_id: str, version_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """
        Activate a policy version.

        Args:
            policy_id: Policy identifier
            version_id: UUID of the version to activate
            tenant_id: Tenant identifier

        Returns:
            Dict with confirmation and updated status
        """
        request_body: Dict[str, Any] = {
            "version_id": version_id,
            "tenant_id": tenant_id,
        }
        return cast(
            Dict[str, Any],
            self._request(
                "POST",
                f"/v1/compliance/policies/{policy_id}/activate",
                json=request_body,
            ),
        )

    def enforce_policy(
        self, policy_id: str, tenant_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enforce a policy against a context.

        Args:
            policy_id: Policy identifier
            tenant_id: Tenant identifier
            context: Context data to check against policy

        Returns:
            Dict with enforcement result, violations, and warnings
        """
        request_body: Dict[str, Any] = {"tenant_id": tenant_id, "context": context}
        return cast(
            Dict[str, Any],
            self._request(
                "POST",
                f"/v1/compliance/policies/{policy_id}/enforce",
                json=request_body,
            ),
        )

    # Reflection Methods

    def rebuild_reflections(self, tenant_id: str, project: str) -> Dict[str, Any]:
        """
        Trigger background task to rebuild reflective memories.

        Args:
            tenant_id: Tenant identifier
            project: Project identifier

        Returns:
            Dict with confirmation message
        """
        request_body: Dict[str, Any] = {"tenant_id": tenant_id, "project": project}
        return cast(
            Dict[str, Any],
            self._request("POST", "/v1/memory/rebuild-reflections", json=request_body),
        )

    def get_reflection_stats(self, project: str) -> Dict[str, Any]:
        """
        Get statistics about reflective memories.

        Args:
            project: Project identifier

        Returns:
            Dict with reflective_memory_count and average_strength
        """
        return cast(
            Dict[str, Any],
            self._request("GET", f"/v1/memory/reflection-stats?project={project}"),
        )

    def generate_hierarchical_reflection(
        self, project: str, bucket_size: int = 10, max_episodes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate hierarchical (map-reduce) reflection from episodes.

        Args:
            project: Project identifier
            bucket_size: Number of episodes per bucket
            max_episodes: Maximum episodes to process

        Returns:
            Dict with summary and statistics
        """
        params: Dict[str, Any] = {"project": project, "bucket_size": bucket_size}
        if max_episodes:
            params["max_episodes"] = max_episodes
        return cast(
            Dict[str, Any],
            self._request("POST", "/v1/memory/reflection/hierarchical", params=params),
        )

    # Health & Cache Methods

    def get_health(self) -> Dict[str, Any]:
        """Get comprehensive health check of all system components."""
        return cast(Dict[str, Any], self._request("GET", "/health"))

    def rebuild_cache(self) -> Dict[str, Any]:
        """Trigger background task to rebuild context cache."""
        return cast(Dict[str, Any], self._request("POST", "/v1/cache/rebuild"))

    # Async methods for non-blocking operations

    async def store_async(self, memory: StoreMemoryRequest) -> StoreMemoryResponse:
        """
        Asynchronously stores a new memory record.

        Args:
            memory: StoreMemoryRequest with memory data

        Returns:
            StoreMemoryResponse with ID and confirmation

        Example:
            ```python
            memory_request = StoreMemoryRequest(
                content="User logged in successfully",
                layer="episodic",
                tags=["auth", "login"]
            )
            response = await client.store_async(memory_request)
            ```
        """
        if not memory.session_id and self.session_id:
            memory.session_id = self.session_id

        response_data = await self._async_request(
            "POST", "/memory/store", json=memory.model_dump(exclude_none=True)
        )
        return StoreMemoryResponse(**response_data)

    async def query_async(
        self, query_text: str, k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> QueryMemoryResponse:
        """
        Asynchronously queries the memory for relevant records.

        Args:
            query_text: Search query
            k: Number of results to return
            filters: Optional filters

        Returns:
            QueryMemoryResponse with scored results
        """
        request_body = QueryMemoryRequest(query_text=query_text, k=k, filters=filters)
        response_data = await self._async_request(
            "POST", "/memory/query", json=request_body.model_dump(exclude_none=True)
        )
        return QueryMemoryResponse(**response_data)

    async def delete_async(self, memory_id: str) -> DeleteMemoryResponse:
        """
        Asynchronously deletes a memory record by its ID.

        Args:
            memory_id: ID of the memory to delete

        Returns:
            DeleteMemoryResponse with confirmation
        """
        response_data = await self._async_request(
            "DELETE", f"/memory/delete?memory_id={memory_id}"
        )
        return DeleteMemoryResponse(**response_data)

    # Async GraphRAG Methods

    async def extract_knowledge_graph_async(
        self,
        project_id: str,
        limit: int = 50,
        min_confidence: float = 0.5,
        auto_store: bool = True,
    ) -> Dict[str, Any]:
        """Async version of extract_knowledge_graph."""
        request_body: Dict[str, Any] = {
            "project_id": project_id,
            "limit": limit,
            "min_confidence": min_confidence,
            "auto_store": auto_store,
        }
        return cast(
            Dict[str, Any],
            await self._async_request("POST", "/v1/graph/extract", json=request_body),
        )

    async def query_graph_async(
        self,
        query: str,
        project_id: str,
        top_k_vector: int = 5,
        graph_depth: int = 2,
        traversal_strategy: str = "bfs",
    ) -> Dict[str, Any]:
        """Async version of query_graph."""
        request_body: Dict[str, Any] = {
            "query": query,
            "project_id": project_id,
            "top_k_vector": top_k_vector,
            "graph_depth": graph_depth,
            "traversal_strategy": traversal_strategy,
        }
        return cast(
            Dict[str, Any],
            await self._async_request("POST", "/v1/graph/query", json=request_body),
        )

    async def get_graph_stats_async(self, project_id: str) -> Dict[str, Any]:
        """Async version of get_graph_stats."""
        return cast(
            Dict[str, Any],
            await self._async_request(
                "GET", f"/v1/graph/stats?project_id={project_id}"
            ),
        )

    async def execute_agent_async(
        self, tenant_id: str, project: str, prompt: str
    ) -> Dict[str, Any]:
        """Async version of execute_agent."""
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project": project,
            "prompt": prompt,
        }
        return cast(
            Dict[str, Any],
            await self._async_request("POST", "/v1/agent/execute", json=request_body),
        )

    # Async ISO/IEC 42001 Compliance Methods

    async def request_approval_async(
        self,
        tenant_id: str,
        project_id: str,
        operation_type: str,
        operation_description: str,
        risk_level: str,
        resource_type: str,
        resource_id: str,
        requested_by: str,
        required_approvers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async version of request_approval."""
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "operation_type": operation_type,
            "operation_description": operation_description,
            "risk_level": risk_level,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "requested_by": requested_by,
        }
        if required_approvers:
            request_body["required_approvers"] = required_approvers
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", "/v1/compliance/approvals", json=request_body
            ),
        )

    async def check_approval_status_async(self, request_id: str) -> Dict[str, Any]:
        """Async version of check_approval_status."""
        return cast(
            Dict[str, Any],
            await self._async_request("GET", f"/v1/compliance/approvals/{request_id}"),
        )

    async def process_approval_decision_async(
        self,
        request_id: str,
        approved: bool,
        approver_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of process_approval_decision."""
        request_body: Dict[str, Any] = {
            "approved": approved,
            "approver_id": approver_id,
        }
        if reason:
            request_body["reason"] = reason

        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST",
                f"/v1/compliance/approvals/{request_id}/decide",
                json=request_body,
            ),
        )

    async def create_decision_context_async(
        self,
        tenant_id: str,
        project_id: str,
        query: str,
        sources: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async version of create_decision_context."""
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "query": query,
            "sources": sources,
        }
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", "/v1/compliance/provenance/context", json=request_body
            ),
        )

    async def record_decision_async(
        self,
        tenant_id: str,
        project_id: str,
        context_id: str,
        decision: str,
        decision_type: str,
        confidence: float,
        human_approved: bool = False,
        approver_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async version of record_decision."""
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "project_id": project_id,
            "context_id": context_id,
            "decision": decision,
            "decision_type": decision_type,
            "confidence": confidence,
            "human_approved": human_approved,
        }
        if approver_id:
            request_body["approver_id"] = approver_id
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", "/v1/compliance/provenance/decision", json=request_body
            ),
        )

    async def get_decision_lineage_async(self, decision_id: str) -> Dict[str, Any]:
        """Async version of get_decision_lineage."""
        return cast(
            Dict[str, Any],
            await self._async_request(
                "GET", f"/v1/compliance/provenance/lineage/{decision_id}"
            ),
        )

    async def get_all_circuit_breakers_async(self) -> List[Dict[str, Any]]:
        """Async version of get_all_circuit_breakers."""
        return cast(
            List[Dict[str, Any]],
            await self._async_request("GET", "/v1/compliance/circuit-breakers"),
        )

    async def get_circuit_breaker_state_async(self, name: str) -> Dict[str, Any]:
        """Async version of get_circuit_breaker_state."""
        return cast(
            Dict[str, Any],
            await self._async_request("GET", f"/v1/compliance/circuit-breakers/{name}"),
        )

    async def reset_circuit_breaker_async(self, name: str) -> Dict[str, Any]:
        """Async version of reset_circuit_breaker."""
        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", f"/v1/compliance/circuit-breakers/{name}/reset"
            ),
        )

    async def list_policies_async(
        self,
        tenant_id: str,
        policy_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Async version of list_policies."""
        params: Dict[str, Any] = {"tenant_id": tenant_id}
        if policy_type:
            params["policy_type"] = policy_type
        if status:
            params["status"] = status

        return cast(
            Dict[str, Any],
            await self._async_request("GET", "/v1/compliance/policies", params=params),
        )

    async def create_policy_async(
        self,
        tenant_id: str,
        policy_id: str,
        policy_type: str,
        rules: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async version of create_policy."""
        request_body: Dict[str, Any] = {
            "tenant_id": tenant_id,
            "policy_id": policy_id,
            "policy_type": policy_type,
            "rules": rules,
            "created_by": created_by,
        }
        if description:
            request_body["description"] = description
        if metadata:
            request_body["metadata"] = metadata

        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", "/v1/compliance/policies", json=request_body
            ),
        )

    async def activate_policy_async(
        self, policy_id: str, version_id: str, tenant_id: str
    ) -> Dict[str, Any]:
        """Async version of activate_policy."""
        request_body: Dict[str, Any] = {
            "version_id": version_id,
            "tenant_id": tenant_id,
        }
        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST",
                f"/v1/compliance/policies/{policy_id}/activate",
                json=request_body,
            ),
        )

    async def enforce_policy_async(
        self, policy_id: str, tenant_id: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Async version of enforce_policy."""
        request_body: Dict[str, Any] = {"tenant_id": tenant_id, "context": context}
        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST",
                f"/v1/compliance/policies/{policy_id}/enforce",
                json=request_body,
            ),
        )

    # Async Reflection Methods

    async def rebuild_reflections_async(
        self, tenant_id: str, project: str
    ) -> Dict[str, Any]:
        """Async version of rebuild_reflections."""
        request_body: Dict[str, Any] = {"tenant_id": tenant_id, "project": project}
        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", "/v1/memory/rebuild-reflections", json=request_body
            ),
        )

    async def get_reflection_stats_async(self, project: str) -> Dict[str, Any]:
        """Async version of get_reflection_stats."""
        return cast(
            Dict[str, Any],
            await self._async_request(
                "GET", f"/v1/memory/reflection-stats?project={project}"
            ),
        )

    async def generate_hierarchical_reflection_async(
        self, project: str, bucket_size: int = 10, max_episodes: Optional[int] = None
    ) -> Dict[str, Any]:
        """Async version of generate_hierarchical_reflection."""
        params: Dict[str, Any] = {"project": project, "bucket_size": bucket_size}
        if max_episodes:
            params["max_episodes"] = max_episodes
        return cast(
            Dict[str, Any],
            await self._async_request(
                "POST", "/v1/memory/reflection/hierarchical", params=params
            ),
        )

    # Async Health & Cache Methods

    async def get_health_async(self) -> Dict[str, Any]:
        """Async version of get_health."""
        return cast(Dict[str, Any], await self._async_request("GET", "/health"))

    async def rebuild_cache_async(self) -> Dict[str, Any]:
        """Async version of rebuild_cache."""
        return cast(
            Dict[str, Any], await self._async_request("POST", "/v1/cache/rebuild")
        )

    # Contextual Helpers

    async def store_interaction(
        self,
        content: str,
        role: str,
        project: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> StoreMemoryResponse:
        """
        Specialized method to store agent-user interaction in the sensory layer.
        Automatically sets layer="sensory" and memory_type="interaction".
        """
        request = StoreMemoryRequest(
            content=content,
            layer="sensory",
            memory_type="interaction",
            project=project,
            session_id=session_id or self.session_id,
            source=role,
            importance=0.4,  # Sensory info starts with lower importance
        )
        return await self.store_async(request)

    async def close(self):
        """Close async HTTP client connections."""
        await self._async_http_client.aclose()

    def __del__(self):
        """Cleanup on deletion."""
        try:
            self._http_client.close()
        except Exception:
            pass


# Aliases for backward compatibility and documentation consistency
RAEClient = MemoryClient
AsyncRAEClient = MemoryClient  # Same class, supports both sync and async methods
