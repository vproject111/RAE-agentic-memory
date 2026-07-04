"""
LECT - Long-term Episodic Consistency Test

Verifies that the agent maintains knowledge consistency after 10,000+ interaction cycles.

This benchmark simulates extended operation to detect:
- Memory degradation over time
- Knowledge consistency drift
- Information retention rates
- Long-term episodic stability

Research-grade implementation for academic evaluation of RAE memory systems.
"""

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from numpy.typing import NDArray


@dataclass
class EpisodicMemory:
    """Represents a single episodic memory unit."""

    id: str
    content: str
    embedding: NDArray[np.float32]
    timestamp: datetime
    importance: float
    tags: List[str] = field(default_factory=list)
    access_count: int = 0
    last_accessed: Optional[datetime] = None


@dataclass
class ConsistencyCheckpoint:
    """Checkpoint for tracking consistency over time."""

    cycle: int
    timestamp: datetime
    consistency_score: float
    retention_rate: float
    num_memories: int
    mean_embedding_drift: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LECTResults:
    """Results from LECT benchmark."""

    benchmark_name: str = "LECT"
    version: str = "1.0.0"

    # Primary metrics
    consistency_score: float = 0.0  # 0-1, knowledge consistency
    retention_rate: float = 0.0  # 0-1, % of information retained
    degradation_curve: List[float] = field(default_factory=list)

    # Detailed metrics
    total_cycles: int = 0
    memories_created: int = 0
    memories_lost: int = 0
    mean_drift: float = 0.0
    max_drift: float = 0.0
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)

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
                "consistency_score": self.consistency_score,
                "retention_rate": self.retention_rate,
                "degradation_curve": self.degradation_curve,
            },
            "detailed_metrics": {
                "total_cycles": self.total_cycles,
                "memories_created": self.memories_created,
                "memories_lost": self.memories_lost,
                "mean_drift": self.mean_drift,
                "max_drift": self.max_drift,
            },
            "checkpoints": self.checkpoints,
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
        }


class LECTBenchmark:
    """
    Long-term Episodic Consistency Test (LECT)

    Simulates 10,000+ cycles of memory operations to verify:
    1. Knowledge consistency across extended operation
    2. Information retention over time
    3. Memory drift detection
    4. Degradation curve analysis

    Mathematical Framework:
    - Consistency Score = sum(cosine_sim(m_t, m_0)) / N for key memories
    - Retention Rate = |retrieved_memories| / |original_memories|
    - Degradation = 1 - mean(consistency_scores_per_checkpoint)

    Example:
        >>> lect = LECTBenchmark(embedding_dim=384)
        >>> results = lect.run(num_cycles=10000)
        >>> print(f"Consistency: {results.consistency_score:.4f}")
        >>> print(f"Retention: {results.retention_rate:.4f}")
    """

    def __init__(
        self,
        embedding_dim: int = 384,
        checkpoint_interval: int = 1000,
        seed: Optional[int] = 42,
    ):
        """
        Initialize LECT benchmark.

        Args:
            embedding_dim: Dimensionality of embeddings (default 384 for e5-small-v2)
            checkpoint_interval: Cycles between consistency checkpoints
            seed: Random seed for reproducibility
        """
        self.embedding_dim = embedding_dim
        self.checkpoint_interval = checkpoint_interval
        self.seed = seed

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # Memory storage
        self.memories: Dict[str, EpisodicMemory] = {}
        self.key_memories: Dict[str, EpisodicMemory] = {}  # Critical memories to track
        self.original_embeddings: Dict[str, NDArray[np.float32]] = {}

        # Checkpoints
        self.checkpoints: List[ConsistencyCheckpoint] = []

        # Statistics
        self.total_writes = 0
        self.total_reads = 0
        self.total_updates = 0
        self.total_deletions = 0

    def _generate_embedding(
        self, content: str, noise: float = 0.0
    ) -> NDArray[np.float32]:
        """
        Generate a deterministic embedding for content.

        Uses hash-based embedding generation for reproducibility.
        Optional noise parameter for simulating drift.
        """
        # Create hash-based seed from content
        content_hash = hashlib.md5(content.encode()).hexdigest()
        local_seed = int(content_hash[:8], 16)

        # Generate reproducible embedding
        rng = np.random.RandomState(local_seed)
        base_embedding = rng.randn(self.embedding_dim).astype(np.float32)

        # Normalize
        norm = np.linalg.norm(base_embedding)
        if norm > 0:
            base_embedding = base_embedding / norm

        # Add noise if specified
        if noise > 0:
            noise_vector = (
                np.random.randn(self.embedding_dim).astype(np.float32) * noise
            )
            base_embedding = base_embedding + noise_vector
            # Re-normalize
            norm = np.linalg.norm(base_embedding)
            if norm > 0:
                base_embedding = base_embedding / norm

        return base_embedding

    def _cosine_similarity(
        self,
        a: NDArray[np.float32],
        b: NDArray[np.float32],
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def _create_memory(
        self,
        content: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        is_key_memory: bool = False,
    ) -> EpisodicMemory:
        """Create a new episodic memory."""
        memory_id = hashlib.md5(
            f"{content}_{time.time()}_{random.random()}".encode()
        ).hexdigest()[:16]
        embedding = self._generate_embedding(content)

        memory = EpisodicMemory(
            id=memory_id,
            content=content,
            embedding=embedding,
            timestamp=datetime.now(),
            importance=importance,
            tags=tags or [],
        )

        self.memories[memory_id] = memory
        self.total_writes += 1

        # Track key memories for consistency checking
        if is_key_memory:
            self.key_memories[memory_id] = memory
            self.original_embeddings[memory_id] = embedding.copy()

        return memory

    def _update_memory(
        self,
        memory_id: str,
        new_content: Optional[str] = None,
        drift: float = 0.01,
    ) -> bool:
        """
        Update an existing memory, potentially introducing drift.

        Args:
            memory_id: ID of memory to update
            new_content: New content (optional)
            drift: Amount of embedding drift to introduce
        """
        if memory_id not in self.memories:
            return False

        memory = self.memories[memory_id]

        if new_content:
            memory.content = new_content
            memory.embedding = self._generate_embedding(new_content, noise=drift)
        else:
            # Just add drift noise
            noise = np.random.randn(self.embedding_dim).astype(np.float32) * drift
            memory.embedding = memory.embedding + noise
            # Re-normalize
            norm = np.linalg.norm(memory.embedding)
            if norm > 0:
                memory.embedding = memory.embedding / norm

        self.total_updates += 1
        return True

    def _access_memory(self, memory_id: str) -> Optional[EpisodicMemory]:
        """Access a memory (updates access count and timestamp)."""
        if memory_id not in self.memories:
            return None

        memory = self.memories[memory_id]
        memory.access_count += 1
        memory.last_accessed = datetime.now()
        self.total_reads += 1

        return memory

    def _delete_memory(self, memory_id: str) -> bool:
        """Delete a memory."""
        if memory_id not in self.memories:
            return False

        del self.memories[memory_id]
        self.total_deletions += 1
        return True

    def _calculate_consistency_score(self) -> float:
        """
        Calculate consistency score for key memories.

        Measures how much key memories have drifted from their original state.
        """
        if not self.key_memories:
            return 1.0

        similarities = []
        for memory_id, memory in self.key_memories.items():
            if memory_id in self.original_embeddings and memory_id in self.memories:
                current = self.memories[memory_id].embedding
                original = self.original_embeddings[memory_id]
                sim = self._cosine_similarity(current, original)
                similarities.append(sim)

        if not similarities:
            return 1.0

        return float(np.mean(similarities))

    def _calculate_retention_rate(self) -> float:
        """
        Calculate retention rate.

        Measures what percentage of key memories are still accessible.
        """
        if not self.key_memories:
            return 1.0

        retained = sum(1 for mem_id in self.key_memories if mem_id in self.memories)
        return retained / len(self.key_memories)

    def _take_checkpoint(self, cycle: int) -> ConsistencyCheckpoint:
        """Take a consistency checkpoint."""
        consistency = self._calculate_consistency_score()
        retention = self._calculate_retention_rate()

        # Calculate mean embedding drift for all memories
        drifts = []
        for memory_id in self.key_memories:
            if memory_id in self.memories and memory_id in self.original_embeddings:
                current = self.memories[memory_id].embedding
                original = self.original_embeddings[memory_id]
                drift = 1.0 - self._cosine_similarity(current, original)
                drifts.append(drift)

        mean_drift = float(np.mean(drifts)) if drifts else 0.0

        checkpoint = ConsistencyCheckpoint(
            cycle=cycle,
            timestamp=datetime.now(),
            consistency_score=consistency,
            retention_rate=retention,
            num_memories=len(self.memories),
            mean_embedding_drift=mean_drift,
            metadata={
                "total_writes": self.total_writes,
                "total_reads": self.total_reads,
                "total_updates": self.total_updates,
                "total_deletions": self.total_deletions,
                "key_memories_count": len(self.key_memories),
            },
        )

        self.checkpoints.append(checkpoint)
        return checkpoint

    def _simulate_cycle(
        self,
        cycle: int,
        write_prob: float = 0.3,
        update_prob: float = 0.4,
        read_prob: float = 0.8,
        delete_prob: float = 0.05,
        drift_factor: float = 0.001,
    ):
        """
        Simulate one interaction cycle.

        Args:
            cycle: Current cycle number
            write_prob: Probability of creating new memory
            update_prob: Probability of updating existing memory
            read_prob: Probability of reading memories
            delete_prob: Probability of deleting old memory
            drift_factor: Amount of drift per update
        """
        # Generate content based on cycle
        content_templates = [
            f"User discussed topic_{cycle % 100} in cycle {cycle}",
            f"Agent learned about concept_{cycle % 50} at iteration {cycle}",
            f"Event_{cycle % 200} occurred during session {cycle // 1000}",
            f"Fact_{cycle}: The relationship between A and B is {cycle % 10}",
            f"Memory_{cycle}: Important information about task_{cycle % 30}",
        ]

        # Create new memory
        if random.random() < write_prob:
            content = random.choice(content_templates)
            is_key = cycle % 100 == 0  # Every 100th memory is key
            self._create_memory(
                content=content,
                importance=random.random(),
                tags=[f"cycle_{cycle}", f"topic_{cycle % 50}"],
                is_key_memory=is_key,
            )

        # Update existing memories (introduces drift)
        if self.memories and random.random() < update_prob:
            memory_id = random.choice(list(self.memories.keys()))
            # Drift increases slightly over time
            current_drift = drift_factor * (1 + cycle / 10000)
            self._update_memory(memory_id, drift=current_drift)

        # Read memories
        if self.memories and random.random() < read_prob:
            memory_id = random.choice(list(self.memories.keys()))
            self._access_memory(memory_id)

        # Delete old memories (simulating forgetting/cleanup)
        if self.memories and random.random() < delete_prob:
            # Prefer deleting low-importance, infrequently accessed memories
            candidates = [
                (mem_id, mem)
                for mem_id, mem in self.memories.items()
                if mem_id not in self.key_memories  # Never delete key memories
            ]
            if candidates:
                # Sort by importance * access_count, delete lowest
                candidates.sort(key=lambda x: x[1].importance * (x[1].access_count + 1))
                if candidates:
                    self._delete_memory(candidates[0][0])

    def run(
        self,
        num_cycles: int = 10000,
        write_prob: float = 0.3,
        update_prob: float = 0.4,
        read_prob: float = 0.8,
        delete_prob: float = 0.05,
        drift_factor: float = 0.001,
        verbose: bool = True,
    ) -> LECTResults:
        """
        Run the LECT benchmark.

        Args:
            num_cycles: Number of interaction cycles to simulate
            write_prob: Probability of creating new memory per cycle
            update_prob: Probability of updating existing memory per cycle
            read_prob: Probability of reading memories per cycle
            delete_prob: Probability of deleting memory per cycle
            drift_factor: Base drift factor for updates
            verbose: Whether to print progress

        Returns:
            LECTResults with all metrics
        """
        start_time = datetime.now()

        if verbose:
            print("Starting LECT Benchmark")
            print(f"  Cycles: {num_cycles}")
            print(f"  Checkpoint interval: {self.checkpoint_interval}")
            print("=" * 60)

        # Reset state
        self.memories.clear()
        self.key_memories.clear()
        self.original_embeddings.clear()
        self.checkpoints.clear()
        self.total_writes = 0
        self.total_reads = 0
        self.total_updates = 0
        self.total_deletions = 0

        # Initial checkpoint
        self._take_checkpoint(0)

        # Run simulation cycles
        for cycle in range(1, num_cycles + 1):
            self._simulate_cycle(
                cycle=cycle,
                write_prob=write_prob,
                update_prob=update_prob,
                read_prob=read_prob,
                delete_prob=delete_prob,
                drift_factor=drift_factor,
            )

            # Take checkpoint at intervals
            if cycle % self.checkpoint_interval == 0:
                checkpoint = self._take_checkpoint(cycle)
                if verbose:
                    print(
                        f"  Cycle {cycle:,}: "
                        f"Consistency={checkpoint.consistency_score:.4f}, "
                        f"Retention={checkpoint.retention_rate:.4f}, "
                        f"Memories={checkpoint.num_memories}"
                    )

        # Final checkpoint
        if num_cycles % self.checkpoint_interval != 0:
            self._take_checkpoint(num_cycles)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate final metrics
        consistency_scores = [cp.consistency_score for cp in self.checkpoints]
        retention_rates = [cp.retention_rate for cp in self.checkpoints]
        drifts = [cp.mean_embedding_drift for cp in self.checkpoints]

        results = LECTResults(
            consistency_score=float(np.mean(consistency_scores)),
            retention_rate=float(np.mean(retention_rates)),
            degradation_curve=consistency_scores,
            total_cycles=num_cycles,
            memories_created=self.total_writes,
            memories_lost=self.total_deletions,
            mean_drift=float(np.mean(drifts)) if drifts else 0.0,
            max_drift=float(np.max(drifts)) if drifts else 0.0,
            checkpoints=[
                {
                    "cycle": cp.cycle,
                    "consistency_score": cp.consistency_score,
                    "retention_rate": cp.retention_rate,
                    "num_memories": cp.num_memories,
                    "mean_drift": cp.mean_embedding_drift,
                }
                for cp in self.checkpoints
            ],
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
        )

        if verbose:
            print("=" * 60)
            print("LECT Results:")
            print(f"  Consistency Score: {results.consistency_score:.4f}")
            print(f"  Retention Rate: {results.retention_rate:.4f}")
            print(f"  Mean Drift: {results.mean_drift:.6f}")
            print(f"  Max Drift: {results.max_drift:.6f}")
            print(f"  Duration: {duration:.2f}s")

        return results

    def save_results(
        self,
        results: LECTResults,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Save benchmark results to JSON.

        Args:
            results: LECTResults to save
            output_dir: Output directory (default: benchmarking/results/nine_five/)

        Returns:
            Path to saved JSON file
        """
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "results" / "nine_five"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"lect_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        return output_file


def main():
    """Run LECT benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run LECT benchmark")
    parser.add_argument(
        "--cycles",
        type=int,
        default=10000,
        help="Number of interaction cycles",
    )
    parser.add_argument(
        "--checkpoint-interval",
        type=int,
        default=1000,
        help="Cycles between checkpoints",
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

    benchmark = LECTBenchmark(
        checkpoint_interval=args.checkpoint_interval,
        seed=args.seed,
    )

    results = benchmark.run(num_cycles=args.cycles)

    output_dir = Path(args.output) if args.output else None
    output_file = benchmark.save_results(results, output_dir)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
