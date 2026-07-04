"""In-Memory storage adapter for RAE-core.

Fast, thread-safe implementation using Python dictionaries.
Ideal for testing, development, and lightweight deployments.
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID, uuid4

from rae_core.interfaces.storage import IMemoryStorage


class InMemoryStorage(IMemoryStorage):
    """In-memory implementation of IMemoryStorage.

    Features:
    - Fast dictionary-based storage
    - Thread-safe operations with asyncio.Lock
    - Automatic timestamps and versioning
    - Filtering by layer, agent, and tags
    - Access count tracking
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        # Main storage: {memory_id: memory_dict}
        self._memories: dict[UUID, dict[str, Any]] = {}

        # Indexes for fast lookups
        self._by_tenant: dict[str, set[UUID]] = defaultdict(set)
        self._by_agent: dict[tuple[str, str], set[UUID]] = defaultdict(
            set
        )  # (tenant, agent)
        self._by_layer: dict[tuple[str, str], set[UUID]] = defaultdict(
            set
        )  # (tenant, layer)
        self._by_tags: dict[tuple[str, str], set[UUID]] = defaultdict(
            set
        )  # (tenant, tag)

        # Multi-model embeddings storage: {memory_id: {model_name: {embedding: ..., metadata: ...}}}
        self._embeddings: dict[UUID, dict[str, dict[str, Any]]] = defaultdict(dict)

        # Thread safety
        self._lock = asyncio.Lock()

    async def save_embedding(
        self,
        memory_id: UUID,
        model_name: str,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save a vector embedding for a memory."""
        async with self._lock:
            # Check existence and tenant ownership (SEC-02)
            if memory_id not in self._memories:
                return False
            
            if self._memories[memory_id]["tenant_id"] != tenant_id:
                raise ValueError(f"Access Denied: Memory {memory_id} not found for tenant {tenant_id}")

            self._embeddings[memory_id][model_name] = {
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc),
            }
            return True

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
    ) -> UUID:
        """Store a new memory."""
        async with self._lock:
            memory_id = uuid4()
            now = datetime.now(timezone.utc)

            memory = {
                "id": memory_id,
                "content": content,
                "layer": layer,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "tags": tags or [],
                "metadata": metadata or {},
                "embedding": embedding,
                "importance": importance or 0.5,
                "created_at": now,
                "last_accessed_at": now,
                "expires_at": expires_at,
                "usage_count": 0,
            }

            # Store memory
            self._memories[memory_id] = memory

            # Update indexes
            self._by_tenant[tenant_id].add(memory_id)
            self._by_agent[(tenant_id, agent_id)].add(memory_id)
            self._by_layer[(tenant_id, layer)].add(memory_id)

            for tag in tags or []:
                self._by_tags[(tenant_id, tag)].add(memory_id)

            return memory_id

    async def get_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a memory by ID."""
        async with self._lock:
            memory = self._memories.get(memory_id)

            if memory and memory["tenant_id"] == tenant_id:
                # Return a copy to prevent external modifications
                return memory.copy()

            return None

    async def update_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update a memory."""
        async with self._lock:
            memory = self._memories.get(memory_id)

            if not memory or memory["tenant_id"] != tenant_id:
                return False

            # Handle tag updates (update index)
            old_tags = set(memory.get("tags", []))
            new_tags = set(updates.get("tags", old_tags))

            removed_tags = old_tags - new_tags
            added_tags = new_tags - old_tags

            for tag in removed_tags:
                self._by_tags[(tenant_id, tag)].discard(memory_id)

            for tag in added_tags:
                self._by_tags[(tenant_id, tag)].add(memory_id)

            # Handle layer updates (update index)
            old_layer = memory.get("layer")
            new_layer = updates.get("layer", old_layer)

            if old_layer != new_layer:
                self._by_layer[(tenant_id, cast(str, old_layer))].discard(memory_id)
                self._by_layer[(tenant_id, cast(str, new_layer))].add(memory_id)

            # Update memory
            memory.update(updates)
            memory["modified_at"] = datetime.now(timezone.utc)
            memory["version"] = memory.get("version", 1) + 1

            return True

    async def delete_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Delete a memory."""
        async with self._lock:
            memory = self._memories.get(memory_id)

            if not memory or memory["tenant_id"] != tenant_id:
                return False

            # Remove from indexes
            self._by_tenant[tenant_id].discard(memory_id)
            self._by_agent[(tenant_id, memory["agent_id"])].discard(memory_id)
            self._by_layer[(tenant_id, memory["layer"])].discard(memory_id)

            for tag in memory.get("tags", []):
                self._by_tags[(tenant_id, tag)].discard(memory_id)

            # Remove memory
            del self._memories[memory_id]

            return True

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
        async with self._lock:
            # Start with tenant memories
            candidate_ids = self._by_tenant[tenant_id].copy()

            # Apply filters using indexes
            if agent_id:
                candidate_ids &= self._by_agent[(tenant_id, agent_id)]

            if layer:
                candidate_ids &= self._by_layer[(tenant_id, layer)]

            if tags:
                # OR logic for tags
                tag_ids = set()
                for tag in tags:
                    tag_ids |= self._by_tags[(tenant_id, tag)]
                candidate_ids &= tag_ids

            # Get memories and sort by created_at
            memories = [
                self._memories[mid].copy()
                for mid in candidate_ids
                if mid in self._memories
            ]
            memories.sort(key=lambda m: m["created_at"], reverse=True)

            # Apply pagination
            return memories[offset : offset + limit]

    async def count_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        """Count memories matching filters."""
        async with self._lock:
            # Start with tenant memories
            candidate_ids = self._by_tenant[tenant_id].copy()

            # Apply filters
            if agent_id:
                candidate_ids &= self._by_agent[(tenant_id, agent_id)]

            if layer:
                candidate_ids &= self._by_layer[(tenant_id, layer)]

            return len(candidate_ids)

    async def increment_access_count(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Increment access count for a memory."""
        async with self._lock:
            memory = self._memories.get(memory_id)

            if not memory or memory["tenant_id"] != tenant_id:
                return False

            memory["access_count"] = memory.get("access_count", 0) + 1
            memory["last_accessed_at"] = datetime.now(timezone.utc)

            return True

    async def clear_tenant(self, tenant_id: str) -> int:
        """Clear all memories for a tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Number of memories deleted
        """
        async with self._lock:
            memory_ids = self._by_tenant[tenant_id].copy()

            for memory_id in memory_ids:
                memory = self._memories.get(memory_id)
                if memory:
                    # Remove from all indexes
                    self._by_agent[(tenant_id, memory["agent_id"])].discard(memory_id)
                    self._by_layer[(tenant_id, memory["layer"])].discard(memory_id)

                    for tag in memory.get("tags", []):
                        self._by_tags[(tenant_id, tag)].discard(memory_id)

                    # Remove memory
                    del self._memories[memory_id]

            # Clear tenant index
            del self._by_tenant[tenant_id]

            return len(memory_ids)

    async def get_statistics(self) -> dict[str, Any]:
        """Get storage statistics.

        Returns:
            Dictionary with storage statistics
        """
        async with self._lock:
            return {
                "total_memories": len(self._memories),
                "tenants": len(self._by_tenant),
                "agents": len(self._by_agent),
                "layers": len(self._by_layer),
                "unique_tags": len(self._by_tags),
            }

    async def clear_all(self) -> int:
        """Clear all data (use with caution!).

        Returns:
            Number of memories deleted
        """
        async with self._lock:
            count = len(self._memories)

            self._memories.clear()
            self._by_tenant.clear()
            self._by_agent.clear()
            self._by_layer.clear()
            self._by_tags.clear()

            return count

    async def delete_memories_with_metadata_filter(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        metadata_filter: dict[str, Any],
    ) -> int:
        """Delete memories matching metadata filter."""
        async with self._lock:
            matching_ids = []
            for memory_id, memory in self._memories.items():
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                ):
                    # Check if metadata matches filter
                    if self._matches_metadata_filter(
                        memory.get("metadata", {}), metadata_filter
                    ):
                        matching_ids.append(memory_id)

            for memory_id in matching_ids:
                await self._delete_memory_internal(memory_id)

            return len(matching_ids)

    async def delete_memories_below_importance(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        importance_threshold: float,
    ) -> int:
        """Delete memories below importance threshold."""
        async with self._lock:
            matching_ids = [
                memory_id
                for memory_id, memory in self._memories.items()
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                    and memory.get("importance", 0) < importance_threshold
                )
            ]

            for memory_id in matching_ids:
                await self._delete_memory_internal(memory_id)

            return len(matching_ids)

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using simple substring matching."""
        async with self._lock:
            results = []
            query_lower = query.lower()

            for memory in self._memories.values():
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                ):
                    # Simple substring search in content
                    content_lower = memory["content"].lower()
                    if query_lower in content_lower:
                        # Calculate simple score based on position
                        score = 1.0 - (
                            content_lower.index(query_lower) / len(content_lower)
                        )
                        results.append({"memory": memory.copy(), "score": score})

            # Sort by score descending
            results.sort(key=lambda x: x["score"], reverse=True)

            return results[:limit]

    async def delete_expired_memories(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
    ) -> int:
        """Delete expired memories."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            matching_ids = [
                memory_id
                for memory_id, memory in self._memories.items()
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                    and memory.get("expires_at")
                    and memory["expires_at"] < now
                )
            ]

            for memory_id in matching_ids:
                await self._delete_memory_internal(memory_id)

            return len(matching_ids)

    async def update_memory_access(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Update last access time and increment usage count."""
        async with self._lock:
            memory = self._memories.get(memory_id)

            if not memory or memory["tenant_id"] != tenant_id:
                return False

            memory["last_accessed_at"] = datetime.now(timezone.utc)
            memory["access_count"] = memory.get("access_count", 0) + 1

            return True

    async def update_memory_expiration(
        self,
        memory_id: UUID,
        tenant_id: str,
        expires_at: Any,
    ) -> bool:
        """Update memory expiration time."""
        async with self._lock:
            memory = self._memories.get(memory_id)

            if not memory or memory["tenant_id"] != tenant_id:
                return False

            memory["expires_at"] = expires_at
            memory["modified_at"] = datetime.now(timezone.utc)

            return True

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        """Calculate aggregate metric."""
        async with self._lock:
            # Stub implementation
            return 0.0

    async def update_memory_access_batch(
        self,
        memory_ids: list[UUID],
        tenant_id: str,
    ) -> bool:
        """Update access count for multiple memories."""
        for mid in memory_ids:
            await self.update_memory_access(mid, tenant_id)
        return True

    async def adjust_importance(
        self,
        memory_id: UUID,
        delta: float,
        tenant_id: str,
    ) -> float:
        """Adjust memory importance."""
        async with self._lock:
            memory = self._memories.get(memory_id)
            if not memory or memory["tenant_id"] != tenant_id:
                return 0.0

            new_imp = float(memory.get("importance", 0.5)) + delta
            new_imp = max(0.0, min(1.0, new_imp))
            memory["importance"] = new_imp
            memory["modified_at"] = datetime.now(timezone.utc)
            return new_imp

    def _matches_metadata_filter(
        self, metadata: dict[str, Any], filter_dict: dict[str, Any]
    ) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

    async def _delete_memory_internal(self, memory_id: UUID) -> None:
        """Internal delete helper (assumes lock is held)."""
        memory = self._memories.get(memory_id)
        if not memory:
            return

        # Remove from main storage
        del self._memories[memory_id]

        # Remove from indexes
        tenant_id = memory["tenant_id"]
        agent_id = memory["agent_id"]
        layer = memory["layer"]

        self._by_tenant[tenant_id].discard(memory_id)
        self._by_agent[(tenant_id, agent_id)].discard(memory_id)
        self._by_layer[(tenant_id, layer)].discard(memory_id)

        for tag in memory.get("tags", []):
            self._by_tags[(tenant_id, tag)].discard(memory_id)
