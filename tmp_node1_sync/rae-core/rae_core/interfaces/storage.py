"""Abstract storage interface for RAE-core.

This module defines the storage interface that all storage adapters must implement.
Storage can be PostgreSQL, SQLite, in-memory, or any other backend.
"""

from typing import Any, Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class IMemoryStorage(Protocol):
    """Abstract interface for memory storage.

    Implementations must provide persistent storage for memories across
    all memory layers (sensory, working, episodic, semantic, reflective).
    """

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
        """Store a new memory.

        Args:
            content: The memory content
            layer: Memory layer (sensory, working, episodic, semantic, reflective)
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            tags: Optional list of tags
            metadata: Optional metadata dictionary
            embedding: Optional vector embedding
            importance: Optional importance score (0.0-1.0)
            expires_at: Optional expiration timestamp
            memory_type: Type of memory (default: text)
            project: Project identifier (primary source)
            session_id: Session identifier
            source: Source of the memory
            strength: Memory strength (default 1.0)
            info_class: Information classification (Smart Black Box Phase 2)
            governance: Governance metadata (Smart Black Box Phase 2)
        """
        ...

    async def get_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        """Retrieve a memory by ID.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier

        Returns:
            Memory dictionary or None if not found
        """
        ...

    async def update_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
        updates: dict[str, Any],
    ) -> bool:
        """Update a memory.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        ...

    async def delete_memory(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Delete a memory.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier

        Returns:
            True if successful, False otherwise
        """
        ...

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
        """List memories with filtering and sorting.

        Args:
            tenant_id: Tenant identifier
            agent_id: Optional agent filter
            layer: Optional layer filter
            tags: Optional tags filter (OR logic)
            filters: Optional additional filters
            limit: Maximum number of results
            offset: Pagination offset
            order_by: Field to sort by
            order_direction: "asc" or "desc"

        Returns:
            List of memory dictionaries
        """
        ...

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
            metadata_filter: Filter criteria

        Returns:
            Number of memories deleted
        """
        ...

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
            importance_threshold: Minimum importance to keep

        Returns:
            Number of memories deleted
        """
        ...

    async def count_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        """Count memories matching filters.

        Args:
            tenant_id: Tenant identifier
            agent_id: Optional agent filter
            layer: Optional layer filter

        Returns:
            Count of matching memories
        """
        ...

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search memories using full-text search.

        Args:
            query: Search query
            tenant_id: Tenant identifier
            agent_id: Agent identifier
            layer: Memory layer
            limit: Maximum number of results
            filters: Optional filters

        Returns:
            List of dictionaries containing 'memory' (dict) and 'score' (float)
        """
        ...

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
        ...

    async def update_memory_access(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        """Update last access time and increment usage count.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier

        Returns:
            True if successful, False otherwise
        """
        ...

    async def update_memory_expiration(
        self,
        memory_id: UUID,
        tenant_id: str,
        expires_at: Any,
    ) -> bool:
        """Update memory expiration time.

        Args:
            memory_id: UUID of the memory
            tenant_id: Tenant identifier
            expires_at: New expiration timestamp

        Returns:
            True if successful, False otherwise
        """
        ...

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        """Calculate aggregate metric for memories.

        Args:
            tenant_id: Tenant identifier
            metric: Field to aggregate (e.g., 'importance', 'access_count')
            func: Aggregation function ('avg', 'sum', 'min', 'max', 'count')
            filters: Optional filters to apply before aggregation

        Returns:
            Aggregated value as float
        """
        ...

    async def update_memory_access_batch(
        self,
        memory_ids: list[UUID],
        tenant_id: str,
    ) -> bool:
        """Update last access time and increment usage count for multiple memories.

        Args:
            memory_ids: List of memory UUIDs
            tenant_id: Tenant identifier

        Returns:
            True if all updates were successful
        """
        ...

    async def adjust_importance(
        self,
        memory_id: UUID,
        delta: float,
        tenant_id: str,
    ) -> float:
        """Adjust memory importance by a delta value.

        Args:
            memory_id: UUID of the memory
            delta: Value to add to current importance (can be negative)
            tenant_id: Tenant identifier

        Returns:
            New importance value
        """
        ...

    async def save_embedding(
        self,
        memory_id: UUID,
        model_name: str,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Save a vector embedding for a memory.

        Args:
            memory_id: UUID of the memory
            model_name: Name of the embedding model
            embedding: Vector embedding list
            tenant_id: Tenant identifier
            metadata: Optional metadata

        Returns:
            True if successful
        """
        ...

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = False,
    ) -> int:
        """Apply importance decay to all memories for a tenant.

        Args:
            tenant_id: Tenant identifier
            decay_rate: Rate of decay (0.0 to 1.0)
            consider_access_stats: If True, decay is slower for frequently accessed memories

        Returns:
            Number of memories updated
        """
        ...
