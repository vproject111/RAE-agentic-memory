import asyncio

from rae_memory_sdk import AsyncRAEClient, RAEClient


def run_sync_example():
    """Demonstrates the synchronous client."""
    print("--- Running Synchronous Example ---")
    client = RAEClient(
        base_url="http://localhost:8000",
        tenant_id="e2e-sync-tenant",
    )

    # 1. Store a few episodic memories
    print("Storing memories...")
    client.store_memory(
        layer="episodic",
        type="event",
        content="User was informed that the legacy system will be deprecated.",
        tags=["legacy", "deprecation"],
    )
    client.store_memory(
        layer="episodic",
        type="event",
        content="User asked for the timeline for the new system rollout.",
        tags=["timeline", "new-system"],
    )

    # 2. Store a semantic memory
    client.store_memory(
        layer="semantic",
        type="fact",
        content="The new system is projected to go live in Q3.",
        tags=["timeline", "fact"],
    )
    print("Memories stored.")

    # 3. Run a query
    print("\nQuerying memories...")
    query = "What is the timeline for the new system?"
    response = client.query_memory(query=query, top_k=3)

    print(f"Query: '{query}'")
    print("Results:")
    if response.memories:
        for mem in response.memories:
            print(f"  - ID: {mem.id}, Score: {mem.score:.2f}, Content: '{mem.content}'")
    else:
        print("  No memories found.")


async def run_async_example():
    """Demonstrates the asynchronous client."""
    print("\n--- Running Asynchronous Example ---")
    client = AsyncRAEClient(
        base_url="http://localhost:8000",
        tenant_id="e2e-async-tenant",
    )

    # 1. Store memories concurrently
    print("Storing memories...")
    await asyncio.gather(
        client.store_memory(
            layer="episodic",
            type="event",
            content="Agent identified a performance bottleneck in the payment gateway.",
            tags=["performance", "payment"],
        ),
        client.store_memory(
            layer="semantic",
            type="rule",
            content="Performance issues in critical paths should be escalated to the on-call engineer.",
            tags=["ops", "rule"],
        ),
    )
    print("Memories stored.")

    # 2. Run a query
    print("\nQuerying memories...")
    query = "What should be done about the payment gateway performance?"
    response = await client.query_memory(query=query, top_k=3)

    print(f"Query: '{query}'")
    print("Results:")
    if response.memories:
        for mem in response.memories:
            print(f"  - ID: {mem.id}, Score: {mem.score:.2f}, Content: '{mem.content}'")
    else:
        print("  No memories found.")

    await client.close()


if __name__ == "__main__":
    run_sync_example()
    asyncio.run(run_async_example())
