import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from apps.memory_api.services.rae_core_service import RAECoreService


@pytest.mark.asyncio
async def test_store_memory_canonical_fields(mock_pool):
    """
    Test that Phase 1 & 2 refactoring correctly passes canonical fields
    (session_id, project, source, memory_type, ttl) to the DB Adapter
    and executes the correct INSERT statement.
    """
    # 1. Setup Service with mocked pool
    service = RAECoreService(postgres_pool=mock_pool)

    # Mock engine's internal components if needed, but we are testing integration
    # from Service -> Engine -> Adapter -> DB Mock.
    # We need to ensure embedding provider doesn't fail.
    service.embedding_provider = MagicMock()
    service.embedding_provider.generate_all_embeddings = AsyncMock(return_value={})
    service.embedding_provider.embed_batch = AsyncMock(return_value=[[0.1] * 1536])

    # 2. Call store_memory with new fields
    tenant_id = "tenant-1"
    project_id = "proj-x"
    session_id = "sess-123"
    source = "user-chat"
    ttl = 3600

    await service.store_memory(
        tenant_id=tenant_id,
        project=project_id,
        content="Test content",
        source=source,
        session_id=session_id,
        memory_type="chat",
        ttl=ttl,
        layer="episodic",
    )

    # 3. Verify DB execution
    # Get all execute calls
    execute_calls = mock_pool._test_conn.execute.call_args_list

    # Find the call for INSERT INTO memories
    insert_call = None
    for call in execute_calls:
        sql = call[0][0]
        if "INSERT INTO memories" in sql:
            insert_call = call
            break

    assert insert_call is not None, "INSERT INTO memories not called"

    sql, *args = insert_call[0]

    # 4. Verify SQL structure (Phase 2 Requirement)
    assert "INSERT INTO memories" in sql
    assert "project" in sql
    assert "session_id" in sql
    assert "source" in sql
    assert "memory_type" in sql
    assert "expires_at" in sql

    # 5. Verify Values passed (Phase 1 Requirement)
    # Args are passed as a tuple/list after sql
    # args[0] is memory_id, args[1] content...
    # We need to find where the values are.
    # The adapter passes:
    # memory_id, content, layer, tenant_id, agent_id, tags, metadata_json, embedding, importance, expires_at, created_at, memory_type, project, session_id, source

    # Let's inspect args values directly
    # args tuple contains all arguments passed to execute *params

    # Verify project matches
    assert project_id in args

    # Verify session_id matches
    assert session_id in args

    # Verify source matches
    assert source in args

    # Verify memory_type matches
    assert "chat" in args

    # Verify expires_at is set (ttl was provided)
    # It should be a datetime object
    from datetime import timezone

    for arg in args:
        if hasattr(arg, "isoformat") and not isinstance(
            arg, str
        ):  # simple check for datetime
            # Found a datetime, check if it's in the future
            # Ensure comparison is timezone-aware
            arg_aware = arg.replace(tzinfo=timezone.utc) if arg.tzinfo is None else arg
            assert arg_aware > datetime.now(timezone.utc)
            break

    # 6. Verify Metadata (Phase 1 Requirement)
    metadata_arg = None
    for arg in args:
        if isinstance(arg, str):
            try:
                d = json.loads(arg)
                if isinstance(d, dict):
                    metadata_arg = d
            except (json.JSONDecodeError, TypeError):
                pass

    assert metadata_arg is not None
    # Ensure project and source are NOT in metadata (removed to avoid duplication)
    assert "project" not in metadata_arg
    assert "source" not in metadata_arg
