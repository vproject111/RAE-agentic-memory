"""Abstract embedding provider interface for RAE-core."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class IEmbeddingProvider(Protocol):
    """Abstract interface for embedding providers."""

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        ...
