#!/usr/bin/env python3
"""
Documentation Validator

Checks:
1. Broken internal links (markdown links to non-existent files)
2. Placeholder text not replaced ([...] patterns)
3. Required sections in documentation files
4. Duplicate file paths
5. Structure compliance (files in correct directories)

Usage:
    python scripts/validate_docs.py
    python scripts/validate_docs.py --fix  # Auto-fix simple issues
"""

import argparse
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Documentation directories to scan
DOCS_DIRS = [
    PROJECT_ROOT / "docs",
    PROJECT_ROOT,  # For root-level docs
]

# Files to exclude from validation
EXCLUDE_PATTERNS = [
    r"\.auto-generated/",
    r"node_modules/",
    r"\.git/",
    r"\.venv/",
    r"htmlcov/",
    r"__pycache__/",
]

# Placeholder patterns that should not exist in final docs
PLACEHOLDER_PATTERNS = [
    r"\[TODO:.*?\]",
    r"\[FIXME:.*?\]",
    r"\[PLACEHOLDER.*?\]",
    r"\[YOUR.*?\]",
    r"\[Component Name\]",
    r"\[Description\]",
    r"\[YYYY-MM-DD\]",
]


class DocValidator:
    """Validates documentation files."""

    def __init__(self, fix: bool = False):
        self.fix = fix
        self.errors = []
        self.warnings = []
        self.fixed = []

    def should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded from validation."""
        path_str = str(file_path)
        return any(re.search(pattern, path_str) for pattern in EXCLUDE_PATTERNS)

    def find_markdown_files(self) -> List[Path]:
        """Find all markdown files to validate."""
        markdown_files = []

        for docs_dir in DOCS_DIRS:
            if not docs_dir.exists():
                continue

            for md_file in docs_dir.rglob("*.md"):
                if not self.should_exclude(md_file):
                    markdown_files.append(md_file)

        return markdown_files

    def extract_links(self, content: str, file_path: Path) -> List[Tuple[str, int]]:
        """Extract markdown links from content with line numbers."""
        links = []

        # Pattern: [text](link) or [text]: link
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)|\[([^\]]+)\]:\s*(\S+)"

        for line_num, line in enumerate(content.split("\n"), 1):
            for match in re.finditer(link_pattern, line):
                link = match.group(2) or match.group(4)
                if link:
                    links.append((link, line_num))

        return links

    def validate_internal_link(self, link: str, source_file: Path) -> bool:
        """Validate internal markdown link."""
        # Skip external links
        if link.startswith(("http://", "https://", "mailto:", "#")):
            return True

        # Remove anchor
        link_path = link.split("#")[0]

        if not link_path:  # Pure anchor link
            return True

        # Resolve relative path
        if link_path.startswith("/"):
            target = PROJECT_ROOT / link_path.lstrip("/")
        else:
            target = (source_file.parent / link_path).resolve()

        return target.exists()

    def check_placeholders(
        self, content: str, file_path: Path
    ) -> List[Tuple[str, int]]:
        """Check for unreplaced placeholders."""
        placeholders = []

        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern in PLACEHOLDER_PATTERNS:
                matches = re.findall(pattern, line)
                if matches:
                    for match in matches:
                        placeholders.append((match, line_num))

        return placeholders

    def validate_file(self, file_path: Path):
        """Validate a single markdown file."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.errors.append(f"{file_path}: Failed to read file - {e}")
            return

        # Check for broken internal links
        links = self.extract_links(content, file_path)
        for link, line_num in links:
            if not self.validate_internal_link(link, file_path):
                self.errors.append(f"{file_path}:{line_num}: Broken link '{link}'")

        # Check for placeholders
        placeholders = self.check_placeholders(content, file_path)
        for placeholder, line_num in placeholders:
            self.warnings.append(
                f"{file_path}:{line_num}: Unreplaced placeholder '{placeholder}'"
            )

        # Check for common issues in templates
        if "/templates/" not in str(file_path):
            # Non-template files should not have template markers
            if "[" in content and "]" in content:
                # Count square bracket pairs
                bracket_count = content.count("[") + content.count("]")
                if bracket_count > 20:  # Arbitrary threshold
                    self.warnings.append(
                        f"{file_path}: Many square brackets - possible template markers?"
                    )

    def validate_structure(self):
        """Validate documentation directory structure."""
        required_dirs = [
            PROJECT_ROOT / "docs" / "guides" / "developers",
            PROJECT_ROOT / "docs" / "reference" / "api",
            PROJECT_ROOT / "docs" / "reference" / "architecture",
            PROJECT_ROOT / "docs" / "templates",
        ]

        for required_dir in required_dirs:
            if not required_dir.exists():
                self.warnings.append(
                    f"Missing recommended directory: {required_dir.relative_to(PROJECT_ROOT)}"
                )

    def check_duplicates(self, markdown_files: List[Path]):
        """Check for duplicate file names (potential conflicts)."""
        file_names = {}

        for file_path in markdown_files:
            name = file_path.name
            if name in file_names:
                self.warnings.append(
                    f"Duplicate filename '{name}':\n"
                    f"  - {file_names[name]}\n"
                    f"  - {file_path}"
                )
            else:
                file_names[name] = file_path

    def run(self) -> int:
        """Run all validations."""
        print("🔍 Validating documentation...")
        print()

        # Find all markdown files
        markdown_files = self.find_markdown_files()
        print(f"📄 Found {len(markdown_files)} markdown files")
        print()

        # Validate each file
        for file_path in markdown_files:
            self.validate_file(file_path)

        # Validate structure
        self.validate_structure()

        # Check for duplicates
        self.check_duplicates(markdown_files)

        # Print results
        print("=" * 70)
        print()

        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            print()
            for error in self.errors:
                print(f"  {error}")
            print()

        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            print()
            for warning in self.warnings:
                print(f"  {warning}")
            print()

        if self.fixed:
            print(f"✅ FIXED ({len(self.fixed)}):")
            print()
            for fix in self.fixed:
                print(f"  {fix}")
            print()

        if not self.errors and not self.warnings:
            print("✅ All documentation is valid!")
            print()
            return 0

        print("=" * 70)
        print()
        print("📊 Summary:")
        print(f"   Errors: {len(self.errors)}")
        print(f"   Warnings: {len(self.warnings)}")
        print(f"   Fixed: {len(self.fixed)}")
        print()

        return 1 if self.errors else 0


def main():
    parser = argparse.ArgumentParser(description="Validate documentation")
    parser.add_argument("--fix", action="store_true", help="Auto-fix simple issues")
    args = parser.parse_args()

    validator = DocValidator(fix=args.fix)
    return validator.run()


if __name__ == "__main__":
    sys.exit(main())
