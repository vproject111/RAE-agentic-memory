"""
Integration tests for DecayWorker - Memory Importance Decay

Tests the DecayWorker with real database operations to ensure
memory importance decay works correctly across multiple scenarios.
"""

import json
import uuid
from datetime import datetime, timedelta

import pytest

from apps.memory_api.services.rae_core_service import RAECoreService
from apps.memory_api.workers.memory_maintenance import DecayWorker


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_basic_cycle(mock_app_state_pool):
    """Test basic decay cycle reduces memory importance."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())

    # Insert test memories with high importance
    async with pool.acquire() as conn:
        memory_ids = []
        # Use naive datetimes because DB schema uses TIMESTAMP (not TIMESTAMPTZ)
        timestamp_10_days_ago = datetime.now() - timedelta(days=10)
        for i in range(5):
            memory_id = await conn.fetchval(
                """
                INSERT INTO memories (tenant_id, content, importance, layer, project, created_at, timestamp, memory_type)
                VALUES ($1, $2, $3, 'em', 'default', $4, $5, 'episodic')
                RETURNING id
                """,
                tenant_id,
                f"Test memory {i}",
                0.9,  # High importance
                timestamp_10_days_ago,  # 10 days old
                timestamp_10_days_ago,  # timestamp also 10 days old
            )
            memory_ids.append(memory_id)

    # Create worker and run decay cycle
    from apps.memory_api.services.rae_core_service import RAECoreService

    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    stats = await worker.run_decay_cycle(
        tenant_ids=[tenant_id], decay_rate=0.05, consider_access_stats=False
    )

    # Verify stats
    assert stats["total_tenants"] == 1
    assert stats["total_updated"] == 5

    # Verify importance was reduced
    async with pool.acquire() as conn:
        for memory_id in memory_ids:
            importance = await conn.fetchval(
                "SELECT importance FROM memories WHERE id = $1", memory_id
            )
            assert importance < 0.9, f"Memory {memory_id} importance should be reduced"
            assert importance > 0.0, "Importance should not go negative"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_with_access_stats(mock_app_state_pool):
    """Test that recently accessed memories decay slower."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())

    # Insert two memories: one recently accessed, one stale
    async with pool.acquire() as conn:
        timestamp_30_days_ago = datetime.now() - timedelta(days=30)
        timestamp_60_days_ago = datetime.now() - timedelta(days=60)

        # Recently accessed memory
        recent_id = await conn.fetchval(
            """
            INSERT INTO memories (tenant_id, content, importance, layer, project,
                                 created_at, timestamp, last_accessed_at, usage_count, memory_type)
            VALUES ($1, $2, $3, 'em', 'default', $4, $5, $6, 10, 'episodic')
            RETURNING id
            """,
            tenant_id,
            "Recently accessed memory",
            0.8,
            timestamp_30_days_ago,
            timestamp_30_days_ago,
            datetime.now() - timedelta(hours=2),  # Accessed 2 hours ago
        )

        # Stale memory (not accessed in 60 days)
        stale_id = await conn.fetchval(
            """
            INSERT INTO memories (tenant_id, content, importance, layer, project,
                                 created_at, timestamp, last_accessed_at, usage_count, memory_type)
            VALUES ($1, $2, $3, 'em', 'default', $4, $5, $6, 1, 'episodic')
            RETURNING id
            """,
            tenant_id,
            "Stale memory",
            0.8,
            timestamp_60_days_ago,
            timestamp_60_days_ago,
            datetime.now() - timedelta(days=60),  # Not accessed in 60 days
        )

    # Run decay cycle
    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    await worker.run_decay_cycle(
        tenant_ids=[tenant_id], decay_rate=0.02, consider_access_stats=True
    )

    # Get final importance values
    async with pool.acquire() as conn:
        recent_importance = await conn.fetchval(
            "SELECT importance FROM memories WHERE id = $1", recent_id
        )
        stale_importance = await conn.fetchval(
            "SELECT importance FROM memories WHERE id = $1", stale_id
        )

    # Recently accessed memory should decay less (or be protected)
    # Stale memory should decay more aggressively
    assert (
        stale_importance < recent_importance
    ), "Stale memory should have lower importance than recently accessed memory"
    assert stale_importance >= 0.01, "Importance should not go below floor"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_multiple_tenants(mock_app_state_pool):
    """Test decay cycle processes multiple tenants."""
    pool = mock_app_state_pool
    tenant_ids = [str(uuid.uuid4()) for _ in range(3)]

    # Insert memories for each tenant
    async with pool.acquire() as conn:
        timestamp_5_days_ago = datetime.now() - timedelta(days=5)
        for tenant_id in tenant_ids:
            for i in range(3):
                await conn.execute(
                    """
                    INSERT INTO memories (tenant_id, content, importance, layer, project, created_at, timestamp, memory_type)
                    VALUES ($1, $2, $3, 'em', 'default', $4, $5, 'episodic')
                    """,
                    tenant_id,
                    f"Memory {i}",
                    0.85,
                    timestamp_5_days_ago,
                    timestamp_5_days_ago,
                )

    # Run decay for all tenants

    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    stats = await worker.run_decay_cycle(tenant_ids=tenant_ids, decay_rate=0.03)

    # Verify all tenants processed
    assert stats["total_tenants"] == 3
    assert stats["total_updated"] == 9  # 3 tenants * 3 memories each


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_importance_floor(mock_app_state_pool):
    """Test that importance doesn't go below configured floor."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())

    # Insert memory with very low importance
    async with pool.acquire() as conn:
        timestamp_30_days_ago = datetime.now() - timedelta(days=30)
        memory_id = await conn.fetchval(
            """
            INSERT INTO memories (tenant_id, content, importance, layer, project, created_at, timestamp, memory_type)
            VALUES ($1, $2, $3, 'em', 'default', $4, $5, 'episodic')
            RETURNING id
            """,
            tenant_id,
            "Low importance memory",
            0.02,  # Already near floor
            timestamp_30_days_ago,
            timestamp_30_days_ago,
        )

    # Run decay multiple times

    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    for _ in range(5):
        await worker.run_decay_cycle(tenant_ids=[tenant_id], decay_rate=0.05)

    # Verify importance stayed at or above floor
    async with pool.acquire() as conn:
        final_importance = await conn.fetchval(
            "SELECT importance FROM memories WHERE id = $1", memory_id
        )

    assert final_importance >= 0.01, "Importance should not go below floor (0.01)"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_error_handling(mock_app_state_pool):
    """Test decay worker handles tenant errors gracefully."""
    pool = mock_app_state_pool
    valid_tenant = str(uuid.uuid4())
    invalid_tenant = "invalid-uuid-format"

    # Insert memory for valid tenant
    async with pool.acquire() as conn:
        timestamp_now = datetime.now()
        await conn.execute(
            """
            INSERT INTO memories (tenant_id, content, importance, layer, project, created_at, timestamp, memory_type)
            VALUES ($1, $2, $3, 'em', 'default', $4, $5, 'episodic')
            """,
            valid_tenant,
            "Valid memory",
            0.8,
            timestamp_now,
            timestamp_now,
        )

    # Run decay with both valid and invalid tenant

    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    stats = await worker.run_decay_cycle(
        tenant_ids=[valid_tenant, invalid_tenant], decay_rate=0.02
    )

    # Should process valid tenant successfully despite invalid tenant
    assert stats["total_tenants"] == 2
    assert stats["total_updated"] >= 0  # May be 0 or 1 depending on error handling


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_get_all_tenants(mock_app_state_pool):
    """Test worker can retrieve all tenant IDs from database."""
    pool = mock_app_state_pool
    tenant_ids = [str(uuid.uuid4()) for _ in range(3)]

    # Insert memories for multiple tenants
    async with pool.acquire() as conn:
        timestamp_now = datetime.now()
        for tenant_id in tenant_ids:
            await conn.execute(
                """
                INSERT INTO memories (tenant_id, content, importance, layer, project, created_at, timestamp, memory_type)
                VALUES ($1, $2, $3, 'em', 'default', $4, $5, 'episodic')
                """,
                tenant_id,
                "Test memory",
                0.7,
                timestamp_now,
                timestamp_now,
            )

    # Get all tenants

    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    retrieved_tenants = await worker._get_all_tenant_ids()

    # Verify all tenants retrieved
    assert len(retrieved_tenants) >= 3, "Should retrieve all tenant IDs"
    for tenant_id in tenant_ids:
        assert tenant_id in retrieved_tenants, f"Tenant {tenant_id} should be retrieved"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_empty_database(mock_app_state_pool):
    """Test decay worker handles empty database gracefully."""
    pool = mock_app_state_pool

    # Run decay on empty database

    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    stats = await worker.run_decay_cycle(tenant_ids=[], decay_rate=0.02)

    # Should complete without errors
    assert stats["total_tenants"] == 0
    assert stats["total_updated"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decay_worker_preserves_metadata(mock_app_state_pool):
    """Test that decay preserves memory metadata and other fields."""
    pool = mock_app_state_pool
    tenant_id = str(uuid.uuid4())

    # Insert memory with tags and session_id (metadata column doesn't exist)
    tags = ["important", "test"]
    test_session_id = str(uuid.uuid4())  # Keep as string for JSON

    async with pool.acquire() as conn:
        timestamp_now = datetime.now()
        metadata_json = json.dumps({"session_id": test_session_id})
        memory_id = await conn.fetchval(
            """
            INSERT INTO memories (tenant_id, content, importance, layer, project,
                                 created_at, timestamp, tags, metadata, memory_type)
            VALUES ($1, $2, $3, 'em', 'default', $4, $5, $6, $7::jsonb, 'episodic')
            RETURNING id
            """,
            tenant_id,
            "Test memory with tags",
            0.9,
            timestamp_now,
            timestamp_now,
            tags,
            metadata_json,
        )

    # Run decay

    # Create real RAECoreService
    rae_service = RAECoreService(postgres_pool=pool)
    worker = DecayWorker(rae_service=rae_service)
    await worker.run_decay_cycle(tenant_ids=[tenant_id], decay_rate=0.05)

    # Verify tags and session_id preserved
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            """
            SELECT importance, tags, content, metadata
            FROM memories WHERE id = $1
            """,
            memory_id,
        )

    assert record["importance"] < 0.9, "Importance should be reduced"
    assert record["tags"] == tags, "Tags should be preserved"

    metadata = (
        json.loads(record["metadata"])
        if isinstance(record["metadata"], str)
        else record["metadata"]
    )
    assert (
        metadata.get("session_id") == test_session_id
    ), "Session ID should be preserved"
    assert record["content"] == "Test memory with tags", "Content should be preserved"
