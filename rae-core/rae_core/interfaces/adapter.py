from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
import hashlib
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType
from rae_core.types.branded import (
    ActorIdValue,
    BinaryPayload,
    ChecksumSha256Value,
    RequestIdValue,
    TenantIdValue,
)


TQueryParams = TypeVar("TQueryParams", bound=BaseModel)


class RetrievalContext(BaseModel, Generic[TQueryParams]):
    model_config = ConfigDict(extra="forbid")

    tenant_id: TenantIdValue
    request_id: RequestIdValue
    actor_id: ActorIdValue | None = None
    scope: list[str] = Field(default_factory=list, max_length=100)
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    max_response_bytes: int = Field(default=2_097_152, ge=1024)
    allow_network: bool = False
    params: TQueryParams | None = None


class RetrievedKnowledge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source_ref: str = Field(min_length=1, max_length=2048)
    source_type: KnowledgeSourceType
    authority_level: AuthorityLevel
    score: float = Field(ge=0.0, le=1.0)
    observed_at: datetime
    source_version: str | None = Field(default=None, max_length=255)
    checksum: ChecksumSha256Value
    knowledge_id: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterError(RuntimeError):
    pass


class AdapterTimeoutError(AdapterError):
    pass


class AdapterUnavailableError(AdapterError):
    pass


class AdapterPayloadTooLargeError(AdapterError):
    pass


def compute_content_checksum(content: BinaryPayload | str) -> str:
    if isinstance(content, str):
        payload = content.encode("utf-8")
    elif isinstance(content, memoryview):
        payload = content
    else:
        payload = memoryview(content)
    return hashlib.sha256(payload).hexdigest()


class IKnowledgeAdapter(ABC, Generic[TQueryParams]):
    adapter_id: str
    source_type: KnowledgeSourceType

    @abstractmethod
    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        context: RetrievalContext[TQueryParams],
    ) -> list[RetrievedKnowledge]:
        raise NotImplementedError
