from qdrant_client import AsyncQdrantClient; import asyncio; 
async def main():
    client = AsyncQdrantClient(location=":memory:")
    print("METHODS:", [m for m in dir(client) if "search" in m.lower()])
    await client.close()
asyncio.run(main())
