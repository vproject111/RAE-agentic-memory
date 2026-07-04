#!/usr/bin/env python3
"""
Mathematical Metrics Report Generator

Generates comprehensive reports from mathematical benchmark results.

Usage:
    python generate_math_report.py --results results/academic_lite_*.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class MathReportGenerator:
    """Generate reports from mathematical metrics"""

    def __init__(self, results_files: List[Path], output_file: Path):
        self.results_files = results_files
        self.output_file = output_file
        self.results_data: List[Dict[str, Any]] = []

    def load_results(self):
        """Load all result files"""
        print(f"📂 Loading {len(self.results_files)} result files...")

        for file_path in self.results_files:
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    self.results_data.append(
                        {
                            "file": file_path.name,
                            "data": data,
                        }
                    )
                    print(f"   ✅ Loaded: {file_path.name}")
            except Exception as e:
                print(f"   ❌ Failed to load {file_path.name}: {e}")

    def generate_report(self) -> str:
        """Generate markdown report"""
        report = []

        report.append("# RAE Mathematical Metrics Report\n")
        report.append(f"**Generated:** {self._get_timestamp()}\n")
        report.append(f"**Files Analyzed:** {len(self.results_data)}\n")
        report.append("\n---\n")

        # Summary section
        report.append("\n## Executive Summary\n")
        report.append(self._generate_summary())

        # Detailed metrics for each file
        for result in self.results_data:
            report.append(f"\n## Results: {result['file']}\n")
            report.append(self._generate_detailed_metrics(result["data"]))

        # Comparative analysis (if multiple files)
        if len(self.results_data) > 1:
            report.append("\n## Comparative Analysis\n")
            report.append(self._generate_comparative_analysis())

        # Recommendations
        report.append("\n## Recommendations\n")
        report.append(self._generate_recommendations())

        return "".join(report)

    def _generate_summary(self) -> str:
        """Generate executive summary"""
        summary = []

        for result in self.results_data:
            data = result["data"]

            if "math" not in data.get("metrics", {}):
                continue

            math_metrics = data["metrics"]["math"]

            summary.append(f"\n### {result['file']}\n")

            # Structure metrics
            if "structure" in math_metrics:
                structure = math_metrics["structure"]
                if "graph_connectivity_score" in structure:
                    gcs = structure["graph_connectivity_score"]["value"]
                    summary.append(f"- **Graph Connectivity:** {gcs:.4f}\n")
                if "semantic_coherence_score" in structure:
                    scs = structure["semantic_coherence_score"]["value"]
                    summary.append(f"- **Semantic Coherence:** {scs:.4f}\n")
                if "graph_entropy" in structure:
                    entropy = structure["graph_entropy"]["value"]
                    summary.append(f"- **Graph Entropy:** {entropy:.4f}\n")

            # Dynamics metrics
            if "dynamics" in math_metrics:
                dynamics = math_metrics["dynamics"]
                if "memory_drift_index" in dynamics:
                    mdi = dynamics["memory_drift_index"]["value"]
                    summary.append(f"- **Memory Drift:** {mdi:.4f}\n")
                if "structural_drift" in dynamics:
                    drift = dynamics["structural_drift"]["value"]
                    summary.append(f"- **Structural Drift:** {drift:.4f}\n")

            # Policy metrics
            if "policy" in math_metrics:
                policy = math_metrics["policy"]
                if "optimal_retrieval_ratio" in policy:
                    orr = policy["optimal_retrieval_ratio"]["value"]
                    summary.append(f"- **Optimal Retrieval Ratio:** {orr:.4f}\n")

        return "".join(summary)

    def _generate_detailed_metrics(self, data: Dict[str, Any]) -> str:
        """Generate detailed metrics section"""
        details = []

        if "math" not in data.get("metrics", {}):
            details.append("*No mathematical metrics found in this result.*\n")
            return "".join(details)

        math_metrics = data["metrics"]["math"]

        # Structure Metrics
        if "structure" in math_metrics:
            details.append("\n### Structure Metrics\n")
            details.append(self._format_metric_category(math_metrics["structure"]))

        # Dynamics Metrics
        if "dynamics" in math_metrics:
            details.append("\n### Dynamics Metrics\n")
            details.append(self._format_metric_category(math_metrics["dynamics"]))

        # Policy Metrics
        if "policy" in math_metrics:
            details.append("\n### Policy Metrics\n")
            details.append(self._format_metric_category(math_metrics["policy"]))

        return "".join(details)

    def _format_metric_category(self, metrics: Dict[str, Any]) -> str:
        """Format a category of metrics"""
        output = []

        for metric_name, metric_data in metrics.items():
            if not isinstance(metric_data, dict):
                continue

            value = metric_data.get("value", "N/A")
            metadata = metric_data.get("metadata", {})

            # Format metric name
            display_name = metric_name.replace("_", " ").title()
            output.append(f"\n#### {display_name}\n")
            output.append(
                f"**Value:** `{value:.4f if isinstance(value, float) else value}`\n"
            )

            # Add metadata if available
            if metadata:
                output.append("\n**Details:**\n")
                for key, val in metadata.items():
                    display_key = key.replace("_", " ").title()
                    formatted_val = f"{val:.4f}" if isinstance(val, float) else str(val)
                    output.append(f"- {display_key}: `{formatted_val}`\n")

        return "".join(output)

    def _generate_comparative_analysis(self) -> str:
        """Generate comparative analysis across multiple results"""
        analysis = []

        analysis.append("\n*Comparing metrics across multiple benchmark runs...*\n")

        # TODO: Implement detailed comparative analysis
        # This would include:
        # - Trend analysis
        # - Statistical comparisons
        # - Performance regression detection

        return "".join(analysis)

    def _generate_recommendations(self) -> str:
        """Generate recommendations based on metrics"""
        recommendations = []

        # Analyze latest results
        if not self.results_data:
            return "*No data available for recommendations.*\n"

        latest = self.results_data[-1]["data"]

        if "math" not in latest.get("metrics", {}):
            return "*No mathematical metrics for recommendations.*\n"

        math_metrics = latest["metrics"]["math"]

        # Structure recommendations
        if "structure" in math_metrics:
            structure = math_metrics["structure"]

            if "graph_connectivity_score" in structure:
                gcs = structure["graph_connectivity_score"]["value"]
                if gcs < 1.0:
                    recommendations.append(
                        "- ⚠️ **Low Graph Connectivity**: Consider adding more memory relationships\n"
                    )
                else:
                    recommendations.append(
                        "- ✅ **Good Graph Connectivity**: Memory is well-integrated\n"
                    )

            if "semantic_coherence_score" in structure:
                scs = structure["semantic_coherence_score"]["value"]
                if scs < 0.6:
                    recommendations.append(
                        "- ⚠️ **Low Semantic Coherence**: Memory connections may be weak\n"
                    )
                else:
                    recommendations.append(
                        "- ✅ **Good Semantic Coherence**: Memory relationships are meaningful\n"
                    )

        # Dynamics recommendations
        if "dynamics" in math_metrics:
            dynamics = math_metrics["dynamics"]

            if "memory_drift_index" in dynamics:
                mdi = dynamics["memory_drift_index"]["value"]
                if mdi > 0.5:
                    recommendations.append(
                        "- ⚠️ **High Memory Drift**: Consider memory consolidation\n"
                    )
                else:
                    recommendations.append(
                        "- ✅ **Stable Memory**: Low drift indicates good retention\n"
                    )

        # Policy recommendations
        if "policy" in math_metrics:
            policy = math_metrics["policy"]

            if "optimal_retrieval_ratio" in policy:
                orr = policy["optimal_retrieval_ratio"]["value"]
                if orr < 0.7:
                    recommendations.append(
                        "- ⚠️ **Suboptimal Retrieval**: Consider improving search algorithms\n"
                    )
                else:
                    recommendations.append(
                        "- ✅ **Good Retrieval Quality**: System finds relevant memories effectively\n"
                    )

        if not recommendations:
            recommendations.append("*No specific recommendations at this time.*\n")

        return "".join(recommendations)

    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save_report(self):
        """Generate and save report"""
        report_content = self.generate_report()

        with open(self.output_file, "w") as f:
            f.write(report_content)

        print(f"\n✅ Report generated: {self.output_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate mathematical metrics report")
    parser.add_argument(
        "--results",
        type=str,
        nargs="+",
        required=True,
        help="Result JSON files to analyze",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarking/results/math_report.md",
        help="Output markdown file",
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    results_files = [project_root / f for f in args.results]
    output_file = project_root / args.output

    # Verify files exist
    missing = [f for f in results_files if not f.exists()]
    if missing:
        print(f"❌ Files not found: {[str(f) for f in missing]}")
        sys.exit(1)

    # Generate report
    generator = MathReportGenerator(results_files, output_file)
    generator.load_results()
    generator.save_report()


if __name__ == "__main__":
    main()
