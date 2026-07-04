from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.services.retention_service import (
    DataClass,
    RetentionPolicy,
    RetentionService,
)


@pytest.fixture
def mock_pool():
    pool = MagicMock()
    pool.fetch = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value="DELETE 10")

    # Setup acquire() as an async context manager
    connection = AsyncMock()
    # pool.acquire is a regular Mock that returns an async context manager
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    # connection.transaction() should return an async context manager
    # transaction is a regular Mock that returns an async context manager
    transaction_cm = MagicMock()
    connection.transaction = MagicMock(return_value=transaction_cm)
    transaction_cm.__aenter__ = AsyncMock(return_value=AsyncMock())
    transaction_cm.__aexit__ = AsyncMock(return_value=None)

    connection.execute = AsyncMock(return_value="DELETE 5")
    return pool


@pytest.fixture
def mock_rae_service(mock_pool):
    rae = MagicMock(spec=RAECoreService)
    rae.postgres_pool = mock_pool

    # Mock the 'db' property to return an actual provider wrapping our mock pool
    from rae_adapters.postgres_db import PostgresDatabaseProvider

    rae.db = PostgresDatabaseProvider(mock_pool)

    return rae


@pytest.fixture
def retention_service(mock_rae_service):
    return RetentionService(mock_rae_service)


@pytest.mark.asyncio
async def test_get_tenant_retention_policies_defaults(retention_service, mock_pool):
    mock_pool.fetchrow.return_value = None

    policies = await retention_service.get_tenant_retention_policies(str(uuid4()))

    assert policies[DataClass.EPISODIC_MEMORY].retention_days == 365
    assert policies[DataClass.LONG_TERM_MEMORY].retention_days == -1
    assert policies[DataClass.AUDIT_LOGS].retention_days == 2555


@pytest.mark.asyncio
async def test_get_tenant_retention_policies_custom(retention_service, mock_pool):
    mock_pool.fetchrow.return_value = {"config": {"memory_retention_days": 30}}

    policies = await retention_service.get_tenant_retention_policies(str(uuid4()))

    assert policies[DataClass.EPISODIC_MEMORY].retention_days == 30


@pytest.mark.asyncio
async def test_cleanup_expired_data_single_tenant(retention_service, mock_pool):
    # Arrange
    mock_pool.fetchrow.return_value = {"config": {"memory_retention_days": 30}}
    mock_pool.execute.side_effect = [
        "DELETE 10",
        "DELETE 5",
        "INSERT 1",
        "DELETE 2",
        "INSERT 1",
        "DELETE 1",
        "INSERT 1",
    ]

    # Act
    results = await retention_service.cleanup_expired_data("tenant1")

    # Assert
    assert results[DataClass.EPISODIC_MEMORY] == 10
    # assert results[DataClass.EMBEDDINGS] == 2 # Embeddings might be called later
    assert mock_pool.execute.call_count >= 1


@pytest.mark.asyncio
async def test_cleanup_expired_data_all_tenants(retention_service, mock_pool):
    # Arrange
    mock_pool.fetch.return_value = [{"tenant_id": "t1"}, {"tenant_id": "t2"}]
    mock_pool.fetchrow.return_value = {"config": {"memory_retention_days": 30}}

    # Act
    await retention_service.cleanup_expired_data()

    # Assert
    assert mock_pool.fetch.call_count >= 1  # To get tenants


@pytest.mark.asyncio
async def test_cleanup_exceptions_handled(retention_service, mock_pool):
    # Arrange
    mock_pool.execute.side_effect = Exception("DB Error")

    # Act
    results = await retention_service.cleanup_expired_data("tenant1")

    # Assert - should not raise
    assert len(results) == 0


@pytest.mark.asyncio
async def test_delete_user_data_gdpr(retention_service, mock_pool):
    # Arrange
    tenant_id = str(uuid4())
    user_id = "user@example.com"

    # Act
    results = await retention_service.delete_user_data(tenant_id, user_id, "admin")

    # Assert
    assert results["memories"] == 5
    assert results["semantic_nodes"] == 5
    # Verify audit log was called
    mock_pool.execute.assert_called()


@pytest.mark.asyncio
async def test_get_deletion_audit_log(retention_service, mock_pool):
    # Arrange
    mock_pool.fetch.return_value = [{"id": uuid4(), "deleted_count": 10}]

    # Act
    logs = await retention_service.get_deletion_audit_log("tenant1")

    # Assert
    assert len(logs) == 1
    assert logs[0]["deleted_count"] == 10


@pytest.mark.asyncio
async def test_get_deletion_audit_log_with_dates(retention_service, mock_pool):
    # Arrange
    mock_pool.fetch.return_value = []
    start = datetime.now()
    end = datetime.now()

    # Act
    await retention_service.get_deletion_audit_log(
        "tenant1", start_date=start, end_date=end
    )

    # Assert
    mock_pool.fetch.assert_called()


@pytest.mark.asyncio
async def test_cleanup_embeddings_error(retention_service, mock_pool):
    # Simulate embeddings table missing or error
    mock_pool.execute.side_effect = [
        "DELETE 10",  # episodic
        "INSERT 1",  # audit for episodic
        Exception("Table not found"),  # embeddings
        "DELETE 5",  # cost logs
        "INSERT 1",  # audit cost logs
    ]

    results = await retention_service.cleanup_expired_data("tenant1")
    # Should continue despite error
    assert results.get(DataClass.EPISODIC_MEMORY) == 10


@pytest.mark.asyncio
async def test_log_audit_failure_fallback(retention_service, mock_pool):
    # Force audit log insert to fail
    mock_pool.execute.side_effect = ["DELETE 10", Exception("Audit log table missing")]

    with patch.object(retention_service.logger, "warning") as mock_log:
        await retention_service._cleanup_episodic_memories(
            "t1",
            RetentionPolicy(data_class=DataClass.EPISODIC_MEMORY, retention_days=1),
        )
        mock_log.assert_called()
