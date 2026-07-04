#!/usr/bin/env python3
import json
import os
import urllib.request

API_BASE = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": "dev-key",
    "X-Tenant-Id": "default",
}


def post_request(url, data):
    req = urllib.request.Request(
        url, data=json.dumps(data).encode("utf-8"), headers=HEADERS, method="POST"
    )
    with urllib.request.urlopen(req) as f:
        return json.loads(f.read().decode("utf-8"))


def main():
    f_path = "apps/memory_api/services/hybrid_search_service.py"
    if not os.path.exists(f_path):
        print(f"Error: {f_path} not found")
        return
    with open(f_path, "r") as f:
        content = f.read()

    print(f"📦 Storing {f_path} in RAE Memory...")
    mem_data = {
        "content": content,
        "source": "automated_audit_system",
        "layer": "em",
        "tags": ["audit-target", "hybrid-search"],
    }
    try:
        memory = post_request(f"{API_BASE}/v1/memory/store", mem_data)
        mem_id = memory["id"]
        print(f"✅ Memory stored! ID: {mem_id}")

        print("🚀 Delegating audit to KUBUS using memory_id...")
        task_data = {
            "type": "code_verify_cycle",
            "priority": 10,
            "payload": {
                "prompt": "Perform a full architectural audit of the code linked by memory_id. Focus on agnosticism.",
                "memory_id": mem_id,
                "writer_model": "deepseek-coder:33b",
                "reviewer_model": "deepseek-coder:6.7b",
            },
        }
        task = post_request(f"{API_BASE}/control/tasks", task_data)
        print(f"🔥 Task Created: {task['id']}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
