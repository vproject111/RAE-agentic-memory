#!/usr/bin/env python3
"""
Check coverage trend to prevent regressions.

Usage:
    python scripts/check_coverage_trend.py current_coverage.xml previous_coverage.xml

Exit codes:
    0: Coverage improved or maintained
    1: Coverage decreased significantly (>2%)
    2: Error reading coverage files
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def parse_coverage(xml_path: str) -> float:
    """Parse coverage percentage from coverage.xml"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Coverage.py format: <coverage line-rate="0.75" ...>
        line_rate = float(root.attrib.get("line-rate", 0))
        return line_rate * 100
    except Exception as e:
        print(f"Error parsing {xml_path}: {e}")
        return 0.0


def compare_coverage(current_file: str, previous_file: str, threshold: float = 2.0):
    """Compare current vs previous coverage"""

    current_cov = parse_coverage(current_file)
    previous_cov = parse_coverage(previous_file) if Path(previous_file).exists() else 0

    if current_cov == 0 and previous_cov == 0:
        print("⚠️  No coverage data available")
        return 0

    if previous_cov == 0:
        print(f"✅ Initial coverage: {current_cov:.2f}%")
        return 0

    diff = current_cov - previous_cov

    print(f"📊 Coverage: {current_cov:.2f}% (was {previous_cov:.2f}%)")

    if diff < -threshold:
        print(f"❌ Coverage decreased by {abs(diff):.2f}% (threshold: {threshold}%)")
        print("   This is not acceptable! Add more tests.")
        return 1
    elif diff < 0:
        print(f"⚠️  Coverage decreased by {abs(diff):.2f}% (within threshold)")
        return 0
    elif diff > 0:
        print(f"✅ Coverage improved by {diff:.2f}%!")
        return 0
    else:
        print(f"✅ Coverage maintained at {current_cov:.2f}%")
        return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python check_coverage_trend.py current.xml previous.xml")
        sys.exit(2)

    current_file = sys.argv[1]
    previous_file = sys.argv[2]

    if not Path(current_file).exists():
        print(f"❌ Current coverage file not found: {current_file}")
        sys.exit(2)

    exit_code = compare_coverage(current_file, previous_file)
    sys.exit(exit_code)
