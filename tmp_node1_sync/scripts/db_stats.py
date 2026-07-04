import asyncio
import os

import asyncpg


async def check_db_stats():
    host = os.getenv("POSTGRES_HOST", "localhost")
    user = os.getenv("POSTGRES_USER", "rae")
    password = os.getenv("POSTGRES_PASSWORD", "rae_password")
    database = os.getenv("POSTGRES_DB", "rae")

    print(f"Connecting to {database} at {host}...")

    try:
        conn = await asyncpg.connect(
            user=user, password=password, database=database, host=host
        )

        # Get all tables in public schema
        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """
        )

        stats = []
        active_tables = 0

        print(f"Found {len(tables)} tables. analyzing usage...")

        for record in tables:
            table_name = record["table_name"]

            # Count rows
            # Note: exact count for verification
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")

            # Check last write (approximate using system catalog if possible,
            # but simpler to just show count here as "usage" proxy)

            is_active = count > 0
            if is_active:
                active_tables += 1

            stats.append([table_name, count, "ACTIVE" if is_active else "EMPTY"])

        # Sort by count desc
        stats.sort(key=lambda x: x[1], reverse=True)

        print("\n=== RAE Database Structure & Usage Report ===")
        print(f"{'Table Name':<30} | {'Row Count':<10} | {'Status':<10}")
        print("-" * 56)
        for row in stats:
            print(f"{row[0]:<30} | {row[1]:<10} | {row[2]:<10}")

        print("\nSummary:")
        print(f"Total Tables: {len(tables)}")
        print(f"Active Tables (with data): {active_tables}")
        print(f"Empty Tables: {len(tables) - active_tables}")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_db_stats())
