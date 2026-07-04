"""
Repository dependencies for RAE Memory API.
Separated from main dependencies to avoid circular imports.
"""

import asyncpg
from fastapi import HTTPException

from .repositories.graph_repository import GraphRepository
from .repositories.graph_repository_enhanced import EnhancedGraphRepository


def get_graph_repository(pool: asyncpg.Pool = None) -> GraphRepository:
    """
    Factory for GraphRepository.
    """
    if pool is None:
        raise HTTPException(status_code=500, detail="Database pool not available")
    return GraphRepository(pool)


def get_enhanced_graph_repository(pool: asyncpg.Pool = None) -> EnhancedGraphRepository:
    """
    Factory for EnhancedGraphRepository.
    """
    if pool is None:
        raise HTTPException(status_code=500, detail="Database pool not available")
    return EnhancedGraphRepository(pool)
