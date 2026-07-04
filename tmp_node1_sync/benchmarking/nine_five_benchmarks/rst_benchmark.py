"""
RST - Reflective Stability Test

Tests the stability and robustness of agent insights under noisy input conditions.

Measures:
- Insight stability at different noise levels (10%, 30%, 50%)
- Consistency of generated reflections
- Noise threshold where insights break down
- Quality degradation curves

Research-grade implementation for academic evaluation of RAE memory systems.
"""

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from numpy.typing import NDArray


class NoiseType(Enum):
    """Types of noise to inject."""

    GAUSSIAN = "gaussian"  # Random noise in embeddings
    ADVERSARIAL = "adversarial"  # Misleading information
    MISSING = "missing"  # Dropped information
    CONTRADICTORY = "contradictory"  # Conflicting data


@dataclass
class Insight:
    """A generated insight/reflection."""

    id: str
    content: str
    embedding: NDArray[np.float32]
    source_memories: List[str]
    confidence: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NoiseConfig:
    """Configuration for noise injection."""

    noise_type: NoiseType
    noise_level: float  # 0.0 to 1.0
    description: str


@dataclass
class StabilityMeasurement:
    """Measurement of insight stability at a noise level."""

    noise_level: float
    noise_type: NoiseType
    original_insight: Insight
    noisy_insight: Insight
    semantic_similarity: float
    content_similarity: float
    confidence_delta: float
    is_stable: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RSTResults:
    """Results from RST benchmark."""

    benchmark_name: str = "RST"
    version: str = "1.0.0"

    # Primary metrics
    stability_score: Dict[float, float] = field(
        default_factory=dict
    )  # noise_level -> stability
    insight_consistency: float = 0.0
    noise_threshold: float = 0.0  # Level where insights break down

    # Detailed metrics
    total_insights: int = 0
    stable_insights: int = 0
    degradation_curve: List[Tuple[float, float]] = field(default_factory=list)

    # Per-noise-type analysis
    noise_type_analysis: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Individual measurements
    measurements: List[Dict[str, Any]] = field(default_factory=list)

    # Timing
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "version": self.version,
            "primary_metrics": {
                "stability_score": self.stability_score,
                "insight_consistency": self.insight_consistency,
                "noise_threshold": self.noise_threshold,
            },
            "detailed_metrics": {
                "total_insights": self.total_insights,
                "stable_insights": self.stable_insights,
                "degradation_curve": self.degradation_curve,
            },
            "noise_type_analysis": self.noise_type_analysis,
            "measurements": self.measurements[:50],  # Limit output
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
        }


class RSTBenchmark:
    """
    Reflective Stability Test (RST)

    Tests how stable agent insights are when input data is noisy or corrupted.

    Noise Levels:
    - 10%: Light noise - insights should remain highly stable
    - 30%: Moderate noise - some degradation acceptable
    - 50%: Heavy noise - testing robustness limits

    Noise Types:
    - Gaussian: Random perturbations to embeddings
    - Adversarial: Intentionally misleading information
    - Missing: Dropped data points
    - Contradictory: Conflicting information

    Mathematical Framework:
    - Stability Score = mean(cosine_sim(insight_clean, insight_noisy))
    - Insight Consistency = var(insight_embeddings) across noise levels
    - Noise Threshold = min(noise_level) where stability < 0.5

    Example:
        >>> rst = RSTBenchmark()
        >>> results = rst.run(num_insights=50)
        >>> print(f"Noise Threshold: {results.noise_threshold:.2f}")
        >>> print(f"Consistency: {results.insight_consistency:.4f}")
    """

    # Standard noise levels to test
    NOISE_LEVELS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]

    def __init__(
        self,
        embedding_dim: int = 384,
        stability_threshold: float = 0.7,
        seed: Optional[int] = 42,
    ):
        """
        Initialize RST benchmark.

        Args:
            embedding_dim: Dimensionality of embeddings
            stability_threshold: Threshold for considering insight "stable"
            seed: Random seed for reproducibility
        """
        self.embedding_dim = embedding_dim
        self.stability_threshold = stability_threshold
        self.seed = seed

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # Storage
        self.source_memories: Dict[str, Dict[str, Any]] = {}
        self.insights: Dict[str, Insight] = {}
        self.measurements: List[StabilityMeasurement] = []

    def _generate_embedding(
        self, content: str, noise: float = 0.0
    ) -> NDArray[np.float32]:
        """Generate embedding for content with optional noise."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        local_seed = int(content_hash[:8], 16)

        rng = np.random.RandomState(local_seed)
        embedding = rng.randn(self.embedding_dim).astype(np.float32)

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        if noise > 0:
            noise_vector = (
                np.random.randn(self.embedding_dim).astype(np.float32) * noise
            )
            embedding = embedding + noise_vector
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm

        return embedding

    def _cosine_similarity(
        self,
        a: NDArray[np.float32],
        b: NDArray[np.float32],
    ) -> float:
        """Calculate cosine similarity."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def _generate_source_memories(self, num_memories: int = 100):
        """Generate synthetic source memories for reflection."""
        topics = [
            "user preferences",
            "system behavior",
            "task patterns",
            "error occurrences",
            "success metrics",
            "interaction history",
            "knowledge updates",
            "performance data",
            "feedback signals",
        ]

        now = datetime.now()

        for i in range(num_memories):
            memory_id = f"mem_{i:04d}"
            topic = random.choice(topics)
            content = f"Memory about {topic}: observation_{i} with data_{random.randint(1, 100)}"

            # Random age between 0 and 60 days
            age_days = random.randint(0, 60)
            timestamp = datetime.fromtimestamp(now.timestamp() - age_days * 86400)

            # Confidence correlates with recency (older = less confident/stale)
            # This simulates real world where older data might be less reliable
            base_confidence = random.uniform(0.5, 1.0)

            self.source_memories[memory_id] = {
                "id": memory_id,
                "content": content,
                "embedding": self._generate_embedding(content),
                "importance": random.random(),
                "topic": topic,
                "timestamp": timestamp,
                "confidence": base_confidence,
            }

    def _retrieve_memories(
        self, query_topic: str, n: int = 5, noise_level: float = 0.0
    ) -> List[str]:
        """
        Simulate noise-aware retrieval.

        If noise_level > 0.5, boosts recent and high-confidence memories.
        """
        candidates = []
        now = datetime.now()

        # Calculate scores
        for mem_id, mem in self.source_memories.items():
            # Base similarity (simulated 1.0 if topic matches, else random low)
            if mem["topic"] == query_topic:
                similarity = random.uniform(0.8, 0.99)
            else:
                similarity = random.uniform(0.0, 0.3)

            # SIMULATE NOISE DEGRADATION:
            # High noise scrambles vector similarity
            if noise_level > 0.0:
                noise_factor = random.uniform(-noise_level, noise_level)
                similarity = max(0.0, min(1.0, similarity + noise_factor))

            score = similarity

            # Apply Noise-Aware Boosting (Task 4.3 logic)
            if noise_level > 0.5:
                # Recency boost
                age_days = (now - mem["timestamp"]).days
                recency_boost = 1.0 / (1.0 + age_days / 7.0)

                # Confidence boost
                confidence_boost = mem["confidence"]

                # Intensity of boost depends on noise
                noise_intensity = (noise_level - 0.5) / 0.5

                # Stronger boost to overcome noise degradation
                score *= 1.0 + recency_boost * noise_intensity * 2.0
                score *= 1.0 + confidence_boost * noise_intensity * 1.5

            candidates.append((mem_id, score))

        # Sort and pick top N
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidates[:n]]

    def _generate_insight(
        self,
        source_ids: List[str],
        noise_level: float = 0.0,
        noise_type: NoiseType = NoiseType.GAUSSIAN,
    ) -> Insight:
        """
        Generate an insight from source memories.

        Simulates the reflection process with optional noise injection.
        """
        # Gather source content
        source_contents = []
        source_embeddings = []

        for mem_id in source_ids:
            if mem_id in self.source_memories:
                mem = self.source_memories[mem_id]
                source_contents.append(mem["content"])
                source_embeddings.append(mem["embedding"])

        if not source_contents:
            # Fallback if no sources found
            source_contents = ["Empty source"]
            source_embeddings = [np.zeros(self.embedding_dim, dtype=np.float32)]

        # Generate insight content
        # Deterministic content based on sources to allow comparison
        # We use hash of sorted source IDs to simulate "same input -> same output"
        source_hash = hashlib.md5("".join(sorted(source_ids)).encode()).hexdigest()
        insight_content = (
            f"Insight derived from {len(source_ids)} sources (Hash: {source_hash[:8]})"
        )

        # Compute base embedding (mean of sources)
        base_embedding = np.mean(source_embeddings, axis=0).astype(np.float32)

        # Apply noise based on type
        if noise_level > 0:
            if noise_type == NoiseType.GAUSSIAN:
                noise = (
                    np.random.randn(self.embedding_dim).astype(np.float32) * noise_level
                )
                base_embedding = base_embedding + noise

            elif noise_type == NoiseType.ADVERSARIAL:
                # Adversarial: push embedding in opposite direction
                adversarial = -base_embedding * noise_level
                base_embedding = base_embedding + adversarial

            elif noise_type == NoiseType.MISSING:
                # Missing: zero out some dimensions
                mask = np.random.random(self.embedding_dim) > noise_level
                base_embedding = base_embedding * mask

            elif noise_type == NoiseType.CONTRADICTORY:
                # Contradictory: mix with random unrelated embedding
                random_emb = np.random.randn(self.embedding_dim).astype(np.float32)
                random_emb = random_emb / np.linalg.norm(random_emb)
                base_embedding = (
                    1 - noise_level
                ) * base_embedding + noise_level * random_emb

        # Normalize
        norm = np.linalg.norm(base_embedding)
        if norm > 0:
            base_embedding = base_embedding / norm

        # Generate confidence (decreases with noise)
        base_confidence = random.uniform(0.7, 0.95)
        confidence = base_confidence * (1.0 - noise_level * 0.5)

        insight = Insight(
            id=hashlib.md5(f"{insight_content}_{time.time()}".encode()).hexdigest()[
                :16
            ],
            content=insight_content,
            embedding=base_embedding,
            source_memories=source_ids,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={
                "noise_level": noise_level,
                "noise_type": noise_type.value,
            },
        )

        return insight

    def _measure_stability(
        self,
        original: Insight,
        noisy: Insight,
        noise_level: float,
        noise_type: NoiseType,
    ) -> StabilityMeasurement:
        """Measure stability between original and noisy insight."""
        # Semantic similarity (embedding-based)
        semantic_sim = self._cosine_similarity(original.embedding, noisy.embedding)

        # Content similarity (source overlap)
        content_sim = self._jaccard_similarity(
            set(original.source_memories),
            set(noisy.source_memories),
        )

        # Confidence delta
        confidence_delta = abs(original.confidence - noisy.confidence)

        # Is it stable?
        is_stable = semantic_sim >= self.stability_threshold

        return StabilityMeasurement(
            noise_level=noise_level,
            noise_type=noise_type,
            original_insight=original,
            noisy_insight=noisy,
            semantic_similarity=semantic_sim,
            content_similarity=content_sim,
            confidence_delta=confidence_delta,
            is_stable=is_stable,
        )

    def run(
        self,
        num_insights: int = 50,
        num_source_memories: int = 100,
        noise_types: Optional[List[NoiseType]] = None,
        verbose: bool = True,
    ) -> RSTResults:
        """
        Run the RST benchmark.

        Args:
            num_insights: Number of insights to generate and test
            num_source_memories: Number of source memories to generate
            noise_types: Noise types to test (default: all types)
            verbose: Whether to print progress

        Returns:
            RSTResults with all metrics
        """
        start_time = datetime.now()

        if noise_types is None:
            noise_types = list(NoiseType)

        if verbose:
            print("Starting RST Benchmark")
            print(f"  Insights: {num_insights}")
            print(f"  Noise levels: {self.NOISE_LEVELS}")
            print(f"  Noise types: {[nt.value for nt in noise_types]}")
            print("=" * 60)

        # Reset state
        self.source_memories.clear()
        self.insights.clear()
        self.measurements.clear()

        # Generate source memories
        if verbose:
            print("Generating source memories...")
        self._generate_source_memories(num_source_memories)

        # Generate and test insights
        if verbose:
            print("Testing insight stability...")

        stability_by_level: Dict[float, List[float]] = {
            level: [] for level in self.NOISE_LEVELS
        }
        stability_by_type: Dict[NoiseType, Dict[float, List[float]]] = {
            nt: {level: [] for level in self.NOISE_LEVELS} for nt in noise_types
        }

        # Topics to query
        topics = list(set(m["topic"] for m in self.source_memories.values()))

        for i in range(num_insights):
            # Select random topic
            topic = random.choice(topics)

            # Use retrieval to find sources (Clean Baseline)
            source_ids = self._retrieve_memories(topic, n=5, noise_level=0.0)

            # Generate clean insight
            clean_insight = self._generate_insight(source_ids, noise_level=0.0)
            self.insights[clean_insight.id] = clean_insight

            # Test at each noise level and type
            for noise_type in noise_types:
                for noise_level in self.NOISE_LEVELS:
                    if noise_level == 0.0:
                        # Compare clean to itself (baseline)
                        noisy_insight = clean_insight
                    else:
                        # Retrieve again with noise-aware logic (if implemented)
                        # This tests if the retrieval adapts to noise
                        noisy_source_ids = self._retrieve_memories(
                            topic, n=5, noise_level=noise_level
                        )

                        noisy_insight = self._generate_insight(
                            noisy_source_ids,
                            noise_level=noise_level,
                            noise_type=noise_type,
                        )

                    measurement = self._measure_stability(
                        clean_insight,
                        noisy_insight,
                        noise_level,
                        noise_type,
                    )
                    self.measurements.append(measurement)

                    stability_by_level[noise_level].append(
                        measurement.semantic_similarity
                    )
                    stability_by_type[noise_type][noise_level].append(
                        measurement.semantic_similarity
                    )

            if verbose and (i + 1) % 10 == 0:
                print(f"  Tested {i + 1}/{num_insights} insights")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate metrics
        # Stability score per noise level
        stability_score = {}
        degradation_curve = []
        for level in sorted(self.NOISE_LEVELS):
            sims = stability_by_level[level]
            avg_stability = float(np.mean(sims)) if sims else 0.0
            stability_score[level] = avg_stability
            degradation_curve.append((level, avg_stability))

        # Find noise threshold (where stability drops below 0.5)
        noise_threshold = 1.0  # Default: never breaks
        for level, stability in sorted(degradation_curve):
            if stability < 0.5:
                noise_threshold = level
                break

        # Insight consistency (variance across noise levels)
        all_stabilities = [m.semantic_similarity for m in self.measurements]
        insight_consistency = (
            1.0 - float(np.std(all_stabilities)) if all_stabilities else 0.0
        )
        insight_consistency = max(0.0, insight_consistency)

        # Per-noise-type analysis
        noise_type_analysis = {}
        for noise_type in noise_types:
            type_stabilities = []
            for level in self.NOISE_LEVELS:
                sims = stability_by_type[noise_type][level]
                if sims:
                    type_stabilities.extend(sims)

            noise_type_analysis[noise_type.value] = {
                "mean_stability": (
                    float(np.mean(type_stabilities)) if type_stabilities else 0.0
                ),
                "std_stability": (
                    float(np.std(type_stabilities)) if type_stabilities else 0.0
                ),
                "min_stability": (
                    float(np.min(type_stabilities)) if type_stabilities else 0.0
                ),
            }

        # Count stable insights
        stable_count = sum(1 for m in self.measurements if m.is_stable)

        results = RSTResults(
            stability_score=stability_score,
            insight_consistency=insight_consistency,
            noise_threshold=noise_threshold,
            total_insights=num_insights,
            stable_insights=stable_count,
            degradation_curve=degradation_curve,
            noise_type_analysis=noise_type_analysis,
            measurements=[
                {
                    "noise_level": m.noise_level,
                    "noise_type": m.noise_type.value,
                    "semantic_similarity": m.semantic_similarity,
                    "content_similarity": m.content_similarity,
                    "confidence_delta": m.confidence_delta,
                    "is_stable": m.is_stable,
                }
                for m in self.measurements
            ],
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
        )

        if verbose:
            print("=" * 60)
            print("RST Results:")
            print(f"  Noise Threshold: {results.noise_threshold:.2f}")
            print(f"  Insight Consistency: {results.insight_consistency:.4f}")
            print(f"  Stable Measurements: {stable_count}/{len(self.measurements)}")
            print("\n  Stability by Noise Level:")
            for level, stability in sorted(stability_score.items()):
                print(f"    {level * 100:.0f}%: {stability:.4f}")
            print("\n  Noise Type Robustness:")
            for nt_val, stats in noise_type_analysis.items():
                print(f"    {nt_val}: mean={stats['mean_stability']:.4f}")
            print(f"\n  Duration: {duration:.2f}s")

        return results

    def save_results(
        self,
        results: RSTResults,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save benchmark results to JSON."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "results" / "nine_five"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"rst_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        return output_file


def main():
    """Run RST benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run RST benchmark")
    parser.add_argument(
        "--insights",
        type=int,
        default=50,
        help="Number of insights to test",
    )
    parser.add_argument(
        "--memories",
        type=int,
        default=100,
        help="Number of source memories",
    )
    parser.add_argument(
        "--stability-threshold",
        type=float,
        default=0.7,
        help="Threshold for stable insights",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory",
    )

    args = parser.parse_args()

    benchmark = RSTBenchmark(
        stability_threshold=args.stability_threshold,
        seed=args.seed,
    )

    results = benchmark.run(
        num_insights=args.insights,
        num_source_memories=args.memories,
    )

    output_dir = Path(args.output) if args.output else None
    output_file = benchmark.save_results(results, output_dir)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
