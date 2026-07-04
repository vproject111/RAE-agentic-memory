"""
Hybrid Search API Routes - Multi-Strategy Search Endpoints

This module provides FastAPI routes for hybrid search operations including:
- Multi-strategy search with dynamic weighting
- Query analysis
- Weight profile management
- Search analytics
"""

from typing import Dict

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request

from apps.memory_api.models.hybrid_search_models import (
    DEFAULT_WEIGHT_PROFILES,
    HybridSearchRequest,
    HybridSearchResponse,
    QueryAnalysisRequest,
    QueryAnalysisResponse,
)
from apps.memory_api.services.hybrid_search_service import HybridSearchService
from apps.memory_api.services.query_analyzer import QueryAnalyzer

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Hybrid Search"])


# ============================================================================
# Dependency Injection
# ============================================================================


async def get_pool(request: Request):
    """Get database connection pool from app state"""
    return request.app.state.pool


# ============================================================================
# Search Endpoints
# ============================================================================


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest, pool=Depends(get_pool)):
    """
    Execute hybrid multi-strategy search.

    Combines vector similarity, semantic nodes, graph traversal, and full-text
    search with dynamic weighting based on query analysis.

    Features:
    - Automatic query intent classification
    - Dynamic weight calculation
    - Multi-strategy result fusion
    - Optional LLM re-ranking
    """
    try:
        service = HybridSearchService(pool)

        result = await service.search(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            query=request.query,
            k=request.k,
            enable_vector=request.enable_vector_search,
            enable_semantic=request.enable_semantic_search,
            enable_graph=request.enable_graph_search,
            enable_fulltext=request.enable_fulltext_search,
            enable_reranking=request.enable_reranking,
            reranking_model=request.reranking_model,
            manual_weights=request.manual_weights,
            temporal_filter=request.temporal_filter,
            tag_filter=request.tag_filter,
            min_importance=request.min_importance,
            graph_max_depth=request.graph_max_depth,
            conversation_history=request.conversation_history,
        )

        logger.info(
            "hybrid_search_complete",
            query=request.query,
            results=result.total_results,
            time=result.total_time_ms,
        )

        return HybridSearchResponse(
            search_result=result,
            message=f"Hybrid search completed: {result.total_results} results in {result.total_time_ms}ms",
        )

    except Exception as e:
        logger.error("hybrid_search_failed", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Query Analysis
# ============================================================================


@router.post("/analyze", response_model=QueryAnalysisResponse)
async def analyze_query(
    req: Request, request: QueryAnalysisRequest, pool=Depends(get_pool)
):
    """
    Analyze query intent and recommend search strategies.

    Returns:
    - Query intent classification
    - Extracted entities and concepts
    - Recommended search strategies
    - Dynamic weight suggestions
    """
    try:
        analyzer = QueryAnalyzer()
        tenant_id = (
            req.state.tenant_id if hasattr(req.state, "tenant_id") else "default"
        )

        analysis = await analyzer.analyze_intent(
            query=request.query,
            tenant_id=str(tenant_id),
            project_id="default",  # Default project
            context=request.conversation_history,
            user_preferences=request.user_preferences,
        )

        logger.info(
            "query_analyzed",
            query=request.query,
            intent=analysis.intent.value,
            confidence=analysis.confidence,
        )

        return QueryAnalysisResponse(
            analysis=analysis, message="Query analyzed successfully"
        )

    except Exception as e:
        logger.error("query_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/analyze/explain")
async def explain_query_analysis(req: Request, request: QueryAnalysisRequest):
    """
    Get human-readable explanation of query analysis.

    Returns a detailed text explanation of the query analysis including
    intent, entities, and recommended strategies.
    """
    try:
        analyzer = QueryAnalyzer()
        # In production, get from auth context
        tenant_id = "default"
        project_id = "default"

        analysis = await analyzer.analyze_intent(
            query=request.query,
            tenant_id=tenant_id,
            project_id=project_id,
            context=request.conversation_history,
            user_preferences=request.user_preferences,
        )

        explanation = await analyzer.explain_analysis(analysis)

        return {
            "query": request.query,
            "explanation": explanation,
            "analysis": analysis,
        }

    except Exception as e:
        logger.error("explain_analysis_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Weight Profiles
# ============================================================================


@router.get("/weights/profiles")
async def get_weight_profiles():
    """
    Get all available weight profiles.

    Returns pre-defined weight configurations for common query types.
    """
    try:
        analyzer = QueryAnalyzer()
        profiles = analyzer.get_available_profiles()

        return {
            "profiles": profiles,
            "default": "balanced",
            "message": "Weight profiles retrieved successfully",
        }

    except Exception as e:
        logger.error("get_profiles_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/weights/profiles/{profile_name}")
async def get_weight_profile(profile_name: str):
    """
    Get a specific weight profile by name.

    Available profiles:
    - balanced: Equal weight across strategies
    - factual: Optimized for factual lookups
    - conceptual: Optimized for concept exploration
    - relational: Optimized for relationship queries
    - keyword: Keyword-based search
    """
    try:
        if profile_name not in DEFAULT_WEIGHT_PROFILES:
            raise HTTPException(
                status_code=404, detail=f"Profile '{profile_name}' not found"
            )

        profile = DEFAULT_WEIGHT_PROFILES[profile_name]

        return {
            "profile_name": profile.profile_name,
            "description": profile.description,
            "weights": {k.value: v for k, v in profile.weights.items()},
            "use_cases": profile.use_cases,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_profile_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/weights/calculate")
async def calculate_weights_for_query(request: QueryAnalysisRequest):
    """
    Calculate optimal weights for a specific query without executing search.

    Useful for testing and understanding weight calculation logic.
    """
    try:
        analyzer = QueryAnalyzer()

        # Analyze query
        # In production, get from auth context
        tenant_id = "default"
        project_id = "default"

        analysis = await analyzer.analyze_intent(
            query=request.query,
            tenant_id=tenant_id,
            project_id=project_id,
            context=request.conversation_history,
            user_preferences=request.user_preferences,
        )

        # Calculate weights
        weights = await analyzer.calculate_dynamic_weights(analysis)

        return {
            "query": request.query,
            "intent": analysis.intent.value,
            "confidence": analysis.confidence,
            "weights": {k.value: v for k, v in weights.items()},
            "recommended_strategies": [
                s.value for s in analysis.recommended_strategies
            ],
            "message": "Weights calculated successfully",
        }

    except Exception as e:
        logger.error("calculate_weights_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Search Comparison
# ============================================================================


@router.post("/compare")
async def compare_search_strategies(
    request: HybridSearchRequest, pool=Depends(get_pool)
):
    """
    Compare results from different search strategies side-by-side.

    Executes each strategy independently and returns results for comparison.
    Useful for evaluation and debugging.
    """
    try:
        service = HybridSearchService(pool)

        # Execute with only vector
        vector_result = await service.search(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            query=request.query,
            k=request.k,
            enable_vector=True,
            enable_semantic=False,
            enable_graph=False,
            enable_fulltext=False,
            enable_reranking=False,
        )

        # Execute with only semantic
        semantic_result = await service.search(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            query=request.query,
            k=request.k,
            enable_vector=False,
            enable_semantic=True,
            enable_graph=False,
            enable_fulltext=False,
            enable_reranking=False,
        )

        # Execute with only fulltext
        fulltext_result = await service.search(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            query=request.query,
            k=request.k,
            enable_vector=False,
            enable_semantic=False,
            enable_graph=False,
            enable_fulltext=True,
            enable_reranking=False,
        )

        # Execute hybrid
        hybrid_result = await service.search(
            tenant_id=request.tenant_id,
            project_id=request.project_id,
            query=request.query,
            k=request.k,
            enable_vector=True,
            enable_semantic=True,
            enable_graph=True,
            enable_fulltext=True,
            enable_reranking=request.enable_reranking,
        )

        logger.info("strategy_comparison_complete", query=request.query)

        return {
            "query": request.query,
            "strategies": {
                "vector": {
                    "results": vector_result.results,
                    "count": len(vector_result.results),
                    "time_ms": vector_result.total_time_ms,
                },
                "semantic": {
                    "results": semantic_result.results,
                    "count": len(semantic_result.results),
                    "time_ms": semantic_result.total_time_ms,
                },
                "fulltext": {
                    "results": fulltext_result.results,
                    "count": len(fulltext_result.results),
                    "time_ms": fulltext_result.total_time_ms,
                },
                "hybrid": {
                    "results": hybrid_result.results,
                    "count": len(hybrid_result.results),
                    "time_ms": hybrid_result.total_time_ms,
                    "applied_weights": hybrid_result.applied_weights,
                },
            },
            "message": "Strategy comparison completed",
        }

    except Exception as e:
        logger.error("comparison_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Testing and Debugging
# ============================================================================


@router.post("/test/weights")
async def test_custom_weights(
    query: str,
    weights: Dict[str, float],
    tenant_id: str,
    project_id: str,
    k: int = 10,
    pool=Depends(get_pool),
):
    """
    Test search with custom weights.

    Allows manual specification of strategy weights for experimentation.

    Weights must be provided for: vector, semantic, graph, fulltext
    and should sum to approximately 1.0.
    """
    try:
        # Validate weights
        total = sum(weights.values())
        if not (0.95 <= total <= 1.05):
            raise HTTPException(
                status_code=400, detail=f"Weights must sum to ~1.0 (got {total})"
            )

        service = HybridSearchService(pool)

        result = await service.search(
            tenant_id=tenant_id,
            project_id=project_id,
            query=query,
            k=k,
            manual_weights=weights,
            enable_reranking=False,  # Disable for clearer weight impact
        )

        return {
            "query": query,
            "custom_weights": weights,
            "results": result.results,
            "total_results": result.total_results,
            "search_time_ms": result.search_time_ms,
            "message": "Custom weights test completed",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("test_weights_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ============================================================================
# Health and Status
# ============================================================================


@router.get("/health")
async def health_check():
    """Health check endpoint for hybrid search service"""
    return {
        "status": "healthy",
        "service": "hybrid_search_api",
        "version": "2.0",
        "features": [
            "multi_strategy_search",
            "query_analysis",
            "dynamic_weighting",
            "llm_reranking",
            "weight_profiles",
            "strategy_comparison",
        ],
        "available_strategies": ["vector", "semantic", "graph", "fulltext"],
        "available_profiles": list(DEFAULT_WEIGHT_PROFILES.keys()),
    }


@router.get("/info")
async def get_search_info():
    """
    Get information about the hybrid search system.

    Returns available strategies, profiles, and configuration.
    """
    return {
        "strategies": {
            "vector": {
                "name": "Vector Similarity Search",
                "description": "Semantic similarity using embeddings",
                "use_cases": ["semantic queries", "conceptual search"],
            },
            "semantic": {
                "name": "Semantic Node Search",
                "description": "Knowledge graph nodes and definitions",
                "use_cases": ["concept exploration", "entity search"],
            },
            "graph": {
                "name": "Graph Traversal Search",
                "description": "Relationship-based graph traversal",
                "use_cases": ["connection queries", "relationship discovery"],
            },
            "fulltext": {
                "name": "Full-Text Keyword Search",
                "description": "Traditional keyword-based search",
                "use_cases": ["exact matches", "keyword lookup"],
            },
        },
        "intents": {
            "factual": "Looking for specific facts",
            "conceptual": "Understanding concepts",
            "exploratory": "Open-ended exploration",
            "temporal": "Time-based queries",
            "relational": "Relationship queries",
            "aggregative": "Summary/statistics",
        },
        "profiles": {
            name: {
                "description": profile.description,
                "weights": {k.value: v for k, v in profile.weights.items()},
            }
            for name, profile in DEFAULT_WEIGHT_PROFILES.items()
        },
        "reranking_models": [
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
            "gpt-4-turbo",
            "gpt-4o",
        ],
    }
