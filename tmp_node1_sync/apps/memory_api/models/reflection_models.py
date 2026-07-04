"""
Reflection Models - Enterprise Hierarchical Reflection System

This module defines Pydantic models for the complete reflection system including:
- ReflectionUnit with hierarchical support
- ReflectionGraph with typed relationships
- Scoring and prioritization
- Clustering and caching metadata
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Enums
# ============================================================================


class ReflectionType(str, Enum):
    """Types of reflections in the hierarchical system"""

    INSIGHT = "insight"  # Basic insight from memories
    ANALYSIS = "analysis"  # Analytical reflection
    PATTERN = "pattern"  # Pattern recognition
    META = "meta"  # Meta-insight (reflection on reflections)
    SYNTHESIS = "synthesis"  # Synthesized knowledge


class ReflectionRelationType(str, Enum):
    """Types of relationships between reflections"""

    SUPPORTS = "supports"  # Reflection B supports/reinforces reflection A
    CONTRADICTS = "contradicts"  # Reflection B contradicts reflection A
    REFINES = "refines"  # Reflection B refines/elaborates on reflection A
    GENERALIZES = "generalizes"  # Reflection B generalizes reflection A
    EXEMPLIFIES = "exemplifies"  # Reflection B is an example of reflection A
    DERIVES_FROM = "derives_from"  # Reflection B is derived from reflection A
    RELATES_TO = "relates_to"  # Generic relationship


# ============================================================================
# Scoring Models
# ============================================================================


class ReflectionScoring(BaseModel):
    """Component scores for reflection quality assessment"""

    novelty_score: float = Field(
        0.5, ge=0.0, le=1.0, description="How novel/unique is this reflection"
    )
    importance_score: float = Field(
        0.5, ge=0.0, le=1.0, description="How important/significant"
    )
    utility_score: float = Field(
        0.5, ge=0.0, le=1.0, description="How useful/actionable"
    )
    confidence_score: float = Field(
        0.5, ge=0.0, le=1.0, description="Model confidence in reflection"
    )

    @property
    def composite_score(self) -> float:
        """Calculate weighted composite score"""
        return (
            self.importance_score * 0.4
            + self.utility_score * 0.3
            + self.novelty_score * 0.2
            + self.confidence_score * 0.1
        )


class ReflectionTelemetry(BaseModel):
    """Telemetry data for reflection generation"""

    generation_model: Optional[str] = Field(
        None, description="Model used for generation"
    )
    generation_duration_ms: Optional[int] = Field(
        None, description="Generation duration in milliseconds"
    )
    generation_tokens_used: Optional[int] = Field(None, description="Total tokens used")
    generation_cost_usd: Optional[float] = Field(
        None, description="Generation cost in USD"
    )


# ============================================================================
# Core Reflection Models
# ============================================================================


class ReflectionUnit(BaseModel):
    """
    Complete reflection unit with hierarchical support, scoring, and metadata.

    This model represents a single reflection in the system, with support for:
    - Hierarchical structure (parent-child relationships)
    - Multi-dimensional scoring
    - Source tracking (from memories or other reflections)
    - Clustering metadata
    - Caching support
    - Full telemetry
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Content
    content: str = Field(..., description="Reflection content/text")
    summary: Optional[str] = Field(None, max_length=500, description="Short summary")

    # Classification
    type: ReflectionType = Field(
        ReflectionType.INSIGHT, description="Type of reflection"
    )
    priority: int = Field(3, ge=1, le=5, description="Priority level 1-5 (5=highest)")

    # Scoring
    score: float = Field(
        0.5, ge=0.0, le=1.0, description="Overall reflection quality score"
    )
    scoring: Optional[ReflectionScoring] = Field(
        None, description="Detailed component scores"
    )

    # Hierarchical structure
    parent_reflection_id: Optional[UUID] = Field(
        None, description="Parent reflection for hierarchy"
    )
    depth_level: int = Field(
        0, ge=0, description="Depth in hierarchy (0=base, 1=meta, etc.)"
    )

    # Source tracking
    source_memory_ids: List[UUID] = Field(
        default_factory=list, description="Source memory IDs"
    )
    source_reflection_ids: List[UUID] = Field(
        default_factory=list, description="Source reflection IDs"
    )

    # Embeddings
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding for similarity search"
    )

    # Clustering
    cluster_id: Optional[str] = Field(None, description="Cluster identifier")
    cluster_centroid: Optional[List[float]] = Field(
        None, description="Cluster centroid vector"
    )

    # Caching
    cache_key: Optional[str] = Field(None, description="Cache key for reuse")
    reuse_count: int = Field(0, ge=0, description="Number of times reused from cache")

    # Telemetry
    telemetry: Optional[ReflectionTelemetry] = Field(
        None, description="Generation telemetry"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime
    accessed_count: int = Field(0, ge=0, description="Number of times accessed")

    model_config = ConfigDict(from_attributes=True)


class ReflectionRelationship(BaseModel):
    """
    Relationship between two reflections in the ReflectionGraph.

    Represents directed edges in the reflection graph with:
    - Typed relationships (supports, contradicts, refines, etc.)
    - Strength and confidence scores
    - Supporting evidence
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Relationship
    source_reflection_id: UUID = Field(..., description="Source reflection ID")
    target_reflection_id: UUID = Field(..., description="Target reflection ID")
    relation_type: ReflectionRelationType = Field(
        ..., description="Type of relationship"
    )

    # Strength and confidence
    strength: float = Field(0.5, ge=0.0, le=1.0, description="Relationship strength")
    confidence: float = Field(
        0.5, ge=0.0, le=1.0, description="Confidence in relationship"
    )

    # Evidence
    supporting_evidence: List[str] = Field(
        default_factory=list, description="Supporting evidence texts"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReflectionCluster(BaseModel):
    """
    Cluster of related reflections.

    Represents a group of semantically similar reflections with:
    - Cluster centroid
    - Cohesion metrics
    - Dominant themes
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Cluster identification
    cluster_id: str = Field(..., description="Cluster identifier")

    # Cluster properties
    centroid: Optional[List[float]] = Field(None, description="Cluster centroid vector")
    size: int = Field(0, ge=0, description="Number of reflections in cluster")
    cohesion_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Cluster cohesion score"
    )

    # Summary
    cluster_summary: Optional[str] = Field(
        None, description="Summary of cluster themes"
    )
    dominant_themes: List[str] = Field(
        default_factory=list, description="Dominant themes in cluster"
    )

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request/Response Models
# ============================================================================


class GenerateReflectionRequest(BaseModel):
    """Request model for generating a new reflection"""

    project: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)

    # Generation parameters
    reflection_type: Optional[ReflectionType] = Field(
        None, description="Desired reflection type"
    )
    max_memories: int = Field(
        50, gt=0, le=1000, description="Maximum memories to process"
    )
    min_cluster_size: int = Field(3, gt=0, le=50, description="Minimum cluster size")

    # Hierarchical parameters
    parent_reflection_id: Optional[UUID] = Field(
        None, description="Parent reflection for meta-insights"
    )
    enable_clustering: bool = Field(
        True, description="Enable clustering-based generation"
    )

    # Filters
    memory_filters: Optional[Dict[str, Any]] = Field(
        None, description="Filters for memory selection"
    )
    since: Optional[datetime] = Field(
        None, description="Only consider memories after this timestamp"
    )


class GenerateReflectionResponse(BaseModel):
    """Response model for reflection generation"""

    reflection: Optional[ReflectionUnit] = Field(
        None, description="Generated reflection"
    )
    statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Generation statistics"
    )
    message: str = Field("Reflection generated successfully")


class QueryReflectionsRequest(BaseModel):
    """Request model for querying reflections"""

    project: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)

    # Query parameters
    query_text: Optional[str] = Field(
        None, min_length=1, max_length=1024, description="Semantic query text"
    )
    k: int = Field(10, gt=0, le=100, description="Number of results to return")

    # Filters
    reflection_types: Optional[List[ReflectionType]] = Field(
        None, description="Filter by reflection types"
    )
    min_priority: Optional[int] = Field(
        None, ge=1, le=5, description="Minimum priority"
    )
    min_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum score"
    )
    cluster_id: Optional[str] = Field(None, description="Filter by cluster ID")
    parent_reflection_id: Optional[UUID] = Field(None, description="Filter by parent")

    # Time range
    since: Optional[datetime] = Field(None, description="After this timestamp")
    until: Optional[datetime] = Field(None, description="Before this timestamp")


class QueryReflectionsResponse(BaseModel):
    """Response model for querying reflections"""

    reflections: List[ReflectionUnit] = Field(
        default_factory=list, description="Matching reflections"
    )
    total_count: int = Field(0, description="Total number of matching reflections")
    statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Query statistics"
    )


class GetReflectionGraphRequest(BaseModel):
    """Request model for retrieving reflection graph"""

    project: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)

    # Starting point
    reflection_id: UUID = Field(..., description="Root reflection ID")

    # Traversal parameters
    max_depth: int = Field(3, ge=1, le=10, description="Maximum traversal depth")
    relation_types: Optional[List[ReflectionRelationType]] = Field(
        None, description="Filter by relation types"
    )
    min_strength: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Minimum relationship strength"
    )


class GetReflectionGraphResponse(BaseModel):
    """Response model for reflection graph"""

    nodes: List[ReflectionUnit] = Field(
        default_factory=list, description="Reflection nodes"
    )
    edges: List[ReflectionRelationship] = Field(
        default_factory=list, description="Relationships"
    )
    statistics: Dict[str, Any] = Field(
        default_factory=dict, description="Graph statistics"
    )


class CreateReflectionRelationshipRequest(BaseModel):
    """Request model for creating a reflection relationship"""

    project: str = Field(..., min_length=1, max_length=255)
    tenant_id: str = Field(..., min_length=1, max_length=255)

    # Relationship
    source_reflection_id: UUID
    target_reflection_id: UUID
    relation_type: ReflectionRelationType

    # Strength and confidence
    strength: float = Field(0.5, ge=0.0, le=1.0)
    confidence: float = Field(0.5, ge=0.0, le=1.0)

    # Evidence
    supporting_evidence: List[str] = Field(default_factory=list)


class CreateReflectionRelationshipResponse(BaseModel):
    """Response model for creating a reflection relationship"""

    relationship: ReflectionRelationship
    message: str = Field("Reflection relationship created successfully")


# ============================================================================
# Analytics Models
# ============================================================================


class ReflectionStatistics(BaseModel):
    """Statistics for reflections in a project"""

    tenant_id: str
    project_id: str

    # Counts
    total_reflections: int = 0
    insights: int = 0
    analyses: int = 0
    patterns: int = 0
    meta_insights: int = 0
    syntheses: int = 0

    # Averages
    avg_score: float = 0.0
    avg_priority: float = 0.0

    # Hierarchy
    hierarchical_count: int = 0
    max_depth: int = 0

    # Usage
    total_accesses: int = 0
    total_generation_cost_usd: float = 0.0


class ReflectionUsageLog(BaseModel):
    """Usage log entry for reflection analytics"""

    id: UUID
    tenant_id: str
    project_id: str

    # Reflection reference
    reflection_id: UUID

    # Usage context
    usage_type: str = Field(
        ..., description="Type of usage: query, api_call, agent_execution, etc."
    )
    query_text: Optional[str] = Field(
        None, description="Query that retrieved this reflection"
    )

    # Results
    relevance_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Relevance to query"
    )
    rank_position: Optional[int] = Field(None, ge=0, description="Position in results")

    # User context
    user_id: Optional[str] = Field(None)
    session_id: Optional[str] = Field(None)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamp
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
