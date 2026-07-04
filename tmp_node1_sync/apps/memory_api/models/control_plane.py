from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class NodeStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    BUSY = "BUSY"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ComputeNode(BaseModel):
    id: UUID
    node_id: str
    status: NodeStatus
    last_heartbeat: Optional[datetime]
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str]
    created_at: datetime
    updated_at: datetime


class DelegatedTask(BaseModel):
    id: UUID
    type: str
    status: TaskStatus
    priority: int
    payload: Dict[str, Any]
    result: Optional[Dict[str, Any]]
    assigned_node_id: Optional[UUID]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class RegisterNodeRequest(BaseModel):
    node_id: str
    api_key: str
    capabilities: Dict[str, Any]
    ip_address: Optional[str] = None


class CreateTaskRequest(BaseModel):
    type: str
    payload: Dict[str, Any]
    priority: int = 0


class HeartbeatRequest(BaseModel):
    node_id: str
    status: NodeStatus


class TaskResultRequest(BaseModel):
    task_id: UUID
    result: Dict[str, Any]
    error: Optional[str] = None
