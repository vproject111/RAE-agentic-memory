import asyncio
import json
import os

import httpx

API_URL = "http://localhost:8000/v1"
NODE_ID = "kubus-gpu-01"
DB_HOST = "100.66.252.117"


async def dispatch_task(name, size, queries):
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"\n🚀 Dispatching {name} ({size} memories) to Node1...")

        # Komenda wykonuje generowanie I benchmark na Node1
        cmd = (
            f"python3 benchmarking/scripts/generate_industrial_dataset.py --name {name} --size {size} --queries {queries} --output benchmarking/sets/{name}.yaml && "
            f"python3 benchmarking/scripts/run_benchmark.py --set {name}.yaml --output benchmarking/results && "
            f"cat $(ls -t benchmarking/results/{name}_*.json | head -n 1)"
        )

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
        print(f"✅ Task created: {task_id}. Waiting for results...")

        while True:
            resp = await client.get(f"{API_URL}/control/tasks/{task_id}")
            task = resp.json()
            status = task["status"]
            if status in ["COMPLETED", "FAILED"]:
                break
            print(f"Status: {status}...", end="\r")
            await asyncio.sleep(5)

        if status == "COMPLETED":
            stdout = task.get("result", {}).get("stdout", "")
            marker = '"benchmark": {'
            idx = stdout.find(marker)
            if idx != -1:
                start_idx = stdout.rfind("{", 0, idx)
                json_str = stdout[start_idx:]
                filename = f"benchmarking/results/{name}_node1_latest.json"
                os.makedirs("benchmarking/results", exist_ok=True)
                with open(filename, "w") as f:
                    f.write(json_str)
                print(f"\n✅ Benchmark {name} COMPLETED. Results saved to {filename}")

                # Wyświetl kluczowe metryki
                data = json.loads(json_str)
                metrics = data.get("metrics", {})
                print(
                    f"📊 MRR: {metrics.get('mrr'):.4f} | Quality: {metrics.get('overall_quality_score'):.4f}"
                )
            else:
                print("\n❌ Success, but JSON not found in output.")
        else:
            print(f"\n❌ Task failed: {task.get('error')}")


async def main():
    # Krok 1: 1k
    await dispatch_task("industrial_large", 1000, 100)
    # Krok 2: 10k
    await dispatch_task("industrial_extreme", 10000, 200)
    # Krok 3: 100k
    await dispatch_task("industrial_ultra", 100000, 500)


if __name__ == "__main__":
    asyncio.run(main())
