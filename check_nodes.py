import asyncio
import os

import asyncpg


async def main():
    try:
        conn = await asyncpg.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            user=os.getenv("POSTGRES_USER", "rae"),
            password=os.getenv("POSTGRES_PASSWORD", "rae_password"),
            database=os.getenv("POSTGRES_DB", "rae"),
        )
        try:
            rows = await conn.fetch(
                "SELECT node_id, status, last_heartbeat FROM compute_nodes"
            )
            print(f"Found {len(rows)} nodes:")
            for r in rows:
                print(
                    f"Node: {r['node_id']}, Status: {r['status']}, Last Heartbeat: {r['last_heartbeat']}"
                )
        except asyncpg.UndefinedTableError:
            print("Table 'compute_nodes' does not exist yet.")

        await conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
