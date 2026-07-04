from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class FederationQueryRequest(BaseModel):
    query_text: str
    tenant_id: str
    project_id: str
    limit: int = Field(10, le=100)


class FederationResultItem(BaseModel):
    memory_id: str
    content_snippet: str
    full_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FederationQueryResponse(BaseModel):
    results: List[FederationResultItem]
