"""
Embedding data models.
Unified format for all embedding providers.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class EmbeddingRequest:
    """
    Standardized request format for embedding generation.
    """

    model: str
    input: List[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    # Optional parameters for specific providers (e.g. Ollama api_base)
    api_base: Optional[str] = None


@dataclass
class EmbeddingResponse:
    """
    Standardized response format for embedding generation.
    """

    embeddings: List[List[float]]
    model: str
    usage: Optional[dict] = None
    raw: dict[str, Any] = field(default_factory=dict)
