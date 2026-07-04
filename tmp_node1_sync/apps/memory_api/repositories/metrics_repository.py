"""
Metrics Repository - Time Series Data Operations

Provides storage and retrieval operations for dashboard metrics time series data.
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, cast

import asyncpg
import structlog

from rae_adapters.postgres_db import PostgresDatabaseProvider
from rae_core.interfaces.database import IDatabaseProvider

logger = structlog.get_logger(__name__)


class MetricsRepository:
    """Repository for time series metrics operations."""

    def __init__(self, pool: asyncpg.Pool | IDatabaseProvider):
        self.db: IDatabaseProvider
        if isinstance(pool, (asyncpg.Pool, asyncpg.Connection)):
            self.db = PostgresDatabaseProvider(pool)
        else:
            self.db = pool

    async def record_metric(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        value: float,
        dimensions: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> int:
        """
        Record a single metric data point.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            metric_name: Metric name (e.g., 'memory_count', 'search_quality_mrr')
            value: Metric value
            dimensions: Optional dimensions for filtering
            tags: Optional tags
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Metric ID
        """
        metric_id = await self.db.fetchval(
            """
            SELECT record_metric($1, $2, $3, $4, $5, $6)
            """,
            tenant_id,
            project_id,
            metric_name,
            value,
            json.dumps(dimensions) if dimensions else "{}",
            tags or [],
        )

        return cast(int, metric_id)

    async def record_metrics_batch(
        self,
        tenant_id: str,
        project_id: str,
        metrics: List[Tuple[str, float, Optional[Dict], Optional[List[str]]]],
    ) -> int:
        """
        Record multiple metric data points efficiently.
        """
        # For now, use simple batch insert
        values = []
        for metric_name, value, dimensions, tags in metrics:
            values.append(
                (
                    tenant_id,
                    project_id,
                    metric_name,
                    value,
                    json.dumps(dimensions) if dimensions else "{}",
                    tags or [],
                    datetime.now(timezone.utc),
                )
            )

        # Batch insert
        await self.db.executemany(
            """
            INSERT INTO metrics_timeseries (
                tenant_id, project_id, metric_name, value,
                dimensions, tags, timestamp, metric_type
            )
            SELECT $1, $2, $3, $4, $5::jsonb, $6, $7,
                    COALESCE(
                        (SELECT metric_type FROM metric_definitions WHERE metric_name = $3),
                        'gauge'
                    )
            """,
            values,
        )

        logger.info(
            "metrics_batch_recorded",
            tenant_id=tenant_id,
            count=len(metrics),
        )

        return len(metrics)

    async def get_timeseries(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        aggregation_interval: Optional[str] = "1 hour",
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.
        """
        try:
            # Try using the get_metric_timeseries function
            records = await self.db.fetch(
                """
                SELECT * FROM get_metric_timeseries($1, $2, $3, $4, $5, $6::interval)
                """,
                tenant_id,
                project_id,
                metric_name,
                start_time,
                end_time,
                aggregation_interval,
            )

            # LIVE FALLBACK: If no data points, try to get current count from memories
            if not records:
                live_val = 0.0
                if metric_name == "memory_count":
                    live_val = await self.db.fetchval(
                        "SELECT COUNT(*)::float FROM memories WHERE tenant_id = $1::uuid AND (project = $2 OR agent_id = $2)",
                        tenant_id,
                        project_id,
                    )
                elif metric_name == "reflection_count":
                    live_val = await self.db.fetchval(
                        "SELECT COUNT(*)::float FROM memories WHERE tenant_id = $1::uuid AND (project = $2 OR agent_id = $2) AND layer IN ('reflective', 'rm')",
                        tenant_id,
                        project_id,
                    )

                if live_val and live_val > 0:
                    return [
                        {
                            "timestamp": datetime.now(timezone.utc),
                            "metric_value": float(live_val),
                            "data_points": 1,
                        }
                    ]

        except (
            Exception
        ) as e:  # Fallback to manual query if function doesn't exist or other error
            logger.warning("metrics_fetch_error", error=str(e))
            # Fallback to manual query
            records = await self.db.fetch(
                """
                SELECT
                    date_trunc('hour', timestamp) AS bucket_timestamp,
                    AVG(value) AS metric_value,
                    COUNT(*)::INTEGER AS data_points
                FROM metrics_timeseries
                WHERE tenant_id = $1
                    AND project_id = $2
                    AND metric_name = $3
                    AND timestamp BETWEEN $4 AND $5
                GROUP BY date_trunc('hour', timestamp)
                ORDER BY date_trunc('hour', timestamp) ASC
                """,
                tenant_id,
                project_id,
                metric_name,
                start_time,
                end_time,
            )

        return [dict(r) for r in records]

    async def get_latest_metric_value(
        self, tenant_id: str, project_id: str, metric_name: str
    ) -> Optional[float]:
        """
        Get the most recent value for a metric.
        """
        value = await self.db.fetchval(
            """
            SELECT value
            FROM metrics_timeseries
            WHERE tenant_id = $1
                AND project_id = $2
                AND metric_name = $3
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            tenant_id,
            project_id,
            metric_name,
        )

        return float(value) if value is not None else None

    async def get_metric_statistics(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Dict[str, Any]:
        """
        Get statistical summary for a metric over a time range.
        """
        stats = await self.db.fetchrow(
            """
            SELECT
                MIN(value) AS min_value,
                MAX(value) AS max_value,
                AVG(value) AS avg_value,
                SUM(value) AS sum_value,
                COUNT(*) AS data_points,
                STDDEV(value) AS stddev_value
            FROM metrics_timeseries
            WHERE tenant_id = $1
                AND project_id = $2
                AND metric_name = $3
                AND timestamp BETWEEN $4 AND $5
            """,
            tenant_id,
            project_id,
            metric_name,
            start_time,
            end_time,
        )

        return dict(stats) if stats else {}

    async def get_available_metrics(
        self, tenant_id: Optional[str] = None, project_id: Optional[str] = None
    ) -> List[str]:
        """
        Get list of available metrics.
        """
        if tenant_id and project_id:
            records = await self.db.fetch(
                """
                SELECT DISTINCT metric_name
                FROM metrics_timeseries
                WHERE tenant_id = $1 AND project_id = $2
                ORDER BY metric_name
                """,
                tenant_id,
                project_id,
            )
        elif tenant_id:
            records = await self.db.fetch(
                """
                SELECT DISTINCT metric_name
                FROM metrics_timeseries
                WHERE tenant_id = $1
                ORDER BY metric_name
                """,
                tenant_id,
            )
        else:
            records = await self.db.fetch(
                """
                SELECT DISTINCT metric_name
                FROM metrics_timeseries
                ORDER BY metric_name
                """
            )

        return [r["metric_name"] for r in records]

    async def get_metric_definition(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """
        Get metric definition metadata.
        """
        record = await self.db.fetchrow(
            "SELECT * FROM metric_definitions WHERE metric_name = $1", metric_name
        )

        return dict(record) if record else None

    async def cleanup_old_metrics(self, retention_days: int = 365) -> int:
        """
        Delete old metrics data beyond retention period.
        """
        try:
            deleted_count = await self.db.fetchval(
                "SELECT cleanup_old_metrics($1)", retention_days
            )
        except Exception:
            # Fallback to manual deletion
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            result = await self.db.execute(
                "DELETE FROM metrics_timeseries WHERE timestamp < $1", cutoff_date
            )
            # Parse "DELETE N" to get count
            if result and isinstance(result, str) and result.startswith("DELETE"):
                deleted_count = int(result.split()[-1])
            else:
                deleted_count = 0

        logger.info("old_metrics_cleaned", deleted_count=deleted_count)

        return cast(int, deleted_count)

    async def get_metrics_by_dimensions(
        self,
        tenant_id: str,
        project_id: str,
        metric_name: str,
        dimensions: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get metrics filtered by specific dimension values.
        """
        records = await self.db.fetch(
            """
            SELECT timestamp, value, dimensions, tags
            FROM metrics_timeseries
            WHERE tenant_id = $1
                AND project_id = $2
                AND metric_name = $3
                AND timestamp BETWEEN $4 AND $5
                AND dimensions @> $6::jsonb
            ORDER BY timestamp DESC
            """,
            tenant_id,
            project_id,
            metric_name,
            start_time,
            end_time,
            json.dumps(dimensions),
        )

        return [dict(r) for r in records]
