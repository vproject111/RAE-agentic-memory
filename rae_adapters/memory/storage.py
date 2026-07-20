"""In-Memory storage adapter for RAE."""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from rae_core.interfaces.storage import IMemoryStorage


class InMemoryStorage(IMemoryStorage):
    """In-memory implementation of IMemoryStorage."""

    def __init__(self) -> None:
        self._memories: dict[UUID, dict[str, Any]] = {}
        self._by_tenant: dict[str, set[UUID]] = defaultdict(set)
        self._by_agent: dict[tuple[str, str], set[UUID]] = defaultdict(set)
        self._by_layer: dict[tuple[str, str], set[UUID]] = defaultdict(set)
        self._by_tags: dict[tuple[str, str], set[UUID]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def save_embedding(
        self, memory_id: UUID, model_name: str, embedding: list[float], tenant_id: str
    ) -> bool:
        return True

    async def store_memory(self, **kwargs: Any) -> UUID:
        async with self._lock:
            memory_id = uuid4()
            now = datetime.now(timezone.utc)
            tenant_id = kwargs.get("tenant_id", "default")
            agent_id = kwargs.get("agent_id", "default")
            layer = kwargs.get("layer", "episodic")

            memory = {
                "id": memory_id,
                "content": kwargs.get("content", ""),
                "layer": layer,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "importance": kwargs.get("importance", 0.5),
                "tags": kwargs.get("tags") or [],
                "metadata": kwargs.get("metadata") or {},
                "governance": kwargs.get("governance") or {},
                "info_class": kwargs.get("info_class", "internal"),
                "project": kwargs.get("project"),
                "session_id": kwargs.get("session_id"),
                "source": kwargs.get("source"),
                "expires_at": kwargs.get("expires_at"),
                "memory_type": kwargs.get("memory_type", "text"),
                "strength": kwargs.get("strength", 1.0),
                "embedding": kwargs.get("embedding"),
                "created_at": now,
            }
            self._memories[memory_id] = memory
            self._by_tenant[tenant_id].add(memory_id)
            self._by_agent[(tenant_id, agent_id)].add(memory_id)
            self._by_layer[(tenant_id, layer)].add(memory_id)
            return memory_id

    async def get_memory(
        self, memory_id: UUID, tenant_id: str
    ) -> dict[str, Any] | None:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                return memory.copy()
            return None

    async def update_memory(
        self, memory_id: UUID, tenant_id: str, updates: dict[str, Any]
    ) -> bool:
        return True

    async def delete_memory(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self._lock:
            if memory_id in self._memories:
                del self._memories[memory_id]
                return True
            return False

    async def list_memories(
        self, tenant_id: str, **kwargs: Any
    ) -> list[dict[str, Any]]:
        async with self._lock:
            return [
                m.copy() for m in self._memories.values() if m["tenant_id"] == tenant_id
            ]

    async def count_memories(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        async with self._lock:
            if not tenant_id:
                return len(self._memories)
            return len(
                [m for m in self._memories.values() if m["tenant_id"] == tenant_id]
            )

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
        layer: str | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            results = []
            project = kwargs.get("project")
            filters = kwargs.get("filters") or {}

            for m in self._memories.values():
                if m.get("tenant_id") != tenant_id:
                    continue
                if agent_id and agent_id != "default" and m.get("agent_id") != agent_id:
                    continue
                if layer and m.get("layer") != layer:
                    continue
                if project and m.get("project") != project:
                    continue

                if query and query != "*":
                    if query.lower() not in m.get("content", "").lower():
                        continue

                match_filters = True
                for fk, fv in filters.items():
                    if fk == "governance.is_failure":
                        gov = m.get("governance") or {}
                        is_fail = gov.get("is_failure")
                        if str(is_fail).lower() != str(fv).lower():
                            match_filters = False
                            break

                if not match_filters:
                    continue

                results.append(m.copy())

            results.sort(key=lambda x: x.get("importance", 0.5), reverse=True)
            return results[:limit]

    async def delete_expired_memories(
        self, tenant_id: str, agent_id: str | None = None, layer: str | None = None
    ) -> int:
        return 0

    async def update_memory_access(self, memory_id: UUID, tenant_id: str) -> bool:
        return True

    async def update_memory_expiration(
        self, memory_id: UUID, tenant_id: str, expires_at: datetime | None
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

    async def decay_importance(self, tenant_id: str, decay_factor: float) -> int:
        return 0

    async def close(self) -> None:
        pass
