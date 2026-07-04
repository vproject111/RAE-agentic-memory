"""Full-text keyword search strategy."""

from typing import Any
from uuid import UUID

from rae_core.interfaces.storage import IMemoryStorage
from rae_core.search.strategies import SearchStrategy


class FullTextStrategy(SearchStrategy):
    """Full-text keyword matching search.

    Simple exact and partial keyword matching for fast retrieval.
    Useful for tag-based and exact phrase searches.
    """

    def __init__(
        self,
        memory_storage: IMemoryStorage,
        default_weight: float = 0.2,
    ):
        """Initialize full-text strategy.

        Args:
            memory_storage: Memory storage for content retrieval
            default_weight: Default weight in hybrid search (0.0-1.0)
        """
        self.memory_storage = memory_storage
        self.default_weight = default_weight

    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        return text.lower().strip()

    def _compute_match_score(
        self,
        query: str,
        content: str,
        tags: list[str],
    ) -> float:
        """Compute match score based on keyword presence.

        Args:
            query: Search query
            content: Memory content
            tags: Memory tags

        Returns:
            Match score (0.0-1.0)
        """
        query_norm = self._normalize(query)
        content_norm = self._normalize(content)
        tags_norm = [self._normalize(tag) for tag in tags]

        score = 0.0

        # Exact phrase match (highest score)
        if query_norm in content_norm:
            score += 1.0

        # Tag exact match
        if query_norm in tags_norm:
            score += 0.8

        # Word-level matches
        query_words = set(query_norm.split())
        content_words = set(content_norm.split())
        tag_words = set(word for tag in tags_norm for word in tag.split())

        # Calculate overlap
        content_overlap = (
            len(query_words & content_words) / len(query_words) if query_words else 0
        )
        tag_overlap = (
            len(query_words & tag_words) / len(query_words) if query_words else 0
        )

        score += content_overlap * 0.6
        score += tag_overlap * 0.4

        return min(score, 1.0)

    async def search(
        self,
        query: str,
        tenant_id: str,
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[tuple[UUID, float]]:
        """Execute full-text search.

        Args:
            query: Search query text
            tenant_id: Tenant identifier
            filters: Optional filters (layer, agent_id, tags)
            limit: Maximum number of results

        Returns:
            List of (memory_id, match_score) tuples
        """
        # Extract filters
        layer = filters.get("layer") if filters else None
        agent_id = filters.get("agent_id") if filters else None
        tag_filter = filters.get("tags") if filters else None

        # Retrieve memories
        memories = await self.memory_storage.list_memories(
            tenant_id=tenant_id,
            agent_id=agent_id,
            layer=layer,
            tags=tag_filter,
            limit=500,  # Limit corpus for performance
        )

        if not memories:
            return []

        # Score each memory
        results: list[tuple[UUID, float]] = []
        is_wildcard = query.strip() == "*"

        for memory in memories:
            memory_id = memory["id"]
            if isinstance(memory_id, str):
                memory_id = UUID(memory_id)

            content = memory.get("content", "")
            tags = memory.get("tags", [])

            if is_wildcard:
                score = 1.0
            else:
                score = self._compute_match_score(query, content, tags)

            if score > 0:
                results.append((memory_id, score))

        # Sort by score descending and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def get_strategy_name(self) -> str:
        """Return strategy name."""
        return "fulltext"

    def get_strategy_weight(self) -> float:
        """Return default weight for hybrid fusion."""
        return self.default_weight
