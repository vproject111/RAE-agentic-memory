from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rae_core.types.branded import (
    ChecksumSha256Value,
    KnowledgeIdValue,
    TenantIdValue,
)
from rae_core.models.knowledge import (
    KnowledgeClass,
    AuthorityLevel,
    KnowledgeSourceType,
)


class KnowledgeRegistryRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: UUID = Field(default_factory=uuid4)
    tenant_id: TenantIdValue
    knowledge_id: KnowledgeIdValue
    knowledge_class: KnowledgeClass
    owner: str = Field(min_length=1, max_length=100)
    scope: list[str] = Field(default_factory=list, max_length=100)
    generation: int = Field(ge=1, default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("scope nie może zawierać duplikatów")
        return normalized


class KnowledgeRevisionDraft(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    registry_id: UUID
    authority_level: AuthorityLevel
    source_type: KnowledgeSourceType
    source_ref: str = Field(min_length=1, max_length=2048)
    version: str | None = Field(default=None, max_length=255)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    checksum: ChecksumSha256Value
    content_summary: str = Field(min_length=1, max_length=16_384)
    content_size_bytes: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_by: str = Field(min_length=1, max_length=255)
    payload: bytes | None = None
    storage_kind: str = Field(default="postgres", min_length=1, max_length=50)
    content_type: str = Field(default="application/json", min_length=1, max_length=255)
    content_encoding: str = Field(default="identity", min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_dates(self) -> "KnowledgeRevisionDraft":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until musi być późniejsze niż valid_from")
        return self


class KnowledgeRevisionRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: UUID = Field(default_factory=uuid4)
    registry_id: UUID
    revision_no: int = Field(ge=1)
    authority_level: AuthorityLevel
    source_type: KnowledgeSourceType
    source_ref: str = Field(min_length=1, max_length=2048)
    version: str | None = Field(default=None, max_length=255)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    checksum: ChecksumSha256Value
    content_summary: str = Field(min_length=1, max_length=16_384)
    content_size_bytes: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: str = Field(min_length=1, max_length=50)
    created_by: str = Field(min_length=1, max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_dates(self) -> "KnowledgeRevisionRecord":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until musi być późniejsze niż valid_from")
        return self
