#!/usr/bin/env python3
"""
RAE Benchmark Plot Generator

Generates visualizations from benchmark results:
- Latency distributions (histograms)
- MRR comparisons (bar charts)
- Performance trends over time
- Memory drift analysis
- Reflection improvement delta

Usage:
    python generate_plots.py --results results/academic_extended_*.json --output plots/
    python generate_plots.py --compare baseline.json improved.json --output comparison.png
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, cast

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


class BenchmarkPlotter:
    """Generate plots from benchmark results"""

    def __init__(self, style: str = "seaborn-v0_8-darkgrid"):
        """Initialize plotter with style"""
        try:
            plt.style.use(style)
        except Exception:
            plt.style.use("default")
        sns.set_palette("husl")

    def load_results(self, results_file: Path) -> Dict[str, Any]:
        """Load benchmark results from JSON"""
        with open(results_file, "r") as f:
            data = json.load(f)
            return cast(Dict[str, Any], data)

    def plot_latency_distribution(self, results: Dict, output_file: Path):
        """
        Plot latency distribution histogram

        Args:
            results: Benchmark results dict
            output_file: Output PNG file path
        """
        detailed_results = results["detailed_results"]
        latencies = [r["latency_ms"] for r in detailed_results]

        fig, ax = plt.subplots(figsize=(10, 6))

        # Histogram
        ax.hist(latencies, bins=30, edgecolor="black", alpha=0.7)

        # Add percentile lines
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)

        ax.axvline(
            p50, color="green", linestyle="--", linewidth=2, label=f"P50: {p50:.1f}ms"
        )
        ax.axvline(
            p95, color="orange", linestyle="--", linewidth=2, label=f"P95: {p95:.1f}ms"
        )
        ax.axvline(
            p99, color="red", linestyle="--", linewidth=2, label=f"P99: {p99:.1f}ms"
        )

        ax.set_xlabel("Query Latency (ms)", fontsize=12)
        ax.set_ylabel("Frequency", fontsize=12)
        ax.set_title(
            f"Query Latency Distribution - {results['benchmark']['name']}",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Latency distribution saved to: {output_file}")

    def plot_mrr_by_difficulty(self, results: Dict, output_file: Path):
        """
        Plot MRR breakdown by query difficulty

        Args:
            results: Benchmark results dict
            output_file: Output PNG file path
        """
        detailed_results = results["detailed_results"]

        # Group by difficulty
        difficulty_groups: Dict[str, List[float]] = {}
        for r in detailed_results:
            diff = r.get("difficulty", "unknown")
            if diff not in difficulty_groups:
                difficulty_groups[diff] = []

            # Calculate reciprocal rank for this query
            expected = r["expected"]
            retrieved = r["retrieved"]
            rr = 0.0
            for i, doc_id in enumerate(retrieved, 1):
                if doc_id in expected:
                    rr = 1.0 / i
                    break
            difficulty_groups[diff].append(rr)

        # Calculate MRR per difficulty
        difficulties = list(difficulty_groups.keys())
        mrrs = [np.mean(difficulty_groups[d]) for d in difficulties]

        # Create bar chart
        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.bar(difficulties, mrrs, edgecolor="black", alpha=0.7)

        # Color bars by performance
        for bar, mrr in zip(bars, mrrs):
            if mrr > 0.8:
                bar.set_color("green")
            elif mrr > 0.6:
                bar.set_color("orange")
            else:
                bar.set_color("red")

        # Add value labels on bars
        for bar, mrr in zip(bars, mrrs):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{mrr:.3f}",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        ax.set_xlabel("Query Difficulty", fontsize=12)
        ax.set_ylabel("MRR", fontsize=12)
        ax.set_title(
            f"MRR by Query Difficulty - {results['benchmark']['name']}",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_ylim(0, 1.0)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ MRR by difficulty saved to: {output_file}")

    def plot_comparison(self, baseline: Dict, comparison: Dict, output_file: Path):
        """
        Plot comparison between two benchmark runs

        Args:
            baseline: Baseline benchmark results
            comparison: Comparison benchmark results
            output_file: Output PNG file path
        """
        metrics_to_compare = [
            ("mrr", "MRR"),
            ("hit_rate['@5']", "Hit Rate @5"),
            ("precision['@5']", "Precision @5"),
            ("recall['@5']", "Recall @5"),
        ]

        baseline_values = []
        comparison_values = []
        labels = []

        for metric_path, label in metrics_to_compare:
            # Navigate nested dict
            baseline_val = baseline["metrics"]
            comparison_val = comparison["metrics"]

            for key in metric_path.replace("'", "").split("["):
                key = key.rstrip("]")
                if key:
                    baseline_val = baseline_val[key]
                    comparison_val = comparison_val[key]

            baseline_values.append(baseline_val)
            comparison_values.append(comparison_val)
            labels.append(label)

        # Create grouped bar chart
        x = np.arange(len(labels))
        width = 0.35

        fig, ax = plt.subplots(figsize=(12, 6))

        bars1 = ax.bar(
            x - width / 2,
            baseline_values,
            width,
            label="Baseline",
            alpha=0.8,
            edgecolor="black",
        )
        bars2 = ax.bar(
            x + width / 2,
            comparison_values,
            width,
            label="Comparison",
            alpha=0.8,
            edgecolor="black",
        )

        # Color bars based on improvement
        for b1, b2, base_val, comp_val in zip(
            bars1, bars2, baseline_values, comparison_values
        ):
            if comp_val > base_val:
                b2.set_color("green")
            elif comp_val < base_val:
                b2.set_color("red")
            else:
                b2.set_color("gray")

        ax.set_ylabel("Score", fontsize=12)
        ax.set_title(
            "Benchmark Comparison: Baseline vs Improved", fontsize=14, fontweight="bold"
        )
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.legend()
        ax.set_ylim(0, 1.0)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Comparison plot saved to: {output_file}")

    def plot_performance_over_time(self, results_files: List[Path], output_file: Path):
        """
        Plot performance metrics over multiple runs

        Args:
            results_files: List of benchmark result files (chronological order)
            output_file: Output PNG file path
        """
        timestamps = []
        mrr_scores = []
        avg_latencies = []

        for results_file in sorted(results_files):
            try:
                # results_file is a Path object here
                with open(results_file, "r") as f:
                    results = json.load(f)

                # Verify it's a valid benchmark result
                if "execution" not in results or "metrics" not in results:
                    continue

                timestamps.append(results["execution"]["timestamp"])
                mrr_scores.append(results["metrics"]["mrr"])

                # Handle inconsistent keys between different benchmark sets
                perf = results["metrics"]["performance"]
                if "average_query_time" in perf:
                    avg_latencies.append(perf["average_query_time"] * 1000)
                else:
                    avg_latencies.append(perf.get("avg_query_time_ms", 0))
            except Exception as e:
                print(f"⚠️  Error processing {results_file}: {e}")
                continue

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # MRR over time
        ax1.plot(
            range(len(timestamps)), mrr_scores, marker="o", linewidth=2, markersize=8
        )
        ax1.set_ylabel("MRR", fontsize=12)
        ax1.set_title("Performance Trends Over Time", fontsize=14, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(0, 1.0)

        # Latency over time
        ax2.plot(
            range(len(timestamps)),
            avg_latencies,
            marker="s",
            linewidth=2,
            markersize=8,
            color="orange",
        )
        ax2.set_xlabel("Benchmark Run", fontsize=12)
        ax2.set_ylabel("Avg Latency (ms)", fontsize=12)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"✅ Performance trends saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate plots from RAE benchmark results"
    )
    parser.add_argument(
        "--results", type=str, nargs="+", help="Benchmark result JSON file(s)"
    )
    parser.add_argument(
        "--compare", type=str, nargs=2, help="Compare two results: baseline comparison"
    )
    parser.add_argument(
        "--output", type=str, required=True, help="Output file or directory"
    )
    parser.add_argument(
        "--type",
        type=str,
        choices=["latency", "mrr", "comparison", "trends", "all"],
        default="all",
        help="Type of plot to generate",
    )

    args = parser.parse_args()

    if not args.results and not args.compare:
        print("❌ Error: Must specify --results or --compare")
        sys.exit(1)

    plotter = BenchmarkPlotter()
    output_path = Path(args.output)

    try:
        if args.compare:
            # Comparison mode
            baseline = plotter.load_results(Path(args.compare[0]))
            comparison = plotter.load_results(Path(args.compare[1]))

            if output_path.is_dir():
                output_file = output_path / "comparison.png"
            else:
                output_file = output_path

            plotter.plot_comparison(baseline, comparison, output_file)

        else:
            # Single or multiple results mode
            results_files = [Path(f) for f in args.results]

            if len(results_files) == 1:
                # Single result - generate multiple plots
                results = plotter.load_results(results_files[0])

                if output_path.is_dir():
                    output_path.mkdir(parents=True, exist_ok=True)
                    if args.type in ["latency", "all"]:
                        plotter.plot_latency_distribution(
                            results, output_path / "latency_distribution.png"
                        )
                    if args.type in ["mrr", "all"]:
                        plotter.plot_mrr_by_difficulty(
                            results, output_path / "mrr_by_difficulty.png"
                        )
                else:
                    # Single output file - generate requested type only
                    if args.type == "latency":
                        plotter.plot_latency_distribution(results, output_path)
                    elif args.type == "mrr":
                        plotter.plot_mrr_by_difficulty(results, output_path)

            else:
                # Multiple results - trend analysis AND individual plots
                output_path.mkdir(parents=True, exist_ok=True)

                # Individual plots for each file
                for res_file in results_files:
                    try:
                        single_results = plotter.load_results(res_file)
                        base_name = res_file.stem
                        plotter.plot_latency_distribution(
                            single_results, output_path / f"{base_name}_latency.png"
                        )
                        plotter.plot_mrr_by_difficulty(
                            single_results, output_path / f"{base_name}_mrr.png"
                        )
                    except Exception as e:
                        print(f"⚠️  Skipping {res_file.name}: {e}")

                if output_path.is_dir():
                    output_file = output_path / "performance_trends.png"
                else:
                    output_file = output_path

                plotter.plot_performance_over_time(results_files, output_file)

        print("\n✅ Plot generation complete!")

    except Exception as e:
        print(f"\n❌ Plot generation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
