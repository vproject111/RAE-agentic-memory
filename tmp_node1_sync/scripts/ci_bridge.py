#!/usr/bin/env python3
"""
CI Bridge - Automated Interaction with GitHub Actions
Allows AI Agents to inspect CI failures and retrieve logs/artifacts.
"""

import json
import subprocess
import sys
import time
from typing import Dict, List, Optional


def run_gh_command(args: List[str]) -> str:
    """Run a gh CLI command and return stdout."""
    try:
        result = subprocess.run(
            ["gh"] + args, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running gh command: {e}")
        print(f"Stderr: {e.stderr}")
        return ""


def get_current_branch() -> str:
    """Get the current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "main"


def get_latest_run(branch: str) -> Optional[Dict]:
    """Get the latest workflow run for the given branch."""
    # Fetch runs for the specific branch
    output = run_gh_command(
        [
            "run",
            "list",
            "--branch",
            branch,
            "--limit",
            "1",
            "--json",
            "databaseId,status,conclusion,headBranch,workflowName",
        ]
    )

    if not output:
        return None

    runs = json.loads(output)
    return runs[0] if runs else None


def wait_for_run_completion(run_id: int, poll_interval: int = 10) -> str:
    """Wait for a run to complete and return its conclusion."""
    print(f"Waiting for run {run_id} to complete...")
    while True:
        output = run_gh_command(
            ["run", "view", str(run_id), "--json", "status,conclusion"]
        )

        if not output:
            time.sleep(poll_interval)
            continue

        status_data = json.loads(output)
        if status_data["status"] == "completed":
            return status_data["conclusion"]

        print(f"Status: {status_data['status']}...")
        time.sleep(poll_interval)


def get_failure_logs(run_id: int) -> str:
    """Fetch logs for failed steps."""
    return run_gh_command(["run", "view", str(run_id), "--log-failed"])


def download_artifacts(run_id: int, output_dir: str = "./artifacts"):
    """Download artifacts from the run."""
    run_gh_command(["run", "download", str(run_id), "--dir", output_dir])


def main():
    branch = get_current_branch()
    print(f"Checking CI status for branch: {branch}")

    run = get_latest_run(branch)
    if not run:
        print("No workflow runs found for this branch.")
        sys.exit(0)

    run_id = run["databaseId"]
    status = run["status"]

    print(f"Found run ID: {run_id} (Status: {status})")

    if status != "completed":
        conclusion = wait_for_run_completion(run_id)
    else:
        conclusion = run["conclusion"]

    print(f"Run conclusion: {conclusion}")

    if conclusion == "failure":
        print("\n=== FAILURE LOGS ===")
        logs = get_failure_logs(run_id)
        print(logs)

        print("\nDownloading artifacts...")
        download_artifacts(run_id)
        print("Artifacts downloaded to ./artifacts")

        # Exit with error code to signal the agent that something is wrong
        sys.exit(1)
    else:
        print("CI passed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
