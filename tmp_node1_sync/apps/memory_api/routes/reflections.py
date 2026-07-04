"""
Reflections API Routes - Enterprise Hierarchical Reflection System

This module provides FastAPI routes for:
- Generating reflections from memories (with clustering)
- Querying reflections (with semantic search)
- Managing reflection relationships (ReflectionGraph)
- Retrieving reflection statistics and analytics
"""

from typing import Dict, List
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.dependencies import get_rae_core_service
from apps.memory_api.models.reflection_models import (
    CreateReflectionRelationshipRequest,
    CreateReflectionRelationshipResponse,
    GenerateReflectionRequest,
    GenerateReflectionResponse,
    GetReflectionGraphRequest,
    GetReflectionGraphResponse,
    QueryReflectionsRequest,
    QueryReflectionsResponse,
    ReflectionStatistics,
    ReflectionUnit,
)
from apps.memory_api.repositories import reflection_repository
from apps.memory_api.services.ml_service_client import MLServiceClient
from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.reflection_pipeline import ReflectionPipeline

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/v1/reflections", tags=["Reflections"])


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_pool(request: Request):
    """Get database connection pool from app state"""
    return request.app.state.pool


# ============================================================================
# Reflection Generation
# ============================================================================


@router.post("/generate", response_model=GenerateReflectionResponse)
async def generate_reflections(
    request: GenerateReflectionRequest,
    pool=Depends(get_pool),
    rae_service: RAECoreService = Depends(get_rae_core_service),
):
    """
    Generate reflections from memories using clustering pipeline.

    This endpoint:
    1. Fetches memories based on filters
    2. Clusters memories using HDBSCAN or k-means
    3. Generates insights for each cluster
    4. Optionally generates meta-insights
    5. Scores and stores all reflections

    **Example Request:**
    ```json
    {
      "tenant_id": "acme-corp",
      "project": "production",
      "max_memories": 100,
      "min_cluster_size": 5,
      "enable_clustering": true,
      "since": "2025-01-01T00:00:00Z"
    }
    ```

    **Returns:**
    - Generated reflections with scoring and metadata
    - Statistics (clusters found, insights generated, cost)
    """
    logger.info(
        "generate_reflections_request",
        tenant_id=request.tenant_id,
        project=request.project,
    )

    try:
        pipeline = ReflectionPipeline(rae_service)
        reflections, statistics = await pipeline.generate_reflections(request)

        # Return first reflection as primary (or empty if none)
        primary_reflection = reflections[0] if reflections else None

        return GenerateReflectionResponse(
            reflection=primary_reflection,
            statistics=statistics,
            message=f"Generated {len(reflections)} reflection(s) successfully",
        )

    except Exception as e:
        logger.error("generate_reflections_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Reflection generation failed: {str(e)}"
        ) from e


# ============================================================================
# Querying Reflections
# ============================================================================


@router.post("/query", response_model=QueryReflectionsResponse)
async def query_reflections(request: QueryReflectionsRequest, pool=Depends(get_pool)):
    """
    Query reflections with filters and optional semantic search.

    Supports:
    - Semantic search using query embeddings
    - Filtering by type, priority, score, cluster
    - Hierarchical filtering (by parent)
    - Time range filtering

    **Example Request:**
    ```json
    {
      "tenant_id": "acme-corp",
      "project": "production",
      "query_text": "authentication patterns",
      "k": 10,
      "reflection_types": ["pattern", "insight"],
      "min_priority": 3,
      "min_score": 0.6
    }
    ```

    **Returns:**
    - Matching reflections sorted by relevance/score
    - Total count for pagination
    """
    logger.info(
        "query_reflections_request",
        tenant_id=request.tenant_id,
        project=request.project,
        has_query=request.query_text is not None,
    )

    try:
        # Generate embedding for semantic search if query provided
        query_embedding = None
        if request.query_text:
            ml_client = MLServiceClient()
            query_embedding = await ml_client.get_embedding(request.query_text)

        # Query reflections
        reflections, total_count = await reflection_repository.query_reflections(
            pool=pool,
            tenant_id=request.tenant_id,
            project_id=request.project,
            query_embedding=query_embedding,
            k=request.k,
            reflection_types=request.reflection_types,
            min_priority=request.min_priority,
            min_score=request.min_score,
            cluster_id=request.cluster_id,
            parent_reflection_id=request.parent_reflection_id,
            since=request.since,
            until=request.until,
        )

        # Log usage for analytics
        for i, reflection in enumerate(reflections):
            await reflection_repository.log_reflection_usage(
                pool=pool,
                tenant_id=request.tenant_id,
                project_id=request.project,
                reflection_id=reflection.id,
                usage_type="query",
                query_text=request.query_text,
                rank_position=i + 1,
            )

        logger.info(
            "query_reflections_success", count=len(reflections), total=total_count
        )

        return QueryReflectionsResponse(
            reflections=reflections,
            total_count=total_count,
            statistics={
                "returned": len(reflections),
                "total_matching": total_count,
                "has_more": total_count > len(reflections),
            },
        )

    except Exception as e:
        logger.error("query_reflections_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}") from e


# ============================================================================
# Reflection Details
# ============================================================================


@router.get("/{reflection_id}", response_model=ReflectionUnit)
async def get_reflection(
    reflection_id: UUID, tenant_id: str, project: str, pool=Depends(get_pool)
):
    """
    Get a single reflection by ID.

    Automatically increments access count and updates last_accessed_at.

    **Parameters:**
    - `reflection_id`: UUID of the reflection
    - `tenant_id`: Tenant identifier (query param)
    - `project`: Project identifier (query param)

    **Returns:**
    - Complete reflection with all metadata
    """
    logger.info("get_reflection_request", reflection_id=str(reflection_id))

    reflection = await reflection_repository.get_reflection_by_id(
        pool=pool, reflection_id=reflection_id, increment_access=True
    )

    if not reflection:
        raise HTTPException(status_code=404, detail="Reflection not found")

    # Verify tenant access
    if reflection.tenant_id != tenant_id or reflection.project_id != project:
        raise HTTPException(status_code=403, detail="Access denied")

    # Log usage
    await reflection_repository.log_reflection_usage(
        pool=pool,
        tenant_id=tenant_id,
        project_id=project,
        reflection_id=reflection_id,
        usage_type="api_call",
    )

    return reflection


# ============================================================================
# Hierarchical Reflections
# ============================================================================


@router.get("/{reflection_id}/children", response_model=List[ReflectionUnit])
async def get_child_reflections(
    reflection_id: UUID, recursive: bool = False, pool=Depends(get_pool)
):
    """
    Get child reflections of a parent.

    **Parameters:**
    - `reflection_id`: Parent reflection UUID
    - `recursive`: If true, returns all descendants (default: false)

    **Returns:**
    - List of child reflections
    - If recursive=true, includes grandchildren, etc.
    """
    logger.info(
        "get_child_reflections_request",
        reflection_id=str(reflection_id),
        recursive=recursive,
    )

    children = await reflection_repository.get_child_reflections(
        pool=pool, parent_reflection_id=reflection_id, recursive=recursive
    )

    logger.info("child_reflections_retrieved", count=len(children))

    return children


# ============================================================================
# Reflection Graph
# ============================================================================


@router.post("/graph", response_model=GetReflectionGraphResponse)
async def get_reflection_graph(
    request: GetReflectionGraphRequest, pool=Depends(get_pool)
):
    """
    Get reflection graph starting from a reflection.

    Traverses relationships (supports, contradicts, refines, etc.) up to max_depth.

    **Example Request:**
    ```json
    {
      "tenant_id": "acme-corp",
      "project": "production",
      "reflection_id": "123e4567-e89b-12d3-a456-426614174000",
      "max_depth": 3,
      "relation_types": ["supports", "refines"],
      "min_strength": 0.5
    }
    ```

    **Returns:**
    - Nodes: List of reflections in graph
    - Edges: List of relationships
    - Statistics: Node count, edge count, depth distribution
    """
    logger.info(
        "get_reflection_graph_request",
        reflection_id=str(request.reflection_id),
        max_depth=request.max_depth,
    )

    try:
        nodes, edges = await reflection_repository.get_reflection_graph(
            pool=pool,
            reflection_id=request.reflection_id,
            max_depth=request.max_depth,
            relation_types=request.relation_types,
            min_strength=request.min_strength,
        )

        # Calculate statistics
        depth_distribution: Dict[int, int] = {}
        for node in nodes:
            depth = node.depth_level
            depth_distribution[depth] = depth_distribution.get(depth, 0) + 1

        statistics = {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "max_depth_reached": max([n.depth_level for n in nodes]) if nodes else 0,
            "depth_distribution": depth_distribution,
        }

        logger.info("reflection_graph_retrieved", nodes=len(nodes), edges=len(edges))

        return GetReflectionGraphResponse(
            nodes=nodes, edges=edges, statistics=statistics
        )

    except Exception as e:
        logger.error("get_reflection_graph_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Graph retrieval failed: {str(e)}"
        ) from e


# ============================================================================
# Reflection Relationships
# ============================================================================


@router.post("/relationships", response_model=CreateReflectionRelationshipResponse)
async def create_reflection_relationship(
    request: CreateReflectionRelationshipRequest, pool=Depends(get_pool)
):
    """
    Create a relationship between two reflections.

    Automatically checks for cycles to prevent graph corruption.

    **Example Request:**
    ```json
    {
      "tenant_id": "acme-corp",
      "project": "production",
      "source_reflection_id": "123e4567-e89b-12d3-a456-426614174000",
      "target_reflection_id": "223e4567-e89b-12d3-a456-426614174000",
      "relation_type": "supports",
      "strength": 0.8,
      "confidence": 0.9,
      "supporting_evidence": ["Memory A", "Memory B"]
    }
    ```

    **Raises:**
    - 400: If relationship would create a cycle
    - 404: If source or target reflection not found
    """
    logger.info(
        "create_relationship_request",
        source=str(request.source_reflection_id),
        target=str(request.target_reflection_id),
        relation_type=request.relation_type,
    )

    try:
        relationship = await reflection_repository.create_reflection_relationship(
            pool=pool,
            tenant_id=request.tenant_id,
            project_id=request.project,
            source_reflection_id=request.source_reflection_id,
            target_reflection_id=request.target_reflection_id,
            relation_type=request.relation_type,
            strength=request.strength,
            confidence=request.confidence,
            supporting_evidence=request.supporting_evidence,
            check_cycles=True,
        )

        logger.info("relationship_created", relationship_id=str(relationship.id))

        return CreateReflectionRelationshipResponse(
            relationship=relationship,
            message="Reflection relationship created successfully",
        )

    except ValueError as e:
        # Cycle detected
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error("create_relationship_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Relationship creation failed: {str(e)}"
        ) from e


# ============================================================================
# Analytics
# ============================================================================


@router.get("/statistics/{tenant_id}/{project}", response_model=ReflectionStatistics)
async def get_reflection_statistics(
    tenant_id: str, project: str, pool=Depends(get_pool)
):
    """
    Get reflection statistics for a project.

    Returns aggregated statistics including:
    - Total reflections by type
    - Average scores and priorities
    - Hierarchical metrics
    - Usage statistics
    - Total generation costs

    **Returns:**
    - Comprehensive statistics for dashboards and monitoring
    """
    logger.info("get_statistics_request", tenant_id=tenant_id, project=project)

    statistics = await reflection_repository.get_reflection_statistics(
        pool=pool, tenant_id=tenant_id, project_id=project
    )

    return statistics


# ============================================================================
# Batch Operations
# ============================================================================


@router.delete("/batch")
async def delete_reflections_batch(
    tenant_id: str, project: str, reflection_ids: List[UUID], pool=Depends(get_pool)
):
    """
    Delete multiple reflections in batch.

    **Note:** This will also delete:
    - All child reflections (cascade)
    - All relationships involving these reflections
    - All usage logs

    **Parameters:**
    - `tenant_id`: Tenant identifier (query param)
    - `project`: Project identifier (query param)
    - `reflection_ids`: List of reflection UUIDs to delete (body)

    **Returns:**
    - Count of deleted reflections
    """
    logger.info(
        "delete_batch_request",
        tenant_id=tenant_id,
        project=project,
        count=len(reflection_ids),
    )

    try:
        deleted_count = await pool.execute(
            """
            DELETE FROM reflections
            WHERE tenant_id = $1
              AND project_id = $2
              AND id = ANY($3)
            """,
            tenant_id,
            project,
            reflection_ids,
        )

        # Parse count from result
        count = int(deleted_count.split()[-1])

        logger.info("reflections_deleted", count=count)

        return {"message": f"Deleted {count} reflection(s)", "deleted_count": count}

    except Exception as e:
        logger.error("delete_batch_failed", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"Batch deletion failed: {str(e)}"
        ) from e
