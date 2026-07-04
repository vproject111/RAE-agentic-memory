#!/usr/bin/env python3
import json
import os
import urllib.request


def create_task(task_type, prompt, code_content):
    payload = {
        "type": task_type,
        "priority": 10,
        "payload": {
            "prompt": prompt,
            "diff": code_content,  # Sending full content as 'diff' to trigger analysis
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
        print(f"Task Created: {res['id']} | Type: {task_type}")


def load_file(path):
    with open(path, "r") as f:
        return f.read()


if __name__ == "__main__":
    # Heavy files to analyze
    files = [
        "apps/memory_api/services/hybrid_search_service.py",
        "apps/memory_api/core/graph_operator.py",
        "apps/memory_api/repositories/graph_repository_enhanced.py",
    ]

    print("🔥 Launching heavy tasks to Node1 (KUBUS)...")

    for f_path in files:
        if os.path.exists(f_path):
            content = load_file(f_path)
            prompt = f"Perform a deep architectural and security audit of this file: {f_path}. Focus on agnosticism and performance bottlenecks."
            # We use 'code_verify_cycle' as it's the most intensive one (Writer + Reviewer)
            create_task("code_verify_cycle", prompt, content)
        else:
            print(f"⚠️ File not found: {f_path}")
