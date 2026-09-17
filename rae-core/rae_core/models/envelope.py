"""ContextEnvelope data model for contextual attribution in RAE."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CodeAttribution(BaseModel):
    """Detailed structural attribution of code artifacts."""

    model_config = ConfigDict(extra="forbid")

    repository: str = Field(description="Repository name or URI")
    branch: str | None = Field(default=None, description="Git branch name")
    commit_sha: str | None = Field(default=None, description="Commit SHA hash")
    file_path: str = Field(description="Relative or normalized file path")
    language: str | None = Field(
        default=None, description="Programming or markup language"
    )
    class_name: str | None = Field(
        default=None, description="Enclosing class or interface name"
    )
    function_name: str | None = Field(
        default=None, description="Enclosing function or method name"
    )
    start_line: int | None = Field(
        default=None, ge=1, description="1-indexed starting line"
    )
    end_line: int | None = Field(
        default=None, ge=1, description="1-indexed ending line"
    )


class ContextEnvelope(BaseModel):
    """Context envelope encapsulating provenance without polluting raw memory content."""

    model_config = ConfigDict(extra="forbid")

    source_type: str = Field(
        default="code",
        description="Origin source category: code | doc | test | architecture | system_log | chat",
    )
    project: str = Field(
        description="Target project identifier (e.g. rae_suite, dreamsoft, screenwatcher)"
    )
    task_id: str | None = Field(default=None, description="Associated task identifier")
    trace_id: str | None = Field(
        default=None, description="Correlation trace identifier"
    )
    correlation_id: str | None = Field(
        default=None, description="Distributed correlation ID"
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    attribution: CodeAttribution | None = Field(
        default=None, description="Structural code attribution if source is code"
    )
    scope_tags: list[str] = Field(
        default_factory=list, description="Categorical or semantic tags"
    )
    semantic_summary: str | None = Field(
        default=None,
        max_length=500,
        description="Brief deterministic summary of contextual intent",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional contextual properties"
    )
