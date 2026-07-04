import asyncio
from uuid import UUID

from apps.memory_api.config import settings
from apps.memory_api.services.memory_consolidation import MemoryConsolidationService
from apps.memory_api.services.rae_core_service import RAECoreService

# Mock required components or use simpler initialization if possible
# Since we are inside the container, we can import actual services


async def main():
    print("Initializing RAE Services for Manual Consolidation...")

    # We need a basic RAE Core Service setup
    # In 'dev' mode, DB params are in env vars
    from rae_adapters.infra_factory import InfrastructureFactory

    # Simple mock app state to hold connections
    class MockApp:
        state = type("obj", (object,), {})

    app = MockApp()

    try:
        await InfrastructureFactory.initialize(app, settings)

        rae_service = RAECoreService(
            getattr(app.state, "pool", None),
            getattr(app.state, "qdrant_client", None),
            getattr(app.state, "redis_client", None),
        )
        await rae_service.ainit()

        consolidation_service = MemoryConsolidationService(rae_service)

        tenant_id = UUID(
            settings.DEFAULT_TENANT_UUID
        )  # '00000000-0000-0000-0000-000000000000'

        print(f"Triggering automatic consolidation for tenant {tenant_id}...")

        # This will call our patched _generate_consolidated_content
        summary = await consolidation_service.run_automatic_consolidation(tenant_id)

        print("\n--- Consolidation Result ---")
        print(f"Total Consolidated: {summary.get('total_consolidated', 0)}")
        print(f"Details: {summary}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Cleanup
        if hasattr(app.state, "pool") and app.state.pool:
            await app.state.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
