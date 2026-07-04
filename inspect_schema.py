import asyncio

import asyncpg


async def main():
    try:
        conn = await asyncpg.connect(
            host="localhost", user="rae", password="rae_password", database="rae"
        )
        rows = await conn.fetch(
            "SELECT column_name, column_default, is_nullable FROM information_schema.columns WHERE table_name = 'memories'"
        )
        print("Schema for 'memories' table:")
        for r in rows:
            print(
                f"Column: {r['column_name']}, Default: {r['column_default']}, Nullable: {r['is_nullable']}"
            )
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
