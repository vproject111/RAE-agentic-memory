"""In-Memory adapters for RAE-core.

Fast, thread-safe implementations for testing and lightweight deployments.
"""

from .cache import InMemoryCache
from .storage import InMemoryStorage
from .vector import InMemoryVectorStore

__all__ = [
    "InMemoryStorage",
    "InMemoryVectorStore",
    "InMemoryCache",
]
