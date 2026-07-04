"""PostgreSQL storage adapter for RAE-core.

Implements IMemoryStorage interface using asyncpg for async PostgreSQL access.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional, cast
from uuid import UUID, uuid4

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None  # pragma: no cover

from rae_core.interfaces.storage import IMemoryStorage


class PostgreSQLStorage(IMemoryStorage):
    """PostgreSQL implementation of IMemoryStorage.

    Requires asyncpg package and PostgreSQL 12+ with:
    - UUID extension
    - JSONB support
    - Optional: pgvector extension for embedding storage

    Schema expected:
    ```sql
    CREATE TABLE memories (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        content TEXT NOT NULL,
        layer TEXT NOT NULL,
        tenant_id TEXT NOT NULL,
        agent_id TEXT NOT NULL,
        project TEXT,      -- Added in v2.7.0 (Phase 1)
        session_id TEXT,   -- Added in v2.7.0 (Phase 1)
        source TEXT,       -- Added in v2.7.0 (Phase 1)
        info_class TEXT DEFAULT 'internal', -- Added in v2.9.0 (Phase 2)
        governance JSONB DEFAULT '{}',      -- Added in v2.9.0 (Phase 2)
        memory_type TEXT DEFAULT 'text',
        tags TEXT[] DEFAULT '{}',
        metadata JSONB DEFAULT '{}',
        embedding VECTOR(1536),  -- Optional, requires pgvector
        importance FLOAT DEFAULT 0.5,
        usage_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT NOW(),
        last_accessed_at TIMESTAMP DEFAULT NOW(),
        expires_at TIMESTAMP
    );

    CREATE INDEX idx_memories_tenant_agent ON memories(tenant_id, agent_id);
    CREATE INDEX idx_memories_layer ON memories(layer);
    CREATE INDEX idx_memories_expires_at ON memories(expires_at) WHERE expires_at IS NOT NULL;
    CREATE INDEX idx_memories_importance ON memories(importance);
    CREATE INDEX idx_memories_metadata ON memories USING GIN(metadata);
    CREATE INDEX idx_memories_governance ON memories USING GIN(governance); -- Phase 2

    -- Performance Indexes (Phase 5)
    CREATE INDEX idx_memories_project ON memories(project);
    CREATE INDEX idx_memories_session_id ON memories(session_id);
    CREATE INDEX idx_memories_source ON memories(source);
    CREATE INDEX idx_memories_info_class ON memories(info_class); -- Phase 2
    CREATE INDEX idx_memories_project_created_at ON memories(project, created_at);
    ```
    """

    def __init__(
        self,
        dsn: str | None = None,
        pool: Optional["asyncpg.Pool"] = None,
        **pool_kwargs: Any,
    ) -> None:
        """Initialize PostgreSQL storage.

        Args:
            dsn: PostgreSQL connection string (e.g., postgresql://user:pass@host/db)
            pool: Existing asyncpg connection pool
            **pool_kwargs: Additional arguments for asyncpg.create_pool()
        """
        if asyncpg is None:
            raise ImportError(
                "asyncpg is required for PostgreSQLStorage. "
                "Install with: pip install asyncpg"
            )

        self.dsn = dsn
        self._pool = pool
        self._pool_kwargs = pool_kwargs

    async def _get_pool(self) -> "asyncpg.Pool":
        """Get or create connection pool."""
        if self._pool is None:
            if self.dsn is None:
                raise ValueError("Either dsn or pool must be provided")
            self._pool = await asyncpg.create_pool(self.dsn, **self._pool_kwargs)
        return cast("asyncpg.Pool", self._pool)

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def store_memory(
        self,
        content: str,
        layer: str,
        tenant_id: str,
        agent_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        importance: float | None = None,
        expires_at: datetime | None = None,
        memory_type: str = "text",
        project: str | None = None,
        session_id: str | None = None,
        source: str | None = None,
        strength: float = 1.0,
        info_class: str = "internal",
        governance: dict[str, Any] | None = None,
    ) -> UUID:
        """Store a new memory in PostgreSQL."""
        pool = await self._get_pool()

        memory_id = uuid4()
        tags = tags or []
        metadata = metadata or {}
        governance = governance or {}
        importance = importance if importance is not None else 0.5

        import json

        async with pool.acquire() as conn:
            # Convert embedding to string for pgvector compatibility if using asyncpg without codec
            embedding_val = str(embedding) if embedding is not None else None

            await conn.execute(
                """
                INSERT INTO memories (
                    id, content, layer, tenant_id, agent_id,
                    tags, metadata, embedding, importance, expires_at,
                    created_at, last_accessed_at, memory_type, usage_count,
                    project, session_id, source, strength,
                    info_class, governance
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11, $12, 0, $13, $14, $15, $16, $17, $18)
                """,
                memory_id,
                content,
                layer,
                str(tenant_id),
                agent_id,
                tags,
                json.dumps(metadata),
                embedding_val,
                importance,
                expires_at,
                datetime.now(timezone.utc).replace(tzinfo=None),
                memory_type,
                project,
                session_id,
                source,
                strength,
                info_class,
                json.dumps(governance),
            )

        return memory_id

    async def get_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a memory by ID."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    id, content, layer, tenant_id, agent_id,
                    tags, metadata, embedding, importance, usage_count,
                    created_at, last_accessed_at, expires_at,
                    project, session_id, memory_type, source, strength,
                    info_class, governance
                FROM memories
                WHERE id = $1 AND tenant_id = $2
                """,
                memory_id,
                str(tenant_id),
            )

        if not row:
            return None

        return {
            "id": row["id"],
            "content": row["content"],
            "layer": row["layer"],
            "tenant_id": row["tenant_id"],
            "agent_id": row["agent_id"],
            "project": row["project"],
            "session_id": row["session_id"],
            "memory_type": row["memory_type"],
            "source": row["source"],
            "strength": float(row["strength"]) if row["strength"] is not None else 1.0,
            "info_class": row["info_class"] or "internal",
            "governance": row["governance"] if row["governance"] else {},
            "tags": list(row["tags"]) if row["tags"] else [],
            "metadata": row["metadata"] if row["metadata"] else {},
            "embedding": (
                (
                    json.loads(row["embedding"])
                    if isinstance(row["embedding"], str)
                    else list(row["embedding"])
                )
                if row["embedding"]
                else None
            ),
            "importance": float(row["importance"] or 0.5),
            "usage_count": int(row["usage_count"] or 0),
            "created_at": row["created_at"],
            "last_accessed_at": row["last_accessed_at"],
            "expires_at": row["expires_at"],
        }

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using PostgreSQL full-text search.

        Note: This is a basic implementation. For production, consider:
        - Adding tsvector column with GIN index
        - Using pgvector for semantic search
        - Implementing proper text search configuration
        """
        pool = await self._get_pool()
        filters = filters or {}

        # Build WHERE clause
        conditions = [
            "tenant_id = $1",
            "agent_id = $2",
            "layer = $3",
        ]
        params: list[Any] = [str(tenant_id), agent_id, layer]
        param_idx = 4

        # Handle not_expired filter
        if filters.get("not_expired"):
            conditions.append(f"(expires_at IS NULL OR expires_at > ${param_idx})")
            params.append(datetime.now(timezone.utc))
            param_idx += 1

        # Handle tags filter
        if "tags" in filters:
            conditions.append(f"tags && ${param_idx}")
            params.append(filters["tags"])
            param_idx += 1

        # Handle importance filter
        if "min_importance" in filters:
            conditions.append(f"importance >= ${param_idx}")
            params.append(filters["min_importance"])
            param_idx += 1

        # Text search (simple ILIKE for now)
        conditions.append(f"content ILIKE ${param_idx}")
        params.append(f"%{query}%")
        param_idx += 1

        where_clause = " AND ".join(conditions)

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT
                    id, content, layer, tenant_id, agent_id,
                    tags, metadata, embedding, importance, usage_count,
                    created_at, last_accessed_at, expires_at,
                    project, session_id, source, strength, memory_type,
                    info_class, governance,
                    -- Simple relevance scoring
                    CASE
                        WHEN content ILIKE ${param_idx} THEN 1.0
                        ELSE 0.5
                    END as score
                FROM memories
                WHERE {where_clause}
                ORDER BY score DESC, importance DESC, last_accessed_at DESC
                LIMIT ${param_idx + 1}
                """,
                *params,
                f"%{query}%",  # For score calculation
                limit,
            )

        results = []
        for row in rows:
            memory = {
                "id": row["id"],
                "content": row["content"],
                "layer": row["layer"],
                "tenant_id": row["tenant_id"],
                "agent_id": row["agent_id"],
                "project": row["project"],
                "session_id": row["session_id"],
                "source": row["source"],
                "strength": (
                    float(row["strength"]) if row["strength"] is not None else 1.0
                ),
                "memory_type": row["memory_type"],
                "info_class": row["info_class"] or "internal",
                "governance": row["governance"] if row["governance"] else {},
                "tags": list(row["tags"]) if row["tags"] else [],
                "metadata": row["metadata"] if row["metadata"] else {},
                "embedding": (
                    (
                        json.loads(row["embedding"])
                        if isinstance(row["embedding"], str)
                        else list(row["embedding"])
                    )
                    if row["embedding"]
                    else None
                ),
                "importance": float(row["importance"]),
                "usage_count": int(row["usage_count"] or 0),
                "created_at": row["created_at"],
                "last_accessed_at": row["last_accessed_at"],
                "expires_at": row["expires_at"],
            }
            results.append(
                {
                    "memory": memory,
                    "score": float(row["score"]),
                }
            )

        return results

    async def list_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
        tags: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> list[dict[str, Any]]:
        """List memories with pagination."""
        pool = await self._get_pool()
        filters = filters or {}

        conditions = [
            "tenant_id = $1",
        ]
        params: list[Any] = [str(tenant_id)]
        param_idx = 2

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if layer:
            conditions.append(f"layer = ${param_idx}")
            params.append(layer)
            param_idx += 1

        if tags:
            conditions.append(f"tags && ${param_idx}")
            params.append(tags)
            param_idx += 1

        # Apply additional filters
        if filters:
            if "since" in filters or "created_after" in filters:
                since = filters.get("since") or filters.get("created_after")
                conditions.append(f"created_at >= ${param_idx}")
                params.append(since)
                param_idx += 1

            if "min_importance" in filters:
                conditions.append(f"importance >= ${param_idx}")
                params.append(filters["min_importance"])
                param_idx += 1

            if "memory_ids" in filters:
                conditions.append(f"id = ANY(${param_idx}::uuid[])")
                params.append(filters["memory_ids"])
                param_idx += 1

        where_clause = " AND ".join(conditions)
        order_clause = f"ORDER BY {order_by} {order_direction.upper()}"

        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT
                    id, content, layer, tenant_id, agent_id,
                    tags, metadata, embedding, importance, usage_count,
                    created_at, last_accessed_at, expires_at,
                    project, session_id, source, strength, memory_type,
                    info_class, governance
                FROM memories
                WHERE {where_clause}
                {order_clause}
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
                """,
                *params,
                limit,
                offset,
            )

        results = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "content": row["content"],
                    "layer": row["layer"],
                    "tenant_id": row["tenant_id"],
                    "agent_id": row["agent_id"],
                    "project": row["project"],
                    "session_id": row["session_id"],
                    "source": row["source"],
                    "strength": (
                        float(row["strength"]) if row["strength"] is not None else 1.0
                    ),
                    "memory_type": row["memory_type"],
                    "info_class": row["info_class"] or "internal",
                    "governance": row["governance"] if row["governance"] else {},
                    "tags": list(row["tags"]) if row["tags"] else [],
                    "metadata": row["metadata"] if row["metadata"] else {},
                    "embedding": (
                        (
                            json.loads(row["embedding"])
                            if isinstance(row["embedding"], str)
                            else list(row["embedding"])
                        )
                        if row["embedding"]
                        else None
                    ),
                    "importance": float(row["importance"]),
                    "usage_count": int(row["usage_count"] or 0),
                    "created_at": row["created_at"],
                    "last_accessed_at": row["last_accessed_at"],
                    "expires_at": row["expires_at"],
                }
            )

        return results

    async def update_memory_access(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Update last access time and increment usage count."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE memories
                SET
                    last_accessed_at = $1,
                    usage_count = usage_count + 1
                WHERE id = $2 AND tenant_id = $3
                """,
                datetime.now(timezone.utc),
                memory_id,
                str(tenant_id),
            )

        return cast(str, result) == "UPDATE 1"

    async def update_memory_expiration(
        self,
        memory_id: UUID,
        tenant_id: str,
        expires_at: datetime,
    ) -> bool:
        """Update memory expiration time."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE memories
                SET expires_at = $1
                WHERE id = $2 AND tenant_id = $3
                """,
                expires_at,
                memory_id,
                str(tenant_id),
            )

        return cast(str, result) == "UPDATE 1"

    async def update_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update a memory with given fields.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        pool = await self._get_pool()

        # Build dynamic UPDATE query
        set_clauses = []
        params = []
        param_idx = 1

        for key, value in updates.items():
            if key not in ["id", "created_at", "tenant_id"]:  # Immutable fields
                set_clauses.append(f"{key} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not set_clauses:
            return False

        # Always update modified_at if it exists in schema
        # (Note: current schema doesn't have modified_at, but this is future-proof)

        # Add WHERE clause parameters
        params.extend([memory_id, str(tenant_id)])

        query = f"""
            UPDATE memories
            SET {", ".join(set_clauses)}
            WHERE id = ${param_idx} AND tenant_id = ${param_idx + 1}
        """

        async with pool.acquire() as conn:
            result = await conn.execute(query, *params)

        return cast(str, result) == "UPDATE 1"

    async def increment_access_count(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Increment access count for a memory.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier

        Returns:
            True if successful, False otherwise
        """
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE memories
                SET
                    usage_count = usage_count + 1,
                    last_accessed_at = $1
                WHERE id = $2 AND tenant_id = $3
                """,
                datetime.now(timezone.utc),
                memory_id,
                str(tenant_id),
            )

        return cast(str, result) == "UPDATE 1"

    async def delete_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Delete a memory."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories
                WHERE id = $1 AND tenant_id = $2
                """,
                memory_id,
                str(tenant_id),
            )

        return cast(str, result) == "DELETE 1"

    async def delete_expired_memories(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
    ) -> int:
        """Delete expired memories."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories
                WHERE tenant_id = $1
                  AND agent_id = $2
                  AND layer = $3
                  AND expires_at IS NOT NULL
                  AND expires_at < $4
                """,
                str(tenant_id),
                agent_id,
                layer,
                datetime.now(timezone.utc),
            )

        # Parse "DELETE N" to get count
        # Parse "DELETE N" to get count
        status = cast(str, result)
        count = int(status.split()[-1]) if status.startswith("DELETE") else 0
        return count

    async def delete_memories_below_importance(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        importance_threshold: float,
    ) -> int:
        """Delete memories below importance threshold."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM memories
                WHERE tenant_id = $1
                  AND agent_id = $2
                  AND layer = $3
                  AND importance < $4
                """,
                str(tenant_id),
                agent_id,
                layer,
                importance_threshold,
            )

        # Parse "DELETE N" to get count
        status = cast(str, result)
        count = int(status.split()[-1]) if status.startswith("DELETE") else 0
        return count

    async def delete_memories_with_metadata_filter(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        metadata_filter: dict[str, Any],
    ) -> int:
        """Delete memories matching metadata filter.

        Note: This is a simplified implementation.
        Production code should properly handle JSONB queries.
        """
        pool = await self._get_pool()

        # For now, implement simple key-value matching
        # Production: use jsonb operators like @>, ?, etc.
        async with pool.acquire() as conn:
            # Get all memories and filter in Python (not ideal for production)
            rows = await conn.fetch(
                """
                SELECT id, metadata
                FROM memories
                WHERE tenant_id = $1 AND agent_id = $2 AND layer = $3
                """,
                tenant_id,
                agent_id,
                layer,
            )

            ids_to_delete = []
            for row in rows:
                metadata = dict(row["metadata"]) if row["metadata"] else {}
                matches = True

                for key, value in metadata_filter.items():
                    # Handle special operators like confidence__lt
                    if "__lt" in key:
                        field = key.replace("__lt", "")
                        if field not in metadata or metadata[field] >= value:
                            matches = False
                            break
                    else:
                        if metadata.get(key) != value:
                            matches = False
                            break

                if matches:
                    ids_to_delete.append(row["id"])

            if ids_to_delete:
                result = await conn.execute(
                    """
                    DELETE FROM memories
                    WHERE id = ANY($1)
                    """,
                    ids_to_delete,
                )
                count = int(result.split()[-1]) if result.startswith("DELETE") else 0
                return count

        return 0

    async def count_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        """Count memories in a layer."""
        pool = await self._get_pool()

        conditions = ["tenant_id = $1"]
        params = [str(tenant_id)]
        param_idx = 2

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if layer:
            conditions.append(f"layer = ${param_idx}")
            params.append(layer)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                f"SELECT COUNT(*) FROM memories WHERE {where_clause}",
                *params,
            )
            return cast(int, result or 0)

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        """Calculate aggregate metric for memories."""
        pool = await self._get_pool()
        filters = filters or {}

        # Validate metric and func to prevent SQL injection
        allowed_metrics = {"importance", "usage_count"}
        allowed_funcs = {"avg", "sum", "min", "max", "count"}

        if metric not in allowed_metrics:
            raise ValueError(f"Invalid metric: {metric}. Allowed: {allowed_metrics}")
        if func not in allowed_funcs:
            raise ValueError(f"Invalid function: {func}. Allowed: {allowed_funcs}")

        conditions = ["tenant_id = $1"]
        params: list[Any] = [str(tenant_id)]
        param_idx = 2

        if "agent_id" in filters:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(filters["agent_id"])
            param_idx += 1

        if "layer" in filters:
            conditions.append(f"layer = ${param_idx}")
            params.append(filters["layer"])
            param_idx += 1

        where_clause = " AND ".join(conditions)

        async with pool.acquire() as conn:
            result = await conn.fetchval(
                f"""
                SELECT {func}({metric})
                FROM memories
                WHERE {where_clause}
                """,
                *params,
            )

        return float(result) if result is not None else 0.0

    async def update_memory_access_batch(
        self,
        memory_ids: list[UUID],
        tenant_id: str,
    ) -> bool:
        """Update last access time and increment usage count for multiple memories."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE memories
                SET
                    last_accessed_at = $1,
                    usage_count = usage_count + 1
                WHERE id = ANY($2) AND tenant_id = $3
                """,
                datetime.now(timezone.utc),
                memory_ids,
                str(tenant_id),
            )

        # We consider it successful if the query executed, even if 0 rows updated
        # (though ideally we might want to check if count matches)
        return True

    async def adjust_importance(
        self,
        memory_id: UUID,
        delta: float,
        tenant_id: str,
    ) -> float:
        """Adjust memory importance by a delta value."""
        pool = await self._get_pool()

        async with pool.acquire() as conn:
            new_importance = await conn.fetchval(
                """
                UPDATE memories
                SET importance = GREATEST(0.0, LEAST(1.0, importance + $1))
                WHERE id = $2 AND tenant_id = $3
                RETURNING importance
                """,
                delta,
                memory_id,
                str(tenant_id),
            )

        if new_importance is None:
            raise ValueError(f"Memory not found: {memory_id}")

        return float(new_importance)

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = True,
    ) -> int:
        """Apply time-based decay to all memories with temporal considerations."""
        pool = await self._get_pool()
        now = datetime.now(timezone.utc)

        # SQL query implementing decay with temporal considerations
        query = """
            UPDATE memories SET
                importance = GREATEST(
                    0.01,  -- Floor at 0.01
                    CASE
                        -- Accelerated decay for stale memories (not accessed > 30 days)
                        WHEN $4 = TRUE AND EXTRACT(EPOCH FROM ($1 - COALESCE(last_accessed_at, created_at))) / 86400 > 30
                        THEN importance * (
                            1 - ($2 * (1 + (EXTRACT(EPOCH FROM ($1 - COALESCE(last_accessed_at, created_at))) / 86400) / 30))
                        )
                        -- Protected decay for recent memories (accessed < 7 days ago)
                        WHEN $4 = TRUE AND EXTRACT(EPOCH FROM ($1 - COALESCE(last_accessed_at, created_at))) / 86400 < 7
                        THEN importance * (1 - ($2 * 0.5))
                        -- Standard decay for everything else
                        ELSE importance * (1 - $2)
                    END
                )
            WHERE tenant_id = $3
              AND importance > 0.01
        """

        async with pool.acquire() as conn:
            status = await conn.execute(
                query,
                now.replace(tzinfo=None),
                decay_rate,
                str(tenant_id),
                consider_access_stats,
            )

        # Parse "UPDATE N"
        if status and status.startswith("UPDATE "):
            try:
                return int(status.split(" ")[1])
            except (IndexError, ValueError):
                return 0
        return 0

    async def save_embedding(
        self,
        memory_id: UUID,
        model_name: str,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save a vector embedding for a memory.

        [ISO 27001] Verifies tenant ownership before saving.
        """
        pool = await self._get_pool()
        metadata = metadata or {}
        embedding_val = str(embedding) if embedding is not None else None

        async with pool.acquire() as conn:
            # 1. Verify ownership (SEC-02)
            # We could do this in one query with CTE, but explicit check is safer for logic
            exists = await conn.fetchval(
                "SELECT 1 FROM memories WHERE id = $1 AND tenant_id = $2",
                memory_id,
                str(tenant_id),
            )
            if not exists:
                # Security: fail silently or raise?
                # Raising helps debugging, silent is safer against enumeration.
                # Given UUIDs are unguessable, raising is fine.
                raise ValueError(
                    f"Access Denied: Memory {memory_id} not found for tenant {tenant_id}"
                )

            # 2. Insert/Update
            await conn.execute(
                """
                INSERT INTO memory_embeddings (
                    memory_id, model_name, embedding, metadata, created_at
                ) VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (memory_id, model_name)
                DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata,
                    created_at = NOW()
                """,
                memory_id,
                model_name,
                embedding_val,
                json.dumps(metadata),
            )

        return True
