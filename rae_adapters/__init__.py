"""
RAE Adapters Package.
Contains storage, vector store, and cache adapters for the RAE system.
"""

from .memory.cache import InMemoryCache
from .memory.storage import InMemoryStorage
from .memory.vector import InMemoryVectorStore
from .postgres_adapter import PostgresAdapter as PostgreSQLStorage
from .qdrant_adapter import QdrantAdapter as QdrantVectorStore
from .redis_adapter import RedisAdapter as RedisCache
from .sqlite.storage import SQLiteStorage
from .sqlite.vector import SQLiteVectorStore
from .openapi_adapter import OpenAPIAdapter, OpenAPIQueryParams
from .git_adapter import GitRuntimeAdapter
from .rae_memory_adapter import RAEAgenticMemoryAdapter, RAEMemoryQueryParams

# Aliases for backwards compatibility
PostgreSQLStorage = PostgreSQLStorage
RedisCache = RedisCache
QdrantStore = QdrantVectorStore
QdrantVectorStore = QdrantVectorStore
PostgresAdapter = PostgreSQLStorage
QdrantAdapter = QdrantVectorStore
RedisAdapter = RedisCache
