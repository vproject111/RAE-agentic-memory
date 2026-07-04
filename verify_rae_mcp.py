import asyncio
import aiohttp
import json
import sys

async def main():
    # Local RAE Dev
    base_url = "http://localhost:8001"
    
    # Check Health
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/health") as resp:
            print(f"Health Check: {resp.status}")
            if resp.status != 200:
                print("Lumina Lite is unhealthy.")
                return
            print(await resp.text())

    # Store Memory via REST (since MCP SSE is hard to script simply)
    print("\n--- Storing Test Memory ---")
    payload = {
        "content": "Verification memory for RAE Lite connection.",
        "layer": "working",
        "importance": 0.9,
        "tags": ["verification", "mcp-test"]
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Tenant-Id": "default-tenant"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{base_url}/v1/memory/store", json=payload, headers=headers) as resp:
            print(f"Store Response: {resp.status}")
            print(await resp.text())
            
    # Query Memory
    print("\n--- Querying Test Memory ---")
    query_payload = {
        "query_text": "Verification memory",
        "k": 1
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{base_url}/v1/memory/query", json=query_payload, headers=headers) as resp:
            print(f"Query Response: {resp.status}")
            result = await resp.json()
            print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
