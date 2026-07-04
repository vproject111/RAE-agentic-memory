"""Qdrant vector store adapter for RAE-core.

Implements IVectorStore interface using Qdrant for similarity search.
"""

from typing import Any, cast
from uuid import UUID

try:
    from qdrant_client import AsyncQdrantClient, QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams
except ImportError:  # pragma: no cover
    QdrantClient = Any  # type: ignore # pragma: no cover
    AsyncQdrantClient = Any  # type: ignore # pragma: no cover

from rae_core.interfaces.vector import IVectorStore


class QdrantVectorStore(IVectorStore):
    """Qdrant implementation of IVectorStore.

    Requires qdrant-client package and access to Qdrant server.

    Collection schema:
    - Vectors: embeddings (dimension configurable, default 1536 for OpenAI)
    - Payload: {
        memory_id: UUID,
        tenant_id: str,
        agent_id: str,
        session_id: str,
        layer: str,
        content: str (optional, for debugging),
        importance: float,
        created_at: timestamp
      }
    """

    def __init__(
        self,
        collection_name: str = "memories",
        url: str | None = None,
        api_key: str | None = None,
        client: Any | None = None,
        embedding_dim: int = 384,
        distance: str = "Cosine",
    ):
        """Initialize Qdrant vector store.

        Args:
            collection_name: Name of Qdrant collection
            url: Qdrant server URL (e.g., http://localhost:6333)
            api_key: Optional API key for Qdrant Cloud
            client: Existing QdrantClient or AsyncQdrantClient instance
            embedding_dim: Dimension of embeddings (default: 1536 for OpenAI)
            distance: Distance metric (Cosine, Euclid, Dot)
        """
        if QdrantClient is None:
            raise ImportError(
                "qdrant-client is required for QdrantVectorStore. "
                "Install with: pip install qdrant-client"
            )

        self.collection_name = collection_name
        self.embedding_dim = embedding_dim

        # Distance metric mapping
        distance_map = {
            "Cosine": Distance.COSINE,
            "Euclid": Distance.EUCLID,
            "Dot": Distance.DOT,
        }
        self.distance = distance_map.get(distance, Distance.COSINE)

        if client:
            self.client = client
        elif url:
            # Default to Async client if not provided but url is?
            # Original code used QdrantClient (sync).
            # To support async by default for this adapter when used in async context:
            # But here we stick to what was passed or default.
            # If we want async, we should probably default to AsyncQdrantClient if we can?
            # For now, let's keep it sync by default if no client passed, to avoid breaking other usages?
            # But wait, RAE-Core might be used in sync context?
            # The adapter methods are `async def`, so they imply async usage.
            # So `self.client` SHOULD be async for `await` to work.

            # If we initialize it ourselves, we should use AsyncQdrantClient.
            self.client = AsyncQdrantClient(url=url, api_key=api_key)
        else:
            # Use in-memory mode for testing
            self.client = AsyncQdrantClient(":memory:")

        self._initialized = False

    async def _ensure_collection(self) -> None:
        """Ensure collection exists with proper schema."""
        if self._initialized:
            return

        try:
            await self.client.get_collection(self.collection_name)
        except Exception:
            # Collection doesn't exist, create it
            from qdrant_client.models import SparseVectorParams

            # Multi-vector configuration to support various models
            vectors_config = {
                "dense": VectorParams(
                    size=384,  # Default/MiniLM
                    distance=self.distance,
                ),
                "openai": VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small/large
                    distance=self.distance,
                ),
                "ollama": VectorParams(
                    size=768,  # Nomic-embed-text
                    distance=self.distance,
                ),
                "cohere": VectorParams(
                    size=1024,  # Cohere/Jina
                    distance=self.distance,
                ),
            }

            # If the initialized dimension doesn't match standard buckets, add it as custom
            if self.embedding_dim not in [384, 768, 1024, 1536]:
                vectors_config["custom"] = VectorParams(
                    size=self.embedding_dim,
                    distance=self.distance,
                )

            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=vectors_config,
                # Default configuration for hybrid search (dense + sparse)
                sparse_vectors_config={"text": SparseVectorParams()},
            )

        self._initialized = True

    def _get_vector_name(self, dim: int) -> str:
        """Determine vector name based on dimension."""
        if dim == 1536:
            return "openai"
        elif dim == 768:
            return "ollama"
        elif dim == 384:
            return "dense"
        elif dim == 1024:
            return "cohere"
        # If unknown dimension but matches init dim, use custom or dense fallback
        if dim == self.embedding_dim and self.embedding_dim not in [
            384,
            768,
            1024,
            1536,
        ]:
            return "custom"
        return "dense"  # Fallback

    async def add_vector(
        self,
        memory_id: UUID,
        embedding: list[float] | dict[str, list[float]],
        tenant_id: str,
        agent_id: str,
        layer: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> bool:
        """Add a vector to Qdrant."""
        await self._ensure_collection()

        metadata = metadata or {}

        payload = {
            "memory_id": str(memory_id),
            "tenant_id": tenant_id,
            "agent_id": agent_id,
            "session_id": session_id or metadata.get("session_id", "default"),
            "layer": layer,
            **metadata,
        }

        if isinstance(embedding, dict):
            # Already mapped to named vectors
            vector_data = embedding
        else:
            # Single vector, map by dimension
            vector_name = self._get_vector_name(len(embedding))
            vector_data = {vector_name: embedding}

        try:
            await self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=str(memory_id),
                        vector=vector_data,
                        payload=payload,
                    )
                ],
            )
            return True
        except Exception:
            return False

    async def store_vector(
        self,
        memory_id: UUID,
        embedding: list[float] | dict[str, list[float]],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Store a vector embedding."""
        metadata = metadata or {}
        agent_id = str(metadata.get("agent_id", "default"))
        session_id = str(metadata.get("session_id", "default"))
        layer = str(metadata.get("layer", "episodic"))
        return await self.add_vector(
            memory_id, embedding, tenant_id, agent_id, layer, metadata, session_id
        )

    async def update_vector(
        self,
        memory_id: UUID,
        embedding: list[float] | dict[str, list[float]],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a vector embedding."""
        return await self.store_vector(memory_id, embedding, tenant_id, metadata)

    async def batch_store_vectors(
        self,
        vectors: list[tuple[UUID, list[float], dict[str, Any]]],
        tenant_id: str,
    ) -> int:
        """Store multiple vectors in a batch."""
        await self._ensure_collection()

        points = []
        for memory_id, embedding, metadata in vectors:
            meta = metadata or {}
            agent_id = str(meta.get("agent_id", "default"))
            session_id = str(meta.get("session_id", "default"))
            layer = str(meta.get("layer", "episodic"))

            payload = {
                "memory_id": str(memory_id),
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "session_id": session_id,
                "layer": layer,
                **meta,
            }

            vector_name = self._get_vector_name(len(embedding))

            points.append(
                PointStruct(
                    id=str(memory_id), vector={vector_name: embedding}, payload=payload
                )
            )

        if not points:
            return 0

        try:
            await self.client.upsert(
                collection_name=self.collection_name, points=points
            )
            return len(points)
        except Exception:
            return 0

    async def search_similar(
        self,
        query_embedding: list[float],
        tenant_id: str,
        layer: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
    ) -> list[tuple[UUID, float]]:
        """Search for similar vectors using cosine similarity.

        Args:
            query_embedding: Query vector
            tenant_id: Tenant ID (mandatory for multi-tenancy)
            layer: Optional memory layer filter
            limit: Maximum results to return
            score_threshold: Minimum similarity score
            agent_id: Optional agent ID for namespace isolation
            session_id: Optional session ID for namespace isolation
        """
        await self._ensure_collection()

        # Build filter - mandatory tenant_id
        must_conditions = [{"key": "tenant_id", "match": {"value": tenant_id}}]

        # Add agent_id filter if provided (namespace isolation)
        if agent_id:
            must_conditions.append({"key": "agent_id", "match": {"value": agent_id}})

        # Add session_id filter if provided (namespace isolation)
        if session_id:
            must_conditions.append(
                {"key": "session_id", "match": {"value": session_id}}
            )

        if layer:
            must_conditions.append({"key": "layer", "match": {"value": layer}})

        query_filter = {"must": must_conditions} if must_conditions else None

        vector_name = self._get_vector_name(len(query_embedding))

        try:
            from qdrant_client.models import NamedVector

            results = await self.client.search(
                collection_name=self.collection_name,
                query_vector=NamedVector(name=vector_name, vector=query_embedding),
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                (UUID(result.payload["memory_id"]), result.score)
                for result in results
                if result.payload and "memory_id" in result.payload
            ]
        except Exception:
            return []

    async def get_vector(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> list[float] | None:
        """Get vector by memory ID."""
        await self._ensure_collection()

        try:
            result = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[str(memory_id)],
            )

            if result and len(result) > 0:
                # Verify tenant_id matches
                payload = result[0].payload
                if payload and payload.get("tenant_id") == tenant_id:
                    return cast(list[float], result[0].vector)
        except Exception:
            pass

        return None

    async def delete_vector(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Delete a vector."""
        await self._ensure_collection()

        try:
            # First verify it belongs to tenant
            result = await self.client.retrieve(
                collection_name=self.collection_name,
                ids=[str(memory_id)],
            )

            if not result:
                return False

            payload = result[0].payload
            if not payload or payload.get("tenant_id") != tenant_id:
                return False

            from qdrant_client.models import PointIdsList

            await self.client.delete(
                collection_name=self.collection_name,
                points_selector=PointIdsList(points=[str(memory_id)]),
            )
            return True
        except Exception:
            return False

    async def delete_by_layer(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
    ) -> int:
        """Delete all vectors in a layer."""
        await self._ensure_collection()

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Use filter to delete
            delete_filter = Filter(
                must=[
                    FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
                    FieldCondition(key="agent_id", match=MatchValue(value=agent_id)),
                    FieldCondition(key="layer", match=MatchValue(value=layer)),
                ]
            )

            result = await self.client.delete(
                collection_name=self.collection_name,
                points_selector=delete_filter,
            )

            # Qdrant doesn't return count easily, return success indicator
            return 1 if result else 0
        except Exception:
            return 0

    async def count_vectors(
        self,
        tenant_id: str,
        layer: str | None = None,
    ) -> int:
        """Count vectors matching criteria."""
        await self._ensure_collection()

        try:
            count_filter = {
                "must": [{"key": "tenant_id", "match": {"value": tenant_id}}]
            }

            if layer:
                count_filter["must"].append({"key": "layer", "match": {"value": layer}})

            result = await self.client.count(
                collection_name=self.collection_name,
                count_filter=count_filter,
            )

            return result.count if result else 0
        except Exception:
            return 0

    async def search_with_contradiction_penalty(
        self,
        query_embedding: list[float],
        tenant_id: str,
        layer: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
        agent_id: str | None = None,
        session_id: str | None = None,
        penalty_factor: float = 0.5,
        contradiction_threshold: float = 0.15,
    ) -> list[tuple[UUID, float]]:
        """Search with penalty for contradictory results.

        This method:
        1. Performs similarity search
        2. Detects contradictory pairs in results
        3. Penalizes both contradictory memories
        4. Re-sorts by penalized scores

        Contradictory detection:
        - If cosine similarity < contradiction_threshold, memories contradict
        - Low similarity in embedding space suggests opposite meanings

        Args:
            query_embedding: Query vector
            tenant_id: Tenant ID (mandatory)
            layer: Optional memory layer filter
            limit: Maximum results (will fetch more for filtering)
            score_threshold: Minimum similarity score
            agent_id: Optional agent ID for namespace isolation
            session_id: Optional session ID for namespace isolation
            penalty_factor: Multiplier for contradictory scores (default: 0.5)
            contradiction_threshold: Similarity below this = contradiction

        Returns:
            List of (memory_id, penalized_score) tuples sorted by score

        Example:
            >>> results = await store.search_with_contradiction_penalty(
            ...     query_embedding=embedding,
            ...     tenant_id="tenant1",
            ...     penalty_factor=0.5,  # Halve contradictory scores
            ...     contradiction_threshold=0.15,  # <0.15 similarity = contradiction
            ... )
        """
        # Fetch more results for contradiction detection
        initial_results = await self.search_similar(
            query_embedding=query_embedding,
            tenant_id=tenant_id,
            layer=layer,
            limit=limit * 2,  # Fetch extra for filtering
            score_threshold=score_threshold,
            agent_id=agent_id,
            session_id=session_id,
        )

        if len(initial_results) < 2:
            # Not enough results for contradiction detection
            return initial_results[:limit]

        # Retrieve vectors for all results
        result_vectors: dict[UUID, list[float]] = {}
        for memory_id, _ in initial_results:
            vector = await self.get_vector(memory_id=memory_id, tenant_id=tenant_id)
            if vector:
                result_vectors[memory_id] = vector

        # Detect contradictions and build penalty map
        penalties: dict[UUID, int] = {}  # Count of contradictions per memory

        for i, (mem_a_id, _) in enumerate(initial_results):
            if mem_a_id not in result_vectors:
                continue

            for mem_b_id, _ in initial_results[i + 1 :]:
                if mem_b_id not in result_vectors:
                    continue

                # Compute cosine similarity between the two vectors
                vec_a = result_vectors[mem_a_id]
                vec_b = result_vectors[mem_b_id]
                similarity = self._cosine_similarity(vec_a, vec_b)

                # If similarity is very low, they contradict
                if similarity < contradiction_threshold:
                    penalties[mem_a_id] = penalties.get(mem_a_id, 0) + 1
                    penalties[mem_b_id] = penalties.get(mem_b_id, 0) + 1

        # Apply penalties to scores
        penalized_results = []
        for memory_id, base_score in initial_results:
            penalty_count = penalties.get(memory_id, 0)
            if penalty_count > 0:
                # Apply penalty: score *= penalty_factor^penalty_count
                penalized_score = base_score * (penalty_factor**penalty_count)
            else:
                penalized_score = base_score

            penalized_results.append((memory_id, penalized_score))

        # Re-sort by penalized scores
        penalized_results.sort(key=lambda x: x[1], reverse=True)

        return penalized_results[:limit]

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec_a: First vector
            vec_b: Second vector

        Returns:
            Cosine similarity (-1 to 1, higher = more similar)
        """
        if len(vec_a) != len(vec_b):
            return 0.0

        # Dot product
        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))

        # Magnitudes
        mag_a = sum(a * a for a in vec_a) ** 0.5
        mag_b = sum(b * b for b in vec_b) ** 0.5

        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0

        return float(dot_product / (mag_a * mag_b))

    async def close(self) -> None:
        """Close Qdrant client."""
        if hasattr(self.client, "close"):
            await self.client.close()
