"""
Memory Metrics - Working Memory Performance Analysis

These metrics analyze the quality and efficiency of Working Memory operations:
- Working Memory Precision/Recall (WM-P/R): Quality and completeness of Working Memory content

Working Memory in RAE serves as a temporary, high-priority buffer for:
- Recently accessed memories
- Contextually relevant information
- Active conversation fragments
- Pending consolidation items

These metrics help evaluate how well Working Memory captures and retains
relevant information for the agent's current task.
"""

from typing import Any, Dict, List, Optional, Set

import numpy as np
from numpy.typing import NDArray

from .base import MathMetricBase, cosine_similarity


def calculate_f1_score(precision: float, recall: float) -> float:
    """
    Calculate F1 score from precision and recall.

    Formula: F1 = 2 * (precision * recall) / (precision + recall)

    Args:
        precision: Precision value (0.0 to 1.0)
        recall: Recall value (0.0 to 1.0)

    Returns:
        F1 score (0.0 to 1.0)
    """
    if precision + recall == 0:
        return 0.0
    return 2 * (precision * recall) / (precision + recall)


class WorkingMemoryPrecisionRecall(MathMetricBase):
    """
    Working Memory Precision/Recall (WM-P/R)

    Measures the quality and completeness of Working Memory content
    by comparing it against ground truth relevant items.

    This metric evaluates two aspects of Working Memory performance:

    1. **Precision**: What fraction of items in Working Memory are actually relevant?
       Formula: precision = |WM intersection relevant| / |WM|
       High precision = Working Memory contains mostly relevant items
       Low precision = Working Memory is cluttered with irrelevant items

    2. **Recall**: What fraction of all relevant items are in Working Memory?
       Formula: recall = |WM intersection relevant| / |relevant|
       High recall = Working Memory captures most relevant items
       Low recall = Working Memory misses important items

    The metric returns F1 score by default (harmonic mean of precision and recall),
    but also provides individual precision/recall values in metadata.

    Matching modes:
    - "exact": Items must match exactly (string comparison)
    - "embedding": Items match if embedding similarity exceeds threshold
    - "hybrid": Combine exact matching with embedding-based matching

    Range: 0.0 (no relevant items in WM) to 1.0 (perfect WM)
    Typical good value: > 0.7 (F1), > 0.8 (precision), > 0.6 (recall)

    Example:
        >>> wm_metric = WorkingMemoryPrecisionRecall()
        >>> result = wm_metric.calculate(
        ...     working_memory_items=["mem_1", "mem_2", "mem_3", "mem_4"],
        ...     relevant_items=["mem_1", "mem_2", "mem_5", "mem_6"],
        ... )
        >>> print(f"F1: {result:.2f}")
        F1: 0.50
        >>> metadata = wm_metric.get_metadata()
        >>> print(f"Precision: {metadata['precision']:.2f}, Recall: {metadata['recall']:.2f}")
        Precision: 0.50, Recall: 0.50
    """

    def __init__(self):
        super().__init__(
            name="working_memory_precision_recall",
            description="Quality and completeness of Working Memory content",
        )

    def calculate(
        self,
        working_memory_items: List[str],
        relevant_items: List[str],
        working_memory_embeddings: Optional[List[NDArray[np.float32]]] = None,
        relevant_embeddings: Optional[List[NDArray[np.float32]]] = None,
        matching_mode: str = "exact",
        similarity_threshold: float = 0.85,
    ) -> float:
        """
        Calculate Working Memory Precision and Recall.

        Args:
            working_memory_items: List of item IDs currently in Working Memory
            relevant_items: List of all relevant item IDs (ground truth)
            working_memory_embeddings: Optional embeddings for WM items (for embedding matching)
            relevant_embeddings: Optional embeddings for relevant items
            matching_mode: How to match items:
                - "exact": Exact string matching of item IDs
                - "embedding": Match by embedding similarity above threshold
                - "hybrid": Combine exact + embedding matching
            similarity_threshold: Cosine similarity threshold for embedding matching

        Returns:
            F1 score (0.0 to 1.0)
        """
        # Handle empty cases
        if not working_memory_items and not relevant_items:
            # Perfect score: no items to track and WM is appropriately empty
            precision = 1.0
            recall = 1.0
            f1 = 1.0
            self._last_value = f1
            self._last_metadata = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "working_memory_size": 0,
                "relevant_size": 0,
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": 0,
                "matching_mode": matching_mode,
                "reason": "Both WM and relevant sets are empty",
            }
            return f1

        if not working_memory_items:
            # Empty WM when there are relevant items = 0 recall
            precision = 1.0  # No false positives (vacuously true)
            recall = 0.0  # No relevant items retrieved
            f1 = 0.0
            self._last_value = f1
            self._last_metadata = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "working_memory_size": 0,
                "relevant_size": len(relevant_items),
                "true_positives": 0,
                "false_positives": 0,
                "false_negatives": len(relevant_items),
                "matching_mode": matching_mode,
                "reason": "Working Memory is empty but relevant items exist",
            }
            return f1

        if not relevant_items:
            # WM has items but nothing is relevant = 0 precision
            precision = 0.0  # All items are false positives
            recall = 1.0  # No relevant items to miss (vacuously true)
            f1 = 0.0
            self._last_value = f1
            self._last_metadata = {
                "precision": precision,
                "recall": recall,
                "f1_score": f1,
                "working_memory_size": len(working_memory_items),
                "relevant_size": 0,
                "true_positives": 0,
                "false_positives": len(working_memory_items),
                "false_negatives": 0,
                "matching_mode": matching_mode,
                "reason": "Working Memory has items but no relevant items defined",
            }
            return f1

        # Calculate matches based on matching mode
        if matching_mode == "exact":
            matches = self._exact_matching(working_memory_items, relevant_items)
        elif matching_mode == "embedding":
            matches = self._embedding_matching(
                working_memory_items,
                relevant_items,
                working_memory_embeddings,
                relevant_embeddings,
                similarity_threshold,
            )
        elif matching_mode == "hybrid":
            # Combine exact and embedding matching
            exact_matches = self._exact_matching(working_memory_items, relevant_items)
            if working_memory_embeddings and relevant_embeddings:
                emb_matches = self._embedding_matching(
                    working_memory_items,
                    relevant_items,
                    working_memory_embeddings,
                    relevant_embeddings,
                    similarity_threshold,
                )
                # Union of both matching methods
                matches = exact_matches | emb_matches
            else:
                matches = exact_matches
        else:
            raise ValueError(f"Unknown matching_mode: {matching_mode}")

        # Calculate precision and recall
        wm_set = set(working_memory_items)
        relevant_set = set(relevant_items)

        true_positives = len(matches)
        false_positives = len(wm_set) - true_positives
        false_negatives = len(relevant_set) - true_positives

        # Precision: TP / (TP + FP) = relevant items in WM / all items in WM
        precision = true_positives / len(wm_set) if len(wm_set) > 0 else 0.0

        # Recall: TP / (TP + FN) = relevant items in WM / all relevant items
        recall = true_positives / len(relevant_set) if len(relevant_set) > 0 else 0.0

        # F1 score
        f1 = calculate_f1_score(precision, recall)

        self._last_value = f1
        self._last_metadata = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "working_memory_size": len(working_memory_items),
            "relevant_size": len(relevant_items),
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "matching_mode": matching_mode,
            "similarity_threshold": (
                similarity_threshold if matching_mode != "exact" else None
            ),
            "matched_items": list(matches)[:10],  # First 10 matched items
        }

        return f1

    def _exact_matching(
        self,
        working_memory_items: List[str],
        relevant_items: List[str],
    ) -> Set[str]:
        """
        Perform exact string matching between WM and relevant items.

        Returns:
            Set of matched item IDs (intersection)
        """
        wm_set = set(working_memory_items)
        relevant_set = set(relevant_items)
        return wm_set & relevant_set

    def _embedding_matching(
        self,
        working_memory_items: List[str],
        relevant_items: List[str],
        working_memory_embeddings: Optional[List[NDArray[np.float32]]],
        relevant_embeddings: Optional[List[NDArray[np.float32]]],
        similarity_threshold: float,
    ) -> Set[str]:
        """
        Perform embedding-based matching between WM and relevant items.

        An item in WM is considered a match if its embedding is similar enough
        to any relevant item's embedding (above threshold).

        Returns:
            Set of matched WM item IDs
        """
        if not working_memory_embeddings or not relevant_embeddings:
            # Fall back to exact matching if embeddings not provided
            return self._exact_matching(working_memory_items, relevant_items)

        matches = set()

        for i, wm_id in enumerate(working_memory_items):
            if i >= len(working_memory_embeddings):
                continue

            wm_emb = working_memory_embeddings[i]

            for j, rel_emb in enumerate(relevant_embeddings):
                similarity = cosine_similarity(wm_emb, rel_emb)

                if similarity >= similarity_threshold:
                    matches.add(wm_id)
                    break  # Found a match, no need to check other relevant items

        return matches

    def calculate_over_time(
        self,
        wm_snapshots: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate WM-P/R metrics over multiple time snapshots.

        Useful for analyzing how Working Memory quality evolves during
        a conversation or task.

        Args:
            wm_snapshots: List of snapshots, each with:
                - "timestamp": datetime or comparable
                - "working_memory_items": List[str]
                - "relevant_items": List[str]
                - "embeddings": Optional dict with "wm" and "relevant" keys

        Returns:
            Dict with:
                - "mean_f1": Average F1 over all snapshots
                - "mean_precision": Average precision
                - "mean_recall": Average recall
                - "f1_trend": List of F1 values over time
                - "precision_trend": List of precision values
                - "recall_trend": List of recall values
        """
        if not wm_snapshots:
            return {
                "mean_f1": 0.0,
                "mean_precision": 0.0,
                "mean_recall": 0.0,
                "f1_trend": [],
                "precision_trend": [],
                "recall_trend": [],
                "num_snapshots": 0,
            }

        f1_values = []
        precision_values = []
        recall_values = []

        for snapshot in wm_snapshots:
            wm_items = snapshot.get("working_memory_items", [])
            relevant = snapshot.get("relevant_items", [])

            embeddings = snapshot.get("embeddings", {})
            wm_emb = embeddings.get("wm")
            rel_emb = embeddings.get("relevant")

            # Calculate for this snapshot
            self.calculate(
                working_memory_items=wm_items,
                relevant_items=relevant,
                working_memory_embeddings=wm_emb,
                relevant_embeddings=rel_emb,
            )

            metadata = self.get_metadata()
            f1_values.append(metadata["f1_score"])
            precision_values.append(metadata["precision"])
            recall_values.append(metadata["recall"])

        return {
            "mean_f1": float(np.mean(f1_values)),
            "mean_precision": float(np.mean(precision_values)),
            "mean_recall": float(np.mean(recall_values)),
            "f1_trend": f1_values,
            "precision_trend": precision_values,
            "recall_trend": recall_values,
            "num_snapshots": len(wm_snapshots),
            "f1_std": float(np.std(f1_values)),
            "precision_std": float(np.std(precision_values)),
            "recall_std": float(np.std(recall_values)),
        }
