"""Storage adapter wrapper for RAE-Server.

Configures storage adapters based on RAE-Server settings.
"""

import os

import asyncpg

from rae_core.interfaces.storage import IMemoryStorage

from .postgres import PostgreSQLStorage


def get_storage_adapter(pool: asyncpg.Pool) -> IMemoryStorage:
    """Get configured storage adapter based on environment.

    Args:
        pool: PostgreSQL connection pool from RAE-Server (if using Postgres)

    Returns:
        Configured IMemoryStorage instance
    """
    storage_type = os.getenv("RAE_STORAGE_TYPE", "postgres").lower()

    if storage_type == "postgres":
        return PostgreSQLStorage(pool=pool)

    # Placeholder for future adapters (e.g., sqlite, in-memory)
    # elif storage_type == "sqlite":
    #     return SQLiteStorage(...)

    raise ValueError(f"Unsupported storage type: {storage_type}")
