import asyncio

import asyncpg


async def main():
    conn = await asyncpg.connect(
        host="localhost", user="rae", password="rae_password", database="rae"
    )
    await conn.execute(
        "UPDATE memories SET usage_count = 0, agent_id = project, metadata = '{}'::jsonb WHERE tenant_id = 'benchmark_tenant'"
    )
    print("Fixed 100k memories.")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
