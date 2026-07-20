from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from rae_core.types.branded import (
    ActorIdValue,
    RequestIdValue,
    TenantIdValue,
)


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        raise NotImplementedError


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class ResolutionContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: TenantIdValue
    request_id: RequestIdValue
    actor_id: ActorIdValue | None = None
    scope: list[str] = Field(default_factory=list, max_length=100)
    policy_version: str = Field(min_length=1, max_length=100)
    enforce: bool = False
    shadow: bool = False
