"""Storage and service adapters for RAE-core.

This module provides concrete implementations of the abstract interfaces:
- PostgreSQLStorage: IMemoryStorage implementation using asyncpg
- QdrantVectorStore: IVectorStore implementation using Qdrant
- RedisCache: ICacheProvider implementation using Redis
- SQLiteStorage: IMemoryStorage implementation using SQLite (Phase 1)
- SQLiteVectorStore: IVectorStore implementation using SQLite (Phase 1)
- InMemoryStorage: IMemoryStorage for testing (Phase 1)
- InMemoryVectorStore: IVectorStore for testing (Phase 1)
- InMemoryCache: ICacheProvider for testing (Phase 1)

Adapters follow dependency injection pattern for easy testing and swapping.
"""

from .memory.cache import InMemoryCache
from .memory.storage import InMemoryStorage
from .memory.vector import InMemoryVectorStore
from .postgres import PostgreSQLStorage
from .qdrant import QdrantVectorStore
from .redis import RedisCache
from .sqlite.storage import SQLiteStorage
from .sqlite.vector import SQLiteVectorStore

# Aliases for backwards compatibility
PostgresMemoryAdapter = PostgreSQLStorage
QdrantVectorAdapter = QdrantVectorStore
RedisCacheAdapter = RedisCache

__all__ = [
    "PostgreSQLStorage",
    "QdrantVectorStore",
    "RedisCache",
    "SQLiteStorage",
    "SQLiteVectorStore",
    "InMemoryStorage",
    "InMemoryVectorStore",
    "InMemoryCache",
    # Aliases
    "PostgresMemoryAdapter",
    "QdrantVectorAdapter",
    "RedisCacheAdapter",
]
