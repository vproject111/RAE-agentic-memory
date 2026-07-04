#!/usr/bin/env python3
"""
Setup Sandbox Database
Seeds default tenant and admin user roles in the sandbox database (port 5440).
"""
import asyncio
import sys
from uuid import UUID, uuid4

try:
    import asyncpg
except ImportError:
    print("❌ asyncpg not found. Please run: pip install asyncpg")
    sys.exit(1)

# Configuration for Sandbox
DB_URL = "postgresql://rae:rae@localhost:5440/rae"
USER_ID = "admin-user"  # Assuming test uses this user or API key mapping
API_KEY_USER_ID = "apikey_secret"  # User ID mapped to 'secret' API key in main.py
DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000000"
ROLE = "owner"


async def setup_sandbox():
    print(f"🚀 Setting up Sandbox DB at {DB_URL}...")

    try:
        conn = await asyncpg.connect(DB_URL)

        # 1. Ensure Tenant Exists
        t_id = UUID(DEFAULT_TENANT_ID)
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM tenants WHERE id = $1)", t_id
        )
        if not exists:
            print(f"ℹ️ Creating default tenant {DEFAULT_TENANT_ID}...")
            await conn.execute(
                "INSERT INTO tenants (id, name, tier) VALUES ($1, $2, 'enterprise')",
                t_id,
                "Sandbox Tenant",
            )

        # 2. Grant Role to API Key User (used in tests with X-API-Key: secret)
        # Note: main.py creates 'apikey_secret' user mapping
        print(f"ℹ️ Granting '{ROLE}' to API Key User '{API_KEY_USER_ID}'...")
        await conn.execute(
            """
            INSERT INTO user_tenant_roles
            (id, user_id, tenant_id, role, project_ids, assigned_at, assigned_by)
            VALUES ($1, $2, $3, $4, $5, NOW(), $6)
            ON CONFLICT (user_id, tenant_id)
            DO UPDATE SET role = $4
        """,
            uuid4(),
            API_KEY_USER_ID,
            t_id,
            ROLE,
            [],
            "sandbox-setup",
        )

        await conn.close()
        print("✅ Sandbox DB setup complete!")

    except Exception as e:
        print(f"❌ Error: {e}")
        # Don't fail hard if DB is not ready yet, usually tests handle wait
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(setup_sandbox())
