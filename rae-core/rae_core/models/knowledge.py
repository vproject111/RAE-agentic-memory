from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rae_core.types.branded import (
    ChecksumSha256Value,
    KnowledgeIdValue,
    TenantIdValue,
)


class KnowledgeClass(StrEnum):
    NORMATIVE = "normative"
    ARCHITECTURAL = "architectural"
    OPERATIONAL = "operational"
    EMPIRICAL = "empirical"
    EPISODIC = "episodic"
    EXTERNAL = "external"


class AuthorityLevel(StrEnum):
    CANONICAL = "canonical"
    APPROVED = "approved"
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNTRUSTED = "untrusted"


class KnowledgeSourceType(StrEnum):
    GIT = "git"
    OPENAPI = "openapi"
    JSON_SCHEMA = "json-schema"
    DATABASE = "database"
    API = "api"
    FILE = "file"
    TEST = "test"


class KnowledgeRecord(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    id: UUID = Field(default_factory=uuid4)
    tenant_id: TenantIdValue
    knowledge_id: KnowledgeIdValue
    knowledge_class: KnowledgeClass
    authority_level: AuthorityLevel
    source_type: KnowledgeSourceType
    source_ref: str = Field(min_length=1, max_length=2048)
    owner: str = Field(min_length=1, max_length=100)
    version: str | None = Field(default=None, max_length=255)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    supersedes: list[KnowledgeIdValue] = Field(default_factory=list)
    scope: list[str] = Field(default_factory=list, max_length=100)
    checksum: ChecksumSha256Value
    content_summary: str = Field(min_length=1, max_length=16_384)
    content_size_bytes: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scope")
    @classmethod
    def validate_scope(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values if value.strip()]
        if len(normalized) != len(set(normalized)):
            raise ValueError("scope nie może zawierać duplikatów")
        return normalized

    @model_validator(mode="after")
    def validate_dates(self) -> "KnowledgeRecord":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until musi być późniejsze niż valid_from")
        return self
