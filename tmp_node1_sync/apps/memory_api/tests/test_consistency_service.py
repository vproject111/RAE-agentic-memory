from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from apps.memory_api.services.consistency_service import ConsistencyService


@pytest.fixture
def mock_rae_service():
    service = MagicMock()
    service.postgres_pool = MagicMock()  # acquire is called on this
    service.qdrant_client = AsyncMock()

    # Mock the 'db' property to return an actual provider wrapping our mock pool
    from rae_adapters.postgres_db import PostgresDatabaseProvider

    service.db = PostgresDatabaseProvider(service.postgres_pool)

    return service


@pytest.fixture
def consistency_service(mock_rae_service):
    return ConsistencyService(rae_service=mock_rae_service)


@pytest.mark.asyncio
async def test_reconcile_vectors_no_orphans(consistency_service, mock_rae_service):
    tenant_id = str(uuid4())
    memory_id = str(uuid4())

    # Mock Qdrant scroll returning one point
    mock_point = MagicMock()
    mock_point.id = memory_id
    mock_rae_service.qdrant_client.scroll.return_value = ([mock_point], None)

    # Mock Postgres check confirming existence
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = [{"id": memory_id}]

    # Mocking asyncpg pool.acquire() context manager
    mock_rae_service.postgres_pool.acquire.return_value.__aenter__.return_value = (
        mock_conn
    )

    removed = await consistency_service.reconcile_vectors(tenant_id)

    assert removed == 0
    mock_rae_service.qdrant_client.delete.assert_not_called()


@pytest.mark.asyncio
async def test_reconcile_vectors_with_orphans(consistency_service, mock_rae_service):
    tenant_id = str(uuid4())
    orphan_id = str(uuid4())

    # Mock Qdrant scroll returning one orphan point
    mock_point = MagicMock()
    mock_point.id = orphan_id
    mock_rae_service.qdrant_client.scroll.return_value = ([mock_point], None)

    # Mock Postgres check returning empty (not found)
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    # Mocking asyncpg pool.acquire() context manager
    mock_rae_service.postgres_pool.acquire.return_value.__aenter__.return_value = (
        mock_conn
    )

    removed = await consistency_service.reconcile_vectors(tenant_id)

    assert removed == 1
    mock_rae_service.qdrant_client.delete.assert_called_once()
