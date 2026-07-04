"""
Base classes and utilities for mathematical metrics

This module provides foundational classes for memory analysis:
- MemorySnapshot: Captures memory state at a point in time
- MathMetricBase: Abstract base class for all mathematical metrics
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
from numpy.typing import NDArray


@dataclass
class MemorySnapshot:
    """
    Snapshot of memory state at a specific point in time.

    Used for temporal analysis and drift detection.

    Attributes:
        timestamp: When this snapshot was taken
        memory_ids: List of memory IDs present in this snapshot
        embeddings: Memory embeddings (numpy array)
        graph_edges: List of (source_id, target_id, weight) tuples
        metadata: Additional metadata (importance scores, tags, etc.)
    """

    timestamp: datetime
    memory_ids: List[str]
    embeddings: NDArray[np.float32]
    graph_edges: List[Tuple[str, str, float]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate snapshot data"""
        if len(self.memory_ids) != len(self.embeddings):
            raise ValueError(
                f"Mismatch: {len(self.memory_ids)} IDs vs {len(self.embeddings)} embeddings"
            )

    @property
    def num_memories(self) -> int:
        """Number of memories in this snapshot"""
        return len(self.memory_ids)

    @property
    def embedding_dim(self) -> int:
        """Dimensionality of embeddings"""
        return self.embeddings.shape[1] if len(self.embeddings.shape) > 1 else 0

    def get_embedding(self, memory_id: str) -> Optional[NDArray[np.float32]]:
        """Get embedding for a specific memory ID"""
        try:
            idx = self.memory_ids.index(memory_id)
            return cast(NDArray[np.float32], self.embeddings[idx])
        except ValueError:
            return None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "num_memories": self.num_memories,
            "embedding_dim": self.embedding_dim,
            "num_edges": len(self.graph_edges),
            "metadata": self.metadata,
        }


class MathMetricBase(ABC):
    """
    Abstract base class for all mathematical metrics.

    All metrics should inherit from this class and implement:
    - calculate(): Compute the metric value
    - get_metadata(): Return metric-specific metadata
    """

    def __init__(self, name: str, description: str):
        """
        Initialize metric.

        Args:
            name: Metric name (e.g., "graph_connectivity_score")
            description: Human-readable description
        """
        self.name = name
        self.description = description
        self._last_value: Optional[float] = None
        self._last_metadata: Dict[str, Any] = {}

    @abstractmethod
    def calculate(self, *args, **kwargs) -> float:
        """
        Calculate the metric value.

        Returns:
            Metric value (typically 0.0 to 1.0, but can vary by metric)
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the last calculation.

        Returns:
            Dictionary with metric-specific metadata
        """
        return self._last_metadata

    def get_result(self) -> Dict[str, Any]:
        """
        Get complete result including value and metadata.

        Returns:
            Dictionary with 'value' and 'metadata' keys
        """
        return {
            "name": self.name,
            "description": self.description,
            "value": self._last_value,
            "metadata": self._last_metadata,
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', last_value={self._last_value})"


def cosine_similarity(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    """
    Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity (-1.0 to 1.0)
    """
    if len(a) == 0 or len(b) == 0:
        return 0.0

    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


def cosine_distance(a: NDArray[np.float32], b: NDArray[np.float32]) -> float:
    """
    Calculate cosine distance (1 - cosine_similarity).

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine distance (0.0 to 2.0)
    """
    return 1.0 - cosine_similarity(a, b)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """
    Calculate Jaccard similarity between two sets.

    Args:
        set_a: First set
        set_b: Second set

    Returns:
        Jaccard similarity (0.0 to 1.0)
    """
    if len(set_a) == 0 and len(set_b) == 0:
        return 1.0

    intersection = set_a & set_b
    union = set_a | set_b

    if len(union) == 0:
        return 0.0

    return len(intersection) / len(union)


def calculate_entropy(probabilities: NDArray[np.float32]) -> float:
    """
    Calculate Shannon entropy.

    Args:
        probabilities: Probability distribution (sums to 1.0)

    Returns:
        Entropy value (0.0 to log(N))
    """
    # Remove zero probabilities (log(0) is undefined)
    probs = probabilities[probabilities > 0]

    if len(probs) == 0:
        return 0.0

    return float(-np.sum(probs * np.log2(probs)))


def normalize_vector(vector: NDArray[np.float32]) -> NDArray[np.float32]:
    """
    Normalize vector to unit length.

    Args:
        vector: Input vector

    Returns:
        Normalized vector
    """
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector
    return vector / norm
