"""Core models for RAE-core.

This module exports all Pydantic models used across RAE-core:
- Memory models: MemoryItem, MemoryLayer, MemoryType, etc.
- Search models: SearchQuery, SearchStrategy, SearchResult, etc.
- Graph models: GraphNode, GraphEdge, NodeType, EdgeType, etc.
- Reflection models: Reflection, ReflectionType, ReflectionPolicy
- Sync models: SyncChange, SyncOperation, SyncState, SyncConflict
"""

from .envelope import CodeAttribution, ContextEnvelope
from .evidence import (
    ConflictSeverity,
    ConflictType,
    EvidenceBundle,
)
from .evidence import EvidenceItem as GovernanceEvidenceItem
from .evidence import (
    KnowledgeConflict,
    ResolutionStatus,
)
from .evidence_package import EvidenceConflict, EvidenceItem, EvidencePackage
from .graph import EdgeType, GraphEdge, GraphNode, GraphPath, NodeType, Subgraph
from .knowledge import (
    AuthorityLevel,
    KnowledgeClass,
    KnowledgeRecord,
    KnowledgeSourceType,
)
from .memory import MemoryItem, MemoryLayer, MemoryStats, MemoryType, ScoredMemoryItem
from .reflection import Reflection, ReflectionPolicy, ReflectionPriority, ReflectionType
from .registry import (
    KnowledgeRegistryRecord,
    KnowledgeRevisionDraft,
    KnowledgeRevisionRecord,
)
from .search import (
    ScoringWeights,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchStrategy,
)
from .sync import SyncChange, SyncConflict, SyncOperation, SyncState

__all__ = [
    # Context Envelope models
    "ContextEnvelope",
    "CodeAttribution",
    # Memory models
    "MemoryItem",
    "MemoryLayer",
    "MemoryType",
    "ScoredMemoryItem",
    "MemoryStats",
    # Search models
    "SearchQuery",
    "SearchStrategy",
    "SearchResult",
    "SearchResponse",
    "ScoringWeights",
    # Graph models
    "GraphNode",
    "GraphEdge",
    "NodeType",
    "EdgeType",
    "GraphPath",
    "Subgraph",
    # Reflection models
    "Reflection",
    "ReflectionType",
    "ReflectionPriority",
    "ReflectionPolicy",
    # Sync models
    "SyncChange",
    "SyncOperation",
    "SyncState",
    "SyncConflict",
    # Knowledge models
    "KnowledgeRecord",
    "KnowledgeClass",
    "AuthorityLevel",
    "KnowledgeSourceType",
    # Registry models
    "KnowledgeRegistryRecord",
    "KnowledgeRevisionDraft",
    "KnowledgeRevisionRecord",
    # Evidence models
    "EvidenceItem",
    "GovernanceEvidenceItem",
    "EvidencePackage",
    "EvidenceConflict",
    "EvidenceBundle",
    "KnowledgeConflict",
    "ConflictType",
    "ConflictSeverity",
    "ResolutionStatus",
]
