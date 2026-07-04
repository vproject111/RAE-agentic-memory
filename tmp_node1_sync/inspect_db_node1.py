import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect(
            host="localhost",
            user="rae",
            password="rae_password",
            database="rae"
        )
        print("Connected successfully to Node1 DB.")
        
        # Check current database name
        dbname = await conn.fetchval("SELECT current_database()")
        print(f"Current database: {dbname}")
        
        # List tables in public schema
        tables = await conn.fetch("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
        print("Tables in public schema:")
        for t in tables:
            print(f"- {t['table_name']}")
            
        await conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
