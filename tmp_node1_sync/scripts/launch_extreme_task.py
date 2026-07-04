#!/usr/bin/env python3
import json
import urllib.request


def launch_extreme_task():
    f_path = "apps/memory_api/services/hybrid_search_service.py"
    with open(f_path, "r") as f:
        content = f.read()

    payload = {
        "type": "code_verify_cycle",
        "priority": 10,
        "payload": {
            "prompt": "MANDATORY: Analyze the code between --- START --- and --- END ---. No excuses about file access. Perform full architectural audit.",
            "code": content,
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
        print(f"🔥 EXTREME Task Created: {res['id']}")


if __name__ == "__main__":
    launch_extreme_task()
