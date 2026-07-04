from typing import Any, Dict, List, Protocol

from ...models import MemoryRecord, ScoredMemoryRecord


class MemoryVectorStore(Protocol):
    """
    A protocol defining the interface for a vector database store.
    """

    async def upsert(
        self, memories: List[MemoryRecord], embeddings: List[List[float]]
    ) -> None:
        """
        Upserts a list of memories into the vector store.

        Args:
            memories: A list of MemoryRecord objects.
            embeddings: A list of corresponding vector embeddings.
        """
        ...

    async def query(
        self, query_embedding: List[float], top_k: int, filters: Dict[str, Any]
    ) -> List[ScoredMemoryRecord]:
        """
        Queries the vector store for similar memories.

        Args:
            query_embedding: The vector embedding of the query text.
            top_k: The number of results to return.
            filters: A dictionary of filters to apply to the search.

        Returns:
            A list of ScoredMemoryRecord objects.
        """
        ...

    async def delete(self, memory_id: str) -> None:
        """
        Deletes a memory from the vector store by its ID.

        Args:
            memory_id: The ID of the memory to delete.
        """
        ...
