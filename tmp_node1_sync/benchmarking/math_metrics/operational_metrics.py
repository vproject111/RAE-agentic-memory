"""
Operational Metrics - Production Performance & Cost

These metrics analyze operational characteristics for production deployments:
- LLM Cost Index (LCI): Track and optimize API costs
- Storage Pressure Index (SPI): Monitor storage resource usage
- Telemetry Event Correlation (TEC): Correlate performance events
- Worker Saturation Index (WSI): Monitor worker queue health
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

from .base import MathMetricBase


class LLMCostIndex(MathMetricBase):
    """
    LLM Cost Index (LCI)

    Tracks cumulative LLM API costs and cost efficiency.

    Formula: LCI = total_cost_usd / total_operations

    Low LCI = cost-efficient system
    High LCI = expensive operations, needs optimization

    Range: $0.00 to unbounded (typical: $0.001 - $0.10 per operation)
    Target: < $0.01 per operation for production systems
    """

    def __init__(self):
        super().__init__(
            name="llm_cost_index",
            description="LLM API cost per operation in USD",
        )

    def calculate(
        self,
        cost_logs: List[Dict[str, Any]],
        time_window: Optional[timedelta] = None,
    ) -> float:
        """
        Calculate LCI from cost logs.

        Args:
            cost_logs: List of cost log entries with fields:
                - timestamp: datetime
                - cost_usd: float
                - operation: str (e.g., "embedding", "llm_call")
                - tokens: int
            time_window: Optional time window to filter logs

        Returns:
            Average cost per operation in USD
        """
        if not cost_logs:
            self._last_metadata = {
                "total_cost_usd": 0.0,
                "total_operations": 0,
                "operations_by_type": {},
                "warning": "No cost logs available",
            }
            return 0.0

        # Filter by time window if specified
        if time_window:
            cutoff = datetime.now() - time_window
            cost_logs = [
                log for log in cost_logs if log.get("timestamp", datetime.min) > cutoff
            ]

        # Calculate total cost and operations
        total_cost = sum(log.get("cost_usd", 0.0) for log in cost_logs)
        total_operations = len(cost_logs)

        # Break down by operation type
        operations_by_type = {}
        for log in cost_logs:
            op_type = log.get("operation", "unknown")
            if op_type not in operations_by_type:
                operations_by_type[op_type] = {"count": 0, "cost": 0.0}
            operations_by_type[op_type]["count"] += 1
            operations_by_type[op_type]["cost"] += log.get("cost_usd", 0.0)

        # Calculate cost per operation for each type
        for op_type, stats in operations_by_type.items():
            stats["cost_per_op"] = (
                stats["cost"] / stats["count"] if stats["count"] > 0 else 0.0
            )

        # Calculate LCI (average cost per operation)
        lci = total_cost / total_operations if total_operations > 0 else 0.0

        self._last_value = lci
        self._last_metadata = {
            "total_cost_usd": round(total_cost, 4),
            "total_operations": total_operations,
            "cost_per_operation_usd": round(lci, 6),
            "operations_by_type": operations_by_type,
            "time_window_hours": (
                time_window.total_seconds() / 3600 if time_window else None
            ),
        }

        return lci

    def get_metadata(self) -> Dict[str, Any]:
        """Return cost breakdown metadata"""
        return self._last_metadata


class StoragePressureIndex(MathMetricBase):
    """
    Storage Pressure Index (SPI)

    Monitors storage resource usage across PostgreSQL and Qdrant.

    Formula: SPI = (db_usage_ratio + vector_usage_ratio) / 2

    Low SPI = plenty of storage available
    High SPI = approaching storage limits, needs attention

    Range: 0.0 (empty) to 1.0 (at capacity)
    Warning threshold: > 0.7
    Critical threshold: > 0.9
    """

    def __init__(self):
        super().__init__(
            name="storage_pressure_index",
            description="Storage resource usage pressure (0=empty, 1=full)",
        )

    def calculate(
        self,
        db_stats: Dict[str, Any],
        vector_stats: Dict[str, Any],
    ) -> float:
        """
        Calculate SPI from storage statistics.

        Args:
            db_stats: PostgreSQL stats with fields:
                - used_mb: float (used storage in MB)
                - total_mb: float (total available in MB)
                - memory_count: int (number of memories)
                - table_sizes: dict (sizes by table)

            vector_stats: Qdrant stats with fields:
                - used_mb: float (used storage in MB)
                - total_mb: float (total available in MB)
                - vector_count: int (number of vectors)
                - collection_sizes: dict (sizes by collection)

        Returns:
            Storage pressure index (0.0 to 1.0)
        """
        # Calculate DB usage ratio
        db_used = db_stats.get("used_mb", 0.0)
        db_total = db_stats.get("total_mb", 1.0)  # Avoid division by zero
        db_ratio = min(db_used / db_total, 1.0) if db_total > 0 else 0.0

        # Calculate vector store usage ratio
        vector_used = vector_stats.get("used_mb", 0.0)
        vector_total = vector_stats.get("total_mb", 1.0)
        vector_ratio = min(vector_used / vector_total, 1.0) if vector_total > 0 else 0.0

        # Calculate SPI (average of both ratios)
        spi = (db_ratio + vector_ratio) / 2.0

        # Determine pressure level
        if spi < 0.5:
            pressure_level = "low"
        elif spi < 0.7:
            pressure_level = "moderate"
        elif spi < 0.9:
            pressure_level = "high"
        else:
            pressure_level = "critical"

        self._last_value = spi
        self._last_metadata = {
            "spi": round(spi, 4),
            "pressure_level": pressure_level,
            "database": {
                "used_mb": round(db_used, 2),
                "total_mb": round(db_total, 2),
                "usage_ratio": round(db_ratio, 4),
                "memory_count": db_stats.get("memory_count", 0),
            },
            "vector_store": {
                "used_mb": round(vector_used, 2),
                "total_mb": round(vector_total, 2),
                "usage_ratio": round(vector_ratio, 4),
                "vector_count": vector_stats.get("vector_count", 0),
            },
        }

        return spi

    def get_metadata(self) -> Dict[str, Any]:
        """Return storage usage breakdown"""
        return self._last_metadata


class TelemetryEventCorrelation(MathMetricBase):
    """
    Telemetry Event Correlation (TEC)

    Measures correlation between performance events in OpenTelemetry traces.

    Formula: TEC = correlation(latency_events, error_events)

    High positive TEC = errors correlate with high latency (good signal)
    Low TEC = errors independent of latency (harder to diagnose)

    Range: -1.0 (negative correlation) to 1.0 (positive correlation)
    Target: > 0.6 (strong positive correlation for debuggability)
    """

    def __init__(self):
        super().__init__(
            name="telemetry_event_correlation",
            description="Correlation between telemetry events (-1 to 1)",
        )

    def calculate(
        self,
        spans: List[Dict[str, Any]],
    ) -> float:
        """
        Calculate TEC from OpenTelemetry spans.

        Args:
            spans: List of span dictionaries with fields:
                - span_id: str
                - duration_ms: float
                - status: str ("ok", "error")
                - attributes: dict

        Returns:
            Pearson correlation coefficient between latency and errors
        """
        if len(spans) < 2:
            self._last_metadata = {
                "correlation": 0.0,
                "sample_size": len(spans),
                "warning": "Insufficient spans for correlation analysis",
            }
            return 0.0

        # Extract latency and error signals
        latencies = []
        errors = []

        for span in spans:
            duration = span.get("duration_ms", 0.0)
            status = span.get("status", "ok")

            latencies.append(duration)
            errors.append(1.0 if status == "error" else 0.0)

        # Calculate Pearson correlation
        if len(set(errors)) < 2:  # All same value (all ok or all errors)
            correlation = 0.0
            warning = "No variance in error status (all ok or all errors)"
        else:
            correlation = float(np.corrcoef(latencies, errors)[0, 1])
            warning = None

        # Calculate additional statistics
        error_count = sum(errors)
        error_rate = error_count / len(errors)
        avg_latency = np.mean(latencies)
        avg_latency_on_error = (
            np.mean([lat for lat, e in zip(latencies, errors) if e == 1.0])
            if error_count > 0
            else 0.0
        )
        avg_latency_on_success = (
            np.mean([lat for lat, e in zip(latencies, errors) if e == 0.0])
            if error_count < len(errors)
            else 0.0
        )

        self._last_value = correlation
        self._last_metadata = {
            "correlation": round(correlation, 4),
            "sample_size": len(spans),
            "error_count": int(error_count),
            "error_rate": round(error_rate, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "avg_latency_on_error_ms": (
                round(avg_latency_on_error, 2) if error_count > 0 else None
            ),
            "avg_latency_on_success_ms": (
                round(avg_latency_on_success, 2) if error_count < len(errors) else None
            ),
            "warning": warning,
        }

        return correlation

    def get_metadata(self) -> Dict[str, Any]:
        """Return correlation analysis details"""
        return self._last_metadata


class WorkerSaturationIndex(MathMetricBase):
    """
    Worker Saturation Index (WSI)

    Monitors background worker queue saturation.

    Formula: WSI = (active_tasks + pending_tasks) / max_workers

    Low WSI = workers have capacity
    High WSI = workers saturated, queues building up

    Range: 0.0 (idle) to unbounded (severely saturated)
    Warning threshold: > 0.8
    Critical threshold: > 1.5
    """

    def __init__(self):
        super().__init__(
            name="worker_saturation_index",
            description="Worker queue saturation (0=idle, >1=saturated)",
        )

    def calculate(
        self,
        worker_stats: Dict[str, Any],
    ) -> float:
        """
        Calculate WSI from worker statistics.

        Args:
            worker_stats: Worker pool stats with fields:
                - active_tasks: int (currently executing)
                - pending_tasks: int (in queue)
                - max_workers: int (pool size)
                - worker_types: dict (stats by worker type)

        Returns:
            Worker saturation index (0.0 to unbounded)
        """
        active_tasks = worker_stats.get("active_tasks", 0)
        pending_tasks = worker_stats.get("pending_tasks", 0)
        max_workers = worker_stats.get("max_workers", 1)  # Avoid division by zero

        # Calculate WSI
        total_load = active_tasks + pending_tasks
        wsi = total_load / max_workers if max_workers > 0 else 0.0

        # Determine saturation level
        if wsi < 0.5:
            saturation_level = "low"
        elif wsi < 0.8:
            saturation_level = "moderate"
        elif wsi < 1.5:
            saturation_level = "high"
        else:
            saturation_level = "critical"

        # Calculate utilization percentage
        utilization = min(active_tasks / max_workers, 1.0) if max_workers > 0 else 0.0

        # Calculate average queue wait time if available
        worker_types = worker_stats.get("worker_types", {})

        self._last_value = wsi
        self._last_metadata = {
            "wsi": round(wsi, 4),
            "saturation_level": saturation_level,
            "active_tasks": active_tasks,
            "pending_tasks": pending_tasks,
            "total_load": total_load,
            "max_workers": max_workers,
            "utilization_percent": round(utilization * 100, 2),
            "worker_types": worker_types,
        }

        return wsi

    def get_metadata(self) -> Dict[str, Any]:
        """Return worker saturation details"""
        return self._last_metadata
