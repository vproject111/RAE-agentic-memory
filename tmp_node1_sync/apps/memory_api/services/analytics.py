"""
Analytics Service - Usage statistics and insights for tenants
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Service for collecting and analyzing tenant usage statistics"""

    def __init__(self, rae_service=None):
        """
        Initialize analytics service

        Args:
            rae_service: RAECoreService instance
        """
        self.rae_service = rae_service
        self._cache: Dict[str, Any] = {}

    async def get_tenant_stats(
        self, tenant_id: UUID, period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive usage statistics for tenant

        Args:
            tenant_id: Tenant UUID
            period_days: Number of days to analyze (default 30)

        Returns:
            Dictionary with comprehensive statistics
        """
        cache_key = f"analytics:{tenant_id}:{period_days}"

        # Check cache first (5 minute TTL)
        cached = await self._get_from_cache(cache_key)
        if cached:
            return cached

        logger.info(
            "calculating_tenant_stats",
            tenant_id=str(tenant_id),
            period_days=period_days,
        )

        # Calculate all statistics
        stats = {
            "tenant_id": str(tenant_id),
            "period": {
                "start": (
                    datetime.now(timezone.utc) - timedelta(days=period_days)
                ).isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
                "days": period_days,
            },
            "memories": await self._get_memory_stats(tenant_id, period_days),
            "queries": await self._get_query_stats(tenant_id, period_days),
            "knowledge_graph": await self._get_graph_stats(tenant_id),
            "reflections": await self._get_reflection_stats(tenant_id, period_days),
            "api_usage": await self._get_api_usage_stats(tenant_id, period_days),
            "performance": await self._get_performance_stats(tenant_id, period_days),
            "costs": await self._get_cost_stats(tenant_id, period_days),
        }

        # Cache results
        await self._set_cache(cache_key, stats, ttl_seconds=300)

        return stats

    async def _get_memory_stats(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, Any]:
        """Get memory-related statistics"""

        # In production, these would be actual database queries
        # For now, returning mock data structure

        total_memories = await self._count_memories(tenant_id)
        by_layer = await self._count_by_layer(tenant_id)
        growth_rate = await self._calculate_growth_rate(tenant_id, period_days)

        return {
            "total": total_memories,
            "by_layer": by_layer,
            "growth_rate_per_day": growth_rate,
            "by_importance": await self._count_by_importance(tenant_id),
            "by_project": await self._count_by_project(tenant_id),
            "storage_mb": await self._calculate_storage_size(tenant_id),
            "avg_memory_size_bytes": await self._avg_memory_size(tenant_id),
            "most_active_projects": await self._get_most_active_projects(
                tenant_id, period_days
            ),
        }

    async def _get_query_stats(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, Any]:
        """Get query and search statistics"""

        return {
            "total_queries": await self._count_queries(tenant_id, period_days),
            "queries_today": await self._count_queries_today(tenant_id),
            "avg_latency_ms": await self._avg_query_latency(tenant_id, period_days),
            "p95_latency_ms": await self._p95_query_latency(tenant_id, period_days),
            "most_common_queries": await self._get_top_queries(
                tenant_id, period_days, limit=10
            ),
            "query_success_rate": await self._calculate_success_rate(
                tenant_id, period_days
            ),
            "semantic_search_usage": await self._count_semantic_searches(
                tenant_id, period_days
            ),
            "hybrid_search_usage": await self._count_hybrid_searches(
                tenant_id, period_days
            ),
            "queries_by_hour": await self._get_queries_by_hour(tenant_id, period_days),
        }

    async def _get_graph_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get knowledge graph statistics"""

        nodes = await self._count_graph_nodes(tenant_id)
        edges = await self._count_graph_edges(tenant_id)
        density = await self._calculate_graph_density(tenant_id, nodes, edges)

        return {
            "nodes": nodes,
            "edges": edges,
            "density": density,
            "avg_connections_per_node": edges / nodes if nodes > 0 else 0,
            "by_entity_type": await self._count_nodes_by_type(tenant_id),
            "by_relation_type": await self._count_edges_by_type(tenant_id),
            "communities": await self._count_communities(tenant_id),
            "isolated_nodes": await self._count_isolated_nodes(tenant_id),
            "graph_diameter": await self._calculate_graph_diameter(tenant_id),
            "top_entities": await self._get_top_entities(tenant_id, limit=10),
        }

    async def _get_reflection_stats(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, Any]:
        """Get reflection engine statistics"""

        return {
            "total_generated": await self._count_reflections(tenant_id, period_days),
            "reflections_today": await self._count_reflections_today(tenant_id),
            "avg_insight_quality": await self._avg_insight_score(
                tenant_id, period_days
            ),
            "by_trigger": await self._count_reflections_by_trigger(
                tenant_id, period_days
            ),
            "by_strategy": await self._count_reflections_by_strategy(
                tenant_id, period_days
            ),
            "high_quality_insights": await self._count_high_quality_insights(
                tenant_id, period_days
            ),
            "reflection_success_rate": await self._calculate_reflection_success_rate(
                tenant_id, period_days
            ),
            "avg_processing_time_ms": await self._avg_reflection_time(
                tenant_id, period_days
            ),
        }

    async def _get_api_usage_stats(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, Any]:
        """Get API usage statistics"""

        return {
            "total_requests": await self._count_api_requests(tenant_id, period_days),
            "requests_today": await self._count_api_requests_today(tenant_id),
            "by_endpoint": await self._count_by_endpoint(tenant_id, period_days),
            "by_method": await self._count_by_method(tenant_id, period_days),
            "by_status_code": await self._count_by_status_code(tenant_id, period_days),
            "error_rate": await self._calculate_error_rate(tenant_id, period_days),
            "rate_limit_hits": await self._count_rate_limit_hits(
                tenant_id, period_days
            ),
            "peak_usage_hour": await self._get_peak_usage_hour(tenant_id, period_days),
            "daily_breakdown": await self._get_daily_breakdown(tenant_id, period_days),
        }

    async def _get_performance_stats(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, Any]:
        """Get performance metrics"""

        return {
            "avg_response_time_ms": await self._avg_response_time(
                tenant_id, period_days
            ),
            "p50_response_time_ms": await self._p50_response_time(
                tenant_id, period_days
            ),
            "p95_response_time_ms": await self._p95_response_time(
                tenant_id, period_days
            ),
            "p99_response_time_ms": await self._p99_response_time(
                tenant_id, period_days
            ),
            "cache_hit_rate": await self._calculate_cache_hit_rate(
                tenant_id, period_days
            ),
            "db_query_time_ms": await self._avg_db_query_time(tenant_id, period_days),
            "vector_search_time_ms": await self._avg_vector_search_time(
                tenant_id, period_days
            ),
            "llm_call_time_ms": await self._avg_llm_call_time(tenant_id, period_days),
        }

    async def _get_cost_stats(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, Any]:
        """Get cost tracking statistics (for internal use)"""

        return {
            "llm_api_calls": await self._count_llm_calls(tenant_id, period_days),
            "embedding_api_calls": await self._count_embedding_calls(
                tenant_id, period_days
            ),
            "tokens_used": await self._count_tokens_used(tenant_id, period_days),
            "estimated_llm_cost_usd": await self._estimate_llm_cost(
                tenant_id, period_days
            ),
            "estimated_storage_cost_usd": await self._estimate_storage_cost(tenant_id),
            "estimated_compute_cost_usd": await self._estimate_compute_cost(
                tenant_id, period_days
            ),
            "total_estimated_cost_usd": 0.0,  # Will be calculated
        }

    # Helper methods - In production, these would query actual databases
    # For now, returning mock data

    async def _count_memories(self, tenant_id: UUID) -> int:
        """Count total memories for tenant"""
        if self.rae_service:
            # Aggregate across all layers
            count = 0
            for layer in ["episodic", "working", "semantic", "ltm"]:
                count += await self.rae_service.count_memories(
                    tenant_id=str(tenant_id), layer=layer, project="default"
                )
            return count
        return 0

    async def _count_by_layer(self, tenant_id: UUID) -> Dict[str, int]:
        """Count memories by layer"""
        counts = {"episodic": 0, "working": 0, "semantic": 0, "ltm": 0}
        if self.rae_service:
            for layer in counts.keys():
                counts[layer] = await self.rae_service.count_memories(
                    tenant_id=str(tenant_id), layer=layer, project="default"
                )
        return counts

    async def _calculate_growth_rate(self, tenant_id: UUID, period_days: int) -> float:
        """Calculate memory growth rate per day"""
        # Would need historical data from metrics repo or similar
        return 0.0

    async def _count_by_importance(self, tenant_id: UUID) -> Dict[str, int]:
        """Count memories by importance level"""
        return {"high": 0, "medium": 0, "low": 0}

    async def _count_by_project(self, tenant_id: UUID) -> Dict[str, int]:
        """Count memories by project"""
        return {}

    async def _calculate_storage_size(self, tenant_id: UUID) -> float:
        """Calculate total storage size in MB"""
        return 0.0

    async def _avg_memory_size(self, tenant_id: UUID) -> float:
        """Calculate average memory size in bytes"""
        return 0.0

    async def _get_most_active_projects(
        self, tenant_id: UUID, period_days: int
    ) -> List[Dict[str, Any]]:
        """Get most active projects"""
        return []

    async def _count_queries(self, tenant_id: UUID, period_days: int) -> int:
        """Count total queries"""
        return 0

    async def _count_queries_today(self, tenant_id: UUID) -> int:
        """Count queries today"""
        return 0

    async def _avg_query_latency(self, tenant_id: UUID, period_days: int) -> float:
        """Average query latency in milliseconds"""
        return 0.0

    async def _p95_query_latency(self, tenant_id: UUID, period_days: int) -> float:
        """P95 query latency"""
        return 0.0

    async def _get_top_queries(
        self, tenant_id: UUID, period_days: int, limit: int
    ) -> List[Dict[str, Any]]:
        """Get most common queries"""
        return []

    async def _calculate_success_rate(self, tenant_id: UUID, period_days: int) -> float:
        """Calculate query success rate (0-1)"""
        return 1.0

    async def _count_semantic_searches(self, tenant_id: UUID, period_days: int) -> int:
        """Count semantic searches"""
        return 0

    async def _count_hybrid_searches(self, tenant_id: UUID, period_days: int) -> int:
        """Count hybrid searches"""
        return 0

    async def _get_queries_by_hour(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[int, int]:
        """Get query distribution by hour of day"""
        return {hour: 0 for hour in range(24)}

    async def _count_graph_nodes(self, tenant_id: UUID) -> int:
        """Count knowledge graph nodes"""
        # In future, use GraphRepository
        return 0

    async def _count_graph_edges(self, tenant_id: UUID) -> int:
        """Count knowledge graph edges"""
        # In future, use GraphRepository
        return 0

    async def _calculate_graph_density(
        self, tenant_id: UUID, nodes: int, edges: int
    ) -> float:
        """Calculate graph density"""
        if nodes <= 1:
            return 0.0
        max_edges = nodes * (nodes - 1) / 2
        return edges / max_edges if max_edges > 0 else 0.0

    async def _count_nodes_by_type(self, tenant_id: UUID) -> Dict[str, int]:
        """Count nodes by entity type"""
        return {}

    async def _count_edges_by_type(self, tenant_id: UUID) -> Dict[str, int]:
        """Count edges by relation type"""
        return {}

    async def _count_communities(self, tenant_id: UUID) -> int:
        """Count graph communities"""
        return 0

    async def _count_isolated_nodes(self, tenant_id: UUID) -> int:
        """Count isolated nodes (no connections)"""
        return 0

    async def _calculate_graph_diameter(self, tenant_id: UUID) -> int:
        """Calculate graph diameter (longest shortest path)"""
        return 0

    async def _get_top_entities(
        self, tenant_id: UUID, limit: int
    ) -> List[Dict[str, Any]]:
        """Get top entities by centrality"""
        return []

    async def _count_reflections(self, tenant_id: UUID, period_days: int) -> int:
        """Count total reflections generated"""
        return 0

    async def _count_reflections_today(self, tenant_id: UUID) -> int:
        """Count reflections generated today"""
        return 0

    async def _avg_insight_score(self, tenant_id: UUID, period_days: int) -> float:
        """Average insight quality score"""
        return 0.0

    async def _count_reflections_by_trigger(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, int]:
        """Count reflections by trigger type"""
        return {"threshold": 0, "scheduled": 0, "manual": 0, "event": 0}

    async def _count_reflections_by_strategy(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, int]:
        """Count reflections by strategy"""
        return {
            "summarization": 0,
            "pattern_detection": 0,
            "knowledge_extraction": 0,
            "meta_cognitive": 0,
        }

    async def _count_high_quality_insights(
        self, tenant_id: UUID, period_days: int
    ) -> int:
        """Count high quality insights (score > 0.7)"""
        return 0

    async def _calculate_reflection_success_rate(
        self, tenant_id: UUID, period_days: int
    ) -> float:
        """Calculate reflection success rate"""
        return 1.0

    async def _avg_reflection_time(self, tenant_id: UUID, period_days: int) -> float:
        """Average reflection processing time"""
        return 0.0

    async def _count_api_requests(self, tenant_id: UUID, period_days: int) -> int:
        """Count total API requests"""
        return 0

    async def _count_api_requests_today(self, tenant_id: UUID) -> int:
        """Count API requests today"""
        return 0

    async def _count_by_endpoint(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, int]:
        """Count requests by endpoint"""
        return {}

    async def _count_by_method(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, int]:
        """Count requests by HTTP method"""
        return {"GET": 0, "POST": 0, "PUT": 0, "DELETE": 0}

    async def _count_by_status_code(
        self, tenant_id: UUID, period_days: int
    ) -> Dict[str, int]:
        """Count requests by status code"""
        return {"2xx": 0, "4xx": 0, "5xx": 0}

    async def _calculate_error_rate(self, tenant_id: UUID, period_days: int) -> float:
        """Calculate API error rate"""
        return 0.0

    async def _count_rate_limit_hits(self, tenant_id: UUID, period_days: int) -> int:
        """Count rate limit hits"""
        return 0

    async def _get_peak_usage_hour(self, tenant_id: UUID, period_days: int) -> int:
        """Get peak usage hour (0-23)"""
        return 0

    async def _get_daily_breakdown(
        self, tenant_id: UUID, period_days: int
    ) -> List[Dict[str, Any]]:
        """Get daily request breakdown"""
        return []

    async def _avg_response_time(self, tenant_id: UUID, period_days: int) -> float:
        """Average response time"""
        return 0.0

    async def _p50_response_time(self, tenant_id: UUID, period_days: int) -> float:
        """P50 response time"""
        return 0.0

    async def _p95_response_time(self, tenant_id: UUID, period_days: int) -> float:
        """P95 response time"""
        return 0.0

    async def _p99_response_time(self, tenant_id: UUID, period_days: int) -> float:
        """P99 response time"""
        return 0.0

    async def _calculate_cache_hit_rate(
        self, tenant_id: UUID, period_days: int
    ) -> float:
        """Calculate cache hit rate"""
        return 0.0

    async def _avg_db_query_time(self, tenant_id: UUID, period_days: int) -> float:
        """Average database query time"""
        return 0.0

    async def _avg_vector_search_time(self, tenant_id: UUID, period_days: int) -> float:
        """Average vector search time"""
        return 0.0

    async def _avg_llm_call_time(self, tenant_id: UUID, period_days: int) -> float:
        """Average LLM call time"""
        return 0.0

    async def _count_llm_calls(self, tenant_id: UUID, period_days: int) -> int:
        """Count LLM API calls"""
        return 0

    async def _count_embedding_calls(self, tenant_id: UUID, period_days: int) -> int:
        """Count embedding API calls"""
        return 0

    async def _count_tokens_used(self, tenant_id: UUID, period_days: int) -> int:
        """Count total tokens used"""
        return 0

    async def _estimate_llm_cost(self, tenant_id: UUID, period_days: int) -> float:
        """Estimate LLM costs in USD"""
        return 0.0

    async def _estimate_storage_cost(self, tenant_id: UUID) -> float:
        """Estimate storage costs in USD"""
        return 0.0

    async def _estimate_compute_cost(self, tenant_id: UUID, period_days: int) -> float:
        """Estimate compute costs in USD"""
        return 0.0

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value from cache"""
        if (
            self.rae_service
            and hasattr(self.rae_service, "redis_client")
            and self.rae_service.redis_client
        ):
            try:
                import json
                from typing import cast

                val = await self.rae_service.redis_client.get(key)
                if val:
                    return cast(Dict[str, Any], json.loads(val))
            except Exception:
                pass
        return self._cache.get(key)

    async def _set_cache(self, key: str, value: Dict[str, Any], ttl_seconds: int):
        """Set value in cache with TTL"""
        if (
            self.rae_service
            and hasattr(self.rae_service, "redis_client")
            and self.rae_service.redis_client
        ):
            try:
                import json

                await self.rae_service.redis_client.set(
                    key, json.dumps(value), ex=ttl_seconds
                )
            except Exception:
                pass
        self._cache[key] = value

    async def generate_report(
        self, tenant_id: UUID, period_days: int = 30, format: str = "json"
    ) -> Any:
        """
        Generate analytics report

        Args:
            tenant_id: Tenant UUID
            period_days: Report period in days
            format: Output format (json, csv, pdf)

        Returns:
            Report in specified format
        """
        stats = await self.get_tenant_stats(tenant_id, period_days)

        if format == "json":
            return stats
        elif format == "csv":
            return await self._export_to_csv(stats)
        elif format == "pdf":
            return await self._export_to_pdf(stats)
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def _export_to_csv(self, stats: Dict[str, Any]) -> str:
        """Export stats to CSV format"""
        # Implementation would flatten stats and convert to CSV
        return ""

    async def _export_to_pdf(self, stats: Dict[str, Any]) -> bytes:
        """Export stats to PDF format"""
        # Implementation would use reportlab or similar
        return b""

    async def get_real_time_metrics(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get real-time metrics (not cached)

        Used for monitoring dashboards and alerts
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": str(tenant_id),
            "current_active_requests": 0,
            "requests_per_second": 0.0,
            "avg_latency_ms": 0.0,
            "error_rate": 0.0,
            "queue_depth": 0,
            "cache_hit_rate": 0.0,
            "memory_usage_mb": 0.0,
            "cpu_usage_percent": 0.0,
        }

    async def get_usage_alerts(self, tenant_id: UUID) -> List[Dict[str, Any]]:
        """
        Check for usage alerts (quota limits, performance issues, etc.)

        Returns:
            List of active alerts
        """
        alerts: List[Dict[str, Any]] = []

        # Check various thresholds
        # In production, this would check against tenant.config limits

        return alerts
