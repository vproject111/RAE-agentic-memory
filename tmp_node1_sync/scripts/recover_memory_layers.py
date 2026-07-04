import asyncio
import os

import asyncpg


async def recover_memory():
    # Configuration from .env
    host = os.getenv("POSTGRES_HOST", "localhost")
    user = os.getenv("POSTGRES_USER", "rae")
    password = os.getenv("POSTGRES_PASSWORD", "rae_password")
    database = os.getenv("POSTGRES_DB", "rae")

    print(f"Connecting to database {database} at {host}...")

    try:
        conn = await asyncpg.connect(
            user=user, password=password, database=database, host=host
        )
        print("Connected.")

        # Execute updates
        print("Executing memory recovery (layer name normalization)...")

        # 1. em -> episodic
        res = await conn.execute(
            "UPDATE memories SET layer = 'episodic' WHERE layer = 'em'"
        )
        print(f" - Recovered episodic memories (em -> episodic): {res}")

        # 2. stm/wm -> working
        res = await conn.execute(
            "UPDATE memories SET layer = 'working' WHERE layer = 'stm' OR layer = 'wm'"
        )
        print(f" - Recovered working memories (stm/wm -> working): {res}")

        # 3. ltm/sm -> semantic
        res = await conn.execute(
            "UPDATE memories SET layer = 'semantic' WHERE layer = 'ltm' OR layer = 'sm'"
        )
        print(f" - Recovered semantic memories (ltm/sm -> semantic): {res}")

        # 4. rm -> reflective
        res = await conn.execute(
            "UPDATE memories SET layer = 'reflective' WHERE layer = 'rm'"
        )
        print(f" - Recovered reflective memories (rm -> reflective): {res}")

        await conn.close()
        print("Memory recovery complete.")

    except Exception as e:
        print(f"Error during recovery: {e}")


if __name__ == "__main__":
    asyncio.run(recover_memory())
