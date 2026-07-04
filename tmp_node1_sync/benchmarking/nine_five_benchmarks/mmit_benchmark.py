"""
MMIT - Multi-Layer Memory Interference Test

Tests for interference and contamination between RAE memory layers:
- Episodic Memory (short-term)
- Working Memory (active processing)
- Semantic Memory (knowledge + graph)
- Long-Term Memory (persistent storage)

Detects:
- Memory leakage between layers
- Cross-contamination events
- Layer isolation violations
- Unintended information flow

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


class MemoryLayer(Enum):
    """RAE Memory Layer types."""

    EPISODIC = "episodic"
    WORKING = "working"
    SEMANTIC = "semantic"
    LTM = "ltm"

    @property
    def description(self) -> str:
        descriptions = {
            "episodic": "Short-term episodic memory",
            "working": "Active working memory",
            "semantic": "Semantic memory with knowledge graph",
            "ltm": "Long-term persistent memory",
        }
        return descriptions.get(self.value, "Unknown")


@dataclass
class LayerMemory:
    """Memory item within a specific layer."""

    id: str
    content: str
    embedding: NDArray[np.float32]
    layer: MemoryLayer
    timestamp: datetime
    origin_layer: MemoryLayer  # Original layer (for tracking leakage)
    agent_id: str = "default_agent"
    session_id: str = "default_session"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContaminationEvent:
    """Records a detected contamination/leakage event."""

    event_id: str
    source_layer: MemoryLayer
    target_layer: MemoryLayer
    memory_id: str
    content_hash: str
    timestamp: datetime
    similarity_score: float
    event_type: str  # "leakage", "contamination", "cross_reference", "cross_agent_contamination"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerIsolationScore:
    """Isolation score for a specific layer."""

    layer: MemoryLayer
    isolation_score: float  # 0-1, 1 = perfect isolation
    leakage_in: int  # Memories leaked INTO this layer
    leakage_out: int  # Memories leaked FROM this layer
    contamination_sources: Dict[str, int] = field(default_factory=dict)


@dataclass
class MMITResults:
    """Results from MMIT benchmark."""

    benchmark_name: str = "MMIT"
    version: str = "1.0.0"

    # Primary metrics
    interference_score: float = 0.0  # 0-1, 0 = no interference
    layer_isolation: Dict[str, float] = field(default_factory=dict)
    contamination_events: List[Dict[str, Any]] = field(default_factory=list)

    # Detailed metrics
    total_operations: int = 0
    cross_layer_transfers: int = 0
    legitimate_transfers: int = 0
    illegitimate_leakages: int = 0
    blocked_attacks: int = 0  # Number of blocked cross-agent attempts

    # Per-layer analysis
    layer_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Interference matrix (layer x layer)
    interference_matrix: List[List[float]] = field(default_factory=list)

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
                "interference_score": self.interference_score,
                "layer_isolation": self.layer_isolation,
                "contamination_events_count": len(self.contamination_events),
                "blocked_attacks": self.blocked_attacks,
            },
            "detailed_metrics": {
                "total_operations": self.total_operations,
                "cross_layer_transfers": self.cross_layer_transfers,
                "legitimate_transfers": self.legitimate_transfers,
                "illegitimate_leakages": self.illegitimate_leakages,
                "blocked_attacks": self.blocked_attacks,
            },
            "layer_stats": self.layer_stats,
            "interference_matrix": self.interference_matrix,
            "contamination_events": self.contamination_events[:100],  # Limit for output
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
        }


class MMITBenchmark:
    """
    Multi-Layer Memory Interference Test (MMIT)

    Tests isolation and interference between RAE's 4 memory layers:
    1. Episodic Memory - Short-term recent events
    2. Working Memory - Active task context
    3. Semantic Memory - Knowledge graph and concepts
    4. Long-Term Memory - Persistent storage

    Key measurements:
    - Layer isolation: How well each layer keeps its data separate
    - Leakage detection: Unintended data flow between layers
    - Cross-contamination: Data corruption from other layers
    - Interference score: Overall measure of unwanted interactions

    Mathematical Framework:
    - Interference Score = sum(leaked_memories) / sum(all_memories)
    - Layer Isolation = 1 - (leakage_in + leakage_out) / (2 * layer_size)
    - Contamination Rate = contamination_events / total_operations

    Example:
        >>> mmit = MMITBenchmark(embedding_dim=384)
        >>> results = mmit.run(num_operations=5000)
        >>> print(f"Interference: {results.interference_score:.4f}")
        >>> print(f"Isolation: {results.layer_isolation}")
    """

    # Legitimate transfer paths (allowed data flow)
    LEGITIMATE_TRANSFERS = {
        (
            MemoryLayer.EPISODIC,
            MemoryLayer.WORKING,
        ): True,  # Recent events to active context
        (
            MemoryLayer.WORKING,
            MemoryLayer.SEMANTIC,
        ): True,  # Processed info to knowledge
        (MemoryLayer.WORKING, MemoryLayer.LTM): True,  # Important info to long-term
        (
            MemoryLayer.SEMANTIC,
            MemoryLayer.WORKING,
        ): True,  # Retrieved knowledge to context
        (MemoryLayer.LTM, MemoryLayer.WORKING): True,  # Retrieved memories to context
        (MemoryLayer.SEMANTIC, MemoryLayer.LTM): True,  # Knowledge consolidation
    }

    def __init__(
        self,
        embedding_dim: int = 384,
        similarity_threshold: float = 0.97,
        seed: Optional[int] = 42,
    ):
        """
        Initialize MMIT benchmark.

        Args:
            embedding_dim: Dimensionality of embeddings
            similarity_threshold: Threshold for detecting similar content (leakage)
            seed: Random seed for reproducibility
        """
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold
        self.seed = seed

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # Layer storage
        self.layers: Dict[MemoryLayer, Dict[str, LayerMemory]] = {
            layer: {} for layer in MemoryLayer
        }

        # Content tracking (for detecting duplicates/leakage)
        self.content_hashes: Dict[str, Set[MemoryLayer]] = {}

        # Events
        self.contamination_events: List[ContaminationEvent] = []

        # Statistics
        self.operations = 0
        self.transfers = 0
        self.legitimate_transfers = 0
        self.illegitimate_leakages = 0
        self.blocked_attacks = 0

    def _generate_embedding(
        self, content: str, noise: float = 0.0
    ) -> NDArray[np.float32]:
        """Generate embedding for content."""
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

    def _content_hash(self, content: str) -> str:
        """Generate hash for content tracking."""
        return hashlib.md5(content.encode()).hexdigest()

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

    def _check_for_leakage(
        self,
        memory: LayerMemory,
        target_layer: MemoryLayer,
    ) -> Optional[ContaminationEvent]:
        """
        Check if adding memory to target_layer constitutes leakage.

        Leakage is detected when:
        1. Very similar content exists in another layer
        2. The transfer path is not legitimate
        3. Or it violates agent isolation boundaries
        """
        content_hash = self._content_hash(memory.content)

        # Check if this content exists in other layers
        for other_layer, layer_memories in self.layers.items():
            if other_layer == target_layer:
                continue

            for other_id, other_mem in layer_memories.items():
                sim = self._cosine_similarity(memory.embedding, other_mem.embedding)

                if sim >= self.similarity_threshold:
                    # High similarity detected - check if legitimate
                    transfer_path = (other_layer, target_layer)
                    is_legitimate = self.LEGITIMATE_TRANSFERS.get(transfer_path, False)

                    # Strict Isolation Check: Must belong to same agent/session
                    is_cross_agent = (
                        other_mem.agent_id != memory.agent_id
                        or other_mem.session_id != memory.session_id
                    )

                    if not is_legitimate or is_cross_agent:
                        # Illegitimate leakage detected!
                        event_type = "leakage"
                        if is_cross_agent:
                            event_type = "cross_agent_contamination"

                        event = ContaminationEvent(
                            event_id=hashlib.md5(
                                f"{memory.id}_{other_id}_{time.time()}".encode()
                            ).hexdigest()[:16],
                            source_layer=other_layer,
                            target_layer=target_layer,
                            memory_id=memory.id,
                            content_hash=content_hash,
                            timestamp=datetime.now(),
                            similarity_score=sim,
                            event_type=event_type,
                            metadata={
                                "source_memory_id": other_id,
                                "similarity": sim,
                                "source_agent": other_mem.agent_id,
                                "target_agent": memory.agent_id,
                            },
                        )
                        return event

        return None

    def _add_to_layer(
        self,
        content: str,
        layer: MemoryLayer,
        agent_id: str = "agent_1",
        session_id: str = "session_1",
        check_leakage: bool = True,
    ) -> Tuple[Optional[LayerMemory], Optional[ContaminationEvent]]:
        """
        Add content to a memory layer.

        Returns:
            Tuple of (memory, contamination_event if detected).
            Memory is None if operation was blocked by guard.
        """
        memory_id = hashlib.md5(
            f"{content}_{layer.value}_{time.time()}".encode()
        ).hexdigest()[:16]
        embedding = self._generate_embedding(content)

        memory = LayerMemory(
            id=memory_id,
            content=content,
            embedding=embedding,
            layer=layer,
            timestamp=datetime.now(),
            origin_layer=layer,
            agent_id=agent_id,
            session_id=session_id,
        )

        event = None
        if check_leakage:
            event = self._check_for_leakage(memory, layer)
            if event:
                # GUARD LAYER SIMULATION
                # Block ALL illegitimate operations (cross-agent OR wrong flow)
                # This simulates a strict system that enforces data flow rules
                self.blocked_attacks += 1
                return None, event

        self.layers[layer][memory_id] = memory
        self.operations += 1

        # Track content hash
        content_hash = self._content_hash(content)
        if content_hash not in self.content_hashes:
            self.content_hashes[content_hash] = set()
        self.content_hashes[content_hash].add(layer)

        return memory, event

    def _transfer_memory(
        self,
        memory_id: str,
        source_layer: MemoryLayer,
        target_layer: MemoryLayer,
    ) -> Optional[ContaminationEvent]:
        """
        Transfer memory between layers.

        Returns contamination event if transfer is illegitimate.
        """
        if memory_id not in self.layers[source_layer]:
            return None

        source_memory = self.layers[source_layer][memory_id]
        transfer_path = (source_layer, target_layer)
        is_legitimate = self.LEGITIMATE_TRANSFERS.get(transfer_path, False)

        # Create new memory in target layer
        new_id = hashlib.md5(
            f"{memory_id}_{target_layer.value}_{time.time()}".encode()
        ).hexdigest()[:16]
        new_memory = LayerMemory(
            id=new_id,
            content=source_memory.content,
            embedding=source_memory.embedding.copy(),
            layer=target_layer,
            timestamp=datetime.now(),
            origin_layer=source_memory.origin_layer,
            agent_id=source_memory.agent_id,
            session_id=source_memory.session_id,
            metadata={"transferred_from": source_layer.value},
        )

        self.layers[target_layer][new_id] = new_memory
        self.transfers += 1

        event = None
        if is_legitimate:
            self.legitimate_transfers += 1
        else:
            self.illegitimate_leakages += 1
            event = ContaminationEvent(
                event_id=hashlib.md5(
                    f"{memory_id}_{source_layer}_{target_layer}_{time.time()}".encode()
                ).hexdigest()[:16],
                source_layer=source_layer,
                target_layer=target_layer,
                memory_id=memory_id,
                content_hash=self._content_hash(source_memory.content),
                timestamp=datetime.now(),
                similarity_score=1.0,  # Exact copy
                event_type="contamination",
            )
            self.contamination_events.append(event)

        return event

    def _calculate_layer_isolation(self, layer: MemoryLayer) -> LayerIsolationScore:
        """Calculate isolation score for a layer."""
        layer_memories = self.layers[layer]
        if not layer_memories:
            return LayerIsolationScore(
                layer=layer,
                isolation_score=1.0,
                leakage_in=0,
                leakage_out=0,
            )

        leakage_in = 0
        leakage_out = 0
        contamination_sources: Dict[str, int] = {}

        # Check for memories that originated from other layers (leakage in)
        for mem_id, memory in layer_memories.items():
            if memory.origin_layer != layer:
                leakage_in += 1
                source = memory.origin_layer.value
                contamination_sources[source] = contamination_sources.get(source, 0) + 1

        # Check for this layer's content in other layers (leakage out)
        our_contents = {self._content_hash(m.content) for m in layer_memories.values()}
        for other_layer, other_memories in self.layers.items():
            if other_layer == layer:
                continue
            for other_mem in other_memories.values():
                if self._content_hash(other_mem.content) in our_contents:
                    leakage_out += 1

        # Calculate isolation score
        total_memories = len(layer_memories)
        if total_memories == 0:
            isolation_score = 1.0
        else:
            leakage_ratio = (leakage_in + leakage_out) / (2 * total_memories)
            isolation_score = max(0.0, 1.0 - leakage_ratio)

        return LayerIsolationScore(
            layer=layer,
            isolation_score=isolation_score,
            leakage_in=leakage_in,
            leakage_out=leakage_out,
            contamination_sources=contamination_sources,
        )

    def _calculate_interference_matrix(self) -> List[List[float]]:
        """
        Calculate interference matrix between all layer pairs.

        Returns NxN matrix where matrix[i][j] = interference from layer i to layer j.
        """
        layers = list(MemoryLayer)
        n = len(layers)
        matrix = [[0.0] * n for _ in range(n)]

        for i, source_layer in enumerate(layers):
            source_memories = self.layers[source_layer]
            if not source_memories:
                continue

            source_contents = {
                self._content_hash(m.content) for m in source_memories.values()
            }

            for j, target_layer in enumerate(layers):
                if i == j:
                    continue

                target_memories = self.layers[target_layer]
                if not target_memories:
                    continue

                # Count shared content
                shared = 0
                for mem in target_memories.values():
                    if self._content_hash(mem.content) in source_contents:
                        # Only count as interference if it belongs to same agent context
                        # Different agents having same content is fine (coincidence)
                        # BUT same agent having duplicated content in wrong layers is interference
                        source_mem_id = [
                            mid
                            for mid, m in source_memories.items()
                            if self._content_hash(m.content)
                            == self._content_hash(mem.content)
                        ][0]
                        source_mem = source_memories[source_mem_id]

                        if source_mem.agent_id == mem.agent_id:
                            shared += 1

                # Interference = shared / target_size
                matrix[i][j] = shared / len(target_memories)

        return matrix

    def _simulate_operations(
        self,
        num_operations: int,
        verbose: bool = True,
    ):
        """
        Simulate multi-layer memory operations.

        Generates realistic workload with:
        - Layer-specific content creation
        - Legitimate and illegitimate transfers
        - Random access patterns
        """
        # Content templates per layer
        layer_templates = {
            MemoryLayer.EPISODIC: [
                "User asked about {topic} at {time}",
                "Event: {action} occurred in context {ctx}",
                "Recent interaction: {detail}",
            ],
            MemoryLayer.WORKING: [
                "Current task: processing {task}",
                "Active context: {context}",
                "Working on: {item}",
            ],
            MemoryLayer.SEMANTIC: [
                "Concept: {concept} relates to {related}",
                "Knowledge: {fact} is {value}",
                "Relationship: {entity1} {rel} {entity2}",
            ],
            MemoryLayer.LTM: [
                "Long-term fact: {fact}",
                "Historical: {event} happened at {time}",
                "Persistent memory: {content}",
            ],
        }

        topics = ["AI", "memory", "learning", "reasoning", "graphs", "search"]
        actions = ["query", "update", "create", "delete", "link"]
        concepts = ["entity", "relation", "node", "edge", "path", "tree"]

        # Simulate 3 different agents to test isolation
        agents = ["agent_alpha", "agent_beta", "agent_gamma"]

        for op in range(num_operations):
            # Pick active agent for this op
            current_agent = random.choice(agents)
            current_session = f"session_{current_agent}_{op % 5}"  # Rotate sessions

            # Randomly select operation type
            op_type = random.choice(["create", "create", "create", "transfer", "leak"])

            if op_type == "create":
                # Create new content in a random layer
                layer = random.choice(list(MemoryLayer))
                template = random.choice(layer_templates[layer])
                content = template.format(
                    topic=random.choice(topics),
                    time=op,
                    action=random.choice(actions),
                    ctx=random.randint(1, 100),
                    detail=f"detail_{op}",
                    task=f"task_{op % 50}",
                    context=f"context_{op % 20}",
                    item=f"item_{op % 30}",
                    concept=random.choice(concepts),
                    related=random.choice(concepts),
                    fact=f"fact_{op % 100}",
                    value=random.random(),
                    entity1=f"entity_{op % 10}",
                    entity2=f"entity_{(op + 5) % 10}",
                    rel=random.choice(["is", "has", "links", "contains"]),
                    event=f"event_{op % 50}",
                    content=f"content_{op}",
                )
                self._add_to_layer(
                    content, layer, agent_id=current_agent, session_id=current_session
                )

            elif op_type == "transfer":
                # Legitimate transfer between layers
                valid_paths = list(self.LEGITIMATE_TRANSFERS.keys())
                if valid_paths:
                    source, target = random.choice(valid_paths)
                    # Filter memories belonging to current agent
                    source_memories = [
                        mid
                        for mid, m in self.layers[source].items()
                        if m.agent_id == current_agent
                    ]

                    if source_memories:
                        mem_id = random.choice(source_memories)
                        self._transfer_memory(mem_id, source, target)

            elif op_type == "leak":
                # Simulate potential leakage (same content in different layer)
                # Pick a random memory and add similar content to wrong layer
                all_memories = [
                    (layer, mem)
                    for layer, mems in self.layers.items()
                    for mem in mems.values()
                ]
                if all_memories:
                    source_layer, source_mem = random.choice(all_memories)

                    # Scenario A: Leak to wrong layer (same agent)
                    # Scenario B: Leak to wrong agent (critical violation!)

                    target_agent = current_agent
                    if random.random() < 0.3:  # 30% chance of cross-agent leak attempt
                        target_agent = random.choice(
                            [a for a in agents if a != source_mem.agent_id]
                        )

                    # Pick a non-adjacent layer (illegitimate target)
                    illegitimate_targets = [
                        layer
                        for layer in MemoryLayer
                        if layer != source_layer
                        and (source_layer, layer) not in self.LEGITIMATE_TRANSFERS
                    ]

                    if illegitimate_targets:
                        target = random.choice(illegitimate_targets)
                        # Add slightly modified content
                        leaked_content = source_mem.content + f" (leaked at {op})"
                        self._add_to_layer(
                            leaked_content,
                            target,
                            agent_id=target_agent,
                            session_id=current_session,
                            check_leakage=True,
                        )

            if verbose and (op + 1) % 1000 == 0:
                print(f"  Operation {op + 1:,}/{num_operations:,}")

    def run(
        self,
        num_operations: int = 5000,
        verbose: bool = True,
    ) -> MMITResults:
        """
        Run the MMIT benchmark.

        Args:
            num_operations: Number of operations to simulate
            verbose: Whether to print progress

        Returns:
            MMITResults with all metrics
        """
        start_time = datetime.now()

        if verbose:
            print("Starting MMIT Benchmark")
            print(f"  Operations: {num_operations}")
            print(f"  Similarity threshold: {self.similarity_threshold}")
            print("=" * 60)

        # Reset state
        self.layers = {layer: {} for layer in MemoryLayer}
        self.content_hashes.clear()
        self.contamination_events.clear()
        self.operations = 0
        self.transfers = 0
        self.legitimate_transfers = 0
        self.illegitimate_leakages = 0
        self.blocked_attacks = 0

        # Run simulation
        self._simulate_operations(num_operations, verbose)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate layer isolation scores
        layer_isolation = {}
        layer_stats = {}
        for layer in MemoryLayer:
            isolation = self._calculate_layer_isolation(layer)
            layer_isolation[layer.value] = isolation.isolation_score
            layer_stats[layer.value] = {
                "isolation_score": isolation.isolation_score,
                "leakage_in": isolation.leakage_in,
                "leakage_out": isolation.leakage_out,
                "memory_count": len(self.layers[layer]),
                "contamination_sources": isolation.contamination_sources,
            }

        # Calculate interference matrix
        interference_matrix = self._calculate_interference_matrix()

        # Calculate overall interference score
        total_memories = sum(len(mems) for mems in self.layers.values())
        if total_memories > 0:
            interference_score = self.illegitimate_leakages / total_memories
        else:
            interference_score = 0.0

        # Cap at 1.0
        interference_score = min(1.0, interference_score)

        results = MMITResults(
            interference_score=interference_score,
            layer_isolation=layer_isolation,
            contamination_events=[
                {
                    "event_id": e.event_id,
                    "source_layer": e.source_layer.value,
                    "target_layer": e.target_layer.value,
                    "memory_id": e.memory_id,
                    "similarity_score": e.similarity_score,
                    "event_type": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self.contamination_events
            ],
            total_operations=self.operations,
            cross_layer_transfers=self.transfers,
            legitimate_transfers=self.legitimate_transfers,
            illegitimate_leakages=self.illegitimate_leakages,
            blocked_attacks=self.blocked_attacks,
            layer_stats=layer_stats,
            interference_matrix=interference_matrix,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
        )

        if verbose:
            print("=" * 60)
            print("MMIT Results:")
            print(f"  Interference Score: {results.interference_score:.4f}")
            print(f"  Contamination Events: {len(self.contamination_events)}")
            print(f"  Blocked Attacks: {self.blocked_attacks}")
            print(f"  Legitimate Transfers: {self.legitimate_transfers}")
            print(f"  Illegitimate Leakages: {self.illegitimate_leakages}")
            print("\n  Layer Isolation Scores:")
            for layer_name, score in layer_isolation.items():
                print(f"    {layer_name}: {score:.4f}")
            print(f"\n  Duration: {duration:.2f}s")

        return results

    def save_results(
        self,
        results: MMITResults,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save benchmark results to JSON."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "results" / "nine_five"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"mmit_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        return output_file


def main():
    """Run MMIT benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run MMIT benchmark")
    parser.add_argument(
        "--operations",
        type=int,
        default=5000,
        help="Number of operations to simulate",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.97,
        help="Threshold for leakage detection",
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

    benchmark = MMITBenchmark(
        similarity_threshold=args.similarity_threshold,
        seed=args.seed,
    )

    results = benchmark.run(num_operations=args.operations)

    output_dir = Path(args.output) if args.output else None
    output_file = benchmark.save_results(results, output_dir)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
