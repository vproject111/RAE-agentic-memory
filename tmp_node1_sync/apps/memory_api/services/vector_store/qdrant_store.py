import asyncio
import hashlib
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import structlog
from qdrant_client import QdrantClient, models
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Optional ML dependencies
try:  # pragma: no cover
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:  # pragma: no cover
    SentenceTransformer = None  # type: ignore[assignment,misc]
    SENTENCE_TRANSFORMERS_AVAILABLE = False

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer  # noqa: F401

from ...config import settings
from ...metrics import vector_query_time_histogram
from ...models import MemoryRecord, ScoredMemoryRecord
from .base import MemoryVectorStore

logger = structlog.get_logger(__name__)


class QdrantStore(MemoryVectorStore):
    """
    A vector store implementation using Qdrant (Thread-safe Async).
    """

    def __init__(self, client: Optional[QdrantClient] = None):
        if client:
            self.qdrant_client = client
        else:
            self.qdrant_client = QdrantClient(
                host=settings.QDRANT_HOST, port=settings.QDRANT_PORT
            )
        self._initialized = False

    async def ainit(self):
        if self._initialized:
            return
        await asyncio.to_thread(self.ensure_collection_exists)
        self._initialized = True

    def ensure_collection_exists(self):
        collection_name = "memories"
        try:
            from apps.memory_api.services.embedding import (
                LocalEmbeddingProvider,
                get_embedding_service,
            )

            try:
                embedding_service = get_embedding_service()
                provider = LocalEmbeddingProvider(embedding_service)
                dimension = provider.get_dimension()
            except Exception:
                dimension = 384

            collections_resp = self.qdrant_client.get_collections()
            collections = collections_resp.collections
            exists = any(c.name == collection_name for c in collections)

            if not exists:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config={
                        "dense": models.VectorParams(
                            size=dimension, distance=models.Distance.COSINE
                        ),
                        "openai": models.VectorParams(
                            size=1536, distance=models.Distance.COSINE
                        ),
                        "ollama": models.VectorParams(
                            size=768, distance=models.Distance.COSINE
                        ),
                    },
                    sparse_vectors_config={"text": models.SparseVectorParams()},
                )
        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {e}")

    def _get_sparse_vector(self, text: str) -> models.SparseVector:
        words = text.lower().split()
        index_values: Dict[int, float] = {}
        for word in set(words):
            index = (
                int(hashlib.md5(word.encode(), usedforsecurity=False).hexdigest(), 16)
                % 100000
            )
            index_values[index] = index_values.get(index, 0.0) + 1.0
        indices = sorted(index_values.keys())
        values = [index_values[i] for i in indices]
        return models.SparseVector(indices=indices, values=values)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def upsert(self, memories: List[MemoryRecord], embeddings: List[Any]):
        if not self._initialized:
            await self.ainit()
        return await asyncio.to_thread(self._sync_upsert, memories, embeddings)

    def _sync_upsert(self, memories: List[MemoryRecord], embeddings: List[Any]):
        points_to_upsert = []
        for memory, embedding in zip(memories, embeddings):
            sparse_vector = self._get_sparse_vector(memory.content)
            if isinstance(embedding, dict):
                vector_payload = embedding
                vector_payload["text"] = sparse_vector
            else:
                vector_payload = {"dense": embedding, "text": sparse_vector}

            points_to_upsert.append(
                models.PointStruct(
                    id=str(memory.id),
                    vector=vector_payload,
                    payload=memory.model_dump(),
                )
            )
        self.qdrant_client.upsert(
            collection_name="memories", points=points_to_upsert, wait=True
        )

    @vector_query_time_histogram.time()
    async def query(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Dict[str, Any],
        vector_name: str = "dense",
    ) -> List[ScoredMemoryRecord]:
        if not self._initialized:
            await self.ainit()
        return await asyncio.to_thread(
            self._sync_query, query_embedding, top_k, filters, vector_name
        )

    def _sync_query(
        self,
        query_embedding: List[float],
        top_k: int,
        filters: Dict[str, Any],
        vector_name: str,
    ) -> List[ScoredMemoryRecord]:
        qdrant_filters = models.Filter(**filters) if filters else None

        # Use query_points with the most compatible signature for 1.11+
        try:
            # Try new query_points API first
            query_response = self.qdrant_client.query_points(
                collection_name="memories",
                query=query_embedding,  # Bare list for the default/single vector, or specific for named
                using=vector_name,
                query_filter=qdrant_filters,
                limit=top_k,
                with_payload=True,
            )
            return [
                ScoredMemoryRecord(score=point.score, **point.payload)
                for point in query_response.points
                if point.payload
            ]
        except Exception:
            # Fallback to legacy search
            legacy_results = self.qdrant_client.search(
                collection_name="memories",
                query_vector=models.NamedVector(
                    name=vector_name, vector=query_embedding
                ),
                query_filter=qdrant_filters,
                limit=top_k,
                with_payload=True,
            )
            return [
                ScoredMemoryRecord(score=point.score, **point.payload)
                for point in legacy_results
                if point.payload
            ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def delete(self, memory_id: str):
        if not self._initialized:
            await self.ainit()
        await asyncio.to_thread(
            self.qdrant_client.delete,
            collection_name="memories",
            points_selector=models.PointIdsList(points=[memory_id]),
        )
