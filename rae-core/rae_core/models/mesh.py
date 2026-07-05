import time
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import uuid4

class MeshPeer(BaseModel):
    peer_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    endpoint: str

class MeshExchangeEnvelope(BaseModel):
    envelope_id: str = Field(default_factory=lambda: str(uuid4()))
    source_instance: str = ""
    target_peer_id: str = ""
    pack_type: str
    pack_id: str = ""
    consent_ref: str = ""
    expires_at: Optional[datetime] = None
    sensitivity_label: str = "internal"
    payload_data: dict = Field(default_factory=dict)
    provenance: dict = Field(default_factory=dict)
    contract_version: str = "1.0.0"

class ConsentGrant(BaseModel):
    grant_id: str = Field(default_factory=lambda: str(uuid4()))
    peer_id: str
    created_at: float = Field(default_factory=lambda: time.time())
    ttl_days: float = 30.0
