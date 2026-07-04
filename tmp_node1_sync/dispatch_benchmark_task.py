import asyncio
import os

import httpx

API_URL = "http://localhost:8001/v1"
NODE_ID = "kubus-gpu-01"
DB_HOST = "100.66.252.117"


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"Checking node {NODE_ID}...")
        try:
            resp = await client.get(f"{API_URL}/control/nodes")
            if resp.status_code != 200:
                print(f"Error checking nodes: {resp.status_code} {resp.text}")
                nodes = []
            else:
                nodes = resp.json()

            if isinstance(nodes, list):
                if not any(
                    n.get("node_id") == NODE_ID and n.get("status") == "ONLINE"
                    for n in nodes
                ):
                    print(
                        f"Warning: {NODE_ID} not online. Nodes: {[n.get('node_id') for n in nodes]}"
                    )
            else:
                print(f"Unexpected nodes response format: {nodes}")

        except Exception as e:
            print(f"Error checking nodes: {e}")

        print("Creating benchmark task (Full 1000 memories test)...")
        # Use run_benchmark.py for standard sets, or run_extreme_benchmark.py if it supports it
        # Actually run_benchmark.py is more standard for small sets.
        cmd = "python3 benchmarking/scripts/run_benchmark.py --set industrial_large.yaml --output benchmarking/results && cat $(ls -t benchmarking/results/*.json | head -n 1)"

        payload = {
            "type": "shell_command",
            "payload": {
                "command": cmd,
                "env": {
                    "POSTGRES_HOST": DB_HOST,
                    "POSTGRES_USER": "rae",
                    "POSTGRES_PASSWORD": "rae_password",
                    "POSTGRES_DB": "rae",
                    "RAE_API_URL": f"http://{DB_HOST}:8000",
                },
            },
            "priority": 10,
        }

        resp = await client.post(f"{API_URL}/control/tasks", json=payload)
        resp.raise_for_status()
        task_id = resp.json()["id"]
        print(f"Task created: {task_id}")

        print("Waiting for completion...")
        while True:
            resp = await client.get(f"{API_URL}/control/tasks/{task_id}")
            task = resp.json()
            status = task["status"]
            if status in ["COMPLETED", "FAILED"]:
                break
            print(f"Status: {status}...", end="\r")
            await asyncio.sleep(2)
        if status == "COMPLETED":
            stdout = task.get("result", {}).get("stdout", "")
            marker = '"benchmark": {'
            idx = stdout.find(marker)
            if idx != -1:
                start_idx = stdout.rfind("{", 0, idx)
                if start_idx != -1:
                    json_str = stdout[start_idx:]
                    filename = "benchmarking/results/industrial_extreme_node1.json"
                    os.makedirs("benchmarking/results", exist_ok=True)
                    with open(filename, "w") as f:
                        f.write(json_str)
                    print(f"\n✅ Report saved to {filename}")
                else:
                    print("\n❌ JSON start not found.")
            else:
                print("\n❌ Benchmark marker not found in output.")
                print(stdout[-500:])
        else:
            print(f"\n❌ Task failed: {task.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
