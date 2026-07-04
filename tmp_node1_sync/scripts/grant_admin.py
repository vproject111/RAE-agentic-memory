#!/usr/bin/env python3
"""
Grant Admin Privileges Script - Corrected
Grants 'owner' role to 'admin-user' for demo tenants in RAE database.
"""
import asyncio
import os
import sys
from uuid import UUID, uuid4

try:
    import asyncpg
except ImportError:
    print("❌ asyncpg not found. Please run: pip install asyncpg")
    sys.exit(1)

# Default values from apps/memory_api/config.py
DB_URL = os.getenv("DATABASE_URL", "postgresql://rae:rae_password@localhost:5432/rae")
USER_ID = "admin-user"
# Demo tenants from seed_demo_data.py and default tenant from main.py
TENANTS = [
    "00000000-0000-0000-0000-000000000000",  # Default
    "00000000-0000-0000-0000-000000000100",  # Phoenix
    "00000000-0000-0000-0000-000000000200",  # City Hall
]
ROLE = "owner"


async def grant_admin():
    print(f"🚀 Granting '{ROLE}' role to user '{USER_ID}' for multiple tenants...")

    try:
        conn = await asyncpg.connect(DB_URL)

        # Check if table exists
        exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_tenant_roles')"
        )
        if not exists:
            print(
                "❌ Table 'user_tenant_roles' does not exist. Did you run migrations?"
            )
            await conn.close()
            return

        for t_id_str in TENANTS:
            t_id = UUID(t_id_str)
            # Ensure tenant exists first
            t_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM tenants WHERE id = $1)", t_id
            )
            if not t_exists:
                print(f"ℹ️ Tenant {t_id_str} not found, creating it...")
                await conn.execute(
                    "INSERT INTO tenants (id, name, tier) VALUES ($1, $2, 'enterprise') ON CONFLICT DO NOTHING",
                    t_id,
                    f"Tenant {t_id_str[:8]}",
                )

            await conn.execute(
                """
                INSERT INTO user_tenant_roles
                (id, user_id, tenant_id, role, project_ids, assigned_at, assigned_by)
                VALUES ($1, $2, $3, $4, $5, NOW(), $6)
                ON CONFLICT (user_id, tenant_id)
                DO UPDATE SET role = $4, assigned_at = NOW()
            """,
                uuid4(),
                USER_ID,
                t_id,
                ROLE,
                [],
                "system-setup",
            )

            print(
                f"✅ Successfully granted '{ROLE}' role to '{USER_ID}' for tenant '{t_id_str}'."
            )

        await conn.close()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(grant_admin())
