#!/usr/bin/env python3
"""
Collect performance metrics for drift detection.
Integrates with existing benchmarking infrastructure.

Part of RAE CI Quality Implementation - Iteration 3: Zero Drift
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil not available, memory metrics will be limited", file=sys.stderr)


def collect_test_timing():
    """Run tests and collect timing metrics."""
    print("📊 Collecting timing metrics...")
    start = time.time()
    result = subprocess.run(
        [
            "pytest",
            "-m",
            "not integration and not llm and not contract and not performance",
            "--tb=no",
            "-q",
            "--durations=50",
        ],
        capture_output=True,
        text=True,
    )
    duration = time.time() - start

    # Parse slowest tests from durations output
    slowest_tests = []
    for line in result.stdout.split("\n"):
        if "s call" in line:
            parts = line.strip().split()
            if len(parts) >= 3:
                try:
                    test_duration = float(parts[0].replace("s", ""))
                    slowest_tests.append({"test": parts[-1], "duration": test_duration})
                except (ValueError, IndexError):
                    pass

    return {
        "total_duration_seconds": round(duration, 2),
        "slowest_tests": slowest_tests[:10],
        "test_count": result.stdout.count("passed") + result.stdout.count("failed"),
    }


def collect_memory_metrics():
    """Collect memory usage during test run."""
    if not PSUTIL_AVAILABLE:
        return {
            "memory_before_mb": 0,
            "memory_after_mb": 0,
            "memory_peak_mb": 0,
            "memory_delta_mb": 0,
            "note": "psutil not available",
        }

    print("💾 Collecting memory metrics...")
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB

    subprocess.run(
        [
            "pytest",
            "-m",
            "not integration and not llm and not contract and not performance",
            "--tb=no",
            "-q",
            "-x",
        ],
        capture_output=True,
    )

    mem_after = process.memory_info().rss / 1024 / 1024
    mem_peak = mem_after  # Simplified - would need memory_profiler for accurate peak

    return {
        "memory_before_mb": round(mem_before, 2),
        "memory_after_mb": round(mem_after, 2),
        "memory_peak_mb": round(mem_peak, 2),
        "memory_delta_mb": round(mem_after - mem_before, 2),
    }


def collect_log_metrics():
    """Collect log level counts from test run."""
    print("📝 Collecting log metrics...")
    result = subprocess.run(
        [
            "pytest",
            "-m",
            "not integration and not llm and not contract and not performance",
            "--tb=no",
            "-q",
            "-s",
        ],
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    # Count log levels (exclude pytest markers like "error::")
    warning_count = output.lower().count("warning")
    error_count = output.lower().count("error") - output.lower().count("error::")
    critical_count = output.lower().count("critical")

    return {
        "warning_count": warning_count,
        "error_count": error_count,
        "critical_count": critical_count,
        "log_volume_lines": len(output.split("\n")),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="metrics_current.json")
    parser.add_argument("--include-memory", action="store_true")
    parser.add_argument("--include-timing", action="store_true")
    args = parser.parse_args()

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_sha": subprocess.getoutput("git rev-parse HEAD"),
        "git_branch": subprocess.getoutput("git rev-parse --abbrev-ref HEAD"),
        "collector_version": "1.0.0",
    }

    metrics["timing"] = collect_test_timing()

    if args.include_memory:
        metrics["memory"] = collect_memory_metrics()

    metrics["logs"] = collect_log_metrics()

    with open(args.output, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"✅ Metrics saved to {args.output}")


if __name__ == "__main__":
    main()
