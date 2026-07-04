"""Vector store adapter wrapper for RAE-Server.

Configures RAE-core QdrantVectorStore with RAE-Server settings.
"""

from typing import Any, cast

from qdrant_client import AsyncQdrantClient

from rae_core.adapters import QdrantVectorStore


def get_vector_adapter(
    client: AsyncQdrantClient,
    collection_name: str = "rae_vectors",
    dimension: int = 384,
) -> QdrantVectorStore:
    """Get configured Qdrant vector store adapter.

    Args:
        client: Qdrant async client from RAE-Server
        collection_name: Collection name (default: "rae_vectors")
        dimension: Vector dimension (default: 384 for all-MiniLM-L6-v2)

    Returns:
        Configured QdrantVectorStore instance
    """
    return QdrantVectorStore(
        client=cast(Any, client),
        collection_name=collection_name,
        embedding_dim=dimension,
    )
