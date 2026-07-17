"""Core testing fixtures and mocks."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest

from rae_core.interfaces.storage import IMemoryStorage


class MockMemoryStorage(IMemoryStorage):
    """Simple mock storage for unit tests."""

    def __init__(self):
        self._memories: dict[UUID, dict[str, Any]] = {}
        self._lock = asyncio.Lock()  # To simulate async behavior

    async def store_memory(self, **kwargs: Any) -> UUID:
        async with self._lock:
            memory_id = uuid4()
            now = datetime.now(timezone.utc)

            memory = {
                "id": memory_id,
                "content": kwargs.get("content", ""),
                "layer": kwargs.get("layer", "episodic"),
                "tenant_id": kwargs.get("tenant_id", "default"),
                "agent_id": kwargs.get("agent_id", "default"),
                "importance": kwargs.get("importance", 0.5),
                "created_at": now,
                "last_accessed_at": now,
                "usage_count": 0,
                "access_count": 0,
                "metadata": kwargs.get("metadata") or {},
                "tags": kwargs.get("tags") or [],
                "memory_type": kwargs.get("memory_type", "text"),
                "info_class": kwargs.get("info_class", "internal"),
                "expires_at": kwargs.get("expires_at"),
                "version": 1,
            }
            self._memories[memory_id] = memory
            return memory_id

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = False,
    ) -> int:
        async with self._lock:
            count = 0
            for memory in self._memories.values():
                if memory["tenant_id"] == tenant_id:
                    memory["importance"] = (
                        float(memory.get("importance", 0.5)) * decay_rate
                    )
                    count += 1
            return count

    async def get_memory(
        self, memory_id: UUID, tenant_id: str
    ) -> dict[str, Any] | None:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                return memory.copy()
            return None

    async def get_memories_batch(
        self, memory_ids: list[UUID], tenant_id: str
    ) -> list[dict[str, Any]]:
        results = []
        for mid in memory_ids:
            m = await self.get_memory(mid, tenant_id)
            if m:
                results.append(m)
        return results

    async def update_memory(
        self, memory_id: UUID, tenant_id: str, updates: dict[str, Any]
    ) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory.update(updates)
                memory["version"] = memory.get("version", 1) + 1
                return True
            return False

    async def delete_memory(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                del self._memories[memory_id]
                return True
            return False

    async def list_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            filters = kwargs.get("filters", {})
            order_by = kwargs.get("order_by", "created_at")
            direction = kwargs.get("order_direction", "desc")

            results = []
            for m in self._memories.values():
                if m["tenant_id"] != tenant_id:
                    continue
                if agent_id and m["agent_id"] != agent_id:
                    continue
                if layer and m["layer"] != layer:
                    continue

                # Support advanced filters (dot notation)
                match = True
                for k, v in filters.items():
                    if k.startswith("metadata."):
                        meta_key = k.split(".", 1)[1]
                        if m["metadata"].get(meta_key) != v:
                            match = False
                            break
                    elif m.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

                results.append(m.copy())

            # Sorting
            results.sort(
                key=lambda x: x.get(order_by, 0), reverse=(direction == "desc")
            )

            limit = kwargs.get("limit", 100)
            offset = kwargs.get("offset", 0)
            return results[offset : offset + limit]

    async def delete_memories_with_metadata_filter(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        layer: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> int:
        count = 0
        to_delete = []
        for mid, m in self._memories.items():
            if tenant_id and m["tenant_id"] != tenant_id:
                continue
            if agent_id and m["agent_id"] != agent_id:
                continue
            if layer and m["layer"] != layer:
                continue

            match = True
            for k, v in (metadata_filter or {}).items():
                # Handle __lt suffix
                if k.endswith("__lt"):
                    key = k.rsplit("__", 1)[0]
                    if m["metadata"].get(key, 1.0) >= v:
                        match = False
                        break
                elif m["metadata"].get(k) != v:
                    match = False
                    break
            if match:
                to_delete.append(mid)

        for mid in to_delete:
            del self._memories[mid]
            count += 1
        return count

    async def delete_memories_below_importance(
        self, tenant_id: str, agent_id: str, layer: str, importance_threshold: float
    ) -> int:
        count = 0
        to_delete = []
        for mid, m in self._memories.items():
            if (
                m["tenant_id"] == tenant_id
                and m["agent_id"] == agent_id
                and m["layer"] == layer
            ):
                if m["importance"] < importance_threshold:
                    to_delete.append(mid)

        for mid in to_delete:
            del self._memories[mid]
            count += 1
        return count

    async def count_memories(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        count = 0
        for m in self._memories.values():
            if tenant_id and m["tenant_id"] != tenant_id:
                continue
            if agent_id and m["agent_id"] != agent_id:
                continue
            if layer and m["layer"] != layer:
                continue
            count += 1
        return count

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        results = []
        for m in self._memories.values():
            if m["tenant_id"] == tenant_id and m["agent_id"] == agent_id:
                if layer and m["layer"] != layer:
                    continue

                # Check not_expired filter used by SensoryLayer
                if kwargs.get("filters", {}).get("not_expired"):
                    if m["expires_at"] and m["expires_at"] < datetime.now(timezone.utc):
                        continue

                if query.lower() in m["content"].lower():
                    results.append(
                        {
                            "memory": m.copy(),
                            "score": 1.0,
                            "id": m["id"],
                            "content": m["content"],
                            "importance": m["importance"],
                        }
                    )
        return results[:limit]

    async def delete_expired_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        to_delete = []
        for mid, m in self._memories.items():
            if m["tenant_id"] == tenant_id:
                if agent_id and m["agent_id"] != agent_id:
                    continue
                if layer and m["layer"] != layer:
                    continue
                if m["expires_at"] and m["expires_at"] < now:
                    to_delete.append(mid)
        for mid in to_delete:
            del self._memories[mid]
            count += 1
        return count

    async def update_memory_access(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory["usage_count"] += 1
                memory["access_count"] += 1
                memory["last_accessed_at"] = datetime.now(timezone.utc)
                return True
            return False

    async def increment_access_count(self, memory_id: UUID, tenant_id: str) -> bool:
        return await self.update_memory_access(memory_id, tenant_id)

    async def update_memory_expiration(
        self, memory_id: UUID, tenant_id: str, expires_at: datetime | None
    ) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory["expires_at"] = expires_at
                return True
            return False

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        values = []
        for m in self._memories.values():
            if m["tenant_id"] == tenant_id:
                val = m.get(metric)
                if val is not None:
                    values.append(float(val))
        if not values:
            return 0.0
        if func == "sum":
            return sum(values)
        return 0.0

    async def update_memory_access_batch(
        self, memory_ids: list[UUID], tenant_id: str
    ) -> bool:
        for mid in memory_ids:
            await self.update_memory_access(mid, tenant_id)
        return True

    async def adjust_importance(
        self, memory_id: UUID, delta: float, tenant_id: str
    ) -> float:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory["importance"] = max(0.0, min(1.0, memory["importance"] + delta))
                return memory["importance"]
            return 0.0

    async def save_embedding(
        self,
        memory_id: UUID,
        model_name: str,
        embedding: list[float],
        tenant_id: str,
        **kwargs: Any,
    ) -> bool:
        return True

    async def decay_importance(self, tenant_id: str, decay_factor: float) -> int:
        return 0

    async def clear_tenant(self, tenant_id: str) -> int:
        count = 0
        to_delete = [
            mid for mid, m in self._memories.items() if m["tenant_id"] == tenant_id
        ]
        for mid in to_delete:
            del self._memories[mid]
            count += 1
        return count

    async def close(self) -> None:
        pass


@pytest.fixture
def mock_storage():
    return MockMemoryStorage()


@pytest.fixture
def mock_memory_storage():
    return MockMemoryStorage()
