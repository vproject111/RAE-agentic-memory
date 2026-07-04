#!/usr/bin/env python3
"""
Simple Metrics Tracker for Documentation Automation

Lightweight JSON-based metrics - NO OpenTelemetry overhead.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from typing import Dict


class DocsMetrics:
    """Track documentation automation metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.files_generated = []
        self.errors = []
        self.warnings = []

    def record_file(self, filename: str, generator: str):
        """Record successfully generated file."""
        self.files_generated.append(
            {
                "file": filename,
                "generator": generator,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def record_error(self, generator: str, error: str):
        """Record error in generator."""
        self.errors.append(
            {
                "generator": generator,
                "error": str(error),
                "timestamp": datetime.now().isoformat(),
            }
        )

    def record_warning(self, generator: str, warning: str):
        """Record warning (non-fatal issue)."""
        self.warnings.append(
            {
                "generator": generator,
                "warning": warning,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        duration = time.time() - self.start_time
        success_rate = 0.0
        if len(self.files_generated) + len(self.errors) > 0:
            success_rate = (
                len(self.files_generated)
                / (len(self.files_generated) + len(self.errors))
                * 100
            )

        # Get git info
        try:
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
            ).stdout.strip()
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
            ).stdout.strip()
        except Exception:
            branch, commit = "unknown", "unknown"

        return {
            "run_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": round(duration, 2),
            "status": "success" if len(self.errors) == 0 else "failed",
            "files_generated_count": len(self.files_generated),
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "success_rate": round(success_rate, 2),
            "files_generated": self.files_generated,
            "errors": self.errors,
            "warnings": self.warnings,
            "git_branch": branch,
            "git_commit": commit,
        }

    def save_metrics(
        self, filepath: str = "docs/.auto-generated/metrics/automation-health.json"
    ):
        """Save metrics to JSON file."""
        try:
            metrics = self.to_dict()

            # Ensure directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Save current run
            with open(filepath, "w") as f:
                json.dump(metrics, f, indent=2)

            # Append to history (last 50 runs)
            history_file = filepath.replace(".json", "-history.json")
            history = []

            if os.path.exists(history_file):
                try:
                    with open(history_file, "r") as f:
                        history = json.load(f)
                except Exception:
                    history = []

            history.append(
                {
                    "run_id": metrics["run_id"],
                    "timestamp": metrics["timestamp"],
                    "duration_seconds": metrics["duration_seconds"],
                    "status": metrics["status"],
                    "files_count": metrics["files_generated_count"],
                    "errors_count": metrics["errors_count"],
                }
            )

            # Keep only last 50 runs
            history = history[-50:]

            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)

            print(f"✅ Metrics saved to {filepath}")

        except Exception as e:
            print(f"⚠️  Failed to save metrics: {e}")


# Example usage
if __name__ == "__main__":
    metrics = DocsMetrics()

    # Simulate documentation generation
    metrics.record_file("CHANGELOG.md", "update_changelog")
    metrics.record_file("STATUS.md", "update_status")
    metrics.record_file("TODO.md", "update_todo")
    metrics.record_file("TESTING_STATUS.md", "update_testing_status")

    metrics.save_metrics()

    print("\n📊 Summary:")
    print(f"  - Files: {metrics.to_dict()['files_generated_count']}")
    print(f"  - Duration: {metrics.to_dict()['duration_seconds']}s")
    print(f"  - Status: {metrics.to_dict()['status']}")
