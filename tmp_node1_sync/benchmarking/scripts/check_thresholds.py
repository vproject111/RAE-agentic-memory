#!/usr/bin/env python3
"""
Benchmark threshold checker for CI gate.

Blocks merge if benchmarks regress below defined thresholds.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Define minimum thresholds for each benchmark metric
# These are baseline values - benchmarks must NOT regress below these
THRESHOLDS = {
    "lect_consistency": 1.0,  # Must be 100%
    "mmit_interference": 0.006,  # Max 0.6% interference (99.4% isolation)
    "grdt_coherence": 0.55,  # Must not drop below baseline
    "rst_consistency": 0.60,  # Must not drop below baseline
    "mpeb_adaptation": 0.95,  # Must not drop below baseline
}


def load_latest_results(
    results_dir: str = "benchmarking/results/telemetry",
) -> Optional[Dict]:
    """
    Load latest benchmark results from telemetry.

    Args:
        results_dir: Directory containing telemetry files

    Returns:
        Latest benchmark results or None if not found
    """
    telemetry_dir = Path(results_dir)
    if not telemetry_dir.exists():
        return None

    # Find most recent telemetry file
    json_files = sorted(telemetry_dir.glob("telemetry_*.json"), reverse=True)
    if not json_files:
        return None

    with open(json_files[0]) as f:
        data = json.load(f)

    # Convert to benchmark -> metric -> value format
    results = {}
    for record in data:
        benchmark = record["benchmark"]
        metric = record["metric"]
        value = record["value"]

        metric_key = f"{benchmark.lower()}_{metric}"
        results[metric_key] = value

    return results


def check_thresholds(results: Dict[str, float]) -> tuple[bool, list[str]]:
    """
    Check if results meet minimum thresholds.

    Args:
        results: Dict mapping metric_key -> value

    Returns:
        Tuple of (passed, list of failures)
    """
    failures = []

    for metric, threshold in THRESHOLDS.items():
        if metric not in results:
            failures.append(f"⚠️  Missing metric: {metric}")
            continue

        value = results[metric]

        # For interference metrics (lower is better)
        if "interference" in metric:
            if value > threshold:
                failures.append(
                    f"❌ {metric}: {value:.4f} > {threshold:.4f} (REGRESSION!)"
                )
        # For other metrics (higher is better)
        else:
            if value < threshold:
                failures.append(
                    f"❌ {metric}: {value:.4f} < {threshold:.4f} (REGRESSION!)"
                )

    return len(failures) == 0, failures


def main():
    """Check thresholds and exit with appropriate code."""
    print("=" * 60)
    print("  RAE BENCHMARK THRESHOLD CHECK")
    print("=" * 60)
    print()

    # Load latest results
    results = load_latest_results()

    if results is None:
        print("⚠️  No telemetry data found. Skipping threshold check.")
        print(
            "   Run benchmarks first: python -m benchmarking.nine_five_benchmarks.runner"
        )
        sys.exit(0)  # Don't block CI if no data

    print("Checking thresholds...")
    print()

    # Check thresholds
    passed, failures = check_thresholds(results)

    if passed:
        print("✅ All benchmarks meet minimum thresholds!")
        print()
        print("Current metrics:")
        for metric, value in results.items():
            if metric in THRESHOLDS:
                threshold = THRESHOLDS[metric]
                print(f"  {metric}: {value:.4f} (threshold: {threshold:.4f})")
        print()
        sys.exit(0)
    else:
        print("❌ BENCHMARK REGRESSIONS DETECTED!")
        print()
        for failure in failures:
            print(f"  {failure}")
        print()
        print("Benchmarks have regressed below baseline thresholds.")
        print("Please investigate and fix before merging.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
