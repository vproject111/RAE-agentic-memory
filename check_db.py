import asyncio

import asyncpg


async def main():
    try:
        conn = await asyncpg.connect(
            host="localhost", user="rae", password="rae_password", database="rae"
        )
        count = await conn.fetchval(
            "SELECT count(*) FROM memories WHERE tenant_id = 'benchmark_tenant'"
        )
        print(f"Total memories for 'benchmark_tenant': {count}")

        rows = await conn.fetch(
            "SELECT project, layer, count(*) FROM memories WHERE tenant_id = 'benchmark_tenant' GROUP BY project, layer"
        )
        for r in rows:
            print(f"Project: {r['project']}, Layer: {r['layer']}, Count: {r['count']}")

        # Check embeddings
        null_embs = await conn.fetchval(
            "SELECT count(*) FROM memories WHERE tenant_id = 'benchmark_tenant' AND embedding IS NULL"
        )
        print(f"Memories with NULL embedding: {null_embs}")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
