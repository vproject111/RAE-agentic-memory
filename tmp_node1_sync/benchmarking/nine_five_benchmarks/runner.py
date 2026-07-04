"""
Nine-Five Benchmark Runner

Unified runner for all 6 RAE 9/5 research benchmarks:
1. LECT - Long-term Episodic Consistency Test
2. MMIT - Multi-Layer Memory Interference Test
3. GRDT - Graph Reasoning Depth Test
4. RST - Reflective Stability Test
5. MPEB - Math-3 Policy Evolution Benchmark
6. ORB - OpenTelemetry Research Benchmark

Research-grade implementation for academic evaluation of RAE memory systems.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from benchmarking.telemetry import BenchmarkTelemetry

from .grdt_benchmark import GRDTBenchmark, GRDTResults
from .lect_benchmark import LECTBenchmark, LECTResults
from .mmit_benchmark import MMITBenchmark, MMITResults
from .mpeb_benchmark import MPEBBenchmark, MPEBResults
from .orb_benchmark import ORBBenchmark, ORBResults
from .rst_benchmark import RSTBenchmark, RSTResults


@dataclass
class NineFiveResults:
    """Aggregated results from all 9/5 benchmarks."""

    timestamp: str
    version: str = "1.0.0"

    # Individual results
    lect: Optional[Dict[str, Any]] = None
    mmit: Optional[Dict[str, Any]] = None
    grdt: Optional[Dict[str, Any]] = None
    rst: Optional[Dict[str, Any]] = None
    mpeb: Optional[Dict[str, Any]] = None
    orb: Optional[Dict[str, Any]] = None

    # Summary scores
    summary: Dict[str, Any] = field(default_factory=dict)

    # Timing
    total_duration_seconds: float = 0.0
    benchmark_durations: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "benchmarks": {
                "lect": self.lect,
                "mmit": self.mmit,
                "grdt": self.grdt,
                "rst": self.rst,
                "mpeb": self.mpeb,
                "orb": self.orb,
            },
            "summary": self.summary,
            "timing": {
                "total_duration_seconds": self.total_duration_seconds,
                "benchmark_durations": self.benchmark_durations,
            },
        }


class NineFiveBenchmarkRunner:
    """
    Unified runner for all 9/5 benchmarks.

    Provides convenient methods to run individual benchmarks or the full suite.

    Example:
        >>> runner = NineFiveBenchmarkRunner()

        # Run all benchmarks
        >>> results = runner.run_all()

        # Run specific benchmarks
        >>> lect_results = runner.run_lect(num_cycles=10000)
        >>> mmit_results = runner.run_mmit(num_operations=5000)

        # Save results
        >>> runner.save_results(results)
    """

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        seed: int = 42,
        verbose: bool = True,
    ):
        """
        Initialize runner.

        Args:
            output_dir: Output directory for results
            seed: Random seed for reproducibility
            verbose: Whether to print progress
        """
        self.output_dir = output_dir or (
            Path(__file__).parent.parent / "results" / "nine_five"
        )
        self.seed = seed
        self.verbose = verbose

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def run_lect(
        self,
        num_cycles: int = 10000,
        checkpoint_interval: int = 1000,
        **kwargs,
    ) -> LECTResults:
        """Run LECT benchmark."""
        if self.verbose:
            print("\n" + "=" * 60)
            print("Running LECT (Long-term Episodic Consistency Test)")
            print("=" * 60)

        benchmark = LECTBenchmark(
            checkpoint_interval=checkpoint_interval,
            seed=self.seed,
        )
        return benchmark.run(num_cycles=num_cycles, verbose=self.verbose, **kwargs)

    def run_mmit(
        self,
        num_operations: int = 5000,
        similarity_threshold: float = 0.97,
        **kwargs,
    ) -> MMITResults:
        """Run MMIT benchmark."""
        if self.verbose:
            print("\n" + "=" * 60)
            print("Running MMIT (Multi-Layer Memory Interference Test)")
            print("=" * 60)

        benchmark = MMITBenchmark(
            similarity_threshold=similarity_threshold,
            seed=self.seed,
        )
        return benchmark.run(
            num_operations=num_operations, verbose=self.verbose, **kwargs
        )

    def run_grdt(
        self,
        num_queries: int = 100,
        min_depth: int = 3,
        max_depth: int = 10,
        **kwargs,
    ) -> GRDTResults:
        """Run GRDT benchmark."""
        if self.verbose:
            print("\n" + "=" * 60)
            print("Running GRDT (Graph Reasoning Depth Test)")
            print("=" * 60)

        benchmark = GRDTBenchmark(seed=self.seed)
        return benchmark.run(
            num_queries=num_queries,
            min_depth=min_depth,
            max_depth=max_depth,
            verbose=self.verbose,
            **kwargs,
        )

    def run_rst(
        self,
        num_insights: int = 50,
        num_source_memories: int = 100,
        **kwargs,
    ) -> RSTResults:
        """Run RST benchmark."""
        if self.verbose:
            print("\n" + "=" * 60)
            print("Running RST (Reflective Stability Test)")
            print("=" * 60)

        benchmark = RSTBenchmark(seed=self.seed)
        return benchmark.run(
            num_insights=num_insights,
            num_source_memories=num_source_memories,
            verbose=self.verbose,
            **kwargs,
        )

    def run_mpeb(
        self,
        num_iterations: int = 1000,
        episode_length: int = 50,
        **kwargs,
    ) -> MPEBResults:
        """Run MPEB benchmark."""
        if self.verbose:
            print("\n" + "=" * 60)
            print("Running MPEB (Math-3 Policy Evolution Benchmark)")
            print("=" * 60)

        benchmark = MPEBBenchmark(seed=self.seed)
        return benchmark.run(
            num_iterations=num_iterations,
            episode_length=episode_length,
            verbose=self.verbose,
            **kwargs,
        )

    def run_orb(
        self,
        num_samples_per_config: int = 20,
        **kwargs,
    ) -> ORBResults:
        """Run ORB benchmark."""
        if self.verbose:
            print("\n" + "=" * 60)
            print("Running ORB (OpenTelemetry Research Benchmark)")
            print("=" * 60)

        benchmark = ORBBenchmark(seed=self.seed)
        return benchmark.run(
            num_samples_per_config=num_samples_per_config,
            verbose=self.verbose,
            **kwargs,
        )

    def run_all(
        self,
        lect_cycles: int = 10000,
        mmit_operations: int = 5000,
        grdt_queries: int = 100,
        rst_insights: int = 50,
        mpeb_iterations: int = 1000,
        orb_samples: int = 20,
    ) -> NineFiveResults:
        """
        Run all 6 benchmarks.

        Args:
            lect_cycles: LECT cycle count
            mmit_operations: MMIT operation count
            grdt_queries: GRDT query count
            rst_insights: RST insight count
            mpeb_iterations: MPEB iteration count
            orb_samples: ORB samples per config

        Returns:
            NineFiveResults with all benchmark results
        """
        start_time = datetime.now()

        if self.verbose:
            print("\n" + "#" * 60)
            print("  RAE 9/5 RESEARCH BENCHMARK SUITE")
            print("#" * 60)
            print(f"\nStarting full benchmark suite at {start_time.isoformat()}")

        results = NineFiveResults(timestamp=start_time.isoformat())
        durations = {}

        # 1. LECT
        t0 = time.time()
        lect_results = self.run_lect(num_cycles=lect_cycles)
        durations["lect"] = time.time() - t0
        results.lect = lect_results.to_dict()

        # 2. MMIT
        t0 = time.time()
        mmit_results = self.run_mmit(num_operations=mmit_operations)
        durations["mmit"] = time.time() - t0
        results.mmit = mmit_results.to_dict()

        # 3. GRDT
        t0 = time.time()
        grdt_results = self.run_grdt(num_queries=grdt_queries)
        durations["grdt"] = time.time() - t0
        results.grdt = grdt_results.to_dict()

        # 4. RST
        t0 = time.time()
        rst_results = self.run_rst(num_insights=rst_insights)
        durations["rst"] = time.time() - t0
        results.rst = rst_results.to_dict()

        # 5. MPEB
        t0 = time.time()
        mpeb_results = self.run_mpeb(num_iterations=mpeb_iterations)
        durations["mpeb"] = time.time() - t0
        results.mpeb = mpeb_results.to_dict()

        # 6. ORB
        t0 = time.time()
        orb_results = self.run_orb(num_samples_per_config=orb_samples)
        durations["orb"] = time.time() - t0
        results.orb = orb_results.to_dict()

        # Calculate summary
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        results.total_duration_seconds = total_duration
        results.benchmark_durations = durations

        # Summary scores
        results.summary = {
            "lect_consistency": lect_results.consistency_score,
            "lect_retention": lect_results.retention_rate,
            "mmit_interference": mmit_results.interference_score,
            "grdt_max_depth": grdt_results.max_reasoning_depth,
            "grdt_coherence": grdt_results.chain_coherence,
            "rst_noise_threshold": rst_results.noise_threshold,
            "rst_consistency": rst_results.insight_consistency,
            "mpeb_convergence": mpeb_results.convergence_rate,
            "mpeb_stability": mpeb_results.stability_index,
            "orb_pareto_optimal": len(
                [
                    p
                    for p in orb_results.pareto_frontier
                    if p.get("is_pareto_optimal", False)
                ]
            ),
        }

        # Record metrics to telemetry
        telemetry = BenchmarkTelemetry()
        timestamp = datetime.fromisoformat(results.timestamp)

        # Record LECT metrics
        telemetry.record_metric(
            "LECT", "consistency", lect_results.consistency_score, timestamp
        )
        telemetry.record_metric(
            "LECT", "retention", lect_results.retention_rate, timestamp
        )

        # Record MMIT metrics
        telemetry.record_metric(
            "MMIT", "interference", mmit_results.interference_score, timestamp
        )

        # Record GRDT metrics
        telemetry.record_metric(
            "GRDT", "max_depth", grdt_results.max_reasoning_depth, timestamp
        )
        telemetry.record_metric(
            "GRDT", "coherence", grdt_results.chain_coherence, timestamp
        )

        # Record RST metrics
        telemetry.record_metric(
            "RST", "noise_threshold", rst_results.noise_threshold, timestamp
        )
        telemetry.record_metric(
            "RST", "consistency", rst_results.insight_consistency, timestamp
        )

        # Record MPEB metrics
        telemetry.record_metric(
            "MPEB", "convergence", mpeb_results.convergence_rate, timestamp
        )
        telemetry.record_metric(
            "MPEB", "adaptation", mpeb_results.stability_index, timestamp
        )

        # Record ORB metrics
        orb_pareto_count = len(
            [
                p
                for p in orb_results.pareto_frontier
                if p.get("is_pareto_optimal", False)
            ]
        )
        telemetry.record_metric("ORB", "pareto_optimal", orb_pareto_count, timestamp)

        # Export telemetry
        telemetry.export_json()

        if self.verbose:
            print("\n" + "#" * 60)
            print("  BENCHMARK SUITE COMPLETE")
            print("#" * 60)
            print(f"\nTotal Duration: {total_duration:.2f}s")
            print("\nSummary Scores:")
            for key, value in results.summary.items():
                print(f"  {key}: {value}")
            print("\n✅ Telemetry data exported")

        return results

    def save_results(
        self,
        results: NineFiveResults,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Save benchmark results to JSON.

        Args:
            results: NineFiveResults to save
            filename: Optional custom filename

        Returns:
            Path to saved file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nine_five_full_{timestamp}.json"

        output_file = self.output_dir / filename

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        if self.verbose:
            print(f"\nResults saved to: {output_file}")

        return output_file

    def generate_report(
        self,
        results: NineFiveResults,
        filename: Optional[str] = None,
    ) -> Path:
        """
        Generate Markdown report from results.

        Args:
            results: NineFiveResults to report
            filename: Optional custom filename

        Returns:
            Path to saved report
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nine_five_report_{timestamp}.md"

        output_file = self.output_dir / filename

        with open(output_file, "w") as f:
            f.write("# RAE 9/5 Research Benchmark Report\n\n")
            f.write(f"**Generated:** {results.timestamp}\n")
            f.write(f"**Version:** {results.version}\n")
            f.write(f"**Total Duration:** {results.total_duration_seconds:.2f}s\n\n")

            f.write("---\n\n")
            f.write("## Summary Scores\n\n")
            f.write("| Metric | Value |\n")
            f.write("|--------|-------|\n")
            for key, value in results.summary.items():
                if isinstance(value, float):
                    f.write(f"| {key} | {value:.4f} |\n")
                else:
                    f.write(f"| {key} | {value} |\n")

            f.write("\n---\n\n")
            f.write("## Benchmark Durations\n\n")
            f.write("| Benchmark | Duration (s) |\n")
            f.write("|-----------|-------------|\n")
            for benchmark, duration in results.benchmark_durations.items():
                f.write(f"| {benchmark.upper()} | {duration:.2f} |\n")

            f.write("\n---\n\n")
            f.write("## Individual Benchmark Results\n\n")

            benchmarks = ["lect", "mmit", "grdt", "rst", "mpeb", "orb"]
            titles = {
                "lect": "LECT - Long-term Episodic Consistency Test",
                "mmit": "MMIT - Multi-Layer Memory Interference Test",
                "grdt": "GRDT - Graph Reasoning Depth Test",
                "rst": "RST - Reflective Stability Test",
                "mpeb": "MPEB - Math-3 Policy Evolution Benchmark",
                "orb": "ORB - OpenTelemetry Research Benchmark",
            }

            for benchmark in benchmarks:
                data = getattr(results, benchmark)
                if data:
                    f.write(f"### {titles[benchmark]}\n\n")
                    primary = data.get("primary_metrics", {})
                    if primary:
                        f.write("**Primary Metrics:**\n\n")
                        for key, value in primary.items():
                            if isinstance(value, dict):
                                f.write(f"- {key}:\n")
                                for k, v in value.items():
                                    if isinstance(v, float):
                                        f.write(f"  - {k}: {v:.4f}\n")
                                    else:
                                        f.write(f"  - {k}: {v}\n")
                            elif isinstance(value, float):
                                f.write(f"- {key}: {value:.4f}\n")
                            else:
                                f.write(f"- {key}: {value}\n")
                    f.write("\n")

            f.write("---\n\n")
            f.write("*Generated by RAE 9/5 Benchmark Suite*\n")

        if self.verbose:
            print(f"Report saved to: {output_file}")

        return output_file


def run_all_benchmarks(
    output_dir: Optional[Path] = None,
    seed: int = 42,
    verbose: bool = True,
    **kwargs,
) -> NineFiveResults:
    """
    Convenience function to run all benchmarks.

    Args:
        output_dir: Output directory
        seed: Random seed
        verbose: Print progress
        **kwargs: Additional arguments for run_all()

    Returns:
        NineFiveResults
    """
    runner = NineFiveBenchmarkRunner(
        output_dir=output_dir,
        seed=seed,
        verbose=verbose,
    )
    results = runner.run_all(**kwargs)
    runner.save_results(results)
    runner.generate_report(results)
    return results


def main():
    """Run benchmark suite from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run RAE 9/5 Benchmark Suite")
    parser.add_argument(
        "--benchmark",
        type=str,
        choices=["all", "lect", "mmit", "grdt", "rst", "mpeb", "orb"],
        default="all",
        help="Benchmark to run",
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
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick mode with reduced iterations",
    )

    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    runner = NineFiveBenchmarkRunner(output_dir=output_dir, seed=args.seed)

    # Quick mode parameters
    if args.quick:
        quick_params = {
            "lect_cycles": 1000,
            "mmit_operations": 500,
            "grdt_queries": 20,
            "rst_insights": 10,
            "mpeb_iterations": 100,
            "orb_samples": 5,
        }
    else:
        quick_params = {}

    # Results union type
    results: Union[
        NineFiveResults,
        LECTResults,
        MMITResults,
        GRDTResults,
        RSTResults,
        MPEBResults,
        ORBResults,
    ]

    if args.benchmark == "all":
        results = runner.run_all(**quick_params)
        runner.save_results(results)
        runner.generate_report(results)
    elif args.benchmark == "lect":
        results = runner.run_lect(num_cycles=quick_params.get("lect_cycles", 10000))
    elif args.benchmark == "mmit":
        results = runner.run_mmit(
            num_operations=quick_params.get("mmit_operations", 5000)
        )
    elif args.benchmark == "grdt":
        results = runner.run_grdt(num_queries=quick_params.get("grdt_queries", 100))
    elif args.benchmark == "rst":
        results = runner.run_rst(num_insights=quick_params.get("rst_insights", 50))
    elif args.benchmark == "mpeb":
        results = runner.run_mpeb(
            num_iterations=quick_params.get("mpeb_iterations", 1000)
        )
    elif args.benchmark == "orb":
        results = runner.run_orb(
            num_samples_per_config=quick_params.get("orb_samples", 20)
        )

    print("\nBenchmark complete!")


if __name__ == "__main__":
    main()
