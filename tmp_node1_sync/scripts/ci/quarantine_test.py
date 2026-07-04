#!/usr/bin/env python3
"""
Move flaky test to quarantine directory.

Usage:
  python quarantine_test.py tests/api/v1/test_cache.py::test_flaky_function

Part of RAE CI Quality Implementation - Iteration 2: Zero Flake
"""

import argparse
import shutil
from datetime import datetime
from pathlib import Path


def quarantine_test(nodeid: str, reason: str = "flaky"):
    """Move test to quarantine based on nodeid."""
    # Parse nodeid: tests/api/v1/test_cache.py::test_function
    parts = nodeid.split("::")
    file_path = Path(parts[0])

    if not file_path.exists():
        print(f"❌ Error: {file_path} not found")
        return False

    # Create quarantine directory mirroring original structure
    quarantine_base = Path("tests/quarantine")

    # Extract relative path from tests/
    if file_path.is_relative_to("tests"):
        relative_path = file_path.relative_to("tests")
    elif file_path.is_relative_to("apps"):
        # Handle apps/memory_api/tests/ structure
        relative_path = file_path
    else:
        relative_path = file_path

    quarantine_path = quarantine_base / relative_path.parent
    quarantine_path.mkdir(parents=True, exist_ok=True)

    # Copy file to quarantine
    target = quarantine_path / file_path.name
    shutil.copy(file_path, target)

    # Add quarantine marker at the top
    content = target.read_text()
    marker = f'''"""
QUARANTINED: {reason}
Original: {file_path}
Nodeid: {nodeid}
Date: {datetime.now().isoformat()}

This test has been identified as flaky and moved to quarantine.
See tests/quarantine/README.md for fixing guidelines.
"""
import pytest

pytestmark = pytest.mark.skip(reason="Quarantined flaky test - {reason}")

'''
    target.write_text(marker + content)

    print(f"✅ Test quarantined: {target}")
    print("📝 Next step: Create ticket to fix and move back to main suite")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("nodeid", help="Test nodeid to quarantine")
    parser.add_argument("--reason", default="flaky", help="Quarantine reason")
    args = parser.parse_args()

    success = quarantine_test(args.nodeid, args.reason)
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
