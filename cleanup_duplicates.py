import asyncio

import asyncpg


async def cleanup():
    conn = await asyncpg.connect("postgresql://rae:rae_password@localhost:5432/rae")
    # Usuwamy duplikaty pozostawiając tylko jeden rekord dla danej treści w projekcie Alpha
    await conn.execute(
        """
        DELETE FROM memories
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM memories
            WHERE project = 'Project-Alpha'
            GROUP BY content, layer
        ) AND project = 'Project-Alpha'
    """
    )
    print("[+] Project-Alpha cleaned up.")
    await conn.close()


if __name__ == "__main__":
    asyncio.run(cleanup())
