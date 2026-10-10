import time
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class MeshPeer(BaseModel):
    peer_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    endpoint: str


class ConsentGrant(BaseModel):
    grant_id: str = Field(default_factory=lambda: str(uuid4()))
    peer_id: str
    scope: list[str] = Field(default_factory=list)
    ttl_days: int = 30
    created_at: float = Field(default_factory=lambda: time.time())


class MeshExchangeEnvelope(BaseModel):
    envelope_id: str = Field(default_factory=lambda: str(uuid4()))
    source_instance: str = "rae-suite-main"
    target_peer_id: str = ""
    pack_type: str
    pack_id: str = ""
    consent_ref: str = ""
    expires_at: Optional[datetime] = None
    sensitivity_label: str = "internal"
    payload_data: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
    contract_version: str = "1.0.0"

