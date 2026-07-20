"""
Memory API v2 - powered by RAE-Core.

Uses RAEEngine with 4-layer architecture and hybrid search.
"""

from typing import Any, Optional, cast
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services import pii_scrubber
from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.exceptions.base import (
    ContractViolationError,
    SecurityPolicyViolationError,
)

router = APIRouter(prefix="/v2/memories", tags=["Memory v2 (RAE-Core)"])
logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


# Request/Response models
class StoreMemoryRequestV2(BaseModel):
    """Store memory request for v2 API - Extreme Compatibility Mode."""

    content: str
    source: str | None = "api"
    project: str | None = "default"
    importance: float | None = 0.5
    tags: list[str] | None = None
    layer: str | None = "episodic"
    session_id: str | None = None
    memory_type: str | None = "text"
    ttl: int | None = None
    metadata: dict[str, Any] | None = None
    human_label: str | None = None
    agent_id: str | None = "default"
    info_class: str | None = "internal"
    governance: dict[str, Any] | None = None


class StoreMemoryResponseV2(BaseModel):
    """Store memory response for v2 API."""

    memory_id: str
    message: str = "Memory stored in RAE-Core"


class QueryMemoryRequestV2(BaseModel):
    """Query memory request for v2 API."""

    query: str = Field(..., min_length=1, max_length=1024)
    project: str = Field(..., min_length=1, max_length=255)
    k: int = Field(default=10, gt=0, le=100)
    layers: list[str] | None = Field(default=None)
    filters: dict[str, Any] | None = Field(default=None)


class MemoryResult(BaseModel):
    """Memory search result."""

    id: str
    content: str
    score: float
    layer: str
    importance: float
    timestamp: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    human_label: str | None = None


class QueryMemoryResponseV2(BaseModel):
    """Query memory response for v2 API."""

    results: list[MemoryResult]
    total_count: int
    synthesized_context: str | None = None


class ListMemoryResponseV2(BaseModel):
    """Paginated list of memories."""

    results: list[MemoryResult]
    total: int
    limit: int
    offset: int


@router.post("/", response_model=StoreMemoryResponseV2)
async def store_memory(
    request: StoreMemoryRequestV2,
    http_request: Request,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Store memory using RAE-Core engine.
    """
    with tracer.start_as_current_span("rae.api.v2.memory.store") as span:
        span.set_attribute("rae.tenant_id", str(tenant_id))
        span.set_attribute("rae.project", request.project)

        content = pii_scrubber.scrub_text(request.content)
        session_id = request.session_id or getattr(
            http_request.state, "session_id", None
        )

        try:
            memory_id = await rae_service.store_memory(
                tenant_id=str(tenant_id),
                project=request.project,
                content=content,
                source=request.source,
                importance=request.importance,
                tags=request.tags,
                layer=request.layer,
                session_id=session_id,
                memory_type=request.memory_type,
                ttl=request.ttl,
                metadata=request.metadata,
                human_label=request.human_label,
            )

            if memory_id is None:
                return StoreMemoryResponseV2(
                    memory_id="skipped",
                    message="Memory skipped (duplicate or filtered)",
                )

            return StoreMemoryResponseV2(memory_id=str(memory_id))
        except (SecurityPolicyViolationError, ContractViolationError) as e:
            logger.warning("memory_action_blocked", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error("store_memory_failed", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryMemoryResponseV2)
async def query_memories(
    request: QueryMemoryRequestV2,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Query memories using RAE-Core hybrid search.
    """
    with tracer.start_as_current_span("rae.api.v2.memory.query") as span:
        span.set_attribute("rae.tenant_id", str(tenant_id))
        span.set_attribute("rae.query", request.query)

        try:
            response = await rae_service.query_memories(
                tenant_id=str(tenant_id),
                project=request.project,
                query=request.query,
                k=request.k,
                layers=request.layers,
                filters=request.filters,
            )

            results = []
            for res in response.results:
                # Handle timestamp from engine results
                ts = (
                    res.metadata.get("created_at") if hasattr(res, "metadata") else None
                )
                if not ts and hasattr(res, "timestamp"):
                    ts = res.timestamp

                if hasattr(ts, "isoformat"):
                    ts = ts.isoformat()

                results.append(
                    MemoryResult(
                        id=res.memory_id,
                        content=res.content,
                        score=res.score,
                        layer=getattr(res, "layer", "semantic"),
                        importance=getattr(res, "importance", 0.5),
                        timestamp=ts,
                        tags=getattr(res, "tags", []),
                        metadata=getattr(res, "metadata", {}),
                        human_label=getattr(res, "human_label", None),
                    )
                )

            if results:
                await rae_service.update_memory_access_batch(
                    memory_ids=[r.id for r in results], tenant_id=str(tenant_id)
                )

            return QueryMemoryResponseV2(results=results, total_count=len(results))
        except Exception as e:
            logger.error("query_memories_failed", error=str(e), tenant_id=tenant_id)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=ListMemoryResponseV2)
async def list_memories(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    project: Optional[str] = None,
    layer: Optional[str] = None,
    sort: Optional[str] = Query(
        None, description="Sort field and direction, e.g. 'created_at:desc'"
    ),
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """List memories with pagination."""
    try:
        memories = await rae_service.list_memories(
            tenant_id=str(tenant_id),
            limit=limit,
            offset=offset,
            project=project,
            layer=layer,
        )

        # Apply manual sort if needed
        if sort:
            try:
                field, direction = sort.split(":")
                reverse = direction.lower() == "desc"
                sort_field = "created_at" if field == "created_at" else field
                memories.sort(key=lambda x: x.get(sort_field) or "", reverse=reverse)
            except Exception as e:
                logger.warning("manual_sort_failed", error=str(e), sort=sort)

        results = []
        for m in memories:
            metadata_val = m.get("metadata", {})
            if isinstance(metadata_val, str):
                try:
                    import json

                    metadata_val = json.loads(metadata_val)
                except Exception:
                    metadata_val = {}

            ts = m.get("created_at")
            if hasattr(ts, "isoformat"):
                ts = ts.isoformat()

            results.append(
                MemoryResult(
                    id=str(m.get("id")),
                    content=m.get("content", ""),
                    score=1.0,
                    layer=m.get("layer", "semantic"),
                    importance=m.get("importance", 0.5),
                    timestamp=ts,
                    tags=m.get("tags", []),
                    metadata=metadata_val,
                    human_label=m.get("human_label"),
                )
            )

        return ListMemoryResponseV2(
            results=results, total=len(results), limit=limit, offset=offset
        )
    except Exception as e:
        logger.error("list_memories_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics(
    project: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Get memory statistics across all layers."""
    try:
        stats = await rae_service.get_statistics(
            tenant_id=str(tenant_id),
            project=project,
        )
        return {"statistics": stats}
    except Exception as e:
        logger.error("get_statistics_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/consolidate")
async def consolidate_memories(
    project: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Trigger memory consolidation across layers."""
    try:
        results = await rae_service.consolidate_memories(
            tenant_id=str(tenant_id),
            project=project,
        )
        return {"message": "Consolidation completed", "results": results}
    except Exception as e:
        logger.error("consolidate_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(status_code=500, detail=f"Failed to consolidate: {str(e)}")


@router.post("/reflections")
async def generate_reflections(
    project: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Generate reflections from memory patterns."""
    try:
        reflections = await rae_service.generate_reflections(
            tenant_id=str(tenant_id),
            project=project,
        )
        return {
            "message": "Reflections generated",
            "count": len(reflections),
            "reflections": [
                {
                    "id": cast(Any, r).id,
                    "content": cast(Any, r).content,
                    "importance": cast(Any, r).importance,
                    "tags": cast(Any, r).tags or [],
                }
                for r in reflections
            ],
        }
    except Exception as e:
        logger.error("generate_reflections_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate reflections: {str(e)}"
        )


@router.get("/sessions/{session_id}")
async def get_session_context(
    session_id: str,
    limit: int = Query(50, ge=1, le=1000),
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Retrieves all memories associated with a specific session."""
    try:
        memories = await rae_service.get_session_context(
            session_id=session_id,
            tenant_id=str(tenant_id),
            limit=limit,
        )
        return {"session_id": session_id, "memories": memories}
    except Exception as e:
        logger.error("get_session_context_failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{memory_id}", response_model=MemoryResult)
async def get_memory(
    memory_id: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Retrieve a single memory by ID."""
    try:
        memory = await rae_service.get_memory(memory_id, str(tenant_id))
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")

        metadata_val = memory.get("metadata", {})
        if isinstance(metadata_val, str):
            try:
                import json

                metadata_val = json.loads(metadata_val)
            except Exception:
                metadata_val = {}

        ts = memory.get("created_at")
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat()

        return MemoryResult(
            id=str(memory.get("id")),
            content=memory.get("content", ""),
            score=1.0,
            layer=memory.get("layer", "semantic"),
            importance=memory.get("importance", 0.5),
            timestamp=ts,
            tags=memory.get("tags", []),
            metadata=metadata_val,
            human_label=memory.get("human_label"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_memory_failed", memory_id=memory_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """Delete a memory."""
    try:
        deleted = await rae_service.delete_memory(memory_id, str(tenant_id))
        if not deleted:
            raise HTTPException(status_code=404, detail="Memory not found")
        return {"memory_id": memory_id, "message": "Memory deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_memory_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
