"""
Structure Metrics - Geometry of Memory

These metrics analyze the structural properties of the memory graph:
- Graph Connectivity Score (GCS): How well-connected is the memory graph
- Semantic Coherence Score (SCS): Semantic similarity between connected memories
- Graph Entropy: Organization and structure of information
- Structural Drift: Change in graph topology over time
"""

import math
from typing import Dict, List, Tuple

import numpy as np

from .base import (
    MathMetricBase,
    MemorySnapshot,
    calculate_entropy,
    cosine_similarity,
    jaccard_similarity,
)


class GraphConnectivityScore(MathMetricBase):
    """
    Graph Connectivity Score (GCS)

    Measures how well-connected the memory graph is, normalized by graph size.

    Formula: GCS = average_degree / log(|nodes|)

    High GCS indicates well-connected, integrated knowledge.
    Low GCS indicates fragmented, isolated memories.

    Range: 0.0 (disconnected) to unbounded (highly connected)
    Typical good value: > 1.0
    """

    def __init__(self):
        super().__init__(
            name="graph_connectivity_score",
            description="Measures graph connectivity normalized by size",
        )

    def calculate(
        self,
        num_nodes: int,
        edges: List[Tuple[str, str, float]],
    ) -> float:
        """
        Calculate GCS from graph structure.

        Args:
            num_nodes: Number of nodes in the graph
            edges: List of (source, target, weight) tuples

        Returns:
            GCS value (0.0 to unbounded, typically 0-5)
        """
        if num_nodes == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "num_nodes": 0,
                "num_edges": 0,
                "average_degree": 0.0,
            }
            return 0.0

        # Count edges (undirected graph, so count each edge once)
        num_edges = len(edges)

        # Calculate average degree (2 * edges / nodes for undirected graph)
        average_degree = (2.0 * num_edges) / num_nodes

        # Normalize by log(nodes) to account for graph size
        if num_nodes > 1:
            gcs = average_degree / math.log(num_nodes)
        else:
            gcs = 0.0

        self._last_value = gcs
        self._last_metadata = {
            "num_nodes": num_nodes,
            "num_edges": num_edges,
            "average_degree": average_degree,
        }

        return gcs


class SemanticCoherenceScore(MathMetricBase):
    """
    Semantic Coherence Score (SCS)

    Measures average semantic similarity between connected memories.

    Formula: SCS = mean(cosine_similarity(embedding(u), embedding(v))) for all edges

    High SCS means connected memories are semantically similar (good structure).
    Low SCS means connections are random or weak (poor structure).

    Range: 0.0 (incoherent) to 1.0 (perfectly coherent)
    Typical good value: > 0.6
    """

    def __init__(self):
        super().__init__(
            name="semantic_coherence_score",
            description="Average semantic similarity between connected memories",
        )

    def calculate(
        self,
        snapshot: MemorySnapshot,
    ) -> float:
        """
        Calculate SCS from memory snapshot.

        Args:
            snapshot: Memory snapshot with embeddings and edges

        Returns:
            SCS value (0.0 to 1.0)
        """
        if len(snapshot.graph_edges) == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "num_edges_analyzed": 0,
                "similarities": [],
            }
            return 0.0

        similarities = []

        for source_id, target_id, weight in snapshot.graph_edges:
            source_emb = snapshot.get_embedding(source_id)
            target_emb = snapshot.get_embedding(target_id)

            if source_emb is not None and target_emb is not None:
                sim = cosine_similarity(source_emb, target_emb)
                similarities.append(sim)

        if not similarities:
            self._last_value = 0.0
            self._last_metadata = {
                "num_edges_analyzed": 0,
                "similarities": [],
            }
            return 0.0

        scs = float(np.mean(similarities))

        self._last_value = scs
        self._last_metadata = {
            "num_edges_analyzed": len(similarities),
            "min_similarity": float(np.min(similarities)),
            "max_similarity": float(np.max(similarities)),
            "std_similarity": float(np.std(similarities)),
        }

        return scs


class GraphEntropyMetric(MathMetricBase):
    """
    Graph Entropy

    Measures the organization and structure of information in the memory graph.

    Low entropy = highly organized, hierarchical structure
    High entropy = disorganized, flat structure

    We calculate entropy based on degree distribution:
    - Low entropy: some nodes have many connections (hubs), most have few
    - High entropy: all nodes have similar number of connections (flat)

    Range: 0.0 (perfectly organized) to log2(N) (maximally disorganized)
    """

    def __init__(self):
        super().__init__(
            name="graph_entropy",
            description="Information organization and structure in memory graph",
        )

    def calculate(
        self,
        num_nodes: int,
        edges: List[Tuple[str, str, float]],
    ) -> float:
        """
        Calculate graph entropy from degree distribution.

        Args:
            num_nodes: Number of nodes
            edges: List of edges

        Returns:
            Entropy value (0.0 to log2(num_nodes))
        """
        if num_nodes == 0:
            self._last_value = 0.0
            self._last_metadata = {"num_nodes": 0, "degree_distribution": []}
            return 0.0

        # Count node degrees
        degree_count: Dict[str, int] = {}

        for source_id, target_id, _ in edges:
            degree_count[source_id] = degree_count.get(source_id, 0) + 1
            degree_count[target_id] = degree_count.get(target_id, 0) + 1

        # Create degree distribution (probability of each degree)
        degrees = list(degree_count.values())

        if not degrees:
            self._last_value = 0.0
            self._last_metadata = {
                "num_nodes": num_nodes,
                "degree_distribution": [],
            }
            return 0.0

        # Calculate degree frequency distribution
        max_degree = max(degrees)
        degree_freq = np.zeros(max_degree + 1, dtype=np.float32)

        for deg in degrees:
            degree_freq[deg] += 1

        # Normalize to probabilities
        degree_probs = degree_freq / np.sum(degree_freq)

        # Calculate entropy
        entropy = calculate_entropy(degree_probs)

        self._last_value = entropy
        self._last_metadata = {
            "num_nodes": num_nodes,
            "num_connected_nodes": len(degree_count),
            "avg_degree": float(np.mean(degrees)) if degrees else 0.0,
            "max_degree": max_degree,
            "max_possible_entropy": math.log2(num_nodes) if num_nodes > 0 else 0.0,
        }

        return entropy


class StructuralDriftMetric(MathMetricBase):
    """
    Structural Drift

    Measures how much the graph structure has changed between two snapshots.

    Uses Jaccard similarity on the edge set:
    Drift = 1 - Jaccard(edges_t0, edges_t1)

    Low drift = stable structure
    High drift = significant structural changes

    Range: 0.0 (no change) to 1.0 (completely different)
    Typical good value: < 0.3 (stable evolution)
    """

    def __init__(self):
        super().__init__(
            name="structural_drift",
            description="Change in graph topology between snapshots",
        )

    def calculate(
        self,
        snapshot_t0: MemorySnapshot,
        snapshot_t1: MemorySnapshot,
    ) -> float:
        """
        Calculate structural drift between two snapshots.

        Args:
            snapshot_t0: Earlier snapshot
            snapshot_t1: Later snapshot

        Returns:
            Drift value (0.0 to 1.0)
        """
        # Create edge sets (ignoring weights for structural comparison)
        edges_t0 = {(src, tgt) for src, tgt, _ in snapshot_t0.graph_edges}
        edges_t1 = {(src, tgt) for src, tgt, _ in snapshot_t1.graph_edges}

        # Calculate Jaccard similarity
        similarity = jaccard_similarity(edges_t0, edges_t1)

        # Drift is inverse of similarity
        drift = 1.0 - similarity

        self._last_value = drift
        self._last_metadata = {
            "edges_t0": len(edges_t0),
            "edges_t1": len(edges_t1),
            "edges_added": len(edges_t1 - edges_t0),
            "edges_removed": len(edges_t0 - edges_t1),
            "edges_preserved": len(edges_t0 & edges_t1),
            "jaccard_similarity": similarity,
        }

        return drift
