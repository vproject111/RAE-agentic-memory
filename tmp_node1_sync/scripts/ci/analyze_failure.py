#!/usr/bin/env python3
"""
Analyze CI failure and generate context for fix generation.

Part of RAE CI Quality Implementation - Iteration 4: Auto-Healing CI

This module analyzes CI failure logs and artifacts to classify failures
and extract context that can be used by an AI agent to generate fixes.

Usage:
    python analyze_failure.py --workflow-run-id 123456 --artifacts-dir ./artifacts --output failure_context.json

Exit codes:
    0 - Analysis complete (check output for can_auto_fix)
    1 - Error during analysis
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class FailureAnalyzer:
    """Analyze CI failures and categorize them."""

    # Patterns for different types of fixable failures
    FIX_PATTERNS: Dict[str, Dict[str, Any]] = {
        "warning": {
            "patterns": [
                r"DeprecationWarning",
                r"UserWarning",
                r"PydanticDeprecatedSince20",
                r"FutureWarning",
                r"PendingDeprecationWarning",
                r"ResourceWarning",
            ],
            "can_auto_fix": True,
            "confidence": "high",
        },
        "import_error": {
            "patterns": [
                r"ModuleNotFoundError",
                r"ImportError",
                r"No module named",
            ],
            "can_auto_fix": True,
            "confidence": "high",
        },
        "type_error": {
            "patterns": [
                r"TypeError.*argument",
                r"mypy.*error",
                r"Incompatible types",
            ],
            "can_auto_fix": True,
            "confidence": "medium",
        },
        "flaky_test": {
            "patterns": [
                r"FAILED.*::.*test_",
                r"error.*timeout",
                r"TimeoutError",
                r"AssertionError.*eventually",
            ],
            "can_auto_fix": True,
            "confidence": "medium",
        },
        "lint": {
            "patterns": [
                r"ruff.*error",
                r"black.*would reformat",
                r"isort.*error",
                r"flake8.*E\d{3}",
            ],
            "can_auto_fix": True,
            "confidence": "high",
        },
        "drift": {
            "patterns": [
                r"Regression detected",
                r"SLO violation",
                r"threshold exceeded",
                r"Performance degradation",
            ],
            "can_auto_fix": False,
            "confidence": "low",
        },
    }

    def __init__(self, artifacts_dir: Path):
        """Initialize analyzer with artifacts directory.

        Args:
            artifacts_dir: Path to directory containing CI artifacts
        """
        self.artifacts_dir = artifacts_dir
        self.logs: List[str] = []
        self.failures: List[Dict[str, Any]] = []

    def load_artifacts(self) -> None:
        """Load all log files from artifacts.

        Reads .log files and parses .json files for test results.
        """
        if not self.artifacts_dir.exists():
            print(f"Warning: Artifacts directory not found: {self.artifacts_dir}")
            return

        # Load .log files
        for log_file in self.artifacts_dir.rglob("*.log"):
            try:
                content = log_file.read_text(encoding="utf-8", errors="replace")
                self.logs.append(content)
            except Exception as e:
                print(f"Warning: Failed to read {log_file}: {e}")

        # Load .txt files (often contain logs too)
        for txt_file in self.artifacts_dir.rglob("*.txt"):
            try:
                content = txt_file.read_text(encoding="utf-8", errors="replace")
                self.logs.append(content)
            except Exception as e:
                print(f"Warning: Failed to read {txt_file}: {e}")

        # Parse JSON test reports
        for json_file in self.artifacts_dir.rglob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                self._process_json_report(data)
            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON in {json_file}: {e}")
            except Exception as e:
                print(f"Warning: Failed to parse {json_file}: {e}")

    def _process_json_report(self, data: Dict[str, Any]) -> None:
        """Process a JSON test report and extract failures.

        Args:
            data: Parsed JSON data from test report
        """
        # pytest-json-report format
        if "tests" in data:
            for test in data["tests"]:
                if test.get("outcome") == "failed":
                    self.failures.append(test)

        # JUnit XML converted to JSON format
        if "testsuites" in data:
            for suite in data.get("testsuites", []):
                for case in suite.get("testcases", []):
                    if case.get("failure") or case.get("error"):
                        self.failures.append(
                            {
                                "nodeid": f"{case.get('classname', '')}::{case.get('name', '')}",
                                "outcome": "failed",
                                "message": case.get("failure", {}).get("message", "")
                                or case.get("error", {}).get("message", ""),
                            }
                        )

    def classify_failure(self) -> Tuple[str, bool, str]:
        """Classify the type of failure.

        Returns:
            Tuple of (fix_type, can_auto_fix, confidence)
        """
        all_text = "\n".join(self.logs)

        # Also add failure messages to text for classification
        for failure in self.failures:
            if "message" in failure:
                all_text += f"\n{failure['message']}"
            if "longrepr" in failure:
                all_text += f"\n{failure['longrepr']}"

        for fix_type, config in self.FIX_PATTERNS.items():
            for pattern in config["patterns"]:
                if re.search(pattern, all_text, re.IGNORECASE):
                    return (fix_type, config["can_auto_fix"], config["confidence"])

        return ("unknown", False, "none")

    def extract_context(self) -> Dict[str, Any]:
        """Extract relevant context for fix generation.

        Returns:
            Dictionary with classification and context for fix generation
        """
        fix_type, can_auto_fix, confidence = self.classify_failure()

        context: Dict[str, Any] = {
            "fix_type": fix_type,
            "can_auto_fix": can_auto_fix,
            "confidence": confidence,
            "failures": self.failures[:10],  # Limit to 10
            "relevant_logs": self._extract_relevant_logs(fix_type),
            "affected_files": self._extract_affected_files(),
            "suggestions": self._get_suggestions(fix_type),
            "summary": self._generate_summary(fix_type),
        }

        return context

    def _extract_relevant_logs(self, fix_type: str, max_lines: int = 50) -> List[str]:
        """Extract most relevant log lines.

        Args:
            fix_type: The classified failure type
            max_lines: Maximum number of lines to extract

        Returns:
            List of relevant log lines
        """
        relevant: List[str] = []
        all_text = "\n".join(self.logs)

        patterns = self.FIX_PATTERNS.get(fix_type, {}).get("patterns", [])

        for line in all_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
                relevant.append(line)
            if len(relevant) >= max_lines:
                break

        return relevant

    def _extract_affected_files(self) -> List[str]:
        """Extract file paths from failures.

        Returns:
            List of unique file paths affected by failures
        """
        affected: List[str] = []

        for failure in self.failures:
            nodeid = failure.get("nodeid", "")
            if "::" in nodeid:
                file_path = nodeid.split("::")[0]
                if file_path and file_path not in affected:
                    affected.append(file_path)

        # Also extract file paths from logs using patterns
        all_text = "\n".join(self.logs)

        # Match patterns like "file.py:123" or "tests/test_foo.py::test_bar"
        file_patterns = [
            r"([\w/]+\.py):\d+",
            r"(tests/[\w/]+\.py)::",
            r"File \"([^\"]+\.py)\"",
        ]

        for pattern in file_patterns:
            for match in re.finditer(pattern, all_text):
                file_path = match.group(1)
                if file_path and file_path not in affected:
                    affected.append(file_path)
                    if len(affected) >= 20:  # Limit
                        break

        return affected

    def _get_suggestions(self, fix_type: str) -> List[str]:
        """Get fix suggestions based on failure type.

        Args:
            fix_type: The classified failure type

        Returns:
            List of suggested fixes
        """
        suggestions: Dict[str, List[str]] = {
            "warning": [
                "Update deprecated API calls",
                "Add filterwarnings to pytest.ini",
                "Use pytest.warns() for expected warnings",
                "Replace datetime.utcnow() with datetime.now(timezone.utc)",
            ],
            "import_error": [
                "Add missing dependency to requirements.txt",
                "Fix import path",
                "Add __init__.py if needed",
                "Check for circular imports",
            ],
            "type_error": [
                "Fix function signature",
                "Add type hints",
                "Update caller to match new signature",
                "Check for None values",
            ],
            "flaky_test": [
                "Add explicit waits for async operations",
                "Mock external dependencies",
                "Add test isolation with fixtures",
                "Add retry decorator for network tests",
            ],
            "lint": [
                "Run black --fix",
                "Run isort --fix",
                "Fix ruff violations",
                "Run ruff check --fix",
            ],
            "drift": [
                "Review performance-critical code",
                "Check for N+1 queries",
                "Optimize slow tests",
                "Review recent changes for regressions",
            ],
        }
        return suggestions.get(fix_type, ["Manual investigation required"])

    def _generate_summary(self, fix_type: str) -> str:
        """Generate a human-readable summary of the failure.

        Args:
            fix_type: The classified failure type

        Returns:
            Summary string
        """
        failure_count = len(self.failures)
        affected_count = len(self._extract_affected_files())

        summaries = {
            "warning": f"Found {failure_count} warning-related failures affecting {affected_count} files",
            "import_error": f"Found {failure_count} import errors affecting {affected_count} files",
            "type_error": f"Found {failure_count} type errors affecting {affected_count} files",
            "flaky_test": f"Found {failure_count} potentially flaky test failures in {affected_count} files",
            "lint": f"Found linting issues in {affected_count} files",
            "drift": f"Found {failure_count} drift/regression issues",
            "unknown": f"Found {failure_count} failures of unknown type",
        }

        return summaries.get(fix_type, f"Found {failure_count} failures")


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Analyze CI failures and generate context for fix generation"
    )
    parser.add_argument(
        "--workflow-run-id", required=True, help="GitHub Actions workflow run ID"
    )
    parser.add_argument(
        "--artifacts-dir", required=True, help="Directory containing CI artifacts"
    )
    parser.add_argument(
        "--output",
        default="failure_context.json",
        help="Output file for failure context (default: failure_context.json)",
    )
    args = parser.parse_args()

    try:
        analyzer = FailureAnalyzer(Path(args.artifacts_dir))
        analyzer.load_artifacts()
        context = analyzer.extract_context()

        context["workflow_run_id"] = args.workflow_run_id

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        # Print summary
        can_fix_indicator = "[AUTO-FIXABLE]" if context["can_auto_fix"] else "[MANUAL]"
        print(f"{can_fix_indicator} Analysis complete: {context['fix_type']}")
        print(f"   Can auto-fix: {context['can_auto_fix']}")
        print(f"   Confidence: {context['confidence']}")
        print(f"   Summary: {context['summary']}")
        print(f"   Context saved to: {args.output}")

        return 0

    except Exception as e:
        print(f"Error during analysis: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
