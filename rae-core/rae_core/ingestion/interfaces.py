"""
RAE Universal Ingest Interfaces.
Defines the contracts for the 5-stage pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IngestAudit:
    """Audit trail for a single ingest step."""

    stage: str
    action: str
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentSignature:
    """Universal signature of input content."""

    struct: dict[str, Any]  # Structural features (S-Layer)
    dist: dict[str, Any]  # Distributional features (D-Layer)
    stab: dict[str, Any]  # Stability features (O-Layer)

    def to_dict(self) -> dict[str, Any]:
        return {"struct": self.struct, "dist": self.dist, "stab": self.stab}


class INormalizer(ABC):
    @abstractmethod
    def normalize(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> tuple[str, IngestAudit]:
        pass


class ISignatureDetector(ABC):
    @abstractmethod
    def detect(self, text: str) -> tuple[ContentSignature, IngestAudit]:
        pass


class IPolicySelector(ABC):
    @abstractmethod
    def select_policy(self, signature: ContentSignature) -> tuple[str, IngestAudit]:
        pass


@dataclass
class IngestChunk:
    content: str
    metadata: dict[str, Any]
    offset: int
    length: int


class ISegmenter(ABC):
    @abstractmethod
    async def segment(
        self, text: str, policy: str, signature: ContentSignature
    ) -> tuple[list[IngestChunk], IngestAudit]:
        pass


class ICompressor(ABC):
    @abstractmethod
    def compress(
        self, chunks: list[IngestChunk], policy: str
    ) -> tuple[list[IngestChunk], dict[str, Any], IngestAudit]:
        pass
