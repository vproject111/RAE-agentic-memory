#!/usr/bin/env python3
import json
import subprocess
import urllib.request


def get_last_commit_diff():
    return subprocess.check_output(["git", "diff", "HEAD~1..HEAD"]).decode("utf-8")


def delegate():
    diff = get_last_commit_diff()
    # Using 'code_verify_cycle' to match the currently running agent on node1
    payload = {
        "type": "code_verify_cycle",
        "priority": 10,
        "payload": {
            "prompt": "Review the last commit for strict agnosticism compliance. Ensure RAECoreService usage doesn't leak implementation details.",
            "diff": diff,
            "writer_model": "deepseek-coder:33b",
            "reviewer_model": "deepseek-coder:6.7b",
        },
    }

    req = urllib.request.Request(
        "http://localhost:8000/control/tasks",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": "dev-key"},
        method="POST",
    )

    with urllib.request.urlopen(req) as f:
        res = json.loads(f.read().decode("utf-8"))
        print(f"Task Created: {res['id']}")
        print(f"Status: {res['status']}")


if __name__ == "__main__":
    delegate()
