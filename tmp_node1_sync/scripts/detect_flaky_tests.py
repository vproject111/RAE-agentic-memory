#!/usr/bin/env python3
"""
Detect flaky tests by analyzing multiple test runs.

Usage:
    python scripts/detect_flaky_tests.py report_1.json report_2.json report_3.json
"""

import json
import sys
from collections import defaultdict


def load_test_report(filepath: str) -> dict:
    """Load pytest JSON report"""
    try:
        with open(filepath) as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Error loading {filepath}: {e}")
        return {"tests": []}


def analyze_flakiness(report_files: list) -> dict:
    """Analyze test results across multiple runs"""
    test_outcomes = defaultdict(list)

    for report_file in report_files:
        report = load_test_report(report_file)
        tests = report.get("tests", [])

        for test in tests:
            test_id = test.get("nodeid", "unknown")
            outcome = test.get("outcome", "unknown")
            test_outcomes[test_id].append(outcome)

    return test_outcomes


def find_flaky_tests(test_outcomes: dict, min_runs: int = 3) -> list:
    """Find tests with inconsistent outcomes"""
    flaky = []

    for test_id, outcomes in test_outcomes.items():
        if len(outcomes) < min_runs:
            continue

        # Test is flaky if it has different outcomes
        if len(set(outcomes)) > 1:
            flaky.append(
                {
                    "test": test_id,
                    "outcomes": outcomes,
                    "pass_rate": outcomes.count("passed") / len(outcomes),
                }
            )

    return flaky


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python detect_flaky_tests.py report1.json report2.json [report3.json ...]"
        )
        sys.exit(2)

    report_files = sys.argv[1:]

    print(f"🔍 Analyzing {len(report_files)} test runs for flakiness...")
    print()

    test_outcomes = analyze_flakiness(report_files)
    flaky_tests = find_flaky_tests(test_outcomes)

    if not flaky_tests:
        print("✅ No flaky tests detected!")
        sys.exit(0)

    print(f"❌ Found {len(flaky_tests)} flaky tests:")
    print()

    # Sort by pass rate (least reliable first)
    flaky_tests.sort(key=lambda x: x["pass_rate"])

    for flaky in flaky_tests[:20]:  # Show top 20
        test = flaky["test"]
        outcomes = flaky["outcomes"]
        pass_rate = flaky["pass_rate"] * 100

        print(f"  {test}")
        print(f"    Pass rate: {pass_rate:.0f}%")
        print(f"    Outcomes: {outcomes}")
        print()

    if len(flaky_tests) > 20:
        print(f"  ... and {len(flaky_tests) - 20} more flaky tests")
        print()

    print("⚠️  Flaky tests reduce CI reliability!")
    print("   Fix them by:")
    print("   1. Adding explicit waits for async operations")
    print("   2. Using fixtures to ensure clean state")
    print("   3. Avoiding time-based assertions")
    print("   4. Mocking external dependencies")

    sys.exit(1)


if __name__ == "__main__":
    main()
