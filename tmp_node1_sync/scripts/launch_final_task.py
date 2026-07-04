#!/usr/bin/env python3
import json
import urllib.request


def launch_final_task():
    f_path = "apps/memory_api/services/hybrid_search_service.py"
    with open(f_path, "r") as f:
        content = f.read()

    # We put EVERYTHING in the prompt to bypass old agent limitations
    instruction = (
        "TASK: Perform a deep architectural audit of the code provided below.\n"
        "FOCUS: Agnosticism compliance and performance.\n\n"
        "CODE TO ANALYZE:\n"
        f"{content}"
    )

    payload = {
        "type": "code_verify_cycle",
        "priority": 10,
        "payload": {
            "prompt": instruction,
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
        print(f"🚀 FINAL Task Created: {res['id']}")


if __name__ == "__main__":
    launch_final_task()
