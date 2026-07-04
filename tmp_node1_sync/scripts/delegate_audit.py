#!/usr/bin/env python3
"""
Delegate Code Audit to Node1 (KUBUS).
Creates a quality_loop task in RAE Control Plane for remote execution.
"""

import os
import subprocess
import sys

import httpx


def get_git_diff() -> str:
    """Get unstaged changes."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting git diff: {e}")
        return ""


async def delegate_task(diff: str):
    """Send diff to RAE for delegation."""
    api_url = os.environ.get("RAE_API_URL", "http://localhost:8000")
    api_key = os.environ.get("RAE_API_KEY", "dev-key")  # Use default if not set

    payload = {
        "type": "quality_loop",
        "priority": 10,
        "payload": {
            "task": "Perform architectural audit of the attached diff. Focus on RAECoreService migration consistency and test coverage.",
            "diff": diff,
            "writer_model": "deepseek-coder:33b",
            "reviewer_model": "deepseek-coder:6.7b",
            "context": "RAE-agentic-memory project, focus on apps/memory_api",
        },
    }

    print(f"🚀 Delegating audit ({len(diff)} chars) to RAE Control Plane...")

    async with httpx.AsyncClient() as client:
        try:
            headers = {"X-API-Key": api_key}
            resp = await client.post(
                f"{api_url}/control/tasks", json=payload, headers=headers
            )
            resp.raise_for_status()
            task_data = resp.json()

            print("✅ Task created successfully!")
            print(f"📝 Task ID: {task_data['id']}")
            print(
                f"🤖 Assigned node: {task_data.get('assigned_node_id', 'Pending polling...')}"
            )
            print(f"📊 Status: {task_data['status']}")

        except httpx.HTTPStatusError as e:
            print(f"❌ API Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")


if __name__ == "__main__":
    diff_content = get_git_diff()
    if not diff_content:
        print("ℹ️ No changes to audit.")
        sys.exit(0)

    import asyncio

    asyncio.run(delegate_task(diff_content))
