import asyncio

import asyncpg


async def deep_audit():
    conn = await asyncpg.connect("postgresql://rae:rae_password@localhost:5432/rae")

    print("\n=== DATA INTEGRITY AUDIT: BLIND COLUMNS ===")
    columns = ["session_id", "project", "source", "ttl", "strength", "memory_type"]
    for col in columns:
        # Sprawdzamy ile rekordów ma NULL lub wartość domyślną w tych kolumnach
        count_null = await conn.fetchval(
            f"SELECT COUNT(*) FROM memories WHERE {col} IS NULL"
        )
        total = await conn.fetchval("SELECT COUNT(*) FROM memories")
        print(
            f"Column '{col:.<15}' | NULLs: {count_null:<6} | Fill Rate: {((total-count_null)/total)*100:>.1f}%"
        )

    print("\n=== DATA INTEGRITY AUDIT: ACTIVE WRITERS ===")
    # Sprawdzamy czy tabele pomocnicze są w ogóle używane
    tables = [
        "access_logs",
        "token_savings_log",
        "knowledge_graph_nodes",
        "memory_embeddings",
    ]
    for table in tables:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        print(f"Table '{table:.<25}' | Row Count: {count}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(deep_audit())
