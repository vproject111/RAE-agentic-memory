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
    print("🚀 Launching RAE-Lite Build Task to Node1 (KUBUS)...")

    # We assume the node agent is running in a directory where 'rae-lite' is accessible.
    # If it's running from repo root, then cwd should be '.'

    task_data = {
        "type": "shell_command",
        "priority": 20,
        "payload": {
            "command": "cd rae-lite && ./build.sh",
            "cwd": os.getcwd(),  # This will be the absolute path on the local machine,
            # which might not match KUBUS if it's different.
            # Better to use relative path if possible, but our agent
            # implementation uses payload.get("cwd", os.getcwd())
        },
    }

    # If we don't know the remote path, we should probably use a relative path or '.'
    # Let's try to find out where the node agent is running from.
    # Actually, let's just use command "cd rae-lite && ./build.sh" and omit cwd to use agent's default.

    task_data["payload"].pop("cwd")

    try:
        task = post_request(f"{API_BASE}/control/tasks", task_data)
        print(f"🔥 Task Created: {task['id']}")
        print(f"Status: {task['status']}")
        print(
            "\nYou can poll for results using: curl -s http://localhost:8000/control/tasks/"
            + task["id"]
        )
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
