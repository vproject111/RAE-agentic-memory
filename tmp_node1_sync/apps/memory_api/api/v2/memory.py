"""
Memory API v2 - powered by RAE-Core.

Uses RAEEngine with 4-layer architecture and hybrid search.
"""

from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services.rae_core_service import RAECoreService

router = APIRouter(prefix="/v2/memories", tags=["Memory v2 (RAE-Core)"])
logger = structlog.get_logger(__name__)


# Request/Response models
class StoreMemoryRequestV2(BaseModel):
    """Store memory request for v2 API."""

    content: str = Field(..., min_length=1, max_length=8192)
    source: str = Field(default="api", max_length=255)
    project: str = Field(..., min_length=1, max_length=255)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    layer: str | None = Field(
        default=None, pattern="^(sensory|working|longterm|reflective)$"
    )
    # Phase 1: Canonical fields
    session_id: str | None = Field(None, description="Session identifier")
    memory_type: str | None = Field(None, description="Memory type (text, code, etc.)")
    ttl: int | None = Field(None, gt=0, description="Time to live in seconds")


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


class MemoryResult(BaseModel):
    """Memory search result."""

    id: str
    content: str
    score: float
    layer: str
    importance: float
    tags: list[str] = Field(default_factory=list)


class QueryMemoryResponseV2(BaseModel):
    """Query memory response for v2 API."""

    results: list[MemoryResult]
    total_count: int
    synthesized_context: str | None = None


@router.post("/", response_model=StoreMemoryResponseV2)
async def store_memory(
    request: StoreMemoryRequestV2,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Store memory using RAE-Core engine.

    Stores memory in appropriate layer based on importance and parameters.
    Memory flows through 4-layer architecture:
    - Sensory: raw input buffer
    - Working: active processing
    - LongTerm: persistent storage
    - Reflective: meta-learning and insights
    """
    try:
        memory_id = await rae_service.store_memory(
            tenant_id=str(tenant_id),
            project=request.project,
            content=request.content,
            source=request.source,
            importance=request.importance,
            tags=request.tags,
            layer=request.layer,
            session_id=request.session_id,
            memory_type=request.memory_type,
            ttl=request.ttl,
        )

        return StoreMemoryResponseV2(memory_id=memory_id)

    except Exception as e:
        logger.error("store_memory_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to store memory: {str(e)}"
        ) from e


@router.post("/query", response_model=QueryMemoryResponseV2)
async def query_memories(
    request: QueryMemoryRequestV2,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Query memories using RAE-Core hybrid search.

    Searches across specified layers using:
    - Keyword matching
    - Importance scoring
    - Recency decay
    - Multi-strategy fusion (RRF, weighted sum)
    """
    try:
        from typing import Any, cast

        response = await rae_service.query_memories(
            tenant_id=str(tenant_id),
            project=request.project,
            query=request.query,
            k=request.k,
            layers=request.layers,
        )

        results = [
            MemoryResult(
                id=(result := cast(Any, res)).id,
                content=result.content,
                score=result.score,
                layer=result.layer,
                importance=result.importance,
                tags=result.tags or [],
            )
            for res in cast(Any, response).results
        ]

        return QueryMemoryResponseV2(
            results=results,
            total_count=len(results),
            synthesized_context=cast(Any, response).synthesized_context,
        )

    except Exception as e:
        logger.error("query_memories_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to query memories: {str(e)}"
        ) from e


@router.post("/consolidate")
async def consolidate_memories(
    project: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Trigger memory consolidation across layers.

    Consolidates memories based on:
    - Sensory → Working: importance threshold
    - Working → LongTerm: usage + importance
    - LongTerm → Reflective: pattern detection
    """
    try:
        results = await rae_service.consolidate_memories(
            tenant_id=str(tenant_id),
            project=project,
        )

        return {
            "message": "Consolidation completed",
            "results": results,
        }

    except Exception as e:
        logger.error("consolidate_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to consolidate: {str(e)}"
        ) from e


@router.post("/reflections")
async def generate_reflections(
    project: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Generate reflections from memory patterns.

    Analyzes patterns in long-term memory and creates
    meta-learning insights stored in reflective layer.
    """
    try:
        reflections = await rae_service.generate_reflections(
            tenant_id=str(tenant_id),
            project=project,
        )

        from typing import Any, cast

        return {
            "message": "Reflections generated",
            "count": len(reflections),
            "reflections": [
                {
                    "id": (ref := cast(Any, r)).id,
                    "content": ref.content,
                    "importance": ref.importance,
                    "tags": ref.tags or [],
                }
                for r in reflections
            ],
        }

    except Exception as e:
        logger.error("generate_reflections_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to generate reflections: {str(e)}"
        ) from e


@router.get("/stats")
async def get_statistics(
    project: str,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Get memory statistics across all layers.

    Returns counts, averages, and metrics for:
    - Sensory layer
    - Working memory
    - Long-term storage
    - Reflective layer
    """
    try:
        stats = await rae_service.get_statistics(
            tenant_id=str(tenant_id),
            project=project,
        )

        return {
            "statistics": stats,
        }

    except Exception as e:
        logger.error("get_statistics_failed", error=str(e), tenant_id=tenant_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to get statistics: {str(e)}"
        ) from e
