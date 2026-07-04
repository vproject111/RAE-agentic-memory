"""SQLite storage adapter for RAE-core with FTS5 full-text search.

Lightweight, file-based storage ideal for RAE-Lite offline-first architecture.
Uses SQLite FTS5 (Full-Text Search) for efficient content search.
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import aiosqlite

from rae_core.interfaces.storage import IMemoryStorage


class SQLiteStorage(IMemoryStorage):
    """SQLite implementation of IMemoryStorage with FTS5 search.

    Features:
    - File-based storage (no server required)
    - FTS5 full-text search on content
    - ACID transactions
    - Multi-index support for fast queries
    - JSON metadata storage
    - Thread-safe via SQLite connection pooling
    """

    def __init__(self, db_path: str = ":memory:"):
        """Initialize SQLite storage.

        Args:
            db_path: Path to SQLite database file, or ":memory:" for in-memory DB
        """
        self.db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database schema and indexes."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrency
            await db.execute("PRAGMA journal_mode=WAL")

            # Main memories table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tags TEXT,  -- JSON array
                    metadata TEXT,  -- JSON object
                    embedding BLOB,  -- Reserved for future use
                    importance REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    last_accessed_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    version INTEGER DEFAULT 1,
                    expires_at TEXT,
                    info_class TEXT DEFAULT 'internal',
                    governance TEXT DEFAULT '{}'
                )
            """
            )

            # FTS5 virtual table for full-text search on content
            await db.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    content,
                    content=memories,
                    content_rowid=rowid
                )
            """
            )

            # Triggers to keep FTS5 in sync
            await db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END
            """
            )

            await db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content)
                    VALUES('delete', old.rowid, old.content);
                END
            """
            )

            await db.execute(
                """
                CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                    INSERT INTO memories_fts(memories_fts, rowid, content)
                    VALUES('delete', old.rowid, old.content);
                    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
                END
            """
            )

            # Indexes for fast lookups
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_tenant_id
                ON memories(tenant_id)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_agent_id
                ON memories(tenant_id, agent_id)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_layer
                ON memories(tenant_id, layer)
            """
            )

            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_memories_created_at
                ON memories(tenant_id, created_at DESC)
            """
            )

            # Memory embeddings table
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    memory_id TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (memory_id, model_name)
                )
            """
            )

            await db.commit()

        self._initialized = True

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
        expires_at: Any | None = None,
        memory_type: str = "text",
        project: str | None = None,
        session_id: str | None = None,
        source: str | None = None,
        strength: float = 1.0,
        info_class: str = "internal",
        governance: dict[str, Any] | None = None,
    ) -> UUID:
        """Store a new memory."""
        await self.initialize()

        memory_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()

        tags_json = json.dumps(tags or [])
        metadata_json = json.dumps(metadata or {})
        governance_json = json.dumps(governance or {})

        # Convert expires_at to ISO string if it's a datetime
        expires_at_str = None
        if expires_at:
            if hasattr(expires_at, "isoformat"):
                expires_at_str = expires_at.isoformat()
            else:
                expires_at_str = str(expires_at)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO memories (
                    id, content, layer, tenant_id, agent_id, tags, metadata,
                    importance, created_at, modified_at, last_accessed_at,
                    access_count, version, expires_at, info_class, governance
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?, ?)
                """,
                (
                    str(memory_id),
                    content,
                    layer,
                    tenant_id,
                    agent_id,
                    tags_json,
                    metadata_json,
                    importance or 0.5,
                    now,
                    now,
                    now,
                    expires_at_str,
                    info_class,
                    governance_json,
                ),
            )
            await db.commit()

        return memory_id

    async def get_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a memory by ID."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM memories
                WHERE id = ? AND tenant_id = ?
                """,
                (str(memory_id), tenant_id),
            ) as cursor:
                row = await cursor.fetchone()

                if not row:
                    return None

                return self._row_to_dict(row)

    async def update_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update a memory."""
        await self.initialize()

        # Build dynamic UPDATE query
        set_clauses = []
        params = []

        for key, value in updates.items():
            if key in ["tags", "metadata"]:
                set_clauses.append(f"{key} = ?")
                params.append(json.dumps(value))
            elif key not in ["id", "created_at"]:  # Immutable fields
                set_clauses.append(f"{key} = ?")
                params.append(value)

        if not set_clauses:
            return False

        # Always update modified_at and increment version
        set_clauses.append("modified_at = ?")
        set_clauses.append("version = version + 1")
        params.append(datetime.now(timezone.utc).isoformat())

        params.extend([str(memory_id), tenant_id])

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                f"""
                UPDATE memories
                SET {", ".join(set_clauses)}
                WHERE id = ? AND tenant_id = ?
                """,
                params,
            )
            await db.commit()

            return cursor.rowcount > 0

    async def delete_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Delete a memory."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM memories
                WHERE id = ? AND tenant_id = ?
                """,
                (str(memory_id), tenant_id),
            )
            await db.commit()

            return cursor.rowcount > 0

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
        """List memories with filtering."""
        await self.initialize()

        # Build dynamic WHERE clause
        where_clauses = ["tenant_id = ?"]
        params: list[Any] = [tenant_id]

        if agent_id:
            where_clauses.append("agent_id = ?")
            params.append(agent_id)

        if layer:
            where_clauses.append("layer = ?")
            params.append(layer)

        # Tag filtering using JSON string matching
        if tags:
            # OR logic for tags - check if tag exists in JSON array
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            where_clauses.append(f"({' OR '.join(tag_conditions)})")

        # Additional metadata filters
        if filters:
            for key, value in filters.items():
                where_clauses.append("json_extract(metadata, '$.' || ?) = ?")
                params.extend([key, value])

        where_clause = " AND ".join(where_clauses)

        # Validate order_by to prevent SQL injection
        allowed_order_by = {
            "created_at",
            "modified_at",
            "last_accessed_at",
            "importance",
            "access_count",
        }
        if order_by not in allowed_order_by:
            order_by = "created_at"

        direction = "DESC" if order_direction.lower() == "desc" else "ASC"

        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                f"""
                SELECT * FROM memories
                WHERE {where_clause}
                ORDER BY {order_by} {direction}
                LIMIT ? OFFSET ?
                """,
                params,
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    async def count_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        """Count memories matching filters."""
        await self.initialize()

        where_clauses = ["tenant_id = ?"]
        params = [tenant_id]

        if agent_id:
            where_clauses.append("agent_id = ?")
            params.append(agent_id)

        if layer:
            where_clauses.append("layer = ?")
            params.append(layer)

        where_clause = " AND ".join(where_clauses)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"""
                SELECT COUNT(*) FROM memories
                WHERE {where_clause}
                """,
                params,
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def increment_access_count(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Increment access count for a memory."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE memories
                SET access_count = access_count + 1,
                    last_accessed_at = ?
                WHERE id = ? AND tenant_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), str(memory_id), tenant_id),
            )
            await db.commit()

            return cursor.rowcount > 0

    async def search_full_text(
        self,
        query: str,
        tenant_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Full-text search using FTS5.

        Args:
            query: Search query (supports FTS5 syntax)
            tenant_id: Tenant identifier
            limit: Maximum number of results

        Returns:
            List of matching memories with relevance scores
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT m.*, bm25(memories_fts) as score
                FROM memories m
                JOIN memories_fts ON m.rowid = memories_fts.rowid
                WHERE memories_fts MATCH ? AND m.tenant_id = ?
                ORDER BY bm25(memories_fts)
                LIMIT ?
                """,
                (query, tenant_id, limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    async def close(self) -> None:
        """Close database connection (if needed)."""
        # aiosqlite uses context managers, so explicit close not needed
        pass

    def _row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        """Convert SQLite row to memory dictionary."""
        memory = dict(row)

        # Parse JSON fields
        if memory.get("tags"):
            memory["tags"] = json.loads(memory["tags"])
        else:  # pragma: no cover
            memory["tags"] = []  # pragma: no cover

        if memory.get("metadata"):
            memory["metadata"] = json.loads(memory["metadata"])
        else:  # pragma: no cover
            memory["metadata"] = {}  # pragma: no cover

        # Convert UUID string back to UUID
        if memory.get("id"):
            memory["id"] = UUID(memory["id"])

        return memory

    async def delete_memories_with_metadata_filter(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        metadata_filter: dict[str, Any],
    ) -> int:
        """Delete memories matching metadata filter.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            layer: Memory layer
            metadata_filter: Dictionary of metadata key-value pairs to match

        Returns:
            Number of memories deleted
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # First, fetch all memories matching tenant, agent, layer
            async with db.execute(
                """
                SELECT id, metadata FROM memories
                WHERE tenant_id = ? AND agent_id = ? AND layer = ?
                """,
                (tenant_id, agent_id, layer),
            ) as cursor:
                rows = await cursor.fetchall()

            # Filter by metadata in Python (SQLite JSON support is limited)
            matching_ids = []
            for row in rows:
                metadata = json.loads(row["metadata"]) if row["metadata"] else {}
                if self._matches_metadata_filter(metadata, metadata_filter):
                    matching_ids.append(row["id"])

            # Delete matching memories
            if matching_ids:
                placeholders = ",".join("?" * len(matching_ids))
                cursor = await db.execute(
                    f"DELETE FROM memories WHERE id IN ({placeholders})",
                    matching_ids,
                )
                await db.commit()
                return cursor.rowcount

            return 0

    async def delete_memories_below_importance(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        importance_threshold: float,
    ) -> int:
        """Delete memories below importance threshold.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            layer: Memory layer
            importance_threshold: Minimum importance value to keep

        Returns:
            Number of memories deleted
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM memories
                WHERE tenant_id = ? AND agent_id = ? AND layer = ?
                AND importance < ?
                """,
                (tenant_id, agent_id, layer, importance_threshold),
            )
            await db.commit()
            return cursor.rowcount

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using FTS5 full-text search.

        Args:
            query: Search query (FTS5 syntax supported)
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            layer: Memory layer
            limit: Maximum number of results
            filters: Optional additional filters (unused in FTS5 basic)

        Returns:
            List of memory dictionaries
        """
        await self.initialize()

        if not query or not tenant_id:
            return []

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # FTS5 search joining with main table
            cursor = await db.execute(
                """
                SELECT m.* FROM memories m
                JOIN memories_fts f ON m.rowid = f.rowid
                WHERE f.content MATCH ?
                AND m.tenant_id = ? AND m.agent_id = ? AND m.layer = ?
                LIMIT ?
                """,
                (query, tenant_id, agent_id, layer, limit),
            )
            rows = await cursor.fetchall()
            return [{"memory": self._row_to_dict(row), "score": 1.0} for row in rows]

    async def delete_expired_memories(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
    ) -> int:
        """Delete expired memories.

        Args:
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            layer: Memory layer

        Returns:
            Number of memories deleted
        """
        await self.initialize()

        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM memories
                WHERE tenant_id = ? AND agent_id = ? AND layer = ?
                AND expires_at IS NOT NULL AND expires_at < ?
                """,
                (tenant_id, agent_id, layer, now),
            )
            await db.commit()
            return cursor.rowcount

    async def update_memory_access(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Update last access time and increment usage count.

        Args:
            memory_id: Memory identifier
            tenant_id: Tenant identifier

        Returns:
            True if memory was updated, False if not found
        """
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE memories
                SET last_accessed_at = ?,
                    access_count = access_count + 1
                WHERE id = ? AND tenant_id = ?
                """,
                (datetime.now(timezone.utc).isoformat(), str(memory_id), tenant_id),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def update_memory_expiration(
        self,
        memory_id: UUID,
        tenant_id: str,
        expires_at: Any,
    ) -> bool:
        """Update memory expiration time.

        Args:
            memory_id: Memory identifier
            tenant_id: Tenant identifier
            expires_at: Expiration datetime (datetime object or ISO string)

        Returns:
            True if memory was updated, False if not found
        """
        await self.initialize()

        # Convert datetime to ISO string if needed
        if hasattr(expires_at, "isoformat"):
            expires_at_str = expires_at.isoformat()
        else:
            expires_at_str = str(expires_at)

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE memories
                SET expires_at = ?, modified_at = ?
                WHERE id = ? AND tenant_id = ?
                """,
                (
                    expires_at_str,
                    datetime.now(timezone.utc).isoformat(),
                    str(memory_id),
                    tenant_id,
                ),
            )
            await db.commit()

            return cursor.rowcount > 0

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        """Calculate aggregate metric."""
        await self.initialize()

        # Validate metric and func
        allowed_metrics = {"importance", "access_count", "version"}
        allowed_funcs = {"avg", "sum", "min", "max", "count"}

        if metric not in allowed_metrics or func not in allowed_funcs:
            return 0.0

        where_clauses = ["tenant_id = ?"]
        params: list[Any] = [tenant_id]

        if filters:
            for key, value in filters.items():
                where_clauses.append("json_extract(metadata, '$.' || ?) = ?")
                params.extend([key, value])

        where_clause = " AND ".join(where_clauses)

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                f"SELECT {func}({metric}) FROM memories WHERE {where_clause}",
                params,
            ) as cursor:
                row = await cursor.fetchone()
                return float(row[0]) if row and row[0] is not None else 0.0

    async def update_memory_access_batch(
        self,
        memory_ids: list[UUID],
        tenant_id: str,
    ) -> bool:
        """Update access count for multiple memories."""
        await self.initialize()
        now = datetime.now(timezone.utc).isoformat()
        ids_str = [str(mid) for mid in memory_ids]

        async with aiosqlite.connect(self.db_path) as db:
            placeholders = ",".join("?" * len(ids_str))
            await db.execute(
                f"""
                UPDATE memories
                SET access_count = access_count + 1,
                    last_accessed_at = ?
                WHERE id IN ({placeholders}) AND tenant_id = ?
                """,
                [now] + ids_str + [tenant_id],
            )
            await db.commit()
        return True

    async def adjust_importance(
        self,
        memory_id: UUID,
        delta: float,
        tenant_id: str,
    ) -> float:
        """Adjust memory importance."""
        await self.initialize()

        async with aiosqlite.connect(self.db_path) as db:
            # SQLite doesn't have GREATEST/LEAST like Postgres, use MIN/MAX
            await db.execute(
                """
                UPDATE memories
                SET importance = MAX(0.0, MIN(1.0, importance + ?)),
                    modified_at = ?
                WHERE id = ? AND tenant_id = ?
                """,
                (
                    delta,
                    datetime.now(timezone.utc).isoformat(),
                    str(memory_id),
                    tenant_id,
                ),
            )
            await db.commit()

            async with db.execute(
                "SELECT importance FROM memories WHERE id = ? AND tenant_id = ?",
                (str(memory_id), tenant_id),
            ) as cursor:
                row = await cursor.fetchone()
                return float(row[0]) if row else 0.0

    async def save_embedding(
        self,
        memory_id: UUID,
        model_name: str,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save a vector embedding for a memory."""
        await self.initialize()
        now = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata or {})
        # Convert float list to BLOB (JSON string for simplicity in SQLite adapter)
        embedding_json = json.dumps(embedding)

        async with aiosqlite.connect(self.db_path) as db:
            # Check existence and tenant ownership (SEC-02)
            async with db.execute(
                "SELECT 1 FROM memories WHERE id = ? AND tenant_id = ?",
                (str(memory_id), tenant_id),
            ) as cursor:
                if not await cursor.fetchone():
                    raise ValueError(
                        f"Access Denied: Memory {memory_id} not found for tenant {tenant_id}"
                    )

            await db.execute(
                """
                INSERT INTO memory_embeddings (
                    memory_id, model_name, embedding, metadata, created_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(memory_id, model_name) DO UPDATE SET
                    embedding = excluded.embedding,
                    metadata = excluded.metadata,
                    created_at = excluded.created_at
                """,
                (str(memory_id), model_name, embedding_json, metadata_json, now),
            )
            await db.commit()
            return True

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = False,
    ) -> int:
        """Apply importance decay to all memories for a tenant."""
        await self.initialize()
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            if not consider_access_stats:
                # Simple linear decay for all
                cursor = await db.execute(
                    """
                    UPDATE memories
                    SET importance = MAX(0.0, importance - ?),
                        modified_at = ?
                    WHERE tenant_id = ?
                    """,
                    (decay_rate, now, tenant_id),
                )
            else:
                # Slower decay for used memories
                # Note: LOG1P equivalent in SQLite is not standard,
                # using a simpler usage-based dampening: decay / (1 + usage_count)
                cursor = await db.execute(
                    """
                    UPDATE memories
                    SET importance = MAX(0.0, importance - (? / (1.0 + access_count))),
                        modified_at = ?
                    WHERE tenant_id = ?
                    """,
                    (decay_rate, now, tenant_id),
                )

            await db.commit()
            return cursor.rowcount

    async def get_edges_between(self, node_ids: list[str], tenant_id: str) -> list[tuple[str, str, float]]:
        """
        Retrieve edges between nodes for resonance calculation.
        Note: In SQLite adapter, edges might be in a separate database file
        specified by settings, but for RAE-Lite we often use the same file.
        """
        await self.initialize()
        if not node_ids:
            return []

        # We assume the table knowledge_graph_edges exists in the same DB 
        # or was attached. For RAE-Lite simplicity, we check if it exists.
        try:
            async with aiosqlite.connect(self.db_path) as db:
                placeholders = ",".join(["?" for _ in node_ids])
                params = node_ids + node_ids + [tenant_id]
                sql = f"""
                    SELECT source_id, target_id, weight 
                    FROM knowledge_graph_edges 
                    WHERE source_id IN ({placeholders}) 
                      AND target_id IN ({placeholders})
                      AND tenant_id = ?
                """
                async with db.execute(sql, params) as cursor:
                    rows = await cursor.fetchall()
                    return [(row[0], row[1], row[2]) for row in rows]
        except Exception:
            # If table doesn't exist yet, return empty
            return []


    def _matches_metadata_filter(
        self, metadata: dict[str, Any], filter_dict: dict[str, Any]
    ) -> bool:
        """Check if metadata matches filter criteria.

        Args:
            metadata: Memory metadata dictionary
            filter_dict: Filter criteria dictionary

        Returns:
            True if all filter criteria match
        """
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
