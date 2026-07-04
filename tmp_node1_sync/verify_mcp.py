import asyncio
import os
import sys
import time
from pathlib import Path

# Add src to path to import rae_mcp
sys.path.insert(0, str(Path(__file__).parent / "integrations/mcp/src"))

from rae_mcp.server import RAEMemoryClient


async def main():
    """
    Connects to RAE API and performs a save and search test.
    """
    print("🚀 Starting RAE MCP verification script...")

    api_url = os.getenv("RAE_API_URL", "http://localhost:8000")
    print(f"Connecting to RAE API at: {api_url}")

    client = RAEMemoryClient(api_url=api_url)

    # 1. Store a unique memory
    timestamp = time.time()
    unique_content = f"MCP verification test content at {timestamp}"
    source = "verify_mcp.py"
    print(
        f"\n1. Storing memory:\n   Content: '{unique_content}'\n   Source: '{source}'"
    )

    try:
        store_result = await client.store_memory(
            content=unique_content,
            source=source,
            layer="episodic",
            tags=["mcp-verification"],
        )
        memory_id = store_result.get("id")
        if not memory_id:
            print("❌ ERROR: Failed to store memory. Response did not contain an ID.")
            print(f"   Response: {store_result}")
            sys.exit(1)

        print(f"✅ Memory stored successfully. ID: {memory_id}")

    except Exception as e:
        print(f"❌ ERROR: An exception occurred while storing memory: {e}")
        sys.exit(1)

    # Give a moment for indexing
    print("\nWaiting 2 seconds for indexing...")
    await asyncio.sleep(2)

    # 2. Search for the stored memory
    print(f"\n2. Searching for memory with query: '{unique_content}'")

    try:
        search_results = await client.search_memory(query=unique_content, top_k=5)

        if not search_results:
            print("❌ ERROR: Search returned no results.")
            sys.exit(1)

        print(f"✅ Search returned {len(search_results)} result(s).")

        # 3. Verify the result
        found = False
        for result in search_results:
            if result.get("content") == unique_content:
                print(
                    "\n✅ VERIFICATION SUCCESS: Found the exact stored memory in search results!"
                )
                found = True
                print(f"   - ID: {result.get('id')}")
                print(f"   - Score: {result.get('score')}")
                print(f"   - Source: {result.get('source')}")
                break

        if not found:
            print(
                "\n❌ VERIFICATION FAILED: The stored memory was not found in the search results."
            )
            print("   Full search results:")
            for r in search_results:
                print(f"   - {r}")
            sys.exit(1)

    except Exception as e:
        print(f"❌ ERROR: An exception occurred while searching for memory: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
