# sdk/python/rae_memory_sdk/__init__.py

from .client import AsyncRAEClient, MemoryClient, RAEClient
from .decorators import trace_memory
from .models import (
    DeleteMemoryRequest,
    DeleteMemoryResponse,
    MemoryLayer,
    MemoryRecord,
    QueryMemoryRequest,
    QueryMemoryResponse,
    ScoredMemoryRecord,
    StoreMemoryRequest,
    StoreMemoryResponse,
)

__version__ = "2.0.0"

__all__ = [
    # Client classes
    "MemoryClient",  # Legacy name
    "RAEClient",  # Primary name (sync + async)
    "AsyncRAEClient",  # Alias for documentation
    # Models
    "MemoryLayer",
    "MemoryRecord",
    "ScoredMemoryRecord",
    "StoreMemoryRequest",
    "StoreMemoryResponse",
    "QueryMemoryRequest",
    "QueryMemoryResponse",
    "DeleteMemoryRequest",
    "DeleteMemoryResponse",
    # Decorators
    "trace_memory",
]
