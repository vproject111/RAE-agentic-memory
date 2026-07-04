"""
Dependency Injection Configuration for RAE Memory API.

This module implements the Composition Root pattern, providing factory functions
for FastAPI dependency injection. All service dependencies are resolved here,
ensuring clean separation of concerns and testability.

Enterprise Architecture Benefits:
- Single source of truth for dependency wiring
- Easy mocking and testing (inject test repositories)
- Clear dependency graph
- No hidden dependencies
"""

from typing import cast

import asyncpg
import redis.asyncio as aioredis
from fastapi import HTTPException, Request
from qdrant_client import AsyncQdrantClient
from redis.asyncio import Redis as AsyncRedis

from .repo_dependencies import get_graph_repository
from .repositories.graph_repository import GraphRepository
from .services.analytics import AnalyticsService
from .services.budget_service import BudgetService
from .services.community_detection import CommunityDetectionService
from .services.compliance_service import ComplianceService
from .services.consistency_service import ConsistencyService
from .services.entity_resolution import EntityResolutionService
from .services.graph_algorithms import GraphAlgorithmsService
from .services.graph_extraction import GraphExtractionService
from .services.human_approval_service import HumanApprovalService
from .services.hybrid_search_service import HybridSearchService
from .services.importance_scoring import ImportanceScoringService
from .services.memory_consolidation import MemoryConsolidationService
from .services.rae_core_service import RAECoreService
from .services.reflection_pipeline import ReflectionPipeline
from .services.retention_service import RetentionService
from .services.semantic_extractor import SemanticExtractor
from .services.temporal_graph import TemporalGraphService

# ==========================================
# Authentication Dependencies
# ==========================================
# NOTE: Auth dependencies moved to apps/memory_api/security/auth.py
# Use verify_token() for authentication globally via FastAPI dependencies
# or import from security.auth for specific endpoints


# ==========================================
# Database Connection Pool
# ==========================================


def get_db_pool(request: Request) -> asyncpg.Pool:
    """
    Get the database connection pool from application state.

    Args:
        request: FastAPI request object

    Returns:
        AsyncPG connection pool
    """
    return request.app.state.pool


# ==========================================
# External Services Clients
# ==========================================


async def create_redis_client(redis_url: str) -> AsyncRedis:
    """
    Factory function to create an asynchronous Redis client.
    """
    return aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)


def get_redis_client(request: Request) -> AsyncRedis:
    """
    Get the Redis client from application state.
    """
    if not hasattr(request.app.state, "redis_client"):
        raise HTTPException(status_code=500, detail="Redis client not initialized")
    return cast(AsyncRedis, request.app.state.redis_client)


def get_qdrant_client(request: Request) -> AsyncQdrantClient:
    """
    Get the Qdrant client from application state.
    """
    if not hasattr(request.app.state, "qdrant_client"):
        raise HTTPException(status_code=500, detail="Qdrant client not initialized")
    return cast(AsyncQdrantClient, request.app.state.qdrant_client)


# ==========================================
# Service Layer Dependencies
# ==========================================


def get_rae_core_service(request: Request) -> RAECoreService:
    """
    Factory for RAECoreService with full dependency injection.

    Composition root for RAE-Core integration.
    Provides access to RAEEngine and storage adapters.

    Args:
        request: FastAPI request object

    Returns:
        Fully configured RAECoreService instance
    """
    if not hasattr(request.app.state, "rae_core_service"):
        raise HTTPException(status_code=500, detail="RAE-Core service not initialized")
    return cast(RAECoreService, request.app.state.rae_core_service)


def get_graph_extraction_service(request: Request) -> GraphExtractionService:
    """
    Factory for GraphExtractionService with full dependency injection.

    This is the Composition Root for graph extraction operations.
    All dependencies are resolved and injected here.

    Args:
        request: FastAPI request object

    Returns:
        Fully configured GraphExtractionService instance
    """
    pool = get_db_pool(request)
    rae_service = get_rae_core_service(request)

    # Instantiate repositories
    # memory_repo = get_memory_repository(pool) # Deprecated
    graph_repo = get_graph_repository(pool)

    # Inject repositories into service
    return GraphExtractionService(rae_service=rae_service, graph_repo=graph_repo)


def get_memory_consolidation_service(request: Request) -> MemoryConsolidationService:
    """
    Factory for MemoryConsolidationService with full dependency injection.

    Uses RAECoreService for memory operations to ensure architectural consistency.

    Args:
        request: FastAPI request object

    Returns:
        Configured MemoryConsolidationService
    """
    rae_service = get_rae_core_service(request)
    # LLM client might need separate injection or be part of rae_service
    # For now, we assume it might be None or injected separately if needed.
    # In future, get_llm_client(request) should be used.

    return MemoryConsolidationService(rae_service=rae_service)


def get_analytics_service(request: Request) -> AnalyticsService:
    """
    Factory for AnalyticsService with full dependency injection.

    Uses RAECoreService for cross-layer data access.

    Args:
        request: FastAPI request object

    Returns:
        Configured AnalyticsService
    """
    rae_service = get_rae_core_service(request)
    return AnalyticsService(rae_service=rae_service)


def get_budget_service(request: Request) -> BudgetService:
    """
    Factory for BudgetService.

    Args:
        request: FastAPI request object

    Returns:
        Configured BudgetService
    """
    rae_service = get_rae_core_service(request)
    return BudgetService(rae_service=rae_service)


def get_compliance_service(request: Request) -> ComplianceService:
    """
    Factory for ComplianceService.

    Args:
        request: FastAPI request object

    Returns:
        Configured ComplianceService
    """
    rae_service = get_rae_core_service(request)
    return ComplianceService(rae_service=rae_service)


def get_hybrid_search_service(request: Request) -> HybridSearchService:
    """
    Factory for HybridSearchService.

    Args:
        request: FastAPI request object

    Returns:
        Configured HybridSearchService
    """
    rae_service = get_rae_core_service(request)
    return HybridSearchService(rae_service=rae_service)


def get_graph_algorithms_service(request: Request) -> GraphAlgorithmsService:
    """
    Factory for GraphAlgorithmsService with full dependency injection.

    Args:
        request: FastAPI request object

    Returns:
        Configured GraphAlgorithmsService
    """
    pool = get_db_pool(request)
    graph_repo = GraphRepository(pool)
    return GraphAlgorithmsService(graph_repo=graph_repo)


def get_temporal_graph_service(request: Request) -> TemporalGraphService:
    """
    Factory for TemporalGraphService.

    Args:
        request: FastAPI request object

    Returns:
        Configured TemporalGraphService
    """
    pool = get_db_pool(request)
    graph_repo = GraphRepository(pool)
    return TemporalGraphService(graph_repo=graph_repo)


def get_consistency_service(request: Request) -> ConsistencyService:
    """
    Factory for ConsistencyService.

    Args:
        request: FastAPI request object

    Returns:
        Configured ConsistencyService
    """
    rae_service = get_rae_core_service(request)
    return ConsistencyService(rae_service=rae_service)


def get_importance_scoring_service(request: Request) -> ImportanceScoringService:
    """
    Factory for ImportanceScoringService.

    Args:
        request: FastAPI request object

    Returns:
        Configured ImportanceScoringService
    """
    rae_service = get_rae_core_service(request)
    return ImportanceScoringService(rae_service=rae_service)


def get_human_approval_service(request: Request) -> HumanApprovalService:
    """
    Factory for HumanApprovalService.

    Args:
        request: FastAPI request object

    Returns:
        Configured HumanApprovalService
    """
    rae_service = get_rae_core_service(request)
    return HumanApprovalService(rae_service=rae_service)


def get_reflection_pipeline(request: Request) -> ReflectionPipeline:
    """
    Factory for ReflectionPipeline with full dependency injection.

    Args:
        request: FastAPI request object

    Returns:
        Configured ReflectionPipeline
    """
    rae_service = get_rae_core_service(request)
    return ReflectionPipeline(rae_service=rae_service)


def get_semantic_extractor(request: Request) -> SemanticExtractor:
    """
    Factory for SemanticExtractor.

    Args:
        request: FastAPI request object

    Returns:
        Configured SemanticExtractor
    """
    rae_service = get_rae_core_service(request)
    return SemanticExtractor(rae_service=rae_service)


def get_retention_service(request: Request) -> RetentionService:
    """
    Factory for RetentionService.

    Args:
        request: FastAPI request object

    Returns:
        Configured RetentionService
    """
    rae_service = get_rae_core_service(request)
    return RetentionService(rae_service=rae_service)


def get_entity_resolution_service(request: Request) -> EntityResolutionService:
    """
    Factory for EntityResolutionService.

    Args:
        request: FastAPI request object

    Returns:
        Configured EntityResolutionService
    """
    rae_service = get_rae_core_service(request)
    return EntityResolutionService(rae_service=rae_service)


def get_community_detection_service(request: Request) -> CommunityDetectionService:
    """
    Factory for CommunityDetectionService.

    Args:
        request: FastAPI request object

    Returns:
        Configured CommunityDetectionService
    """
    rae_service = get_rae_core_service(request)
    return CommunityDetectionService(rae_service=rae_service)
