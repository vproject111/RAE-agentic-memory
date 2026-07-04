"""SQLite storage adapter for RAE."""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import aiosqlite

from rae_core.interfaces.storage import IMemoryStorage


class SQLiteStorage(IMemoryStorage):
    """SQLite implementation of IMemoryStorage."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self) -> None:
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    layer TEXT NOT NULL,
                    tenant_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    tags TEXT,
                    metadata TEXT,
                    importance REAL DEFAULT 0.5,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL,
                    last_accessed_at TEXT NOT NULL,
                    project TEXT
                )
            """
            )
            await db.commit()
        self._initialized = True

    async def store_memory(self, **kwargs: Any) -> UUID:
        await self.initialize()
        m_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO memories (id, content, layer, tenant_id, agent_id, tags, metadata, importance, created_at, modified_at, last_accessed_at, project) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(m_id),
                    kwargs.get("content"),
                    kwargs.get("layer"),
                    kwargs.get("tenant_id"),
                    kwargs.get("agent_id"),
                    json.dumps(kwargs.get("tags", [])),
                    json.dumps(kwargs.get("metadata", {})),
                    kwargs.get("importance", 0.5),
                    now,
                    now,
                    now,
                    kwargs.get("project"),
                ),
            )
            await db.commit()
        return m_id

    async def get_memory(
        self, memory_id: UUID, tenant_id: str
    ) -> dict[str, Any] | None:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM memories WHERE id = ? AND tenant_id = ?",
                (str(memory_id), tenant_id),
            ) as cursor:
                row = await cursor.fetchone()
                return self._row_to_dict(row) if row else None

    async def update_memory(
        self, memory_id: UUID, tenant_id: str, updates: dict[str, Any]
    ) -> bool:
        return True

    async def delete_memory(self, memory_id: UUID, tenant_id: str) -> bool:
        return True

    async def list_memories(
        self, tenant_id: str, **kwargs: Any
    ) -> list[dict[str, Any]]:
        return []

    async def count_memories(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        return 0

    async def delete_memories_with_metadata_filter(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        layer: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> int:
        return 0

    async def delete_memories_below_importance(
        self, tenant_id: str, agent_id: str, layer: str, importance_threshold: float
    ) -> int:
        return 0

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        await self.initialize()
        project = kwargs.get("project")

        where_clauses = ["tenant_id = ?", "agent_id = ?", "layer = ?", "content LIKE ?"]
        params = [tenant_id, agent_id, layer, f"%{query}%"]

        if project:
            where_clauses.append("project = ?")
            params.append(project)

        params.append(limit)
        sql = f"SELECT * FROM memories WHERE {' AND '.join(where_clauses)} LIMIT ?"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": r["id"],
                        "content": r["content"],
                        "score": 1.0,
                        "importance": r["importance"],
                    }
                    for r in rows
                ]

    async def delete_expired_memories(
        self, tenant_id: str, agent_id: str | None = None, layer: str | None = None
    ) -> int:
        return 0

    async def update_memory_access(self, memory_id: UUID, tenant_id: str) -> bool:
        return True

    async def update_memory_expiration(
        self, memory_id: UUID, tenant_id: str, expires_at: Optional[datetime]
    ) -> bool:
        return True

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        return 0.0

    async def update_memory_access_batch(
        self, memory_ids: list[UUID], tenant_id: str
    ) -> bool:
        return True

    async def adjust_importance(
        self, memory_id: UUID, delta: float, tenant_id: str
    ) -> float:
        return 0.5

    async def save_embedding(
        self, memory_id: UUID, model_name: str, embedding: list[float], tenant_id: str
    ) -> bool:
        return True

    async def decay_importance(self, tenant_id: str, decay_factor: float) -> int:
        return 0

    async def close(self) -> None:
        pass

    async def search_full_text(
        self,
        query: str,
        tenant_id: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        await self.initialize()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT *, 1.0 as score FROM memories WHERE tenant_id = ? AND content LIKE ? LIMIT ?",
                (tenant_id, f"%{query}%", limit),
            ) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_dict(row) for row in rows]

    def _row_to_dict(self, row: aiosqlite.Row) -> dict[str, Any]:
        d = dict(row)
        d["id"] = UUID(d["id"])
        d["tags"] = json.loads(d["tags"]) if d["tags"] else []
        d["metadata"] = json.loads(d["metadata"]) if d["metadata"] else {}
        return d
