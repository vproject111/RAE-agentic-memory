from typing import Any, List, Optional, Tuple, cast
from uuid import UUID

import asyncpg

from rae_core.interfaces.vector import IVectorStore


class PostgresVectorAdapter(IVectorStore):
    """
    Adapter for PGVectorStore to implement RAE-Core IVectorStore interface.
    """

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def store_vector(
        self,
        memory_id: UUID,
        embedding: List[float] | dict[str, List[float]],
        tenant_id: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        async with self.pool.acquire() as conn:
            # Handle both list and dict input
            if isinstance(embedding, dict):
                if not embedding:
                    return False
                # For Postgres/pgvector (legacy single column), we take the first one
                # Ideally, we should store all in `memory_embeddings` table, but
                # this adapter targets the main `memories` table column.
                vector_values = next(iter(embedding.values()))
            else:
                vector_values = embedding

            # Convert to pgvector format
            emb_str = "[" + ",".join(map(str, vector_values)) + "]"
            await conn.execute(
                "UPDATE memories SET embedding = $1 WHERE id = $2 AND tenant_id = $3",
                emb_str,
                memory_id,
                tenant_id,
            )
        return True

    async def search_similar(
        self,
        query_embedding: List[float],
        tenant_id: str,
        layer: Optional[str] = None,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        agent_id: Optional[str] = None,
    ) -> List[Tuple[UUID, float]]:
        # Convert embedding to string format for pgvector
        emb_str = "[" + ",".join(map(str, query_embedding)) + "]"

        # Build query
        query = """
            SELECT id, 1 - (embedding <=> $1) AS score
            FROM memories
            WHERE tenant_id = $2 AND embedding IS NOT NULL
        """
        params: List[Any] = [emb_str, tenant_id]

        if layer:
            query += " AND layer = $3"
            params.append(layer)

        if score_threshold is not None:
            query += f" AND 1 - (embedding <=> $1) >= ${len(params) + 1}"
            params.append(score_threshold)

        query += f" ORDER BY score DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [(row["id"], float(row["score"])) for row in rows]

    async def delete_vector(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE memories SET embedding = NULL WHERE id = $1 AND tenant_id = $2",
                memory_id,
                tenant_id,
            )
        return True

    async def update_vector(
        self,
        memory_id: UUID,
        embedding: List[float] | dict[str, List[float]],
        tenant_id: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        return await self.store_vector(memory_id, embedding, tenant_id, metadata)

    async def get_vector(
        self, memory_id: UUID, tenant_id: str
    ) -> Optional[List[float]]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT embedding FROM memories WHERE id = $1 AND tenant_id = $2",
                memory_id,
                tenant_id,
            )
            if row and row["embedding"]:
                # pgvector returns a string or list depending on driver setup
                if isinstance(row["embedding"], str):
                    import json

                    return cast(
                        List[float],
                        json.loads(
                            row["embedding"].replace("{", "[").replace("}", "]")
                        ),
                    )
                return list(row["embedding"])
        return None

    async def batch_store_vectors(
        self,
        vectors: List[Tuple[UUID, List[float], dict]],
        tenant_id: str,
    ) -> int:
        data = []
        for mid, emb, meta in vectors:
            emb_str = "[" + ",".join(map(str, emb)) + "]"
            data.append((emb_str, mid, tenant_id))

        async with self.pool.acquire() as conn:
            await conn.executemany(
                "UPDATE memories SET embedding = $1 WHERE id = $2 AND tenant_id = $3",
                data,
            )
        return len(vectors)
