#!/usr/bin/env python3
"""
Check metrics against SLO thresholds.
Generates drift_report.md with results.

Part of RAE CI Quality Implementation - Iteration 3: Zero Drift
"""

import argparse
import json
import sys

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("⚠️  pyyaml not available, using JSON fallback", file=sys.stderr)


def load_slo_config(path: str) -> dict:
    """Load SLO configuration."""
    if not YAML_AVAILABLE:
        # Fallback to hardcoded defaults
        return {
            "timing": {"max_increase_percent": 10},
            "memory": {"max_peak_mb": 2048},
            "logs": {"max_warning": 0, "max_error": 0, "max_critical": 0},
        }

    with open(path) as f:
        return yaml.safe_load(f)


def check_slo(current: dict, baseline: dict, slo: dict) -> dict:
    """Compare current metrics against baseline with SLO thresholds."""
    results = {"status": "PASS", "violations": [], "warnings": [], "metrics": {}}

    # Timing SLO
    if "timing" in current and "timing" in slo:
        current_duration = current["timing"]["total_duration_seconds"]
        # Get baseline from reference (handle different structures)
        baseline_duration = (
            baseline.get("reference_run", {})
            .get("results", {})
            .get("duration_seconds", current_duration)
        )
        if "timing" in baseline:
            baseline_duration = baseline["timing"].get(
                "total_duration_seconds", baseline_duration
            )

        threshold = slo["timing"].get("max_increase_percent", 10)

        increase = (
            (current_duration - baseline_duration) / baseline_duration * 100
            if baseline_duration > 0
            else 0
        )

        results["metrics"]["timing"] = {
            "current": current_duration,
            "baseline": baseline_duration,
            "increase_percent": round(increase, 2),
            "threshold_percent": threshold,
        }

        if increase > threshold:
            results["violations"].append(
                f"Test duration increased by {increase:.1f}% (threshold: {threshold}%)"
            )
            results["status"] = "FAIL"
        elif increase > threshold * 0.7:
            results["warnings"].append(
                f"Test duration approaching threshold: {increase:.1f}%"
            )

    # Memory SLO
    if "memory" in current and "memory" in slo:
        current_mem = current["memory"]["memory_peak_mb"]
        max_mem = slo["memory"].get("max_peak_mb", 2048)

        results["metrics"]["memory"] = {
            "current_peak_mb": current_mem,
            "max_allowed_mb": max_mem,
        }

        if current_mem > max_mem:
            results["violations"].append(
                f"Memory peak {current_mem}MB exceeds limit {max_mem}MB"
            )
            results["status"] = "FAIL"

    # Log SLO
    if "logs" in current and "logs" in slo:
        for level in ["warning", "error", "critical"]:
            count = current["logs"].get(f"{level}_count", 0)
            max_allowed = slo["logs"].get(f"max_{level}", 0)

            results["metrics"][f"log_{level}"] = {
                "count": count,
                "max_allowed": max_allowed,
            }

            if count > max_allowed:
                results["violations"].append(
                    f"{level.upper()} logs: {count} (max: {max_allowed})"
                )
                results["status"] = "FAIL"

    return results


def generate_report(results: dict, current: dict) -> str:
    """Generate Markdown drift report."""
    status_emoji = "✅" if results["status"] == "PASS" else "❌"

    report = f"""## {status_emoji} Drift Detection Report

**Status:** {results["status"]}
**Timestamp:** {current.get("timestamp", "N/A")}
**Branch:** {current.get("git_branch", "N/A")}
**SHA:** {current.get("git_sha", "N/A")[:8]}

### Metrics Summary

| Metric | Current | Baseline | Delta | Threshold | Status |
|--------|---------|----------|-------|-----------|--------|
"""

    for name, data in results["metrics"].items():
        if "current" in data and "baseline" in data:
            delta = data.get("increase_percent", 0)
            threshold = data.get("threshold_percent", 0)
            status = "✅" if delta <= threshold else "❌"
            report += f"| {name} | {data['current']:.2f} | {data['baseline']:.2f} | {delta:+.1f}% | {threshold}% | {status} |\n"
        elif "count" in data:
            status = "✅" if data["count"] <= data["max_allowed"] else "❌"
            report += f"| {name} | {data['count']} | - | - | {data['max_allowed']} | {status} |\n"

    if results["violations"]:
        report += "\n### ❌ Violations\n\n"
        for v in results["violations"]:
            report += f"- {v}\n"

    if results["warnings"]:
        report += "\n### ⚠️ Warnings\n\n"
        for w in results["warnings"]:
            report += f"- {w}\n"

    if results["status"] == "PASS" and not results["warnings"]:
        report += "\n### ✅ All Checks Passed\n\nNo performance regressions detected.\n"

    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", required=True, help="Current metrics JSON")
    parser.add_argument("--baseline", required=True, help="Baseline metrics JSON")
    parser.add_argument("--slo-config", required=True, help="SLO config YAML")
    parser.add_argument(
        "--output", default="drift_report.md", help="Output report file"
    )
    args = parser.parse_args()

    with open(args.current) as f:
        current = json.load(f)
    with open(args.baseline) as f:
        baseline = json.load(f)
    slo = load_slo_config(args.slo_config)

    results = check_slo(current, baseline, slo)
    report = generate_report(results, current)

    with open(args.output, "w") as f:
        f.write(report)

    print(report)
    print(f"\n📄 Report saved to: {args.output}")

    if results["status"] == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
