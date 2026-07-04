#!/usr/bin/env python3
"""
Enhanced flaky test analyzer.
Analyzes multiple pytest-json-report outputs to detect inconsistent tests.

Part of RAE CI Quality Implementation - Iteration 2: Zero Flake
"""

import argparse
import json
from collections import defaultdict
from typing import Dict, List


def load_reports(files: List[str]) -> List[Dict]:
    """Load pytest-json-report JSON files."""
    reports = []
    for f in files:
        with open(f) as fp:
            reports.append(json.load(fp))
    return reports


def analyze_flakiness(reports: List[Dict], min_runs: int = 3) -> Dict:
    """Analyze test outcomes across runs."""
    outcomes = defaultdict(list)

    for report in reports:
        for test in report.get("tests", []):
            nodeid = test.get("nodeid", "unknown")
            outcome = test.get("outcome", "unknown")
            duration = test.get("duration", 0)
            outcomes[nodeid].append({"outcome": outcome, "duration": duration})

    flaky_tests = []
    stable_tests = []

    for nodeid, runs in outcomes.items():
        if len(runs) < min_runs:
            continue

        run_outcomes = [r["outcome"] for r in runs]

        # Test is flaky if it has different outcomes
        if len(set(run_outcomes)) > 1:
            pass_rate = run_outcomes.count("passed") / len(run_outcomes)
            avg_duration = sum(r["duration"] for r in runs) / len(runs)

            flaky_tests.append(
                {
                    "nodeid": nodeid,
                    "outcomes": run_outcomes,
                    "pass_rate": round(pass_rate, 2),
                    "avg_duration_seconds": round(avg_duration, 3),
                    "recommendation": get_recommendation(
                        nodeid, run_outcomes, avg_duration
                    ),
                }
            )
        else:
            stable_tests.append(nodeid)

    return {
        "total_tests": len(outcomes),
        "flaky_tests": sorted(flaky_tests, key=lambda x: x["pass_rate"]),
        "stable_tests_count": len(stable_tests),
        "analysis_runs": len(reports),
    }


def get_recommendation(nodeid: str, outcomes: List[str], duration: float) -> str:
    """Generate fix recommendation based on failure pattern."""
    pass_rate = outcomes.count("passed") / len(outcomes)

    if duration > 5.0:
        return "Consider adding timeout or async wait - long-running test"
    if pass_rate < 0.5:
        return "Test fails frequently - likely timing/race condition issue"
    if "async" in nodeid.lower() or "integration" in nodeid.lower():
        return "Async test - add explicit waits or increase timeouts"
    return "Review for non-deterministic behavior (random, time, external deps)"


def main():
    parser = argparse.ArgumentParser(description="Analyze flaky tests")
    parser.add_argument("reports", nargs="+", help="pytest-json-report files")
    parser.add_argument("--output", "-o", default="flaky_report.json")
    parser.add_argument("--min-runs", type=int, default=3)

    args = parser.parse_args()

    reports = load_reports(args.reports)
    result = analyze_flakiness(reports, args.min_runs)

    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Analysis complete: {len(result['flaky_tests'])} flaky tests found")
    print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
