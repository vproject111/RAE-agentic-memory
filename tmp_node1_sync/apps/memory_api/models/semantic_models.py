"""
Semantic Memory Models - Enterprise Knowledge Node System

This module defines Pydantic models for the semantic memory layer including:
- SemanticNode with canonical forms and decay
- Semantic relationships
- Semantic index for fast lookup
- TTL/LTM priority decay system
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Enums
# ============================================================================


class SemanticNodeType(str, Enum):
    """Types of semantic nodes"""

    CONCEPT = "concept"  # Abstract concept
    TOPIC = "topic"  # Domain topic
    ENTITY = "entity"  # Named entity
    TERM = "term"  # Technical term
    CATEGORY = "category"  # Category/classification
    RELATION = "relation"  # Relationship type


class SemanticRelationType(str, Enum):
    """Types of semantic relationships"""

    IS_A = "is_a"  # Hyponymy (X is a type of Y)
    PART_OF = "part_of"  # Meronymy (X is part of Y)
    RELATED_TO = "related_to"  # Generic relation
    SYNONYM_OF = "synonym_of"  # Synonymy
    ANTONYM_OF = "antonym_of"  # Antonymy
    CAUSES = "causes"  # Causation
    REQUIRES = "requires"  # Dependency
    SIMILAR_TO = "similar_to"  # Similarity
    DERIVES_FROM = "derives_from"  # Etymology/derivation
    IMPLEMENTS = "implements"  # Implementation
    USES = "uses"  # Usage relation


# ============================================================================
# Core Models
# ============================================================================


class SemanticDefinition(BaseModel):
    """A definition with source attribution"""

    text: str = Field(..., description="Definition text")
    source: Optional[str] = Field(None, description="Source of definition")
    confidence: float = Field(
        0.8, ge=0.0, le=1.0, description="Confidence in definition"
    )


class SemanticNode(BaseModel):
    """
    Semantic knowledge node with canonical form and decay modeling.

    Represents a concept, topic, entity, or term in the knowledge graph with:
    - Canonical form for normalization
    - Multiple definitions with sources
    - Ontological classification
    - Priority decay (TTL/LTM model)
    - Reinforcement tracking
    """

    id: UUID
    tenant_id: str
    project_id: str

    # Core identification
    node_id: str = Field(..., max_length=500, description="Canonical identifier")
    label: str = Field(..., max_length=500, description="Human-readable label")
    node_type: SemanticNodeType = Field(
        SemanticNodeType.CONCEPT, description="Type of node"
    )

    # Canonical form
    canonical_form: str = Field(..., description="Standardized representation")
    aliases: List[str] = Field(
        default_factory=list, description="Alternative names/synonyms"
    )

    # Definitions
    definition: Optional[str] = Field(None, description="Primary definition")
    definitions: List[SemanticDefinition] = Field(
        default_factory=list, description="Multiple definitions"
    )
    context: Optional[str] = Field(None, description="Contextual information")
    examples: List[str] = Field(default_factory=list, description="Usage examples")

    # Ontological classification
    categories: List[str] = Field(
        default_factory=list, description="Categories this node belongs to"
    )
    domain: Optional[str] = Field(
        None, max_length=255, description="Domain (e.g., security, architecture)"
    )

    # Relations
    relations: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Related nodes: {'related_to': ['node1', 'node2'], ...}",
    )

    # Embeddings
    embedding: Optional[List[float]] = Field(None, description="Vector embedding")

    # Priority and decay
    priority: int = Field(3, ge=1, le=5, description="Priority level 1-5")
    importance_score: float = Field(0.5, ge=0.0, le=1.0, description="Importance score")

    # Decay tracking
    last_reinforced_at: datetime
    reinforcement_count: int = Field(0, ge=0, description="Number of times reinforced")
    decay_rate: float = Field(0.01, ge=0.0, le=1.0, description="Decay rate per day")

    # Decay status
    is_degraded: bool = Field(False, description="True if node has decayed")
    degradation_timestamp: Optional[datetime] = Field(
        None, description="When node was degraded"
    )

    # Source tracking
    source_memory_ids: List[UUID] = Field(default_factory=list)
    extraction_model: Optional[str] = None
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

    # ISO/IEC 42001 - Source Trust & Provenance
    source_owner: Optional[str] = Field(
        None, max_length=255, description="Owner/responsible party for this source"
    )
    trust_level: Optional[str] = Field(
        "unverified",
        max_length=50,
        description="Trust level: high/medium/low/unverified",
    )
    last_verified_at: Optional[datetime] = Field(
        None, description="Timestamp of last verification"
    )
    verification_notes: Optional[str] = Field(
        None, description="Notes from verification process"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime
    accessed_count: int = Field(0, ge=0)

    model_config = ConfigDict(from_attributes=True)


class SemanticRelationship(BaseModel):
    """Typed relationship between semantic nodes"""

    id: UUID
    tenant_id: str
    project_id: str

    # Relationship
    source_node_id: UUID
    target_node_id: UUID
    relation_type: SemanticRelationType

    # Strength and confidence
    strength: float = Field(0.5, ge=0.0, le=1.0)
    confidence: float = Field(0.5, ge=0.0, le=1.0)

    # Evidence
    evidence_text: Optional[str] = None
    source_memory_ids: List[UUID] = Field(default_factory=list)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SemanticIndexEntry(BaseModel):
    """Fast lookup index entry for topic → semantic node mapping"""

    id: UUID
    tenant_id: str
    project_id: str

    topic: str
    normalized_topic: str
    semantic_node_id: Optional[UUID] = None

    topic_embedding: Optional[List[float]] = None

    occurrence_count: int = Field(1, ge=1)
    last_seen_at: datetime

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Request/Response Models
# ============================================================================


class ExtractSemanticNodesRequest(BaseModel):
    """Request to extract semantic nodes from memories"""

    tenant_id: str
    project: str

    memory_ids: Optional[List[UUID]] = Field(
        None, description="Specific memory IDs to extract from"
    )
    max_memories: int = Field(
        100, gt=0, le=1000, description="Maximum memories to process"
    )
    min_confidence: float = Field(
        0.5, ge=0.0, le=1.0, description="Minimum extraction confidence"
    )

    # Filters
    since: Optional[datetime] = Field(
        None, description="Only process memories after this timestamp"
    )
    domains: Optional[List[str]] = Field(None, description="Filter by domains")


class ExtractSemanticNodesResponse(BaseModel):
    """Response from semantic extraction"""

    nodes_extracted: int
    relationships_created: int
    nodes: List[SemanticNode] = Field(default_factory=list)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    message: str = "Semantic extraction completed"


class SemanticSearchRequest(BaseModel):
    """Request for 3-stage semantic search"""

    tenant_id: str
    project: str

    query: str = Field(..., min_length=1, max_length=1024)
    k: int = Field(10, gt=0, le=100, description="Number of results")

    # Stage 1: Topic identification
    enable_topic_matching: bool = Field(
        True, description="Enable topic → vector search"
    )

    # Stage 2: Term normalization
    enable_canonicalization: bool = Field(
        True, description="Enable term canonicalization"
    )

    # Stage 3: Semantic re-ranking
    enable_reranking: bool = Field(True, description="Enable semantic re-ranking")

    # Filters
    node_types: Optional[List[SemanticNodeType]] = None
    domains: Optional[List[str]] = None
    min_priority: Optional[int] = Field(None, ge=1, le=5)
    exclude_degraded: bool = Field(True, description="Exclude degraded nodes")


class SemanticSearchResponse(BaseModel):
    """Response from semantic search"""

    nodes: List[SemanticNode] = Field(default_factory=list)
    total_count: int

    # Stage breakdown
    stage1_results: int = Field(0, description="Results from topic matching")
    stage2_results: int = Field(0, description="Results after canonicalization")
    stage3_results: int = Field(0, description="Results after re-ranking")

    # Query analysis
    identified_topics: List[str] = Field(default_factory=list)
    canonical_terms: List[str] = Field(default_factory=list)

    statistics: Dict[str, Any] = Field(default_factory=dict)


class ReinforceSemanticNodeRequest(BaseModel):
    """Request to reinforce a semantic node"""

    tenant_id: str
    project: str
    node_id: UUID


class ApplySemanticDecayRequest(BaseModel):
    """Request to apply decay to semantic nodes"""

    tenant_id: str
    project: str
    decay_threshold_days: int = Field(60, gt=0, le=365, description="Days before decay")


class ApplySemanticDecayResponse(BaseModel):
    """Response from decay application"""

    degraded_count: int = Field(0, description="Newly degraded nodes")
    total_degraded: int = Field(0, description="Total degraded nodes")
    message: str = "Decay applied successfully"


class CreateSemanticRelationshipRequest(BaseModel):
    """Request to create semantic relationship"""

    tenant_id: str
    project: str

    source_node_id: UUID
    target_node_id: UUID
    relation_type: SemanticRelationType

    strength: float = Field(0.5, ge=0.0, le=1.0)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    evidence_text: Optional[str] = None


class SemanticNodeStatistics(BaseModel):
    """Statistics for semantic nodes"""

    tenant_id: str
    project_id: str

    total_nodes: int = 0
    concepts: int = 0
    topics: int = 0
    entities: int = 0
    terms: int = 0
    categories: int = 0

    degraded_nodes: int = 0
    avg_priority: float = 0.0
    avg_importance: float = 0.0

    total_accesses: int = 0
    total_reinforcements: int = 0


# ============================================================================
# Extraction Models
# ============================================================================


class ExtractedTopic(BaseModel):
    """A topic extracted from text"""

    topic: str
    normalized_topic: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedTerm(BaseModel):
    """A term with canonical form"""

    original: str
    canonical: str
    definition: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedRelation(BaseModel):
    """An extracted semantic relation"""

    source: str
    relation: str
    target: str
    confidence: float = Field(ge=0.0, le=1.0)


class SemanticExtractionResult(BaseModel):
    """Complete extraction result from LLM"""

    topics: List[ExtractedTopic] = Field(default_factory=list)
    terms: List[ExtractedTerm] = Field(default_factory=list)
    relations: List[ExtractedRelation] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    domain: Optional[str] = None
