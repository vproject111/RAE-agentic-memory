#!/usr/bin/env python3
"""
RAE Documentation Consistency Checker

Validates documentation for:
- Doc fragment markers
- Broken internal links
- Duplicate content
- API endpoint consistency (TODO)

Usage:
    python docs/autodoc/autodoc_checker.py [--fix] [file1.md file2.md ...]
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List

# Base paths
DOCS_ROOT = Path(__file__).parent.parent
FRAGMENTS_DIR = DOCS_ROOT / "autodoc" / "doc_fragments"
REPO_ROOT = DOCS_ROOT.parent


class DocChecker:
    """Documentation consistency checker."""

    def __init__(self, fix: bool = False):
        self.fix = fix
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.fixed: List[str] = []

    def check_all(self, files: List[Path] = None) -> bool:
        """Check all documentation files or specific files."""
        if files is None:
            files = list(DOCS_ROOT.rglob("*.md"))
            # Exclude auto-generated
            files = [f for f in files if ".auto-generated" not in str(f)]

        print(f"🔍 Checking {len(files)} documentation files...")

        for file_path in files:
            self.check_file(file_path)

        self.print_summary()
        return len(self.errors) == 0

    def check_file(self, file_path: Path):
        """Check a single documentation file."""
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return

        content = file_path.read_text()

        # 1. Check doc fragments
        self.check_doc_fragments(file_path, content)

        # 2. Check internal links
        self.check_internal_links(file_path, content)

    def check_doc_fragments(self, file_path: Path, content: str):
        """Check for doc fragment markers and validate them."""
        # Find all fragment markers: <!-- RAE_DOC_FRAGMENT:name -->
        pattern = r"<!-- RAE_DOC_FRAGMENT:(\w+) -->"
        matches = re.finditer(pattern, content)

        for match in matches:
            fragment_name = match.group(1)
            fragment_file = FRAGMENTS_DIR / f"{fragment_name}.md"

            if not fragment_file.exists():
                self.errors.append(
                    f"{file_path.relative_to(REPO_ROOT)}: "
                    f"Fragment '{fragment_name}' not found at {fragment_file.relative_to(REPO_ROOT)}"
                )
            else:
                # Fragment exists - could inject it if --fix is enabled
                if self.fix:
                    # TODO: Implement fragment injection
                    pass

    def check_internal_links(self, file_path: Path, content: str):
        """Check for broken internal links."""
        # Find all markdown links: [text](path)
        pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        matches = re.finditer(pattern, content)

        for match in matches:
            match.group(1)
            link_path = match.group(2)

            # Skip external links
            if link_path.startswith(("http://", "https://", "mailto:", "#")):
                continue

            # Resolve relative path
            target_path = self.resolve_relative_path(file_path, link_path)

            if not target_path.exists():
                self.errors.append(
                    f"{file_path.relative_to(REPO_ROOT)}: "
                    f"Broken link to {link_path} (resolved to {target_path.relative_to(REPO_ROOT)})"
                )

    def resolve_relative_path(self, from_file: Path, link: str) -> Path:
        """Resolve relative path from a file."""
        # Remove anchor
        link = link.split("#")[0]

        # Handle relative paths
        if link.startswith("./"):
            link = link[2:]
        elif link.startswith("../"):
            pass  # Already relative
        else:
            # Assume relative to current directory
            pass

        # Resolve from file's directory
        target = (from_file.parent / link).resolve()
        return target

    def print_summary(self):
        """Print summary of checks."""
        print("\n" + "=" * 60)
        print("DOCUMENTATION CHECK SUMMARY")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ {len(self.errors)} ERROR(S):")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} WARNING(S):")
            for warning in self.warnings:
                print(f"  • {warning}")

        if self.fixed:
            print(f"\n🔧 {len(self.fixed)} FIX(ES) APPLIED:")
            for fix in self.fixed:
                print(f"  • {fix}")

        if not self.errors and not self.warnings:
            print("\n✅ All checks passed!")

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="RAE Documentation Consistency Checker"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Automatically fix issues where possible"
    )
    parser.add_argument(
        "files", nargs="*", help="Specific files to check (default: all docs/)"
    )
    args = parser.parse_args()

    # Convert file arguments to Path objects
    files = None
    if args.files:
        files = [Path(f) for f in args.files]

    # Run checker
    checker = DocChecker(fix=args.fix)
    success = checker.check_all(files)

    # Exit with error code if there were errors
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
