"""In-Memory vector store adapter for RAE-core.

Simple vector storage with cosine similarity search using NumPy.
Ideal for testing, development, and lightweight deployments.
"""

import asyncio
import sys
from collections import defaultdict
from typing import Any, cast
from uuid import UUID

# Robust NumPy import to avoid re-import warnings
if "numpy" in sys.modules:
    np = sys.modules["numpy"]  # pragma: no cover
else:  # pragma: no cover
    import numpy as np  # pragma: no cover

from rae_core.interfaces.vector import IVectorStore


class InMemoryVectorStore(IVectorStore):
    """In-memory implementation of IVectorStore using NumPy.

    Features:
    - Fast NumPy-based cosine similarity search
    - Thread-safe operations with asyncio.Lock
    - Metadata storage alongside vectors
    - Layer filtering support
    - Batch operations
    """

    def __init__(self) -> None:
        """Initialize in-memory vector store."""
        # Main storage: {memory_id: vector_data}
        # vector_data = {"embedding": np.array, "tenant_id": str, "metadata": dict}
        self._vectors: dict[UUID, dict[str, Any]] = {}

        # Indexes for fast lookups
        self._by_tenant: dict[str, set[UUID]] = defaultdict(set)

        # Thread safety
        self._lock = asyncio.Lock()

    async def store_vector(
        self,
        memory_id: UUID,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store a vector embedding."""
        async with self._lock:
            vector_data = {
                "embedding": np.array(embedding, dtype=np.float32),
                "tenant_id": tenant_id,
                "metadata": metadata or {},
            }

            self._vectors[memory_id] = vector_data
            self._by_tenant[tenant_id].add(memory_id)

            return True

    async def search_similar(
        self,
        query_embedding: list[float],
        tenant_id: str,
        layer: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[tuple[UUID, float]]:
        """Search for similar vectors using cosine similarity."""
        async with self._lock:
            # Get candidate vectors for tenant
            candidate_ids = self._by_tenant[tenant_id]

            if not candidate_ids:
                return []

            # Convert query to numpy array and normalize
            query_vec = np.array(query_embedding, dtype=np.float32)
            query_norm = np.linalg.norm(query_vec)

            if query_norm == 0:
                return []

            query_vec_normalized = query_vec / query_norm

            # Calculate similarities
            results = []

            for memory_id in candidate_ids:
                vector_data = self._vectors.get(memory_id)
                if not vector_data:  # pragma: no cover
                    continue  # pragma: no cover

                # Apply layer filter if specified
                if layer:
                    vector_layer = vector_data["metadata"].get("layer")
                    if vector_layer != layer:
                        continue

                # Calculate cosine similarity
                vec = vector_data["embedding"]
                vec_norm = np.linalg.norm(vec)

                if vec_norm == 0:
                    continue

                vec_normalized = vec / vec_norm
                similarity = float(np.dot(query_vec_normalized, vec_normalized))

                # Apply threshold filter
                if score_threshold is not None and similarity < score_threshold:
                    continue

                results.append((memory_id, similarity))

            # Sort by similarity (descending) and limit
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

    async def delete_vector(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Delete a vector."""
        async with self._lock:
            vector_data = self._vectors.get(memory_id)

            if not vector_data or vector_data["tenant_id"] != tenant_id:
                return False

            # Remove from indexes
            self._by_tenant[tenant_id].discard(memory_id)

            # Remove vector
            del self._vectors[memory_id]

            return True

    async def update_vector(
        self,
        memory_id: UUID,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a vector embedding."""
        async with self._lock:
            vector_data = self._vectors.get(memory_id)

            if not vector_data or vector_data["tenant_id"] != tenant_id:
                return False

            # Update embedding
            vector_data["embedding"] = np.array(embedding, dtype=np.float32)

            # Update metadata if provided
            if metadata is not None:
                vector_data["metadata"] = metadata

            return True

    async def get_vector(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> list[float] | None:
        """Retrieve a vector embedding."""
        async with self._lock:
            vector_data = self._vectors.get(memory_id)

            if not vector_data or vector_data["tenant_id"] != tenant_id:
                return None

            # Convert numpy array back to list
            return cast(list[float], vector_data["embedding"].tolist())

    async def batch_store_vectors(
        self,
        vectors: list[tuple[UUID, list[float], dict[str, Any]]],
        tenant_id: str,
    ) -> int:
        """Store multiple vectors in a batch."""
        async with self._lock:
            count = 0

            for memory_id, embedding, metadata in vectors:
                try:
                    vector_data = {
                        "embedding": np.array(embedding, dtype=np.float32),
                        "tenant_id": tenant_id,
                        "metadata": metadata,
                    }

                    self._vectors[memory_id] = vector_data
                    self._by_tenant[tenant_id].add(memory_id)

                    count += 1
                except Exception:
                    # Skip invalid vectors
                    continue

            return count

    async def search_similar_batch(
        self,
        query_embeddings: list[list[float]],
        tenant_id: str,
        layer: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[list[tuple[UUID, float]]]:
        """Search for similar vectors for multiple queries.

        Args:
            query_embeddings: List of query vectors
            tenant_id: Tenant identifier
            layer: Optional layer filter
            limit: Maximum results per query
            score_threshold: Optional minimum similarity score

        Returns:
            List of result lists, one per query
        """
        results = []

        for query_embedding in query_embeddings:
            result = await self.search_similar(
                query_embedding=query_embedding,
                tenant_id=tenant_id,
                layer=layer,
                limit=limit,
                score_threshold=score_threshold,
            )
            results.append(result)

        return results

    async def clear_tenant(self, tenant_id: str) -> int:
        """Clear all vectors for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Number of vectors deleted
        """
        async with self._lock:
            memory_ids = self._by_tenant[tenant_id].copy()

            for memory_id in memory_ids:
                if memory_id in self._vectors:
                    del self._vectors[memory_id]

            del self._by_tenant[tenant_id]

            return len(memory_ids)

    async def get_statistics(self) -> dict[str, Any]:
        """Get vector store statistics.

        Returns:
            Dictionary with statistics
        """
        async with self._lock:
            total_vectors = len(self._vectors)
            tenants = len(self._by_tenant)

            # Calculate dimension distribution
            dimensions = set()
            for vector_data in self._vectors.values():
                dimensions.add(len(vector_data["embedding"]))

            return {
                "total_vectors": total_vectors,
                "tenants": tenants,
                "dimensions": sorted(dimensions) if dimensions else [],
            }

    async def clear_all(self) -> int:
        """Clear all data (use with caution!).

        Returns:
            Number of vectors deleted
        """
        async with self._lock:
            count = len(self._vectors)

            self._vectors.clear()
            self._by_tenant.clear()

            return count
