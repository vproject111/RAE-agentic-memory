"""
Dynamics Metrics - Evolution of Memory Over Time

These metrics analyze how memory changes and evolves:
- Memory Drift Index (MDI): Semantic drift in memory content
- Retention Curve: How well memory is retained over time
- Reflection Gain Score (RG): Quality improvement from reflection
- Compression Fidelity Ratio (CFR): Information preservation during compression
"""

from typing import List

import numpy as np
from numpy.typing import NDArray

from .base import MathMetricBase, MemorySnapshot, cosine_distance, normalize_vector


class MemoryDriftIndex(MathMetricBase):
    """
    Memory Drift Index (MDI)

    Measures semantic drift in memory content between two snapshots.

    Formula: MDI = cosine_distance(mean_embedding_t0, mean_embedding_t1)

    Low MDI = stable memory content
    High MDI = significant content changes

    Range: 0.0 (no drift) to 2.0 (complete reversal)
    Typical good value: < 0.3 (stable with gradual evolution)
    """

    def __init__(self):
        super().__init__(
            name="memory_drift_index",
            description="Semantic drift in memory content over time",
        )

    def calculate(
        self,
        snapshot_t0: MemorySnapshot,
        snapshot_t1: MemorySnapshot,
    ) -> float:
        """
        Calculate MDI between two snapshots.

        Args:
            snapshot_t0: Earlier snapshot
            snapshot_t1: Later snapshot

        Returns:
            MDI value (0.0 to 2.0)
        """
        if len(snapshot_t0.embeddings) == 0 or len(snapshot_t1.embeddings) == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "memories_t0": 0,
                "memories_t1": 0,
            }
            return 0.0

        # Calculate mean embeddings (centroid of memory space)
        mean_emb_t0 = np.mean(snapshot_t0.embeddings, axis=0)
        mean_emb_t1 = np.mean(snapshot_t1.embeddings, axis=0)

        # Calculate cosine distance
        mdi = cosine_distance(mean_emb_t0, mean_emb_t1)

        self._last_value = mdi
        self._last_metadata = {
            "memories_t0": snapshot_t0.num_memories,
            "memories_t1": snapshot_t1.num_memories,
            "time_delta_seconds": (
                snapshot_t1.timestamp - snapshot_t0.timestamp
            ).total_seconds(),
        }

        return mdi


class RetentionCurve(MathMetricBase):
    """
    Retention Curve

    Measures how well memory is retained over multiple time points.

    We track MRR (Mean Reciprocal Rank) at different time points and calculate
    the area under the retention curve (AUC).

    High AUC = good long-term retention
    Low AUC = rapid memory degradation

    Range: 0.0 (no retention) to 1.0 (perfect retention)
    """

    def __init__(self):
        super().__init__(
            name="retention_curve",
            description="Memory retention quality over time",
        )

    def calculate(
        self,
        time_points: List[float],
        mrr_values: List[float],
    ) -> float:
        """
        Calculate retention curve AUC.

        Args:
            time_points: List of time points (in seconds or arbitrary units)
            mrr_values: MRR values at each time point

        Returns:
            Area under retention curve (0.0 to 1.0)
        """
        if len(time_points) < 2 or len(mrr_values) < 2:
            self._last_value = 0.0
            self._last_metadata = {
                "num_points": len(time_points),
                "reason": "Need at least 2 time points",
            }
            return 0.0

        if len(time_points) != len(mrr_values):
            raise ValueError("time_points and mrr_values must have same length")

        # Sort by time
        sorted_pairs = sorted(zip(time_points, mrr_values))
        times, mrrs = zip(*sorted_pairs)

        # Calculate AUC using trapezoidal rule
        auc = 0.0
        for i in range(len(times) - 1):
            width = times[i + 1] - times[i]
            height = (mrrs[i] + mrrs[i + 1]) / 2.0
            auc += width * height

        # Normalize by time range
        time_range = times[-1] - times[0]
        if time_range > 0:
            normalized_auc = auc / time_range
        else:
            normalized_auc = mrrs[0]  # Single point case

        self._last_value = normalized_auc
        self._last_metadata = {
            "num_points": len(times),
            "time_range": time_range,
            "initial_mrr": mrrs[0],
            "final_mrr": mrrs[-1],
            "retention_decay": mrrs[0] - mrrs[-1],
        }

        return float(normalized_auc)


class ReflectionGainScore(MathMetricBase):
    """
    Reflection Gain Score (RG)

    Measures quality improvement from reflection process.

    Formula: RG = MRR_after_reflection - MRR_before_reflection

    Positive RG = reflection improved memory quality
    Negative RG = reflection degraded quality (rare, indicates problem)
    Zero RG = no effect

    Range: -1.0 to 1.0
    Typical good value: > 0.1 (measurable improvement)
    """

    def __init__(self):
        super().__init__(
            name="reflection_gain_score",
            description="Quality improvement from reflection",
        )

    def calculate(
        self,
        mrr_before: float,
        mrr_after: float,
        tokens_used: int = 0,
    ) -> float:
        """
        Calculate reflection gain.

        Args:
            mrr_before: MRR before reflection
            mrr_after: MRR after reflection
            tokens_used: Tokens consumed by reflection (for cost analysis)

        Returns:
            Reflection gain (-1.0 to 1.0)
        """
        rg = mrr_after - mrr_before

        self._last_value = rg
        self._last_metadata = {
            "mrr_before": mrr_before,
            "mrr_after": mrr_after,
            "tokens_used": tokens_used,
            "gain_per_1k_tokens": (rg / tokens_used * 1000) if tokens_used > 0 else 0.0,
        }

        return rg


class CompressionFidelityRatio(MathMetricBase):
    """
    Compression Fidelity Ratio (CFR)

    Measures how well compressed/summarized memory preserves semantic meaning.

    Formula: CFR = cosine_similarity(original_embedding, compressed_embedding)

    High CFR = compression preserves meaning well
    Low CFR = compression loses significant information

    Range: 0.0 (total information loss) to 1.0 (perfect preservation)
    Typical good value: > 0.8
    """

    def __init__(self):
        super().__init__(
            name="compression_fidelity_ratio",
            description="Information preservation during compression",
        )

    def calculate(
        self,
        original_embeddings: List[NDArray[np.float32]],
        compressed_embeddings: List[NDArray[np.float32]],
    ) -> float:
        """
        Calculate CFR for a set of memories.

        Args:
            original_embeddings: Original memory embeddings
            compressed_embeddings: Compressed/summarized embeddings

        Returns:
            Average CFR across all memories (0.0 to 1.0)
        """
        if len(original_embeddings) == 0 or len(compressed_embeddings) == 0:
            self._last_value = 0.0
            self._last_metadata = {
                "num_memories": 0,
                "reason": "No embeddings provided",
            }
            return 0.0

        if len(original_embeddings) != len(compressed_embeddings):
            raise ValueError(
                "original_embeddings and compressed_embeddings must have same length"
            )

        # Calculate cosine similarity for each pair
        similarities = []
        for orig, comp in zip(original_embeddings, compressed_embeddings):
            # Normalize vectors
            orig_norm = normalize_vector(orig)
            comp_norm = normalize_vector(comp)

            # Calculate similarity
            sim = float(np.dot(orig_norm, comp_norm))
            similarities.append(sim)

        # Average CFR
        cfr = float(np.mean(similarities))

        self._last_value = cfr
        self._last_metadata = {
            "num_memories": len(similarities),
            "min_fidelity": float(np.min(similarities)),
            "max_fidelity": float(np.max(similarities)),
            "std_fidelity": float(np.std(similarities)),
        }

        return cfr
