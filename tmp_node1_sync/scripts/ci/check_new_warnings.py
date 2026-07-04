#!/usr/bin/env python3
"""
Check for new warnings in test output.
Exit 1 if unknown warnings detected.

Part of RAE CI Quality Implementation - Iteration 1: Zero Warnings
"""

import re
import sys
from pathlib import Path

KNOWN_EXTERNAL_WARNINGS = [
    r"google\._upb\._message",
    r"tldextract.*socket",
    r"spacy\.cli\._util",
    r"Can't initialize NVML",
]


def main():
    if len(sys.argv) < 2:
        print("Usage: check_new_warnings.py <warnings.log>")
        sys.exit(2)

    log_file = Path(sys.argv[1])
    content = log_file.read_text()

    # Find all warnings
    warning_pattern = r"(.*Warning.*|.*DeprecationWarning.*)"
    warnings = re.findall(warning_pattern, content, re.IGNORECASE)

    unknown_warnings = []
    for w in warnings:
        is_known = any(re.search(pattern, w) for pattern in KNOWN_EXTERNAL_WARNINGS)
        if not is_known and "RAE" not in w and "apps/" in w:
            unknown_warnings.append(w)

    if unknown_warnings:
        print(f"❌ UNKNOWN WARNINGS DETECTED ({len(unknown_warnings)}):")
        for w in unknown_warnings[:10]:
            print(f"  - {w}")
        sys.exit(1)

    print("✅ No new warnings detected")
    sys.exit(0)


if __name__ == "__main__":
    main()
