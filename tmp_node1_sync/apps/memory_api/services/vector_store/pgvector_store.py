from typing import Any, Dict, List

import asyncpg
import numpy as np

from apps.memory_api.metrics import vector_query_time_histogram
from apps.memory_api.models import MemoryRecord, ScoredMemoryRecord
from apps.memory_api.services.vector_store.base import MemoryVectorStore


class PGVectorStore(MemoryVectorStore):
    """
    A vector store implementation using pgvector in PostgreSQL.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def upsert(
        self, memories: List[MemoryRecord], embeddings: List[List[float]]
    ) -> None:
        """
        Upserts a list of memories and their embeddings into the database.
        """
        if len(memories) != len(embeddings):
            raise ValueError("The number of memories and embeddings must be the same.")

        async with self.pool.acquire() as conn:
            for memory, embedding in zip(memories, embeddings):
                # pgvector expects a numpy array
                embedding_np = np.array(embedding)
                await conn.execute(
                    "UPDATE memories SET embedding = $1 WHERE id = $2",
                    embedding_np,
                    memory.id,
                )

    @vector_query_time_histogram.time()
    async def query(
        self, query_embedding: List[float], top_k: int, filters: Dict[str, Any]
    ) -> List[ScoredMemoryRecord]:
        """
        Queries the database for similar memories using cosine similarity.
        Filters are not yet implemented for pgvector in this implementation.
        """
        embedding_np = np.array(query_embedding)

        # The <=> operator performs cosine similarity search
        records = await self.pool.fetch(
            "SELECT *, 1 - (embedding <=> $1) AS score FROM memories ORDER BY score DESC LIMIT $2",
            embedding_np,
            top_k,
        )

        return [ScoredMemoryRecord(**dict(r)) for r in records]

    async def delete(self, memory_id: str) -> None:
        """
        Deletes a memory's embedding by setting it to NULL.
        The memory record itself is not deleted here.
        """
        await self.pool.execute(
            "UPDATE memories SET embedding = NULL WHERE id = $1", memory_id
        )
