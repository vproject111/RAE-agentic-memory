"""
Analytics Tracker Plugin

Tracks memory operations for analytics and insights.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from apps.memory_api.plugins.base import Plugin, PluginHook, PluginMetadata


class AnalyticsTrackerPlugin(Plugin):
    """
    Plugin that tracks operations for analytics

    Configuration:
        track_creates: Track memory creations
        track_queries: Track queries
        track_reflections: Track reflections
        aggregate_interval: Aggregation interval in seconds
    """

    def _create_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="analytics_tracker",
            version="1.0.0",
            author="RAE Team",
            description="Track memory operations for analytics",
            hooks=[
                PluginHook.AFTER_MEMORY_CREATE,
                PluginHook.AFTER_QUERY,
                PluginHook.AFTER_REFLECTION,
                PluginHook.METRICS_COLLECTED,
            ],
            config=self.config,
        )

    async def initialize(self):
        """Initialize tracking storage"""
        await super().initialize()

        self.track_creates = self.config.get("track_creates", True)
        self.track_queries = self.config.get("track_queries", True)
        self.track_reflections = self.config.get("track_reflections", True)
        self.aggregate_interval = self.config.get("aggregate_interval", 3600)

        # In-memory tracking (production should use database/Redis)
        self._creates_count: Dict[UUID, int] = defaultdict(int)
        self._queries_count: Dict[UUID, int] = defaultdict(int)
        self._reflections_count: Dict[UUID, int] = defaultdict(int)

        self._create_timestamps: List[datetime] = []
        self._query_timestamps: List[datetime] = []
        self._query_latencies: List[float] = []

        self._layer_distribution: Dict[str, int] = defaultdict(int)
        self._tag_usage: Dict[str, int] = defaultdict(int)

        self.logger.info("analytics_tracker_initialized")

    async def on_after_memory_create(
        self, tenant_id: UUID, memory_id: str, memory_data: Dict[str, Any]
    ):
        """Track memory creation"""
        if not self.track_creates:
            return

        self._creates_count[tenant_id] += 1
        self._create_timestamps.append(datetime.now(timezone.utc))

        # Track layer distribution
        layer = memory_data.get("layer", "unknown")
        self._layer_distribution[layer] += 1

        # Track tag usage
        tags = memory_data.get("tags", [])
        for tag in tags:
            self._tag_usage[tag] += 1

        self.logger.debug(
            "create_tracked", tenant_id=str(tenant_id), layer=layer, num_tags=len(tags)
        )

    async def on_after_query(
        self, tenant_id: UUID, query: str, results: List[Dict[str, Any]]
    ):
        """Track query execution"""
        if not self.track_queries:
            return

        self._queries_count[tenant_id] += 1
        self._query_timestamps.append(datetime.now(timezone.utc))

        # Track query performance (would need timing info from context)
        # For now, just track count

        self.logger.debug(
            "query_tracked", tenant_id=str(tenant_id), results_count=len(results)
        )

    async def on_after_reflection(
        self, tenant_id: UUID, reflection_id: str, reflection_data: Dict[str, Any]
    ):
        """Track reflection generation"""
        if not self.track_reflections:
            return

        self._reflections_count[tenant_id] += 1

        self.logger.debug(
            "reflection_tracked",
            tenant_id=str(tenant_id),
            quality=reflection_data.get("quality_score", 0.0),
        )

    async def on_metrics_collected(self, tenant_id: UUID, metrics: Dict[str, Any]):
        """Handle metrics collection event"""
        # Add our tracked metrics to the collection
        metrics.update(self.get_analytics())

    def get_analytics(self) -> Dict[str, Any]:
        """
        Get current analytics data

        Returns:
            Analytics summary
        """
        total_creates = sum(self._creates_count.values())
        total_queries = sum(self._queries_count.values())
        total_reflections = sum(self._reflections_count.values())

        return {
            "plugin": self.metadata.name,
            "totals": {
                "creates": total_creates,
                "queries": total_queries,
                "reflections": total_reflections,
            },
            "by_tenant": {
                "creates": dict(self._creates_count),
                "queries": dict(self._queries_count),
                "reflections": dict(self._reflections_count),
            },
            "layer_distribution": dict(self._layer_distribution),
            "tag_usage": dict(
                sorted(self._tag_usage.items(), key=lambda x: x[1], reverse=True)[:20]
            ),  # Top 20 tags
            "timestamps": {
                "first_create": (
                    self._create_timestamps[0].isoformat()
                    if self._create_timestamps
                    else None
                ),
                "latest_create": (
                    self._create_timestamps[-1].isoformat()
                    if self._create_timestamps
                    else None
                ),
                "first_query": (
                    self._query_timestamps[0].isoformat()
                    if self._query_timestamps
                    else None
                ),
                "latest_query": (
                    self._query_timestamps[-1].isoformat()
                    if self._query_timestamps
                    else None
                ),
            },
        }

    def get_tenant_analytics(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Get analytics for specific tenant

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant analytics
        """
        return {
            "tenant_id": str(tenant_id),
            "creates": self._creates_count.get(tenant_id, 0),
            "queries": self._queries_count.get(tenant_id, 0),
            "reflections": self._reflections_count.get(tenant_id, 0),
        }

    def reset_analytics(self):
        """Reset all analytics data"""
        self._creates_count.clear()
        self._queries_count.clear()
        self._reflections_count.clear()
        self._create_timestamps.clear()
        self._query_timestamps.clear()
        self._query_latencies.clear()
        self._layer_distribution.clear()
        self._tag_usage.clear()

        self.logger.info("analytics_reset")

    async def health_check(self) -> Dict[str, Any]:
        """Health check with current metrics"""
        status = await super().health_check()

        status["metrics"] = {
            "total_creates": sum(self._creates_count.values()),
            "total_queries": sum(self._queries_count.values()),
            "total_reflections": sum(self._reflections_count.values()),
            "unique_tenants": len(
                set(
                    list(self._creates_count.keys())
                    + list(self._queries_count.keys())
                    + list(self._reflections_count.keys())
                )
            ),
        }

        return status
