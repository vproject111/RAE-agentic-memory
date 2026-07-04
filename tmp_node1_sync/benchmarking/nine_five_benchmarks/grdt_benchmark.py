"""
GRDT - Graph Reasoning Depth Test

Tests multi-hop reasoning capabilities on knowledge graphs:
- Chain-of-thought depth verification
- Multi-step inference accuracy
- Graph traversal coherence
- Reasoning path consistency

Generates knowledge graphs with relationships at depths 5-10 and tests
the agent's ability to perform correct multi-hop reasoning.

Research-grade implementation for academic evaluation of RAE memory systems.
"""

import hashlib
import json
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from rae_core.math.reasoning import ReasoningController, ReasoningPath


class RelationType(Enum):
    """Types of relationships in the knowledge graph."""

    IS_A = "is_a"  # Hierarchical
    HAS_PART = "has_part"  # Compositional
    CAUSES = "causes"  # Causal
    REQUIRES = "requires"  # Dependency
    LOCATED_IN = "located_in"  # Spatial
    RELATED_TO = "related_to"  # General association

    @property
    def inverse(self) -> "RelationType":
        """Get inverse relationship type."""
        inverses = {
            "is_a": RelationType.IS_A,  # Parent
            "has_part": RelationType.HAS_PART,  # Part of
            "causes": RelationType.CAUSES,  # Caused by
            "requires": RelationType.REQUIRES,  # Required by
            "located_in": RelationType.LOCATED_IN,  # Contains
            "related_to": RelationType.RELATED_TO,
        }
        return inverses.get(self.value, RelationType.RELATED_TO)


@dataclass
class GraphNode:
    """Node in the knowledge graph."""

    id: str
    name: str
    node_type: str
    embedding: NDArray[np.float32]
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Edge in the knowledge graph."""

    source_id: str
    target_id: str
    relation: RelationType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningQuery:
    """A multi-hop reasoning query."""

    query_id: str
    start_node: str
    end_node: str
    expected_path: List[str]  # Expected node IDs in path
    expected_relations: List[RelationType]  # Relations along path
    depth: int
    query_type: str  # "path_finding", "inference", "chain_of_thought"
    natural_language: str  # Human-readable query


@dataclass
class ReasoningResult:
    """Result of a reasoning query."""

    query_id: str
    found_path: List[str]
    found_relations: List[str]
    correct: bool
    depth_reached: int
    path_coherent: bool
    reasoning_steps: List[Dict[str, Any]]
    latency_ms: float


@dataclass
class GRDTResults:
    """Results from GRDT benchmark."""

    benchmark_name: str = "GRDT"
    version: str = "1.0.0"

    # Primary metrics
    max_reasoning_depth: int = 0
    reasoning_accuracy: Dict[int, float] = field(
        default_factory=dict
    )  # Depth -> accuracy
    chain_coherence: float = 0.0

    # Detailed metrics
    total_queries: int = 0
    successful_queries: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    avg_path_length: float = 0.0
    deviation_stats: Dict[str, Any] = field(default_factory=dict)

    # Per-depth analysis
    depth_stats: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    # Query results
    query_results: List[Dict[str, Any]] = field(default_factory=list)

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
                "max_reasoning_depth": self.max_reasoning_depth,
                "reasoning_accuracy": self.reasoning_accuracy,
                "chain_coherence": self.chain_coherence,
            },
            "detailed_metrics": {
                "total_queries": self.total_queries,
                "successful_queries": self.successful_queries,
                "total_nodes": self.total_nodes,
                "total_edges": self.total_edges,
                "avg_path_length": self.avg_path_length,
                "deviation_stats": self.deviation_stats,
            },
            "depth_stats": self.depth_stats,
            "query_results": self.query_results[:50],  # Limit output
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
        }


class GRDTBenchmark:
    """
    Graph Reasoning Depth Test (GRDT)

    Creates knowledge graphs with multi-level relationships (depth 5-10)
    and tests reasoning capabilities through:

    1. Path Finding - Can the agent find the correct path between nodes?
    2. Multi-hop Inference - Can it answer questions requiring N-hop reasoning?
    3. Chain Coherence - Is the reasoning chain logically consistent?

    Mathematical Framework:
    - Max Depth = max(correct_depth) over all queries
    - Accuracy@d = correct_queries@depth_d / total_queries@depth_d
    - Chain Coherence = sum(coherent_paths) / total_paths

    Example:
        >>> grdt = GRDTBenchmark()
        >>> results = grdt.run(num_queries=100, max_depth=8)
        >>> print(f"Max Depth: {results.max_reasoning_depth}")
        >>> print(f"Chain Coherence: {results.chain_coherence:.4f}")
    """

    def __init__(
        self,
        embedding_dim: int = 384,
        seed: Optional[int] = 42,
        controller_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize GRDT benchmark.

        Args:
            embedding_dim: Dimensionality of node embeddings
            seed: Random seed for reproducibility
            controller_config: Configuration for ReasoningController
        """
        self.embedding_dim = embedding_dim
        self.seed = seed

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # Graph storage
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency: Dict[str, List[Tuple[str, RelationType]]] = defaultdict(list)

        # Queries
        self.queries: List[ReasoningQuery] = []
        self.results: List[ReasoningResult] = []

        # Reasoning Controller
        self.controller = ReasoningController(**(controller_config or {}))

    def _generate_embedding(self, content: str) -> NDArray[np.float32]:
        """Generate embedding for content."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        local_seed = int(content_hash[:8], 16)

        rng = np.random.RandomState(local_seed)
        embedding = rng.randn(self.embedding_dim).astype(np.float32)

        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _create_node(
        self,
        name: str,
        node_type: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> GraphNode:
        """Create a new graph node."""
        node_id = hashlib.md5(f"{name}_{node_type}".encode()).hexdigest()[:12]

        node = GraphNode(
            id=node_id,
            name=name,
            node_type=node_type,
            embedding=self._generate_embedding(name),
            attributes=attributes or {},
        )

        self.nodes[node_id] = node
        return node

    def _create_edge(
        self,
        source_id: str,
        target_id: str,
        relation: RelationType,
        weight: float = 1.0,
    ) -> Optional[GraphEdge]:
        """Create an edge between nodes."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
        )

        self.edges.append(edge)
        self.adjacency[source_id].append((target_id, relation))

        return edge

    def _build_hierarchical_graph(
        self,
        depth: int = 10,
        branching_factor: int = 3,
        cross_links: float = 0.1,
    ):
        """
        Build a hierarchical knowledge graph.

        Creates a tree-like structure with cross-links for more complex reasoning.
        Edges are bidirectional to allow traversal in both directions.
        """
        # Domain-specific node types for realistic graph
        node_types = ["concept", "entity", "property", "action", "state"]
        relations = list(RelationType)

        # Create root nodes
        root_nodes = []
        domains = ["science", "technology", "nature", "society", "abstract"]
        for domain in domains:
            node = self._create_node(f"root_{domain}", "domain", {"level": 0})
            root_nodes.append(node)

        # Build tree levels
        current_level = root_nodes
        all_nodes_by_level: Dict[int, List[GraphNode]] = {0: root_nodes}

        for level in range(1, depth + 1):
            next_level = []

            for parent in current_level:
                # Create children
                num_children = random.randint(1, branching_factor)
                for i in range(num_children):
                    child_name = f"{parent.name}_child_{i}_L{level}"
                    child_type = random.choice(node_types)
                    child = self._create_node(child_name, child_type, {"level": level})
                    next_level.append(child)

                    # Create bidirectional edges (parent -> child and child -> parent)
                    relation = random.choice(relations[:4])  # Use structural relations
                    self._create_edge(parent.id, child.id, relation)
                    # Add reverse edge for bidirectional traversal
                    self._create_edge(child.id, parent.id, relation.inverse)

            all_nodes_by_level[level] = next_level
            current_level = next_level

        # Add cross-links (makes reasoning more complex)
        all_nodes = list(self.nodes.values())
        num_cross_links = int(len(all_nodes) * cross_links)

        for _ in range(num_cross_links):
            source = random.choice(all_nodes)
            target = random.choice(all_nodes)
            if source.id != target.id:
                relation = random.choice(relations)
                self._create_edge(source.id, target.id, relation)
                # Bidirectional cross-links
                self._create_edge(target.id, source.id, relation.inverse)

    def _find_path_bfs(
        self,
        start_id: str,
        end_id: str,
        max_depth: int = 10,
    ) -> Optional[Tuple[List[str], List[RelationType]]]:
        """Find path between two nodes using BFS."""
        if start_id not in self.nodes or end_id not in self.nodes:
            return None

        if start_id == end_id:
            return [start_id], []

        # BFS with path tracking
        queue: deque[tuple[str, list[str], list[RelationType]]] = deque(
            [(start_id, [start_id], [])]
        )
        visited = {start_id}

        while queue:
            current_id, path, relations = queue.popleft()

            if len(path) > max_depth + 1:
                continue

            for neighbor_id, relation in self.adjacency.get(current_id, []):
                if neighbor_id == end_id:
                    return path + [neighbor_id], relations + [relation]

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append(
                        (
                            neighbor_id,
                            path + [neighbor_id],
                            relations + [relation],
                        )
                    )

        return None

    def _generate_reasoning_queries(
        self,
        num_queries: int,
        min_depth: int = 3,
        max_depth: int = 10,
    ):
        """Generate multi-hop reasoning queries."""
        self.queries.clear()

        all_nodes = list(self.nodes.values())
        query_count = 0
        attempts = 0
        max_attempts = num_queries * 10

        while query_count < num_queries and attempts < max_attempts:
            attempts += 1

            # Pick random start and end
            start_node = random.choice(all_nodes)
            end_node = random.choice(all_nodes)

            if start_node.id == end_node.id:
                continue

            # Find path
            result = self._find_path_bfs(start_node.id, end_node.id, max_depth)
            if result is None:
                continue

            path, relations = result
            depth = len(path) - 1

            if depth < min_depth or depth > max_depth:
                continue

            # Create query
            query = ReasoningQuery(
                query_id=f"q_{query_count:04d}",
                start_node=start_node.id,
                end_node=end_node.id,
                expected_path=path,
                expected_relations=relations,
                depth=depth,
                query_type="path_finding",
                natural_language=self._generate_natural_query(
                    start_node, end_node, depth
                ),
            )

            self.queries.append(query)
            query_count += 1

    def _generate_natural_query(
        self,
        start: GraphNode,
        end: GraphNode,
        depth: int,
    ) -> str:
        """Generate natural language query."""
        templates = [
            f"How is '{start.name}' related to '{end.name}' through {depth} steps?",
            f"Find the reasoning path from '{start.name}' to '{end.name}'",
            f"What connects '{start.name}' and '{end.name}' ({depth} hops)?",
            f"Explain the relationship chain between '{start.name}' and '{end.name}'",
        ]
        return random.choice(templates)

    def _simulate_reasoning(
        self,
        query: ReasoningQuery,
        noise_level: float = 0.1,
        beam_width: int = 3,
    ) -> ReasoningResult:
        """
        Simulate agent reasoning on a query using ReasoningController and Beam Search.

        Includes realistic noise/errors to test robustness.
        """
        start_time = time.time()

        # Initialize Beam with one path
        initial_path = ReasoningPath()
        initial_path.add_step(query.start_node, f"Start at {query.start_node}")
        beam = [initial_path]

        # Track best completed path
        best_completed_path: Optional[ReasoningPath] = None

        # Limit max steps to prevent infinite loops
        max_steps = query.depth + 5

        tokens_per_step = 50

        for _ in range(max_steps):
            next_beam = []

            for path in beam:
                current_node = path.nodes[-1]

                # Check with Controller
                should_continue = self.controller.should_continue_reasoning(
                    current_depth=path.depth - 1,
                    uncertainty=path.uncertainty,
                    tokens_used=path.tokens_used,
                )

                if not should_continue:
                    continue

                # Stop if we reached the target
                if current_node == query.end_node:
                    if (
                        best_completed_path is None
                        or path.uncertainty > best_completed_path.uncertainty
                    ):
                        best_completed_path = path
                    continue

                # Get expected next step (for simulation/ground truth)
                # Note: In beam search, we might deviate from expected path but still reach goal.
                # However, for this benchmark we primarily check if we follow the expected chain.
                expected_next = None
                # We want the node that comes AFTER the current path
                # Current path has N nodes. Next node is at index N in expected_path.
                if len(path.nodes) < len(query.expected_path):
                    expected_next = query.expected_path[len(path.nodes)]

                # Expand neighbors
                neighbors = self.adjacency.get(current_node, [])
                if not neighbors:
                    continue

                # Sample a few moves (Beam Expansion)
                # In real agent, this would be LLM generating N thoughts.
                # Here we simulate by picking random neighbors + correct one if lucky.

                # Expansion logic:
                # 1. Always try to include "correct" move if we are on track (with noise prob)
                # 2. Add some random moves

                candidates = []

                # Locate correct move
                correct_move = None
                for n_node, n_rel in neighbors:
                    if n_node == expected_next:
                        correct_move = (n_node, n_rel)
                        break

                # Decide if we find the correct move (noise check)
                if correct_move and random.random() > noise_level:
                    candidates.append(correct_move)

                # Add distractions
                random_candidates = random.sample(
                    neighbors, min(len(neighbors), beam_width)
                )
                for rc in random_candidates:
                    if rc != correct_move:
                        candidates.append(rc)

                # Process candidates
                for next_node, relation in candidates:
                    new_path = ReasoningPath(
                        nodes=path.nodes.copy(),
                        steps=path.steps.copy(),
                        uncertainty=path.uncertainty,
                        contradictions=path.contradictions.copy(),
                        metadata=path.metadata.copy(),
                        tokens_used=path.tokens_used,
                    )

                    # Uncertainty penalty for deviation
                    uncertainty_drop = 0.0
                    if next_node != expected_next:
                        uncertainty_drop = -0.1

                    new_path.add_step(
                        node_id=next_node,
                        description=f"Moved to {next_node} via {relation.value}",
                        uncertainty_delta=uncertainty_drop,
                        tokens=tokens_per_step,
                    )

                    next_beam.append(new_path)

            # Prune Beam using Controller
            if not next_beam:
                break

            # Filter contradictory
            valid_paths = self.controller.prune_contradictory_paths(next_beam)

            # Sort by uncertainty and keep top K
            valid_paths.sort(key=lambda p: p.uncertainty, reverse=True)
            beam = valid_paths[:beam_width]

            if not beam and best_completed_path:
                break

        # Select best path
        final_path = (
            best_completed_path
            if best_completed_path
            else (beam[0] if beam else initial_path)
        )

        # Construct result based on final_path
        # Reconstruct reasoning steps for validation
        reasoning_steps = []
        found_relations = []

        # Skip start node in loop
        for i in range(1, len(final_path.nodes)):
            curr = final_path.nodes[i - 1]
            next_n = final_path.nodes[i]
            # Find relation (hacky lookup)
            rel_val = "unknown"
            for desc in final_path.steps:
                if f"Moved to {next_n} via" in desc:
                    rel_val = desc.split(" via ")[1]
                    break

            found_relations.append(rel_val)

            # Check correctness against query expectation
            is_correct = False
            expected_n = None
            if i < len(query.expected_path):
                expected_n = query.expected_path[i]
                if next_n == expected_n:
                    is_correct = True

            reasoning_steps.append(
                {
                    "step": i,
                    "from": curr,
                    "to": next_n,
                    "relation": rel_val,
                    "expected_next": expected_n,
                    "correct": is_correct,
                    "uncertainty": final_path.uncertainty,
                }
            )

        # Final correctness
        correct = final_path.nodes[-1] == query.end_node and len(
            final_path.nodes
        ) == len(query.expected_path)

        coherent = all(step["correct"] for step in reasoning_steps)
        latency = (time.time() - start_time) * 1000

        return ReasoningResult(
            query_id=query.query_id,
            found_path=final_path.nodes,
            found_relations=found_relations,
            correct=correct,
            depth_reached=len(final_path.nodes) - 1,
            path_coherent=coherent,
            reasoning_steps=reasoning_steps,
            latency_ms=latency,
        )

    def run(
        self,
        num_queries: int = 100,
        min_depth: int = 3,
        max_depth: int = 10,
        graph_depth: int = 10,
        branching_factor: int = 3,
        noise_level: float = 0.1,
        verbose: bool = True,
    ) -> GRDTResults:
        """
        Run the GRDT benchmark.

        Args:
            num_queries: Number of reasoning queries to generate
            min_depth: Minimum path depth for queries
            max_depth: Maximum path depth for queries
            graph_depth: Depth of the generated graph
            branching_factor: Average children per node
            noise_level: Error probability in reasoning simulation
            verbose: Whether to print progress

        Returns:
            GRDTResults with all metrics
        """
        start_time = datetime.now()

        if verbose:
            print("Starting GRDT Benchmark")
            print(f"  Queries: {num_queries}")
            print(f"  Depth range: {min_depth}-{max_depth}")
            print(f"  Noise level: {noise_level}")
            print("=" * 60)

        # Reset state
        self.nodes.clear()
        self.edges.clear()
        self.adjacency.clear()
        self.queries.clear()
        self.results.clear()

        # Build graph
        if verbose:
            print("Building knowledge graph...")
        self._build_hierarchical_graph(
            depth=graph_depth,
            branching_factor=branching_factor,
        )
        if verbose:
            print(f"  Nodes: {len(self.nodes)}, Edges: {len(self.edges)}")

        # Generate queries
        if verbose:
            print("Generating reasoning queries...")
        self._generate_reasoning_queries(num_queries, min_depth, max_depth)
        if verbose:
            print(f"  Generated {len(self.queries)} queries")

        # Run reasoning
        if verbose:
            print("Running reasoning tests...")

        for i, query in enumerate(self.queries):
            result = self._simulate_reasoning(query, noise_level)
            self.results.append(result)

            if verbose and (i + 1) % 20 == 0:
                print(f"  Completed {i + 1}/{len(self.queries)} queries")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate metrics
        # Accuracy per depth
        depth_correct: Dict[int, int] = defaultdict(int)
        depth_total: Dict[int, int] = defaultdict(int)
        max_correct_depth = 0
        coherent_count = 0
        total_path_length = 0

        for query, result in zip(self.queries, self.results):
            depth = query.depth
            depth_total[depth] += 1
            if result.correct:
                depth_correct[depth] += 1
                max_correct_depth = max(max_correct_depth, depth)
            if result.path_coherent:
                coherent_count += 1
            total_path_length += result.depth_reached

        # Reasoning accuracy per depth
        reasoning_accuracy = {}
        depth_stats = {}
        for depth in sorted(depth_total.keys()):
            total = depth_total[depth]
            correct = depth_correct[depth]
            accuracy = correct / total if total > 0 else 0.0
            reasoning_accuracy[depth] = accuracy
            depth_stats[depth] = {
                "total_queries": total,
                "correct_queries": correct,
                "accuracy": accuracy,
            }

        # Chain coherence
        chain_coherence = coherent_count / len(self.results) if self.results else 0.0

        # Average path length
        avg_path_length = total_path_length / len(self.results) if self.results else 0.0

        # Deviation Stats
        total_steps = 0
        total_deviations = 0
        deviation_depths = []

        for r in self.results:
            for step in r.reasoning_steps:
                total_steps += 1
                if not step["correct"]:
                    total_deviations += 1
                    deviation_depths.append(step["step"])

        deviation_stats = {
            "total_steps": total_steps,
            "total_deviations": total_deviations,
            "deviation_rate": (
                total_deviations / total_steps if total_steps > 0 else 0.0
            ),
            "avg_deviation_depth": (
                float(np.mean(deviation_depths)) if deviation_depths else 0.0
            ),
        }

        results = GRDTResults(
            max_reasoning_depth=max_correct_depth,
            reasoning_accuracy=reasoning_accuracy,
            chain_coherence=chain_coherence,
            total_queries=len(self.queries),
            successful_queries=sum(1 for r in self.results if r.correct),
            total_nodes=len(self.nodes),
            total_edges=len(self.edges),
            avg_path_length=avg_path_length,
            deviation_stats=deviation_stats,
            depth_stats=depth_stats,
            query_results=[
                {
                    "query_id": r.query_id,
                    "correct": r.correct,
                    "depth_reached": r.depth_reached,
                    "path_coherent": r.path_coherent,
                    "latency_ms": r.latency_ms,
                }
                for r in self.results
            ],
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
        )

        if verbose:
            print("=" * 60)
            print("GRDT Results:")
            print(f"  Max Reasoning Depth: {results.max_reasoning_depth}")
            print(f"  Chain Coherence: {results.chain_coherence:.4f}")
            print(
                f"  Successful Queries: {results.successful_queries}/{results.total_queries}"
            )
            print("\n  Accuracy by Depth:")
            for depth, accuracy in sorted(reasoning_accuracy.items()):
                print(f"    Depth {depth}: {accuracy:.4f}")
            print(f"\n  Duration: {duration:.2f}s")

        return results

    def run_curriculum(self, noise_level: float = 0.1) -> Dict[str, GRDTResults]:
        """
        Run a curriculum of reasoning scenarios with increasing complexity.

        Scenarios:
        - Simple causal chains (depth 3-5)
        - Planning scenarios (depth 5-8)
        - Complex multi-stage (depth 8-12)

        Args:
            noise_level: Noise level for simulation

        Returns:
            Dictionary of results keyed by scenario name
        """
        scenarios = [
            ("simple_causal", 3, 5),
            ("planning", 5, 8),
            ("complex_multistage", 8, 12),
        ]

        results = {}
        print("\nStarting GRDT Curriculum...")

        for name, min_d, max_d in scenarios:
            print(f"\n>> Scenario: {name} (Depth {min_d}-{max_d})")

            # Configure controller for this scenario
            # Ensure max depth is sufficient
            self.controller.max_depth = max_d + 2
            # Reset stats between scenarios
            self.controller.reset_stats()

            res = self.run(
                num_queries=50,
                min_depth=min_d,
                max_depth=max_d,
                noise_level=noise_level,
                verbose=True,
            )
            res.benchmark_name = f"GRDT_{name}"
            results[name] = res

            # Print Controller Stats
            print("Controller Stats:")
            for k, v in self.controller.get_stats().items():
                if v > 0:
                    print(f"  {k}: {v}")

        return results

    def save_results(
        self,
        results: GRDTResults,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save benchmark results to JSON."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "results" / "nine_five"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"grdt_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        return output_file


def main():
    """Run GRDT benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run GRDT benchmark")
    parser.add_argument(
        "--queries",
        type=int,
        default=100,
        help="Number of reasoning queries",
    )
    parser.add_argument(
        "--min-depth",
        type=int,
        default=3,
        help="Minimum path depth",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=10,
        help="Maximum path depth",
    )
    parser.add_argument(
        "--noise",
        type=float,
        default=0.1,
        help="Noise level in reasoning",
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

    benchmark = GRDTBenchmark(seed=args.seed)

    results = benchmark.run(
        num_queries=args.queries,
        min_depth=args.min_depth,
        max_depth=args.max_depth,
        noise_level=args.noise,
    )

    output_dir = Path(args.output) if args.output else None
    output_file = benchmark.save_results(results, output_dir)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
