"""
Reflection Repository - Database operations for hierarchical reflection system

This repository provides all CRUD operations for:
- Reflections (ReflectionUnit)
- Reflection relationships (ReflectionGraph)
- Reflection clusters
- Reflection usage logging

Implements enterprise features:
- Transaction management
- Cycle detection in relationships
- Hierarchical queries
- Vector similarity search
- Analytics and statistics
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import UUID

import asyncpg
import structlog

from apps.memory_api.models.reflection_models import (
    ReflectionRelationship,
    ReflectionRelationType,
    ReflectionScoring,
    ReflectionStatistics,
    ReflectionTelemetry,
    ReflectionType,
    ReflectionUnit,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# Reflection CRUD Operations
# ============================================================================


async def create_reflection(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    content: str,
    reflection_type: ReflectionType,
    priority: int,
    scoring: ReflectionScoring,
    parent_reflection_id: Optional[UUID] = None,
    source_memory_ids: Optional[List[UUID]] = None,
    source_reflection_ids: Optional[List[UUID]] = None,
    embedding: Optional[List[float]] = None,
    cluster_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    telemetry: Optional[ReflectionTelemetry] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ReflectionUnit:
    """
    Create a new reflection in the database.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        content: Reflection content
        reflection_type: Type of reflection
        priority: Priority level (1-5)
        scoring: Component scores
        parent_reflection_id: Optional parent reflection for hierarchy
        source_memory_ids: Source memory IDs
        source_reflection_ids: Source reflection IDs
        embedding: Vector embedding
        cluster_id: Cluster identifier
        tags: Tags for categorization
        telemetry: Generation telemetry
        metadata: Additional metadata

    Returns:
        Created ReflectionUnit
    """
    logger.info(
        "create_reflection",
        tenant_id=tenant_id,
        project_id=project_id,
        reflection_type=reflection_type,
        priority=priority,
    )

    source_memory_ids = source_memory_ids or []
    source_reflection_ids = source_reflection_ids or []
    tags = tags or []
    metadata = metadata or {}

    # Calculate depth level
    depth_level = 0
    if parent_reflection_id:
        parent_depth = await pool.fetchval(
            "SELECT depth_level FROM reflections WHERE id = $1", parent_reflection_id
        )
        if parent_depth is not None:
            depth_level = parent_depth + 1

    # Prepare telemetry values
    generation_model = telemetry.generation_model if telemetry else None
    generation_duration_ms = telemetry.generation_duration_ms if telemetry else None
    generation_tokens_used = telemetry.generation_tokens_used if telemetry else None
    generation_cost_usd = telemetry.generation_cost_usd if telemetry else None

    # Insert reflection
    record = await pool.fetchrow(
        """
        INSERT INTO reflections (
            tenant_id, project_id, content, type, priority,
            score, novelty_score, importance_score, utility_score, confidence_score,
            parent_reflection_id, depth_level,
            source_memory_ids, source_reflection_ids,
            embedding, cluster_id, tags, metadata,
            generation_model, generation_duration_ms, generation_tokens_used, generation_cost_usd
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9, $10,
            $11, $12,
            $13, $14,
            $15, $16, $17, $18,
            $19, $20, $21, $22
        )
        RETURNING *
        """,
        tenant_id,
        project_id,
        content,
        reflection_type.value,
        priority,
        scoring.composite_score,
        scoring.novelty_score,
        scoring.importance_score,
        scoring.utility_score,
        scoring.confidence_score,
        parent_reflection_id,
        depth_level,
        source_memory_ids,
        source_reflection_ids,
        embedding,
        cluster_id,
        tags,
        metadata,
        generation_model,
        generation_duration_ms,
        generation_tokens_used,
        generation_cost_usd,
    )

    logger.info("reflection_created", reflection_id=str(record["id"]))

    return _record_to_reflection_unit(record)


async def get_reflection_by_id(
    pool: asyncpg.Pool, reflection_id: UUID, increment_access: bool = True
) -> Optional[ReflectionUnit]:
    """
    Get a reflection by ID.

    Args:
        pool: Database connection pool
        reflection_id: Reflection ID
        increment_access: Whether to increment access count (default True)

    Returns:
        ReflectionUnit or None if not found
    """
    if increment_access:
        # Increment access count
        await pool.execute("SELECT increment_reflection_access($1)", reflection_id)

    record = await pool.fetchrow(
        "SELECT * FROM reflections WHERE id = $1", reflection_id
    )

    if not record:
        return None

    return _record_to_reflection_unit(record)


async def query_reflections(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    query_embedding: Optional[List[float]] = None,
    k: int = 10,
    reflection_types: Optional[List[ReflectionType]] = None,
    min_priority: Optional[int] = None,
    min_score: Optional[float] = None,
    cluster_id: Optional[str] = None,
    parent_reflection_id: Optional[UUID] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
) -> Tuple[List[ReflectionUnit], int]:
    """
    Query reflections with filters and optional semantic search.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        query_embedding: Optional query embedding for semantic search
        k: Number of results to return
        reflection_types: Filter by reflection types
        min_priority: Minimum priority
        min_score: Minimum score
        cluster_id: Filter by cluster
        parent_reflection_id: Filter by parent
        since: After timestamp
        until: Before timestamp

    Returns:
        Tuple of (reflections, total_count)
    """
    logger.info(
        "query_reflections",
        tenant_id=tenant_id,
        project_id=project_id,
        k=k,
        has_embedding=query_embedding is not None,
    )

    # Build query conditions
    conditions = ["tenant_id = $1", "project_id = $2"]
    params: List[Any] = [tenant_id, project_id]
    param_idx = 3

    if reflection_types:
        conditions.append(f"type = ANY(${param_idx})")
        params.append([rt.value for rt in reflection_types])
        param_idx += 1

    if min_priority:
        conditions.append(f"priority >= ${param_idx}")
        params.append(min_priority)
        param_idx += 1

    if min_score:
        conditions.append(f"score >= ${param_idx}")
        params.append(min_score)
        param_idx += 1

    if cluster_id:
        conditions.append(f"cluster_id = ${param_idx}")
        params.append(cluster_id)
        param_idx += 1

    if parent_reflection_id:
        conditions.append(f"parent_reflection_id = ${param_idx}")
        params.append(parent_reflection_id)
        param_idx += 1

    if since:
        conditions.append(f"created_at >= ${param_idx}")
        params.append(since)
        param_idx += 1

    if until:
        conditions.append(f"created_at <= ${param_idx}")
        params.append(until)
        param_idx += 1

    where_clause = " AND ".join(conditions)
    # Count total matching
    count_query = f"SELECT COUNT(*) FROM reflections WHERE {where_clause}"  # nosec
    total_count = await pool.fetchval(count_query, *params)

    # Build main query
    if query_embedding:
        # Semantic search with vector similarity
        order_clause = f"ORDER BY embedding <=> ${param_idx} LIMIT ${param_idx + 1}"
        params.extend([query_embedding, k])
    else:
        # Sort by score and priority
        order_clause = (
            f"ORDER BY score DESC, priority DESC, created_at DESC LIMIT ${param_idx}"
        )
        params.append(k)

    query = f"SELECT * FROM reflections WHERE {where_clause} {order_clause}"  # nosec
    records = await pool.fetch(query, *params)
    reflections = [_record_to_reflection_unit(r) for r in records]

    logger.info("reflections_queried", count=len(reflections), total_count=total_count)

    return reflections, total_count


async def get_child_reflections(
    pool: asyncpg.Pool, parent_reflection_id: UUID, recursive: bool = False
) -> List[ReflectionUnit]:
    """
    Get child reflections of a parent.

    Args:
        pool: Database connection pool
        parent_reflection_id: Parent reflection ID
        recursive: Whether to get all descendants recursively

    Returns:
        List of child reflections
    """
    if recursive:
        # Recursive query for all descendants
        records = await pool.fetch(
            """
            WITH RECURSIVE descendants AS (
                SELECT * FROM reflections WHERE parent_reflection_id = $1
                UNION ALL
                SELECT r.* FROM reflections r
                JOIN descendants d ON r.parent_reflection_id = d.id
            )
            SELECT * FROM descendants ORDER BY depth_level, created_at
            """,
            parent_reflection_id,
        )
    else:
        # Direct children only
        records = await pool.fetch(
            "SELECT * FROM reflections WHERE parent_reflection_id = $1 ORDER BY created_at DESC",
            parent_reflection_id,
        )

    return [_record_to_reflection_unit(r) for r in records]


# ============================================================================
# Reflection Relationship Operations
# ============================================================================


async def create_reflection_relationship(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    source_reflection_id: UUID,
    target_reflection_id: UUID,
    relation_type: ReflectionRelationType,
    strength: float,
    confidence: float,
    supporting_evidence: Optional[List[str]] = None,
    check_cycles: bool = True,
) -> ReflectionRelationship:
    """
    Create a relationship between two reflections.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        source_reflection_id: Source reflection ID
        target_reflection_id: Target reflection ID
        relation_type: Type of relationship
        strength: Relationship strength
        confidence: Confidence in relationship
        supporting_evidence: Supporting evidence texts
        check_cycles: Whether to check for cycles (default True)

    Returns:
        Created ReflectionRelationship

    Raises:
        ValueError: If relationship would create a cycle
    """
    logger.info(
        "create_reflection_relationship",
        source=str(source_reflection_id),
        target=str(target_reflection_id),
        relation_type=relation_type,
    )

    supporting_evidence = supporting_evidence or []

    # Check for cycles if enabled
    if check_cycles:
        has_cycle = await pool.fetchval(
            "SELECT detect_reflection_cycle($1, $2)",
            source_reflection_id,
            target_reflection_id,
        )

        if has_cycle:
            raise ValueError(
                f"Adding relationship from {source_reflection_id} to {target_reflection_id} "
                f"would create a cycle"
            )

    # Insert relationship
    record = await pool.fetchrow(
        """
        INSERT INTO reflection_relationships (
            tenant_id, project_id,
            source_reflection_id, target_reflection_id,
            relation_type, strength, confidence,
            supporting_evidence
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING *
        """,
        tenant_id,
        project_id,
        source_reflection_id,
        target_reflection_id,
        relation_type.value,
        strength,
        confidence,
        supporting_evidence,
    )

    logger.info("reflection_relationship_created", relationship_id=str(record["id"]))

    return _record_to_reflection_relationship(record)


async def get_reflection_relationships(
    pool: asyncpg.Pool,
    reflection_id: UUID,
    direction: str = "outgoing",  # "outgoing", "incoming", "both"
    relation_types: Optional[List[ReflectionRelationType]] = None,
    min_strength: Optional[float] = None,
) -> List[ReflectionRelationship]:
    """
    Get relationships for a reflection.

    Args:
        pool: Database connection pool
        reflection_id: Reflection ID
        direction: "outgoing", "incoming", or "both"
        relation_types: Optional filter by relation types
        min_strength: Minimum relationship strength

    Returns:
        List of relationships
    """
    conditions = []
    params: List[Any] = [reflection_id]
    param_idx = 2

    if direction == "outgoing":
        conditions.append("source_reflection_id = $1")
    elif direction == "incoming":
        conditions.append("target_reflection_id = $1")
    elif direction == "both":
        conditions.append("(source_reflection_id = $1 OR target_reflection_id = $1)")
    else:
        raise ValueError(f"Invalid direction: {direction}")

    if relation_types:
        conditions.append(f"relation_type = ANY(${param_idx})")
        params.append([rt.value for rt in relation_types])
        param_idx += 1

    if min_strength:
        conditions.append(f"strength >= ${param_idx}")
        params.append(min_strength)
        param_idx += 1

        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM reflection_relationships WHERE {where_clause}"  # nosec
        records = await pool.fetch(query, *params)

    return [_record_to_reflection_relationship(r) for r in records]


async def get_reflection_graph(
    pool: asyncpg.Pool,
    reflection_id: UUID,
    max_depth: int = 3,
    relation_types: Optional[List[ReflectionRelationType]] = None,
    min_strength: Optional[float] = None,
) -> Tuple[List[ReflectionUnit], List[ReflectionRelationship]]:
    """
    Get reflection graph starting from a reflection.

    Args:
        pool: Database connection pool
        reflection_id: Starting reflection ID
        max_depth: Maximum traversal depth
        relation_types: Optional filter by relation types
        min_strength: Minimum relationship strength

    Returns:
        Tuple of (nodes, edges)
    """
    logger.info(
        "get_reflection_graph", reflection_id=str(reflection_id), max_depth=max_depth
    )

    # Build relation type filter
    relation_filter = ""
    relation_params: List[Any] = []
    if relation_types:
        relation_filter = "AND relation_type = ANY($2)"
        relation_params = [[rt.value for rt in relation_types]]

    # Build strength filter
    strength_filter = ""
    if min_strength:
        param_idx = 3 if relation_types else 2
        strength_filter = f"AND strength >= ${param_idx}"
        relation_params.append(min_strength)

    # Recursive query for graph traversal
    query = f"""
    WITH RECURSIVE graph AS (
        -- Base case: starting reflection
        SELECT
            id,
            0 as depth,
            ARRAY[id] as path
        FROM reflections
        WHERE id = $1

        UNION ALL

        -- Recursive case: follow relationships
        SELECT
            r.id,
            g.depth + 1,
            g.path || r.id
        FROM graph g
        JOIN reflection_relationships rr ON rr.source_reflection_id = g.id
        JOIN reflections r ON r.id = rr.target_reflection_id
        WHERE
            g.depth < $1
            {relation_filter}
            {strength_filter}
            AND NOT (r.id = ANY(g.path))  -- Prevent cycles
    )
    SELECT DISTINCT id FROM graph
    """  # nosec
    params = [max_depth] + relation_params
    node_ids = [r["id"] for r in await pool.fetch(query, *params)]

    # Fetch all nodes
    if node_ids:
        nodes_records = await pool.fetch(
            "SELECT * FROM reflections WHERE id = ANY($1)", node_ids
        )
        nodes = [_record_to_reflection_unit(r) for r in nodes_records]

        # Fetch all edges between these nodes
        edges_query = f"""
        SELECT * FROM reflection_relationships
        WHERE
            source_reflection_id = ANY($1)
            AND target_reflection_id = ANY($1)
            {relation_filter}
            {strength_filter}
        """  # nosec
        edges_records = await pool.fetch(edges_query, node_ids, *relation_params)
        edges = [_record_to_reflection_relationship(r) for r in edges_records]
    else:
        nodes = []
        edges = []

    logger.info("reflection_graph_retrieved", nodes=len(nodes), edges=len(edges))

    return nodes, edges


# ============================================================================
# Statistics and Analytics
# ============================================================================


async def get_reflection_statistics(
    pool: asyncpg.Pool, tenant_id: str, project_id: str
) -> ReflectionStatistics:
    """
    Get reflection statistics for a project.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier

    Returns:
        ReflectionStatistics
    """
    record = await pool.fetchrow(
        "SELECT * FROM reflection_statistics WHERE tenant_id = $1 AND project_id = $2",
        tenant_id,
        project_id,
    )

    if not record:
        return ReflectionStatistics(tenant_id=tenant_id, project_id=project_id)

    return ReflectionStatistics(**dict(record))


async def log_reflection_usage(
    pool: asyncpg.Pool,
    tenant_id: str,
    project_id: str,
    reflection_id: UUID,
    usage_type: str,
    query_text: Optional[str] = None,
    relevance_score: Optional[float] = None,
    rank_position: Optional[int] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> UUID:
    """
    Log reflection usage for analytics.

    Args:
        pool: Database connection pool
        tenant_id: Tenant identifier
        project_id: Project identifier
        reflection_id: Reflection ID
        usage_type: Type of usage
        query_text: Optional query text
        relevance_score: Optional relevance score
        rank_position: Optional rank position
        user_id: Optional user ID
        session_id: Optional session ID
        metadata: Optional metadata

    Returns:
        Usage log entry ID
    """
    metadata = metadata or {}

    record = await pool.fetchrow(
        """
        INSERT INTO reflection_usage_log (
            tenant_id, project_id, reflection_id,
            usage_type, query_text,
            relevance_score, rank_position,
            user_id, session_id, metadata
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """,
        tenant_id,
        project_id,
        reflection_id,
        usage_type,
        query_text,
        relevance_score,
        rank_position,
        user_id,
        session_id,
        metadata,
    )

    return cast(UUID, record["id"])


# ============================================================================
# Helper Functions
# ============================================================================


def _record_to_reflection_unit(record) -> ReflectionUnit:
    """Convert database record to ReflectionUnit"""
    scoring = ReflectionScoring(
        novelty_score=float(record["novelty_score"] or 0.5),
        importance_score=float(record["importance_score"] or 0.5),
        utility_score=float(record["utility_score"] or 0.5),
        confidence_score=float(record["confidence_score"] or 0.5),
    )

    telemetry = None
    if record.get("generation_model"):
        telemetry = ReflectionTelemetry(
            generation_model=record["generation_model"],
            generation_duration_ms=record.get("generation_duration_ms"),
            generation_tokens_used=record.get("generation_tokens_used"),
            generation_cost_usd=(
                float(record["generation_cost_usd"])
                if record.get("generation_cost_usd")
                else None
            ),
        )

    return ReflectionUnit(
        id=record["id"],
        tenant_id=record["tenant_id"],
        project_id=record["project_id"],
        content=record["content"],
        summary=record.get("summary"),
        type=ReflectionType(record["type"]),
        priority=record["priority"],
        score=float(record["score"]),
        scoring=scoring,
        parent_reflection_id=record.get("parent_reflection_id"),
        depth_level=record["depth_level"],
        source_memory_ids=record.get("source_memory_ids", []),
        source_reflection_ids=record.get("source_reflection_ids", []),
        embedding=record.get("embedding"),
        cluster_id=record.get("cluster_id"),
        cluster_centroid=record.get("cluster_centroid"),
        cache_key=record.get("cache_key"),
        reuse_count=record.get("reuse_count", 0),
        telemetry=telemetry,
        tags=record.get("tags", []),
        metadata=record.get("metadata", {}),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        last_accessed_at=record["last_accessed_at"],
        accessed_count=record.get("accessed_count", 0),
    )


def _record_to_reflection_relationship(record) -> ReflectionRelationship:
    """Convert database record to ReflectionRelationship"""
    return ReflectionRelationship(
        id=record["id"],
        tenant_id=record["tenant_id"],
        project_id=record["project_id"],
        source_reflection_id=record["source_reflection_id"],
        target_reflection_id=record["target_reflection_id"],
        relation_type=ReflectionRelationType(record["relation_type"]),
        strength=float(record["strength"]),
        confidence=float(record["confidence"]),
        supporting_evidence=record.get("supporting_evidence", []),
        metadata=record.get("metadata", {}),
        created_at=record["created_at"],
        updated_at=record["updated_at"],
    )
