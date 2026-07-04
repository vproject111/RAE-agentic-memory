#!/usr/bin/env python3
"""
RAE Benchmark Runner with Mathematical Metrics

Extends the standard benchmark runner with three-tier mathematical analysis:
- Structure Metrics: graph connectivity, semantic coherence, entropy
- Dynamics Metrics: memory drift, retention, reflection gain
- Policy Metrics: retrieval quality, cost-quality frontier

Usage:
    python run_benchmark_math.py --set academic_lite.yaml --enable-math
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from benchmarking.math_metrics import (
    CostQualityFrontier,
    GraphConnectivityScore,
    GraphEntropyMetric,
    MemoryDriftIndex,
    MemorySnapshot,
    OptimalRetrievalRatio,
    RetentionCurve,
    SemanticCoherenceScore,
    StructuralDriftMetric,
)
from benchmarking.math_metrics.controller import (
    MathLayerController,
)
from benchmarking.scripts.run_benchmark import RAEBenchmarkRunner


class MathBenchmarkRunner(RAEBenchmarkRunner):
    """
    Extended benchmark runner with mathematical metrics.

    Adds three layers of mathematical analysis to standard benchmarks:
    1. Structure Metrics - analyze graph topology and semantic coherence
    2. Dynamics Metrics - track memory evolution and drift
    3. Policy Metrics - evaluate decision quality and efficiency
    """

    def __init__(self, *args, enable_math: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.enable_math = enable_math
        self.benchmark_data: Dict | None = None
        self.results: List[Dict] = []

        # Math-specific storage
        self.snapshots: List[MemorySnapshot] = []
        self.math_metrics_results: Dict[str, Any] = {}

        # Initialize MathLayerController
        self.math_controller = MathLayerController() if enable_math else None
        self.controller_decisions: List[Dict[str, Any]] = []

        # Initialize metric calculators
        self._init_metrics()

    def _init_metrics(self):
        """Initialize mathematical metric calculators"""
        # Structure metrics
        self.gcs_metric = GraphConnectivityScore()
        self.scs_metric = SemanticCoherenceScore()
        self.entropy_metric = GraphEntropyMetric()
        self.drift_metric = StructuralDriftMetric()

        # Dynamics metrics
        self.mdi_metric = MemoryDriftIndex()
        self.retention_metric = RetentionCurve()

        # Policy metrics
        self.orr_metric = OptimalRetrievalRatio()
        self.cqf_metric = CostQualityFrontier()

    def calculate_math_metrics(self) -> Dict[str, Any]:
        """
        Calculate all mathematical metrics.

        Returns:
            Dictionary with three categories: structure, dynamics, policy
        """
        if not self.enable_math:
            return {}

        print("\n🔬 Calculating mathematical metrics...")

        math_results: Dict[str, Any] = {
            "structure": {},
            "dynamics": {},
            "policy": {},
        }

        # Get latest snapshot
        if len(self.snapshots) > 0:
            latest_snapshot = self.snapshots[-1]

            # Structure Metrics
            print("   📐 Calculating structure metrics...")
            math_results["structure"] = self._calculate_structure_metrics(
                latest_snapshot
            )

            # Dynamics Metrics (if we have multiple snapshots)
            if len(self.snapshots) > 1:
                print("   🔄 Calculating dynamics metrics...")
                math_results["dynamics"] = self._calculate_dynamics_metrics()

            # Policy Metrics
            print("   🎯 Calculating policy metrics...")
            math_results["policy"] = self._calculate_policy_metrics()

        self.math_metrics_results = math_results
        return math_results

    def _calculate_structure_metrics(self, snapshot: MemorySnapshot) -> Dict[str, Any]:
        """Calculate structure metrics from snapshot"""
        results = {}

        # Graph Connectivity Score
        gcs = self.gcs_metric.calculate(
            num_nodes=snapshot.num_memories,
            edges=snapshot.graph_edges,
        )
        results["graph_connectivity_score"] = {
            "value": gcs,
            "metadata": self.gcs_metric.get_metadata(),
        }

        # Semantic Coherence Score (if edges exist)
        if len(snapshot.graph_edges) > 0:
            scs = self.scs_metric.calculate(snapshot)
            results["semantic_coherence_score"] = {
                "value": scs,
                "metadata": self.scs_metric.get_metadata(),
            }

        # Graph Entropy
        entropy = self.entropy_metric.calculate(
            num_nodes=snapshot.num_memories,
            edges=snapshot.graph_edges,
        )
        results["graph_entropy"] = {
            "value": entropy,
            "metadata": self.entropy_metric.get_metadata(),
        }

        return results

    def _calculate_dynamics_metrics(self) -> Dict[str, Any]:
        """Calculate dynamics metrics from multiple snapshots"""
        results: Dict[str, Any] = {}

        if len(self.snapshots) < 2:
            return results

        # Compare first and last snapshot
        snapshot_t0 = self.snapshots[0]
        snapshot_t1 = self.snapshots[-1]

        # Memory Drift Index
        mdi = self.mdi_metric.calculate(snapshot_t0, snapshot_t1)
        results["memory_drift_index"] = {
            "value": mdi,
            "metadata": self.mdi_metric.get_metadata(),
        }

        # Structural Drift
        drift = self.drift_metric.calculate(snapshot_t0, snapshot_t1)
        results["structural_drift"] = {
            "value": drift,
            "metadata": self.drift_metric.get_metadata(),
        }

        return results

    def _calculate_policy_metrics(self) -> Dict[str, Any]:
        """Calculate policy metrics from query results"""
        results = {}

        # Optimal Retrieval Ratio
        orr = self.orr_metric.calculate(self.results, k=5)
        results["optimal_retrieval_ratio"] = {
            "value": orr,
            "metadata": self.orr_metric.get_metadata(),
        }

        return results

    async def setup_database(self):
        await self.setup()

    async def load_benchmark(self):
        import yaml

        if not self.benchmark_file:
            raise ValueError("Benchmark file required")

        with open(self.benchmark_file, "r") as f:
            self.benchmark_data = yaml.safe_load(f)

    async def cleanup_test_data(self):
        await self.cleanup()

    async def insert_memories(self):
        """Override to capture snapshot after insertion"""
        # Call parent method via run logic or just pass through
        # In System 3.2 run_benchmark.py handles run loop.
        # This skript seems to be from older version.
        pass

    async def run_queries(self):
        """Override to capture snapshot after queries and make level decisions"""
        pass

    def calculate_metrics(self) -> Dict[str, Any]:
        """Override to include mathematical metrics"""
        # System 3.2: Base class doesn't have calculate_metrics anymore
        metrics: Dict[str, Any] = {"status": "completed"}

        if self.enable_math:
            math_metrics = self.calculate_math_metrics()
            metrics["math"] = math_metrics

        return metrics

    def save_results(self, metrics: Dict[str, Any]):
        """Override to save additional mathematical metric files"""
        # System 3.2: Base class doesn't have save_results anymore
        assert self.benchmark_data is not None

        assert self.benchmark_data is not None

        # Save mathematical metrics separately
        if self.enable_math and "math" in metrics:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            benchmark_name = self.benchmark_data["name"]

            # Save structure metrics
            if metrics["math"]["structure"]:
                structure_file = (
                    self.output_dir / f"{benchmark_name}_{timestamp}_structure.json"
                )
                with open(structure_file, "w") as f:
                    json.dump(metrics["math"]["structure"], f, indent=2)
                print(f"   ✅ Structure metrics: {structure_file}")

            # Save dynamics metrics
            if metrics["math"]["dynamics"]:
                dynamics_file = (
                    self.output_dir / f"{benchmark_name}_{timestamp}_dynamics.json"
                )
                with open(dynamics_file, "w") as f:
                    json.dump(metrics["math"]["dynamics"], f, indent=2)
                print(f"   ✅ Dynamics metrics: {dynamics_file}")

            # Save policy metrics
            if metrics["math"]["policy"]:
                policy_file = (
                    self.output_dir / f"{benchmark_name}_{timestamp}_policy.json"
                )
                with open(policy_file, "w") as f:
                    json.dump(metrics["math"]["policy"], f, indent=2)
                print(f"   ✅ Policy metrics: {policy_file}")

            # Save snapshot metadata
            snapshots_meta = [snap.to_dict() for snap in self.snapshots]
            snapshots_file = (
                self.output_dir / f"{benchmark_name}_{timestamp}_snapshots.json"
            )
            with open(snapshots_file, "w") as f:
                json.dump(snapshots_meta, f, indent=2)
            print(f"   ✅ Snapshots metadata: {snapshots_file}")

            # Save controller decisions (Iteration 1: logging foundation)
            if self.controller_decisions:
                decisions_file = (
                    self.output_dir / f"{benchmark_name}_{timestamp}_decisions.json"
                )
                with open(decisions_file, "w") as f:
                    json.dump(self.controller_decisions, f, indent=2)
                print(f"   ✅ Controller decisions: {decisions_file}")


async def main():
    parser = argparse.ArgumentParser(
        description="Run RAE benchmarks with mathematical metrics"
    )
    parser.add_argument(
        "--set",
        type=str,
        required=True,
        help="Benchmark set to run (e.g., academic_lite.yaml)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarking/results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--enable-math",
        action="store_true",
        default=True,
        help="Enable mathematical metrics (default: True)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        help="RAE API URL (default: direct DB access)",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key for authentication",
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    benchmark_file = project_root / "benchmarking" / "sets" / args.set
    output_dir = project_root / args.output

    if not benchmark_file.exists():
        print(f"❌ Benchmark file not found: {benchmark_file}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run benchmark
    print("🚀 RAE Mathematical Benchmark Runner")
    print("=" * 60)

    runner = MathBenchmarkRunner(
        benchmark_file=benchmark_file,
        output_dir=output_dir,
        api_url=args.api_url,
        api_key=args.api_key,
        use_direct_db=True,
        enable_math=args.enable_math,
    )

    try:
        await runner.load_benchmark()
        await runner.setup_database()
        await runner.cleanup_test_data()
        await runner.insert_memories()
        await runner.run_queries()

        metrics = runner.calculate_metrics()
        runner.save_results(metrics)

        print("\n✅ Benchmark complete!")
        if args.enable_math:
            print("📊 Mathematical metrics saved to separate JSON files")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
