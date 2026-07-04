import asyncio
import uuid

import httpx

API_URL = "http://localhost:8001/v1"
API_KEY = "dev-key"
TENANT_ID = "b0eebc99-9c0b-4ef8-bb6d-6bb9bd380b22"  # rae-core


async def interact(project: str, prompt: str):
    print(f"\n[Project: {project}] Sending: {prompt}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_URL}/agent/execute",
                json={
                    "tenant_id": TENANT_ID,
                    "project": project,
                    "prompt": prompt,
                    "session_id": f"session-{project}-{uuid.uuid4().hex[:6]}",
                },
                headers={"X-API-Key": API_KEY, "X-Tenant-Id": TENANT_ID},
                timeout=30.0,
            )
            if response.status_code == 200:
                answer = response.json().get("answer")
                print(f"[Project: {project}] Answer: {answer[:100]}...")
            else:
                print(
                    f"[Project: {project}] Error {response.status_code}: {response.text}"
                )
        except Exception as e:
            print(f"[Project: {project}] Connection failed: {e}")


async def main():
    # Krok 1: Budujemy "wiedzę" w dwóch różnych projektach
    print("--- PHASE 1: Building isolated knowledge ---")
    await interact(
        "Project-Alpha",
        "The secret code for Project Alpha is 'DRAGON-2026'. Remember it.",
    )
    await interact(
        "Project-Beta", "The secret code for Project Beta is 'PHOENIX-99'. Remember it."
    )

    # Krok 2: Sprawdzamy czy RAE-First izoluje kontekst
    print("\n--- PHASE 2: Verifying Isolation ---")
    # Zapytamy Project Alpha o kod Bety - nie powinien go znać
    await interact("Project-Alpha", "What is the secret code for Project Beta?")

    # Zapytamy Project Beta o jego własny kod - powinien go znać z pamięci
    await interact("Project-Beta", "What is my secret code?")


if __name__ == "__main__":
    asyncio.run(main())
