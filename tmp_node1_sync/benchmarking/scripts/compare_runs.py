#!/usr/bin/env python3
"""
RAE Benchmark Comparison Tool

Compare results from two benchmark runs to identify improvements or regressions.

Usage:
    python compare_runs.py results/run1.json results/run2.json
    python compare_runs.py results/run1.json results/run2.json --output comparison.md
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


class BenchmarkComparator:
    """Compare two benchmark results"""

    def __init__(self, baseline_file: Path, comparison_file: Path):
        self.baseline_file = baseline_file
        self.comparison_file = comparison_file

        self.baseline: Dict[str, Any] = {}
        self.comparison: Dict[str, Any] = {}

    def load_results(self) -> None:
        """Load both result files"""
        print("📂 Loading results...")
        print(f"   Baseline: {self.baseline_file.name}")
        print(f"   Comparison: {self.comparison_file.name}")

        with open(self.baseline_file, "r") as f:
            self.baseline = json.load(f)

        with open(self.comparison_file, "r") as f:
            self.comparison = json.load(f)

    def calculate_changes(self) -> Dict[str, Any]:
        """Calculate differences between runs"""
        print("\n📊 Calculating changes...")

        if not self.baseline or not self.comparison:
            return {}

        baseline_metrics = self.baseline["metrics"]
        comparison_metrics = self.comparison["metrics"]

        changes: Dict[str, Any] = {
            "quality": {},
            "performance": {},
            "summary": {"improvements": 0, "regressions": 0, "unchanged": 0},
        }

        summary: Dict[str, int] = changes["summary"]

        # Quality metrics changes
        quality_keys = ["mrr", "overall_quality_score"]
        for key in quality_keys:
            baseline_val = baseline_metrics.get(key, 0)
            comparison_val = comparison_metrics.get(key, 0)
            change = comparison_val - baseline_val
            change_pct = (change / baseline_val * 100) if baseline_val != 0 else 0

            changes["quality"][key] = {
                "baseline": baseline_val,
                "comparison": comparison_val,
                "absolute_change": change,
                "percent_change": change_pct,
            }

            if abs(change_pct) < 1:
                summary["unchanged"] += 1
            elif change > 0:
                summary["improvements"] += 1
            else:
                summary["regressions"] += 1

        # Hit rate changes
        for k in ["@3", "@5", "@10"]:
            baseline_val = baseline_metrics["hit_rate"].get(k, 0)
            comparison_val = comparison_metrics["hit_rate"].get(k, 0)
            change = comparison_val - baseline_val
            change_pct = (change / baseline_val * 100) if baseline_val != 0 else 0

            changes["quality"][f"hit_rate{k}"] = {
                "baseline": baseline_val,
                "comparison": comparison_val,
                "absolute_change": change,
                "percent_change": change_pct,
            }

            if abs(change_pct) < 1:
                summary["unchanged"] += 1
            elif change > 0:
                summary["improvements"] += 1
            else:
                summary["regressions"] += 1

        # Precision and Recall changes
        for metric_type in ["precision", "recall"]:
            for k in ["@3", "@5", "@10"]:
                baseline_val = baseline_metrics[metric_type].get(k, 0)
                comparison_val = comparison_metrics[metric_type].get(k, 0)
                change = comparison_val - baseline_val
                change_pct = (change / baseline_val * 100) if baseline_val != 0 else 0

                changes["quality"][f"{metric_type}{k}"] = {
                    "baseline": baseline_val,
                    "comparison": comparison_val,
                    "absolute_change": change,
                    "percent_change": change_pct,
                }

                if abs(change_pct) < 1:
                    summary["unchanged"] += 1
                elif change > 0:
                    summary["improvements"] += 1
                else:
                    summary["regressions"] += 1

        # Performance metrics changes
        perf_keys = [
            "avg_insert_time_ms",
            "avg_query_time_ms",
            "p95_query_time_ms",
            "p99_query_time_ms",
        ]
        for key in perf_keys:
            baseline_val = baseline_metrics["performance"].get(key, 0)
            comparison_val = comparison_metrics["performance"].get(key, 0)
            change = comparison_val - baseline_val
            change_pct = (change / baseline_val * 100) if baseline_val != 0 else 0

            changes["performance"][key] = {
                "baseline": baseline_val,
                "comparison": comparison_val,
                "absolute_change": change,
                "percent_change": change_pct,
                "improved": change < 0,  # Lower is better for latency
            }

            # For performance, lower is better
            if abs(change_pct) < 5:
                summary["unchanged"] += 1
            elif change < 0:
                summary["improvements"] += 1
            else:
                summary["regressions"] += 1

        return changes

    def print_summary(self, changes: Dict):
        """Print comparison summary to console"""
        print("\n" + "=" * 60)
        print("BENCHMARK COMPARISON SUMMARY")
        print("=" * 60)

        print("\n📈 Overall:")
        print(f"   Improvements: {changes['summary']['improvements']}")
        print(f"   Regressions: {changes['summary']['regressions']}")
        print(f"   Unchanged: {changes['summary']['unchanged']}")

        print("\n🎯 Quality Metrics:")
        for key, data in changes["quality"].items():
            if key in ["mrr", "overall_quality_score"]:
                emoji = (
                    "✅"
                    if data["percent_change"] > 1
                    else "❌" if data["percent_change"] < -1 else "➡️"
                )
                print(
                    f"   {emoji} {key.upper()}: {data['baseline']:.4f} → {data['comparison']:.4f} ({data['percent_change']:+.2f}%)"
                )

        print("\n⚡ Performance Metrics:")
        for key, data in changes["performance"].items():
            # Lower is better for latency
            emoji = (
                "✅"
                if data["improved"] and abs(data["percent_change"]) > 5
                else (
                    "❌"
                    if not data["improved"] and abs(data["percent_change"]) > 5
                    else "➡️"
                )
            )
            print(
                f"   {emoji} {key}: {data['baseline']:.2f}ms → {data['comparison']:.2f}ms ({data['percent_change']:+.2f}%)"
            )

    def generate_markdown_report(
        self, output_file: Path, changes: Dict[str, Any]
    ) -> None:
        """Generate detailed Markdown comparison report"""
        print(f"\n💾 Generating report: {output_file}")

        assert self.baseline and self.comparison, "Results must be loaded"

        with open(output_file, "w") as f:
            f.write("# RAE Benchmark Comparison Report\n\n")

            # Header info
            f.write("## Comparison Overview\n\n")
            f.write(
                f"**Baseline:** {self.baseline['benchmark']['name']} "
                f"({self.baseline['execution']['timestamp']})\n\n"
            )
            f.write(
                f"**Comparison:** {self.comparison['benchmark']['name']} "
                f"({self.comparison['execution']['timestamp']})\n\n"
            )

            f.write("---\n\n")

            # Summary
            f.write("## Summary\n\n")
            f.write(f"- ✅ **Improvements:** {changes['summary']['improvements']}\n")
            f.write(f"- ❌ **Regressions:** {changes['summary']['regressions']}\n")
            f.write(f"- ➡️ **Unchanged:** {changes['summary']['unchanged']}\n\n")

            # Quality metrics table
            f.write("## Quality Metrics Comparison\n\n")
            f.write("| Metric | Baseline | Comparison | Change | % Change | Status |\n")
            f.write("|--------|----------|------------|--------|----------|--------|\n")

            for key, data in changes["quality"].items():
                status = (
                    "✅ Better"
                    if data["percent_change"] > 1
                    else "❌ Worse" if data["percent_change"] < -1 else "➡️ Same"
                )

                f.write(
                    f"| {key} | {data['baseline']:.4f} | {data['comparison']:.4f} | "
                    f"{data['absolute_change']:+.4f} | {data['percent_change']:+.2f}% | {status} |\n"
                )

            f.write("\n")

            # Performance metrics table
            f.write("## Performance Metrics Comparison\n\n")
            f.write("| Metric | Baseline | Comparison | Change | % Change | Status |\n")
            f.write("|--------|----------|------------|--------|----------|--------|\n")

            for key, data in changes["performance"].items():
                # Lower is better for latency
                status = (
                    "✅ Faster"
                    if data["improved"] and abs(data["percent_change"]) > 5
                    else (
                        "❌ Slower"
                        if not data["improved"] and abs(data["percent_change"]) > 5
                        else "➡️ Same"
                    )
                )

                f.write(
                    f"| {key} | {data['baseline']:.2f}ms | {data['comparison']:.2f}ms | "
                    f"{data['absolute_change']:+.2f}ms | {data['percent_change']:+.2f}% | {status} |\n"
                )

            f.write("\n")

            # Key observations
            f.write("## Key Observations\n\n")

            mrr_change = changes["quality"]["mrr"]["percent_change"]
            if abs(mrr_change) > 5:
                f.write(
                    f"- MRR {'improved' if mrr_change > 0 else 'decreased'} by {abs(mrr_change):.2f}% "
                    f"- {'significant quality improvement!' if mrr_change > 0 else 'needs attention'}\n"
                )

            quality_change = changes["quality"]["overall_quality_score"][
                "percent_change"
            ]
            if abs(quality_change) > 5:
                f.write(
                    f"- Overall quality score {'improved' if quality_change > 0 else 'decreased'} by {abs(quality_change):.2f}%\n"
                )

            latency_change = changes["performance"]["avg_query_time_ms"][
                "percent_change"
            ]
            if abs(latency_change) > 10:
                f.write(
                    f"- Query latency {'decreased' if latency_change < 0 else 'increased'} by {abs(latency_change):.2f}% "
                    f"- {'great performance gain!' if latency_change < 0 else 'performance regression'}\n"
                )

            if changes["summary"]["regressions"] > changes["summary"]["improvements"]:
                f.write(
                    "\n⚠️ **Warning:** More regressions than improvements detected. Review changes carefully.\n"
                )
            elif changes["summary"]["improvements"] > changes["summary"]["regressions"]:
                f.write(
                    "\n✅ **Success:** More improvements than regressions. Good progress!\n"
                )

            f.write("\n---\n\n")
            f.write("*Generated by RAE Benchmark Comparison Tool*\n")

        print("   ✅ Report generated")


def main():
    parser = argparse.ArgumentParser(description="Compare two RAE benchmark results")
    parser.add_argument(
        "baseline", type=str, help="Baseline benchmark result (JSON file)"
    )
    parser.add_argument(
        "comparison", type=str, help="Comparison benchmark result (JSON file)"
    )
    parser.add_argument(
        "--output", type=str, help="Output file for comparison report (Markdown)"
    )

    args = parser.parse_args()

    baseline_file = Path(args.baseline)
    comparison_file = Path(args.comparison)

    if not baseline_file.exists():
        print(f"❌ Baseline file not found: {baseline_file}")
        sys.exit(1)

    if not comparison_file.exists():
        print(f"❌ Comparison file not found: {comparison_file}")
        sys.exit(1)

    print("🔍 RAE Benchmark Comparison Tool")
    print("=" * 60)

    comparator = BenchmarkComparator(baseline_file, comparison_file)

    try:
        comparator.load_results()
        changes = comparator.calculate_changes()
        comparator.print_summary(changes)

        if args.output:
            output_file = Path(args.output)
            comparator.generate_markdown_report(output_file, changes)

        print("\n✅ Comparison complete!")

    except Exception as e:
        print(f"\n❌ Comparison failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
