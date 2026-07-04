"""
Observability Metrics Exports.
This module re-exports metrics defined in the central apps.memory_api.metrics module
to maintain backward compatibility and avoid duplication.
"""

from apps.memory_api.metrics import rae_active_sessions as active_sessions
from apps.memory_api.metrics import rae_api_requests_total as api_requests_total
from apps.memory_api.metrics import rae_errors_total as api_errors_total
from apps.memory_api.metrics import rae_memory_count_total as memories_stored_total
from apps.memory_api.metrics import (
    rae_reflection_processing_seconds as reflection_processing_seconds,
)
from apps.memory_api.metrics import (
    rae_sync_last_success_timestamp as sync_last_success_timestamp,
)
from apps.memory_api.metrics import rae_uptime_seconds as uptime_seconds

__all__ = [
    "uptime_seconds",
    "memories_stored_total",
    "sync_last_success_timestamp",
    "active_sessions",
    "reflection_processing_seconds",
    "api_errors_total",
    "api_requests_total",
]
