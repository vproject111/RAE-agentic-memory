import asyncio

import asyncpg

from apps.memory_api.config import settings
from apps.memory_api.repositories.token_savings_repository import TokenSavingsRepository
from apps.memory_api.services.token_savings_service import TokenSavingsService


async def test_savings_write():
    print("🚀 Starting manual token savings test...")

    # 1. Setup DB Connection
    pool = await asyncpg.create_pool(
        host="localhost",
        database=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )

    try:
        # 2. Initialize Service
        repo = TokenSavingsRepository(pool)
        service = TokenSavingsService(repo)

        # 3. Track a mock savings event
        # Scenario: We optimized a context from 2000 tokens down to 500.
        print("📝 Logging mock savings event (2000 -> 500 tokens)...")
        await service.track_savings(
            tenant_id="test-tenant",
            project_id="test-project",
            model="gpt-4o",
            predicted_tokens=2000,
            real_tokens=500,
            savings_type="rag",
            request_id="test-req-123",
        )

        # 4. Verify by reading summary
        print("🔍 Verifying write via summary...")
        summary = await service.get_summary(tenant_id="test-tenant")
        print(f"✅ Success! Total saved tokens in DB: {summary.total_saved_tokens}")
        print(f"💰 Estimated cost saved: ${summary.total_saved_usd:.4f}")

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_savings_write())
