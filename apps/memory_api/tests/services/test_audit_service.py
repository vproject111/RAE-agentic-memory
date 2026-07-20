from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.memory_api.models.dashboard_models import AuditTrailEntry
from apps.memory_api.services.audit_service import AuditService

pytestmark = pytest.mark.iso42001


@pytest.fixture
def mock_pool():
    pool_mock = MagicMock()

    conn_mock = AsyncMock()
    conn_mock.fetch.return_value = []
    conn_mock.fetchrow.return_value = None
    conn_mock.fetchval.return_value = 0
    conn_mock.execute = AsyncMock(return_value="INSERT 0 1")

    mock_context_manager = MagicMock()
    mock_context_manager.__aenter__ = AsyncMock(return_value=conn_mock)
    mock_context_manager.__aexit__ = AsyncMock(return_value=None)

    pool_mock.acquire = MagicMock(return_value=mock_context_manager)
    pool_mock.fetch = AsyncMock(return_value=[])
    pool_mock.fetchrow = AsyncMock(return_value=None)
    pool_mock.fetchval = AsyncMock(return_value=0)
    pool_mock.execute = AsyncMock(return_value="INSERT 0 1")

    pool_mock._conn_mock = conn_mock
    yield pool_mock


@pytest.fixture
def mock_rae_service(mock_pool):
    service = MagicMock()
    service.postgres_pool = mock_pool

    from rae_adapters.postgres_db import PostgresDatabaseProvider

    service.db = PostgresDatabaseProvider(mock_pool)

    return service


@pytest.fixture
def audit_service(mock_rae_service):
    return AuditService(mock_rae_service)


def test_verify_memory_hash(audit_service):
    content = "Hello, compliance world!"
    expected_hash = "001f564fa1603f405ad5018773e720e4260cd887fce40af7f9c04dd6a7f0600b"

    assert audit_service.verify_memory_hash(content, expected_hash) is True
    assert audit_service.verify_memory_hash(content, "incorrecthash") is False
    assert audit_service.verify_memory_hash("", expected_hash) is False


def test_mask_secrets(audit_service):
    raw_text = "Here is my secret API key: " + "sk-or-v1-" + "a" * 64
    masked = audit_service.mask_secrets(raw_text)
    assert "[MASKED_OPENROUTER_KEY]" in masked
    assert "sk-or-v1-" not in masked

    raw_text2 = "Standard key: sk-1234567890123456789012"
    masked2 = audit_service.mask_secrets(raw_text2)
    assert "[MASKED_API_KEY]" in masked2

    raw_text3 = "My DB password is password = 'super_secret_pwd_123'"
    masked3 = audit_service.mask_secrets(raw_text3)
    assert "[MASKED_PASSWORD]" in masked3
    assert "super_secret_pwd_123" not in masked3


@pytest.mark.asyncio
async def test_log_access(audit_service, mock_pool):
    await audit_service.log_access(
        tenant_id="f51d8b92-2fb1-524c-86e4-c6f8f6f59872",
        user_id="auditor_test",
        action="test_action",
        resource="test_resource",
    )
    mock_pool.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_audit_trail(audit_service, mock_pool):
    # Mock return rows for memories query
    mock_rows = [
        {
            "id": "11111111-2222-3333-4444-555555555555",
            "tenant_id": "f51d8b92-2fb1-524c-86e4-c6f8f6f59872",
            "content": "Secret key: " + "sk-or-v1-" + "a" * 64,
            "source": "user-input",
            "project": "dreamsoft_factory",
            "session_id": "session-123",
            "agent_id": "agent-xyz",
            "info_class": "RESTRICTED",
            "governance": {"failure_trace": "db_password='abc'"},
            "created_at": datetime.now(timezone.utc),
            "content_hash": "somehash",
            "human_label": "Ingested Memory",
        }
    ]

    mock_pool.fetch.return_value = mock_rows
    mock_pool.fetchval.return_value = 1

    result = await audit_service.get_audit_trail(
        tenant_id="f51d8b92-2fb1-524c-86e4-c6f8f6f59872",
        project="dreamsoft_factory",
        limit=10,
        offset=0,
    )

    assert result["total_count"] == 1
    assert len(result["entries"]) == 1

    entry = result["entries"][0]
    assert isinstance(entry, AuditTrailEntry)
    assert entry.tenant_id == "f51d8b92-2fb1-524c-86e4-c6f8f6f59872"
    assert "[MASKED_OPENROUTER_KEY]" in entry.action_description
    assert "[MASKED_PASSWORD]" in entry.metadata["governance"]["failure_trace"]
