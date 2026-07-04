"""
Hybrid Search Models - Multi-Strategy Search with Query Analysis

This module defines models for the hybrid search system including:
- Query analysis and intent classification
- Dynamic weight calculation
- Multi-strategy search (vector, semantic, graph, full-text)
- LLM re-ranking
- Composite scoring
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ============================================================================
# Enums
# ============================================================================


class QueryIntent(str, Enum):
    """Detected intent of user query"""

    FACTUAL = "factual"  # Looking for specific facts
    CONCEPTUAL = "conceptual"  # Understanding concepts/relationships
    EXPLORATORY = "exploratory"  # Open-ended exploration
    TEMPORAL = "temporal"  # Time-based queries
    RELATIONAL = "relational"  # Relationship/connection queries
    AGGREGATIVE = "aggregative"  # Summary/aggregation queries


class SearchStrategy(str, Enum):
    """Available search strategies"""

    VECTOR = "vector"  # Vector similarity search
    SEMANTIC = "semantic"  # Semantic node search
    GRAPH = "graph"  # Graph traversal search
    FULLTEXT = "fulltext"  # Full-text search
    HYBRID = "hybrid"  # Combined strategies


class RerankingModel(str, Enum):
    """LLM models for re-ranking"""

    CLAUDE_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    GPT4_TURBO = "gpt-4-turbo"
    GPT4O = "gpt-4o"


# ============================================================================
# Query Analysis Models
# ============================================================================


class QueryAnalysis(BaseModel):
    """
    Result of LLM-based query analysis.

    Determines query intent, key entities, and optimal search strategy.
    """

    # Query classification
    intent: QueryIntent = Field(..., description="Detected query intent")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in classification"
    )

    # Extracted components
    key_entities: List[str] = Field(
        default_factory=list, description="Named entities in query"
    )
    key_concepts: List[str] = Field(default_factory=list, description="Core concepts")
    temporal_markers: List[str] = Field(
        default_factory=list, description="Time-related terms"
    )
    relation_types: List[str] = Field(
        default_factory=list, description="Relationship types"
    )

    # Recommended strategies
    recommended_strategies: List[SearchStrategy] = Field(
        default_factory=list,
        description="Ordered list of recommended search strategies",
    )

    # Dynamic weights (sum to 1.0)
    strategy_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Weight for each strategy: {'vector': 0.4, 'semantic': 0.3, ...}",
    )

    # Analysis metadata
    requires_temporal_filtering: bool = Field(False)
    requires_graph_traversal: bool = Field(False)
    suggested_depth: Optional[int] = Field(
        None, description="Suggested traversal depth"
    )

    # Original query
    original_query: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QueryAnalysisRequest(BaseModel):
    """Request for query analysis"""

    query: str = Field(..., min_length=1, max_length=1024)
    tenant_id: str
    project_id: str

    # Context (optional)
    conversation_history: List[str] = Field(default_factory=list)
    user_preferences: Dict[str, Any] = Field(default_factory=dict)


class QueryAnalysisResponse(BaseModel):
    """Response from query analysis"""

    analysis: QueryAnalysis
    message: str = "Query analyzed successfully"


# ============================================================================
# Search Result Models
# ============================================================================


class SearchResultItem(BaseModel):
    """
    A single search result with multi-strategy scores.

    Combines results from vector, semantic, graph, and full-text search.
    """

    # Core result data
    memory_id: UUID
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Strategy-specific scores (0-1)
    vector_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    semantic_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    graph_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    fulltext_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Composite score
    hybrid_score: float = Field(
        ..., ge=0.0, le=1.0, description="Weighted composite score"
    )
    rerank_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="LLM re-ranking score"
    )

    # Final score and rank
    final_score: float = Field(..., ge=0.0, le=1.0)
    rank: int = Field(..., ge=1)

    # Matched components
    matched_entities: List[str] = Field(default_factory=list)
    matched_concepts: List[str] = Field(default_factory=list)

    # Source information
    search_strategies_used: List[SearchStrategy] = Field(default_factory=list)
    source_nodes: List[UUID] = Field(
        default_factory=list, description="Graph nodes if applicable"
    )

    # Timestamps
    created_at: datetime
    relevance_timestamp: Optional[datetime] = None


class HybridSearchResult(BaseModel):
    """
    Complete hybrid search results with analysis.

    Combines results from multiple strategies with comprehensive metadata.
    """

    # Results
    results: List[SearchResultItem] = Field(default_factory=list)
    total_results: int = Field(0, ge=0)

    # Query analysis
    query_analysis: QueryAnalysis

    # Strategy breakdown
    vector_results_count: int = Field(0, ge=0)
    semantic_results_count: int = Field(0, ge=0)
    graph_results_count: int = Field(0, ge=0)
    fulltext_results_count: int = Field(0, ge=0)

    # Performance metrics
    total_time_ms: int = Field(0, ge=0)
    query_analysis_time_ms: int = Field(0, ge=0)
    search_time_ms: int = Field(0, ge=0)
    reranking_time_ms: Optional[int] = None

    # Applied weights
    applied_weights: Dict[str, float] = Field(default_factory=dict)

    # Metadata
    reranking_used: bool = Field(False)
    reranking_model: Optional[RerankingModel] = None

    searched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Request/Response Models
# ============================================================================


class HybridSearchRequest(BaseModel):
    """Request for hybrid multi-strategy search"""

    tenant_id: str
    project_id: str
    query: str = Field(..., min_length=1, max_length=1024)

    # Result parameters
    k: int = Field(10, gt=0, le=100, description="Number of results")

    # Strategy enablement
    enable_vector_search: bool = Field(True)
    enable_semantic_search: bool = Field(True)
    enable_graph_search: bool = Field(True)
    enable_fulltext_search: bool = Field(True)

    # LLM re-ranking
    enable_reranking: bool = Field(True, description="Enable LLM re-ranking")
    reranking_model: RerankingModel = Field(RerankingModel.CLAUDE_HAIKU)

    # Manual weight override (if provided, skips query analysis)
    manual_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Manual weight override: {'vector': 0.4, 'semantic': 0.3, ...}",
    )

    # Filters
    temporal_filter: Optional[datetime] = Field(None, description="Filter by time")
    tag_filter: Optional[List[str]] = Field(None, description="Filter by tags")
    min_importance: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Graph search parameters
    graph_max_depth: int = Field(
        3, gt=0, le=5, description="Max depth for graph traversal"
    )
    graph_start_nodes: Optional[List[str]] = Field(
        None, description="Specific start nodes"
    )

    # Context
    conversation_history: List[str] = Field(default_factory=list)


class HybridSearchResponse(BaseModel):
    """Response from hybrid search"""

    search_result: HybridSearchResult
    message: str = "Hybrid search completed successfully"


# ============================================================================
# Weight Calculation Models
# ============================================================================


class WeightCalculationStrategy(BaseModel):
    """
    Strategy for calculating dynamic weights based on query intent.

    Maps query intents to optimal strategy weights.
    """

    intent: QueryIntent
    weights: Dict[SearchStrategy, float] = Field(
        ..., description="Strategy weights for this intent"
    )
    description: str


class WeightProfile(BaseModel):
    """
    A named weight profile for quick application.

    Pre-defined weight configurations for common use cases.
    """

    profile_name: str = Field(..., max_length=100)
    description: str
    weights: Dict[SearchStrategy, float]
    use_cases: List[str] = Field(default_factory=list)


# Pre-defined weight profiles
DEFAULT_WEIGHT_PROFILES = {
    "balanced": WeightProfile(
        profile_name="balanced",
        description="Balanced weights across all strategies",
        weights={
            SearchStrategy.VECTOR: 0.35,
            SearchStrategy.SEMANTIC: 0.25,
            SearchStrategy.GRAPH: 0.20,
            SearchStrategy.FULLTEXT: 0.20,
        },
        use_cases=["general queries", "exploratory search"],
    ),
    "factual": WeightProfile(
        profile_name="factual",
        description="Optimized for factual lookups",
        weights={
            SearchStrategy.VECTOR: 0.45,
            SearchStrategy.SEMANTIC: 0.30,
            SearchStrategy.GRAPH: 0.10,
            SearchStrategy.FULLTEXT: 0.15,
        },
        use_cases=["specific facts", "direct answers"],
    ),
    "conceptual": WeightProfile(
        profile_name="conceptual",
        description="Optimized for conceptual understanding",
        weights={
            SearchStrategy.VECTOR: 0.20,
            SearchStrategy.SEMANTIC: 0.50,
            SearchStrategy.GRAPH: 0.20,
            SearchStrategy.FULLTEXT: 0.10,
        },
        use_cases=["concept exploration", "understanding relationships"],
    ),
    "relational": WeightProfile(
        profile_name="relational",
        description="Optimized for relationship queries",
        weights={
            SearchStrategy.VECTOR: 0.15,
            SearchStrategy.SEMANTIC: 0.25,
            SearchStrategy.GRAPH: 0.50,
            SearchStrategy.FULLTEXT: 0.10,
        },
        use_cases=["connections", "relationships", "how things relate"],
    ),
    "keyword": WeightProfile(
        profile_name="keyword",
        description="Keyword-based full-text search",
        weights={
            SearchStrategy.VECTOR: 0.30,
            SearchStrategy.SEMANTIC: 0.10,
            SearchStrategy.GRAPH: 0.10,
            SearchStrategy.FULLTEXT: 0.50,
        },
        use_cases=["exact matches", "keyword search"],
    ),
}


# ============================================================================
# Re-ranking Models
# ============================================================================


class RerankingRequest(BaseModel):
    """Request for LLM-based result re-ranking"""

    query: str
    results: List[SearchResultItem]
    k: int = Field(10, gt=0, le=100, description="Top k to re-rank")
    model: RerankingModel = Field(RerankingModel.CLAUDE_HAIKU)


class RerankingResponse(BaseModel):
    """Response from LLM re-ranking"""

    reranked_results: List[SearchResultItem]
    reranking_time_ms: int
    model_used: RerankingModel


class RerankingExplanation(BaseModel):
    """
    Explanation for why a result was ranked at a specific position.

    Provides transparency into LLM re-ranking decisions.
    """

    result_id: UUID
    rank: int
    rerank_score: float = Field(..., ge=0.0, le=1.0)
    explanation: str
    relevance_factors: List[str] = Field(default_factory=list)


# ============================================================================
# Analytics Models
# ============================================================================


class SearchAnalytics(BaseModel):
    """Analytics for search performance"""

    tenant_id: str
    project_id: str

    # Query statistics
    total_queries: int = Field(0, ge=0)
    avg_results_per_query: float = Field(0.0, ge=0.0)
    avg_query_time_ms: float = Field(0.0, ge=0.0)

    # Intent distribution
    intent_distribution: Dict[QueryIntent, int] = Field(default_factory=dict)

    # Strategy usage
    strategy_usage: Dict[SearchStrategy, int] = Field(default_factory=dict)
    avg_hybrid_score: float = Field(0.0, ge=0.0, le=1.0)

    # Re-ranking
    reranking_usage_percent: float = Field(0.0, ge=0.0, le=100.0)
    avg_reranking_time_ms: float = Field(0.0, ge=0.0)

    # Time period
    period_start: datetime
    period_end: datetime


class GetSearchAnalyticsRequest(BaseModel):
    """Request for search analytics"""

    tenant_id: str
    project_id: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class GetSearchAnalyticsResponse(BaseModel):
    """Response with search analytics"""

    analytics: SearchAnalytics
    message: str = "Search analytics retrieved"


# ============================================================================
# Configuration Models
# ============================================================================


class HybridSearchConfig(BaseModel):
    """
    Configuration for hybrid search system.

    Global settings for weight calculation, re-ranking, and strategy selection.
    """

    # Default weights
    default_weight_profile: str = Field("balanced")
    allow_manual_weights: bool = Field(True)

    # Query analysis
    enable_query_analysis: bool = Field(True)
    query_analysis_model: str = Field("claude-3-5-sonnet-20241022")

    # Re-ranking
    enable_reranking_by_default: bool = Field(True)
    default_reranking_model: RerankingModel = Field(RerankingModel.CLAUDE_HAIKU)
    reranking_top_k: int = Field(20, description="Re-rank top K results")

    # Performance
    max_results_per_strategy: int = Field(50)
    query_timeout_ms: int = Field(5000)

    # Caching
    enable_query_cache: bool = Field(True)
    cache_ttl_seconds: int = Field(300)


class UpdateHybridSearchConfigRequest(BaseModel):
    """Request to update hybrid search configuration"""

    config: HybridSearchConfig


class GetHybridSearchConfigResponse(BaseModel):
    """Response with hybrid search configuration"""

    config: HybridSearchConfig
    message: str = "Configuration retrieved"
