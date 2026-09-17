"""Search module for RAE-core.

Provides hybrid search capabilities combining multiple strategies:
- Vector search (semantic similarity)
- Graph traversal (relationship-based)
- Sparse vectors (BM25)
- Full-text (keyword matching)
"""

from rae_core.search.adaptive_engine import AdaptiveSearchEngine
from rae_core.search.cache import SearchCache
from rae_core.search.classifier import ClassificationResult, QueryClassifier
from rae_core.search.conflict_detector import EvidenceConflictDetector
from rae_core.search.engine import HybridSearchEngine
from rae_core.search.optimizer import (
    MaturityMode,
    OptimizationRecommendation,
    RetrievalOptimizer,
)
from rae_core.search.rewriter import QueryRewriter, RewritePlan
from rae_core.search.router import RoutingPlan, StrategyRouter
from rae_core.search.strategies import SearchStrategy
from rae_core.search.strategies.fulltext import FullTextStrategy
from rae_core.search.strategies.graph import GraphTraversalStrategy
from rae_core.search.strategies.graph_lite import GraphLiteStrategy
from rae_core.search.strategies.sparse import SparseVectorStrategy
from rae_core.search.strategies.vector import VectorSearchStrategy
from rae_core.search.strategies.visual import VisualSearchStrategy

__all__ = [
    "SearchStrategy",
    "VectorSearchStrategy",
    "GraphTraversalStrategy",
    "GraphLiteStrategy",
    "SparseVectorStrategy",
    "FullTextStrategy",
    "VisualSearchStrategy",
    "HybridSearchEngine",
    "AdaptiveSearchEngine",
    "QueryRewriter",
    "RewritePlan",
    "QueryClassifier",
    "ClassificationResult",
    "StrategyRouter",
    "RoutingPlan",
    "SearchCache",
    "EvidenceConflictDetector",
    "RetrievalOptimizer",
    "MaturityMode",
    "OptimizationRecommendation",
]
