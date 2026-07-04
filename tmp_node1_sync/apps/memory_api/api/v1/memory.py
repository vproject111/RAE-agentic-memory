from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.metrics import (
    memory_delete_counter,
    memory_query_counter,
    memory_store_counter,
)
from apps.memory_api.models import (
    DeleteMemoryResponse,
    ListMemoryResponse,
    MemoryLayer,
    MemoryRecord,
    QueryMemoryRequest,
    QueryMemoryResponse,
    RebuildReflectionsRequest,
    ScoredMemoryRecord,
    StoreMemoryRequest,
    StoreMemoryResponse,
)
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.security import auth
from apps.memory_api.security.dependencies import get_and_verify_tenant_id
from apps.memory_api.services import pii_scrubber
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.vector_store import get_vector_store
from apps.memory_api.tasks.background_tasks import (
    generate_reflection_for_project,
)

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)

# All memory endpoints require authentication
router = APIRouter(
    prefix="/memory",
    tags=["memory-protocol"],
    dependencies=[Depends(auth.verify_token)],
)


@router.get("/list", response_model=ListMemoryResponse)
async def list_memories(
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    project: Optional[str] = None,
    layer: Optional[MemoryLayer] = None,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    List memories with pagination.

    **Security:** Requires authentication and tenant access.
    """
    with tracer.start_as_current_span("rae.api.memory.list") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        if project:
            span.set_attribute("rae.project_id", project)

        try:
            memories = await rae_service.list_memories(
                tenant_id=str(tenant_id),
                limit=limit,
                offset=offset,
                project=project,
                layer=layer.value if layer else None,
            )

            # Map dictionaries to MemoryRecord objects
            results = []
            layer_mapping = {
                "ltm": "semantic",
                "sm": "semantic",
                "em": "episodic",
                "stm": "working",
                "wm": "working",
                "rm": "reflective",
            }

            for mem in memories:
                # Ensure all required fields are present
                if "timestamp" not in mem:
                    mem["timestamp"] = datetime.now()

                # Normalize layer names
                if "layer" in mem and mem["layer"] in layer_mapping:
                    mem["layer"] = layer_mapping[mem["layer"]]

                # Convert UUID fields to strings for Pydantic
                if "id" in mem and isinstance(mem["id"], UUID):
                    mem["id"] = str(mem["id"])
                if "tenant_id" in mem and isinstance(mem["tenant_id"], UUID):
                    mem["tenant_id"] = str(mem["tenant_id"])

                results.append(MemoryRecord(**mem))

            return ListMemoryResponse(
                results=results,
                total=len(
                    results
                ),  # This is page size, real total requires separate count query
                limit=limit,
                offset=offset,
            )
        except Exception as e:
            span.set_attribute("rae.outcome.label", "list_error")
            logger.error(f"List memories error: {e}")
            raise HTTPException(status_code=500, detail=f"List error: {e}") from e


@router.post("/store", response_model=StoreMemoryResponse)
async def store_memory(
    req: StoreMemoryRequest,
    request: Request,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Stores a new memory record in the database and vector store.

    **Security:** Requires authentication and tenant access with memories:write permission.
    """
    with tracer.start_as_current_span("rae.api.memory.store") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        if req.project:
            span.set_attribute("rae.project_id", req.project)
        span.set_attribute("rae.memory.content_length_original", len(req.content))
        span.set_attribute("rae.memory.importance", req.importance)
        if req.layer:
            span.set_attribute("rae.memory.layer", req.layer.value)
        if req.tags:
            span.set_attribute("rae.memory.tags_count", len(req.tags))
        span.set_attribute("rae.memory.source", req.source)

        content = pii_scrubber.scrub_text(req.content)
        span.set_attribute("rae.memory.content_length_scrubbed", len(content))

        try:
            # 1. Store metadata in Postgres using RAE-Core Service
            session_id = req.session_id or getattr(request.state, "session_id", None)

            memory_id = await rae_service.store_memory(
                tenant_id=str(tenant_id),
                project=req.project,
                content=content,
                source=req.source,
                importance=req.importance,
                layer=req.layer.value if req.layer else None,
                tags=req.tags,
                # Phase 3: Canonical fields
                session_id=session_id,
                memory_type=req.memory_type,
                ttl=req.ttl,
            )

            # RAE-Core Service handles vector storage internally now (via Engine)
            # But legacy API expected MemoryRecord object back or at least ID.
            # RAECoreService.store_memory returns ID string.

            span.set_attribute("rae.memory.id", str(memory_id))

        except HTTPException:
            raise
        except Exception as e:
            span.set_attribute("rae.outcome.label", "storage_error")
            raise HTTPException(status_code=500, detail=f"Storage error: {e}") from e

        span.set_attribute("rae.outcome.label", "success")
        memory_store_counter.labels(
            tenant_id=tenant_id
        ).inc()  # Increment store counter
        return StoreMemoryResponse(id=memory_id)


@router.post("/query", response_model=QueryMemoryResponse)
async def query_memory(
    req: QueryMemoryRequest,
    request: Request,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Queries the memory for relevant records based on a query text.

    Supports vector search.

    Args:
        req: Query request parameters
        request: FastAPI request object
        tenant_id: Verified tenant ID (injected via RBAC)
        rae_service: RAECoreService (injected via DI)

    **Security:** Requires authentication and tenant access with memories:read permission.
    """
    if req.use_graph and not req.project:
        raise HTTPException(
            status_code=400,
            detail="project parameter is required when use_graph is True",
        )

    with tracer.start_as_current_span("rae.api.memory.query") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        if req.project:
            span.set_attribute("rae.project_id", req.project)
        span.set_attribute("rae.query.text_length", len(req.query_text))
        span.set_attribute("rae.query.k", req.k)
        span.set_attribute(
            "rae.query.use_graph", req.use_graph
        )  # Still in request model
        if req.use_graph:
            span.set_attribute(
                "rae.query.graph_depth", req.graph_depth or 1
            )  # Still in request model
        if req.filters:
            span.set_attribute("rae.query.filters_count", len(req.filters))

        # Standard vector search mode (using RAECoreService)
        span.set_attribute("rae.query.mode", "vector_via_rae_core")

        # 3. Query using RAECoreService
        try:
            # RAECoreService.query_memories returns SearchResponse object
            # It internally handles embedding generation and vector store querying
            search_response = await rae_service.query_memories(
                tenant_id=str(tenant_id),
                project=req.project or "default",
                query=req.query_text,
                k=req.k,
            )

            # Convert RAE-Core SearchResponse results back to the format expected by the API
            # SearchResult to ScoredMemoryRecord mapping
            rescored_results = []
            for item in search_response.results:
                rescored_results.append(
                    ScoredMemoryRecord(
                        id=item.memory_id,
                        content=item.content,
                        score=item.score,
                        metadata=item.metadata,
                        tenant_id=str(tenant_id),
                        project=req.project or "default",
                        layer=MemoryLayer.semantic,  # Default for standard query
                    )
                )

            span.set_attribute("rae.query.results_count", len(rescored_results))
        except Exception as e:
            err_msg = str(e)
            span.set_attribute("rae.outcome.label", "rae_core_query_error")
            logger.error(f"rae_core_query_failed: {err_msg}")
            raise HTTPException(
                status_code=502, detail=f"Memory search error: {err_msg}"
            ) from e

        # 4. Update access statistics for retrieved memories
        memory_ids = [item.id for item in rescored_results]
        if memory_ids:
            try:
                await rae_service.update_memory_access_batch(
                    memory_ids=memory_ids, tenant_id=str(tenant_id)
                )
            except Exception as e:
                # Log but don't fail the query
                logger.warning(
                    "vector_query_access_stats_update_failed",
                    tenant_id=tenant_id,
                    error=str(e),
                )

        span.set_attribute("rae.outcome.label", "success")
        memory_query_counter.labels(
            tenant_id=tenant_id
        ).inc()  # Increment query counter
        return QueryMemoryResponse(results=rescored_results)


@router.delete("/delete", response_model=DeleteMemoryResponse)
async def delete_memory(
    memory_id: str,
    request: Request,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Deletes a memory record from the database and vector store.

    **Security:** Requires authentication and tenant access with memories:delete permission.
    """
    with tracer.start_as_current_span("rae.api.memory.delete") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        span.set_attribute("rae.memory.id", memory_id)

        # 1. Delete from database using RAE-Core Service
        try:
            deleted = await rae_service.delete_memory(memory_id, str(tenant_id))

            if not deleted:
                span.set_attribute("rae.outcome.label", "not_found")
                raise HTTPException(status_code=404, detail="Memory not found.")

            span.set_attribute("rae.memory.db_deleted", True)

        except HTTPException:
            raise
        except Exception as e:
            span.set_attribute("rae.outcome.label", "database_error")
            raise HTTPException(status_code=500, detail=f"Database error: {e}") from e

        # 2. Delete from vector store - HANDLED BY RAE-CORE ENGINE via DELETE_MEMORY
        # Assuming RAE-Core engine handles both storage and vector store deletion.
        # RAECoreService.delete_memory calls storage adapter.
        # If vector store is separate in engine, engine.delete_memory should be called instead of adapter directly.
        # RAECoreService.delete_memory wraps adapter.delete_memory currently (based on previous edits).
        # ideally RAECoreService.delete_memory should call engine.delete_memory.
        # Checking RAECoreService implementation:
        # async def delete_memory(self, memory_id: str, tenant_id: str) -> bool:
        #     try:
        #         mem_uuid = UUID(memory_id)
        #     except ValueError:
        #         return False
        #     return await self.postgres_adapter.delete_memory(mem_uuid, tenant_id)

        # It calls adapter directly. So vector store deletion is NOT handled by RAECoreService yet if engine is not used.
        # To maintain vector store deletion, we should use RAEEngine if possible or keep explicit vector store delete.
        # Given we want to move logic to RAECore, RAEEngine should be used.
        # But RAECoreService wraps Engine and Adapters.

        # Let's keep manual vector delete for now to be safe, or assume Engine handles it if we used engine.delete_memory.
        # But RAECoreService.delete_memory uses adapter.
        # Let's keep explicit vector delete for safety until Engine handles it fully.

        try:
            vector_store = get_vector_store(pool=request.app.state.pool)
            await vector_store.delete(memory_id)
            span.set_attribute("rae.memory.vector_deleted", True)
        except Exception as e:
            # Log the error but don't fail the request, as the DB part succeeded.
            logger.warning(
                "vector_store_deletion_failed",
                memory_id=memory_id,
                error=str(e),
                risk_tag="[INTEGRITY_RISK]",
            )
            span.set_attribute("rae.memory.vector_deleted", False)
            span.set_attribute("rae.memory.vector_delete_error", str(e))

        span.set_attribute("rae.outcome.label", "success")
        memory_delete_counter.labels(
            tenant_id=tenant_id
        ).inc()  # Increment delete counter
        return DeleteMemoryResponse(message=f"Memory {memory_id} deleted successfully.")


@router.get("/sessions/{session_id}/context")
async def get_session_context(
    session_id: str,
    limit: int = Query(50, ge=1, le=1000),
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Retrieves all memories associated with a specific session.
    """
    with tracer.start_as_current_span("rae.api.memory.session_context") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        span.set_attribute("rae.session_id", session_id)

        try:
            memories = await rae_service.get_session_context(
                session_id=session_id,
                tenant_id=str(tenant_id),
                limit=limit,
            )
            span.set_attribute("rae.session.memories_count", len(memories))
            return {"session_id": session_id, "memories": memories}
        except Exception as e:
            span.set_attribute("rae.outcome.label", "error")
            logger.error(
                "get_session_context_failed", session_id=session_id, error=str(e)
            )
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/rebuild-reflections", status_code=202)
async def rebuild_reflections(req: RebuildReflectionsRequest):
    """
    Triggers a background task to rebuild reflections for a specific project.
    """
    with tracer.start_as_current_span("rae.api.memory.rebuild_reflections") as span:
        span.set_attribute("rae.tenant_id", req.tenant_id)
        span.set_attribute("rae.project_id", req.project)
        span.set_attribute("rae.task.type", "background")

        generate_reflection_for_project.delay(
            project=req.project, tenant_id=req.tenant_id
        )

        span.set_attribute("rae.outcome.label", "task_dispatched")
        return {
            "message": f"Reflection rebuild task dispatched for project {req.project}."
        }


@router.get("/reflection-stats")
async def get_reflection_stats(
    request: Request,
    tenant_id: UUID = Depends(get_and_verify_tenant_id),
    project: Optional[str] = None,
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Gets statistics about reflective memories.

    **Security:** Requires authentication and tenant access.
    """
    with tracer.start_as_current_span("rae.api.memory.reflection_stats") as span:
        span.set_attribute("rae.tenant_id", tenant_id)
        if project:
            span.set_attribute("rae.project_id", project)

        count = await rae_service.count_memories(
            tenant_id=str(tenant_id), layer="rm", project=project or "default"
        )
        span.set_attribute("rae.reflection.count", count)

        avg_strength = await rae_service.get_metric_aggregate(
            tenant_id=str(tenant_id),
            layer="rm",
            project=project or "default",
            metric="importance",
            func="avg",
        )
        span.set_attribute("rae.reflection.avg_strength", avg_strength or 0.0)

        span.set_attribute("rae.outcome.label", "success")
        return {"reflective_memory_count": count, "average_strength": avg_strength}


@router.post("/reflection/hierarchical", deprecated=True)
async def generate_hierarchical_reflection(
    request: Request,
    project: str = Query(..., description="Project identifier"),
    bucket_size: int = Query(
        10, description="Number of episodes per bucket", ge=1, le=100
    ),
    max_episodes: Optional[int] = Query(
        None, description="Maximum episodes to process", ge=1
    ),
    tenant_id: UUID = Depends(get_and_verify_tenant_id),  # Added dependency
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    **DEPRECATED:** Use `/v1/graph/reflection/hierarchical` instead.

    This endpoint is deprecated and maintained only for backward compatibility.
    The canonical implementation is now in the Graph API at:
    `POST /v1/graph/reflection/hierarchical`

    **Migration:**
    Instead of:
    ```
    POST /v1/memory/reflection/hierarchical?project=my-project&bucket_size=15
    ```

    Use:
    ```
    POST /v1/graph/reflection/hierarchical
    Content-Type: application/json

    {
      "project_id": "my-project",
      "bucket_size": 15
    }
    ```

    This endpoint will be removed in a future version.
    """
    with tracer.start_as_current_span(
        "rae.api.memory.hierarchical_reflection_deprecated"
    ) as span:
        # tenant_id is now provided by Depends(get_and_verify_tenant_id)
        # Manual extraction and error handling removed
        span.set_attribute("rae.tenant_id", tenant_id)
        span.set_attribute("rae.project_id", project)
        span.set_attribute("rae.reflection.bucket_size", bucket_size)
        if max_episodes:
            span.set_attribute("rae.reflection.max_episodes", max_episodes)
        span.set_attribute("rae.api.deprecated", True)

        logger.warning(
            "deprecated_endpoint_used",
            endpoint="/v1/memory/reflection/hierarchical",
            tenant_id=tenant_id,
            message="Use /v1/graph/reflection/hierarchical instead",
        )

        try:
            # Import ReflectionEngine
            from apps.memory_api.services.reflection_engine import ReflectionEngine

            # Initialize reflection engine
            reflection_engine = ReflectionEngine(request.app.state.pool, rae_service)

            # Generate hierarchical reflection
            summary = await reflection_engine.generate_hierarchical_reflection(
                project=project,
                tenant_id=str(tenant_id),
                bucket_size=bucket_size,
                max_episodes=max_episodes,
            )
            span.set_attribute("rae.reflection.summary_length", len(summary))

            # Fetch statistics using RAECoreService
            episode_count = await rae_service.count_memories(
                tenant_id=str(tenant_id), layer="em", project=project
            )
            span.set_attribute("rae.reflection.episode_count", episode_count)

            logger.info(
                "hierarchical_reflection_completed_deprecated",
                tenant_id=tenant_id,
                project=project,
                episode_count=episode_count,
                summary_length=len(summary),
            )

            span.set_attribute("rae.outcome.label", "success")
            return {
                "summary": summary,
                "statistics": {
                    "project": project,
                    "tenant_id": tenant_id,
                    "episode_count": episode_count,
                    "bucket_size": bucket_size,
                    "max_episodes_processed": max_episodes or episode_count,
                    "summary_length": len(summary),
                },
            }

        except Exception as e:
            logger.exception(
                "hierarchical_reflection_failed",
                tenant_id=tenant_id,
                project=project,
                error=str(e),
            )
            span.set_attribute("rae.outcome.label", "generation_failed")
            raise HTTPException(
                status_code=500,
                detail=f"Hierarchical reflection generation failed: {str(e)}",
            ) from e
