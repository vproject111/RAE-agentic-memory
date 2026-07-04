"""RAE-Server adapter wrappers.

Thin wrappers around RAE-core adapters configured with RAE-Server settings.
These adapters integrate RAE-core with RAE-Server's infrastructure.
"""

from .cache import get_cache_adapter
from .storage import get_storage_adapter
from .vector import get_vector_adapter

__all__ = [
    "get_cache_adapter",
    "get_storage_adapter",
    "get_vector_adapter",
]
