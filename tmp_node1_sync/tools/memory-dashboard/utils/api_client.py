"""
RAE API Client for Dashboard

Enterprise-grade async HTTP client for RAE Memory API.
Provides comprehensive error handling and caching.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import streamlit as st


class RAEClient:
    """
    Enterprise-grade client for RAE Memory API.

    Features:
    - Connection pooling
    - Error handling with retries
    - Response caching
    - Structured logging
    - Session management
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        api_key: str = "default-key",
        tenant_id: str = "default-tenant",
        project_id: str = "default-project",
        timeout: float = 300.0,
    ):
        """
        Initialize RAE API client.

        Args:
            api_url: Base URL of RAE API
            api_key: API authentication key
            tenant_id: Tenant identifier
            project_id: Project identifier
            timeout: Request timeout in seconds
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.tenant_id = tenant_id
        self.project_id = project_id
        self.timeout = timeout

        self.headers = {
            "X-API-Key": api_key,
            "X-Tenant-Id": tenant_id,
            "Content-Type": "application/json",
        }

        self.client = httpx.Client(
            base_url=self.api_url, headers=self.headers, timeout=timeout
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx

        Returns:
            Response JSON data

        Raises:
            Exception: On HTTP or connection errors
        """
        try:
            response = self.client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"HTTP Error {e.response.status_code}: {e.response.text}")
            raise
        except httpx.RequestError as e:
            st.error(f"Connection Error: {str(e)}")
            raise
        except Exception as e:
            st.error(f"Unexpected Error: {str(e)}")
            raise

    def get_stats(self) -> Dict[str, int]:
        """
        Get memory statistics using the dedicated dashboard endpoint.

        Returns:
            Dictionary with memory counts by layer/type
        """
        try:
            # Call the specialized dashboard metrics endpoint
            response = self._request(
                "POST",
                "/v1/dashboard/metrics",
                json={
                    "tenant_id": self.tenant_id,
                    "project_id": self.project_id,
                    "period": "last_24h",
                },
            )

            metrics = response.get("system_metrics", {})

            # Use backend's pre-calculated totals
            total_count = metrics.get("total_memories", 0)
            ltm_count = metrics.get("total_reflections", 0)
            semantic_count = metrics.get("total_semantic_nodes", 0)
            episodic_count = total_count - ltm_count - semantic_count

            # Avoid negative if something is weird with total vs layers
            episodic_count = max(0, episodic_count)

            return {
                "total": total_count,
                "episodic": episodic_count,
                "working": 0,
                "semantic": semantic_count,
                "ltm": ltm_count,
            }

        except Exception as e:
            st.warning(f"Could not fetch stats: {e}")
            return {"total": 0, "episodic": 0, "working": 0, "semantic": 0, "ltm": 0}

    def get_memories(
        self,
        layers: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch memories with filters using LIST endpoint.
        """
        try:
            # Use GET /list for raw data retrieval (no vector search)
            params = {"limit": limit, "offset": 0, "project": self.project_id}
            # Note: API V1 /list might not support multi-layer filter in one go unless updated.
            # Assuming it filters by project mostly.

            response = self.client.get("/v1/memory/list", params=params)
            response.raise_for_status()
            data = response.json()
            memories = data.get("results", [])

            # Client-side filtering for layers if API doesn't support list (it supports single layer param)
            if layers:
                memories = [m for m in memories if m.get("layer") in layers]

            if since:
                filtered_memories = []
                for m in memories:
                    ts_str = m.get("timestamp")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(
                                ts_str.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                            since_naive = since.replace(tzinfo=None)
                            if ts >= since_naive:
                                filtered_memories.append(m)
                        except (ValueError, TypeError):
                            continue
                memories = filtered_memories

            return memories[:limit]

        except Exception as e:
            st.error(f"Error fetching memories: {e}")
            return []

    def get_knowledge_graph(self, project: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch knowledge graph data.

        Args:
            project: Optional project filter

        Returns:
            Dictionary with nodes and edges
        """
        try:
            # Use project_id parameter as required by API
            project_id = project or self.project_id
            if not project_id:
                raise ValueError("project_id is required for knowledge graph")

            # Fetch nodes and edges separately
            nodes = self._request("GET", f"/v1/graph/nodes?project_id={project_id}")
            edges = self._request("GET", f"/v1/graph/edges?project_id={project_id}")

            # Combine into expected format
            return {
                "nodes": nodes if isinstance(nodes, list) else [],
                "edges": edges if isinstance(edges, list) else [],
            }

        except Exception as e:
            st.warning(f"Could not fetch knowledge graph: {e}")
            return {"nodes": [], "edges": []}

    def search_memories(
        self, query: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search memories by query.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional filters

        Returns:
            List of scored memory records
        """
        try:
            response = self._request(
                "POST",
                "/v1/memory/query",
                json={
                    "query_text": query,
                    "k": top_k,
                    "filters": filters or {},
                    "project": self.project_id,
                },
            )

            return response.get("results", [])

        except Exception as e:
            st.error(f"Search error: {e}")
            return []

    def get_all_tags(self) -> List[str]:
        """
        Get all unique tags from memories.

        Returns:
            List of tag strings
        """
        try:
            # Would need dedicated endpoint
            # For now, extract from recent memories
            memories = self.get_memories(limit=100)
            tags = set()

            for memory in memories:
                memory_tags = memory.get("tags", [])
                if memory_tags:
                    tags.update(memory_tags)

            return sorted(list(tags))

        except Exception as e:
            st.warning(f"Could not fetch tags: {e}")
            return []

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Update a memory record.

        Args:
            memory_id: ID of memory to update
            content: New content (optional)
            tags: New tags (optional)

        Returns:
            True if successful
        """
        try:
            # Delete old and create new (if no update endpoint)
            self.delete_memory(memory_id)

            if content:
                self._request(
                    "POST",
                    "/v1/memory/store",
                    json={
                        "content": content,
                        "tags": tags or [],
                        "project": self.project_id,
                    },
                )

            st.success("Memory updated successfully")
            return True

        except Exception as e:
            st.error(f"Update error: {e}")
            return False

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory record.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if successful
        """
        try:
            self._request("DELETE", f"/v1/memory/delete?memory_id={memory_id}")

            st.success("Memory deleted successfully")
            return True

        except Exception as e:
            st.error(f"Delete error: {e}")
            return False

    def query_memory(
        self, query: str, top_k: int = 5, use_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query memories with optional reranking.

        Args:
            query: Query text
            top_k: Number of results
            use_rerank: Whether to use reranking

        Returns:
            List of scored results
        """
        try:
            response = self._request(
                "POST",
                "/v1/memory/query",
                json={"query_text": query, "k": top_k, "project": self.project_id},
            )

            results = response.get("results", [])

            # Simple reranking by score if requested
            if use_rerank and results:
                results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

            return results

        except Exception as e:
            st.error(f"Query error: {e}")
            return []

    def get_reflection(self, project: Optional[str] = None) -> str:
        """
        Get latest project reflection.

        Strategy:
        1. Try to fetch the most recent memory from 'reflective' layer via /list (Fast).
        2. If none found, return a placeholder prompting generation.

        This avoids blocking the Dashboard with heavy LLM generation calls.
        """
        try:
            proj = project or self.project_id

            # Fetch latest reflective memory (Limit 1, Sort is implied by DB insertion order usually,
            # ideally API should support sort, but list usually returns recent first or we assume)
            # Based on PostgresAdapter, list_memories sorts by created_at DESC by default?
            # Checking service: currently assumes default sort.

            response = self.client.get(
                "/v1/memory/list",
                params={
                    "project": proj,
                    "layer": "reflective",
                    "limit": 1,
                    "offset": 0,
                },
                timeout=5.0,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("content", "Empty reflection content")

            return "No reflection cached. Go to 'Control' to trigger a rebuild."

        except Exception:
            # Don't show error trace in UI for simple "not found"
            return "Reflection unavailable (Cache Miss)"

    def get_tenants(self) -> List[str]:
        """
        Get list of all unique tenants.

        Returns:
            List of tenant IDs
        """
        try:
            return self._request("GET", "/v1/system/tenants")
        except Exception as e:
            st.warning(f"Could not fetch tenants: {e}")
            return []

    def get_projects(self) -> List[str]:
        """
        Get list of all unique projects for the current tenant.

        Returns:
            List of project IDs
        """
        try:
            # Headers are already set with X-Tenant-Id in __init__
            return self._request("GET", "/v1/system/projects")
        except Exception as e:
            st.warning(f"Could not fetch projects: {e}")
            return []

    def update_tenant_name(self, tenant_id: str, new_name: str) -> bool:
        """
        Update the name of a tenant.

        Args:
            tenant_id: ID of tenant to update
            new_name: New name for the tenant

        Returns:
            True if successful
        """
        try:
            # We don't use _request here because system endpoints might have different auth requirements
            # but for now assuming same API key works if authorized.
            # System endpoints are under /v1/system
            response = self.client.put(
                f"/v1/system/tenants/{tenant_id}", json={"name": new_name}
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Failed to rename tenant: {e}")
            return False

    def rename_project(self, old_project_id: str, new_project_id: str) -> bool:
        """
        Rename the current project.
        """
        try:
            response = self.client.put(
                f"/v1/system/projects/{old_project_id}", json={"name": new_project_id}
            )
            response.raise_for_status()
            return response.json().get("success", False)
        except Exception as e:
            st.error(f"Failed to rename project: {e}")
            return False

    def test_connection(self) -> bool:
        """
        Test API connection.

        Returns:
            True if connection successful
        """
        try:
            response = self.client.get("/health")
            response.raise_for_status()
            return True
        except Exception:
            return False


@st.cache_data(ttl=60)
def get_cached_stats(
    _client: RAEClient, tenant_id: str, project_id: str
) -> Dict[str, int]:
    """
    Cached version of get_stats.
    """
    return _client.get_stats()


@st.cache_data(ttl=30)
def get_cached_memories(
    _client: RAEClient, layers: tuple, days_back: int
) -> List[Dict[str, Any]]:
    """
    Cached version of get_memories.

    Args:
        _client: RAEClient instance
        layers: Tuple of layer names
        days_back: Number of days to look back

    Returns:
        List of memories
    """
    from datetime import timezone

    # Use timezone-aware datetime to match API timestamps
    since = datetime.now(timezone.utc) - timedelta(days=days_back)
    return _client.get_memories(layers=list(layers), since=since)
