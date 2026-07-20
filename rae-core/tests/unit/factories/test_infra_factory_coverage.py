from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rae_core.factories.infra_factory import InfrastructureFactory


class MockSettings:
    def __init__(self):
        self.RAE_PROFILE = "standard"
        self.POSTGRES_HOST = "localhost"
        self.POSTGRES_DB = "rae"
        self.POSTGRES_USER = "rae"
        self.POSTGRES_PASSWORD = "pass"
        self.REDIS_URL = "redis://localhost:6379/0"
        self.QDRANT_HOST = "localhost"
        self.QDRANT_PORT = 6333


class TestInfrastructureFactory:
    @pytest.fixture
    def settings(self):
        return MockSettings()

    @pytest.mark.asyncio
    async def test_initialize_standard(self, settings):
        mock_app = MagicMock()
        # Ensure app.state exists
        mock_app.state = MagicMock()

        with (
            patch("rae_core.factories.infra_factory.AsyncQdrantClient"),
            patch(
                "rae_core.factories.infra_factory.asyncpg.create_pool",
                new_callable=AsyncMock,
            ),
            patch(
                "rae_core.factories.infra_factory.aioredis.from_url",
                new_callable=AsyncMock,
            ),
        ):

            await InfrastructureFactory.initialize(mock_app, settings)
            assert mock_app.state.redis_client is not None
            assert mock_app.state.qdrant_client is not None

    @pytest.mark.asyncio
    async def test_initialize_with_dsn(self, settings):
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        settings.DATABASE_URL = "postgresql://user:pass@host/db"

        with (
            patch("rae_core.factories.infra_factory.AsyncQdrantClient"),
            patch(
                "rae_core.factories.infra_factory.asyncpg.create_pool",
                new_callable=AsyncMock,
            ),
            patch(
                "rae_core.factories.infra_factory.aioredis.from_url",
                new_callable=AsyncMock,
            ),
        ):

            await InfrastructureFactory.initialize(mock_app, settings)
            assert mock_app.state.pool is not None
