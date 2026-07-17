from typing import Any

from pydantic import BaseModel, Field


class AgentCapability(BaseModel):
    name: str
    description: str
    version: str
    parameters_schema: dict[str, Any] = Field(default_factory=dict)


class AgentRegistration(BaseModel):
    agent_id: str
    department: str
    role: str
    capabilities: list[AgentCapability]
    endpoint: str | None = None
    status: str = "active"
