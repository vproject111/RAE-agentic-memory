import pytest

from apps.memory_api.services.rae_core_service import RAECoreService
from rae_core.exceptions.base import SecurityPolicyViolationError
from rae_core.types.enums import InformationClass, MemoryLayer


@pytest.mark.asyncio
async def test_restricted_data_blocked_in_episodic():
    # Setup RAECoreService in Lite/InMemory mode for fast testing
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    # Attempt to store RESTRICTED data in EPISODIC layer
    with pytest.raises(SecurityPolicyViolationError) as excinfo:
        await service.store_memory(
            tenant_id="test-tenant",
            project="test-project",
            content="Top Secret Password",
            source="user",
            layer=MemoryLayer.EPISODIC,
            info_class=InformationClass.RESTRICTED,
        )

    assert "Security Policy Violation" in str(excinfo.value)
    assert (
        "restricted data cannot be stored in episodic layer"
        in str(excinfo.value).lower()
    )


@pytest.mark.asyncio
async def test_restricted_data_allowed_in_working():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    # This should pass
    memory_id = await service.store_memory(
        tenant_id="test-tenant",
        project="test-project",
        content="Transient Secret",
        source="user",
        layer=MemoryLayer.WORKING,
        info_class=InformationClass.RESTRICTED,
    )

    assert memory_id is not None


@pytest.mark.asyncio
async def test_high_risk_sequence_tagging():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    tags = ["initial-tag"]
    governance = {"pattern_type": "prompt_chaining", "fields": {"chain_length": 10}}

    memory_id = await service.store_memory(
        tenant_id="test-tenant",
        project="test-project",
        content="Long chain execution",
        source="agent",
        tags=tags,
        governance=governance,
    )

    # Retrieve memory to check tags
    memory = await service.get_memory(memory_id, "test-tenant")
    # In InMemoryStorage, it might return a dict or similar
    assert memory is not None
    assert "high_risk_sequence" in memory["tags"]
    assert "initial-tag" in memory["tags"]


@pytest.mark.asyncio
async def test_low_confidence_routing_tagging():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    governance = {
        "pattern_type": "routing_decision",
        "fields": {"decision_basis_confidence": 0.3},
    }

    memory_id = await service.store_memory(
        tenant_id="test-tenant",
        project="test-project",
        content="Uncertain routing",
        source="agent",
        governance=governance,
    )

    memory = await service.get_memory(memory_id, "test-tenant")
    assert memory is not None
    assert "hitl_review_required" in memory["tags"]


@pytest.mark.asyncio
async def test_heavy_tool_use_tagging():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    governance = {
        "pattern_type": "tool_invocation",
        "fields": {"cost_metrics": {"token_count": 15000}},
    }

    memory_id = await service.store_memory(
        tenant_id="test-tenant",
        project="test-project",
        content="Expensive tool call",
        source="agent",
        governance=governance,
    )

    memory = await service.get_memory(memory_id, "test-tenant")
    assert memory is not None
    assert "heavy_tool_use" in memory["tags"]


@pytest.mark.asyncio
async def test_negative_confidence_delta_tagging():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    governance = {
        "pattern_type": "reflection",
        "fields": {"confidence_before": 0.8, "confidence_after": 0.5},
    }

    memory_id = await service.store_memory(
        tenant_id="test-tenant",
        project="test-project",
        content="Confusion after reflection",
        source="agent",
        governance=governance,
    )

    memory = await service.get_memory(memory_id, "test-tenant")
    assert memory is not None
    assert "deeper_reflection_needed" in memory["tags"]


@pytest.mark.asyncio
async def test_confidential_data_blocked_in_semantic():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    # Attempt to store CONFIDENTIAL data in SEMANTIC layer
    with pytest.raises(SecurityPolicyViolationError) as excinfo:
        await service.store_memory(
            tenant_id="test-tenant",
            project="test-project",
            content="Sensitive Business Strategy",
            source="user",
            layer=MemoryLayer.SEMANTIC,
            info_class=InformationClass.CONFIDENTIAL,
        )

    assert "Security Policy Violation" in str(excinfo.value)
    assert (
        "confidential data cannot be promoted to semantic layer"
        in str(excinfo.value).lower()
    )


@pytest.mark.asyncio
async def test_multi_agent_conflict_tagging():
    service = RAECoreService(postgres_pool=None, qdrant_client=None, redis_client=None)

    governance = {
        "pattern_type": "multi_agent_interaction",
        "fields": {"conflict_points": ["Resource contention on CPU"]},
    }

    memory_id = await service.store_memory(
        tenant_id="test-tenant",
        project="test-project",
        content="Agents fighting for resources",
        source="agent",
        governance=governance,
    )

    memory = await service.get_memory(memory_id, "test-tenant")
    assert memory is not None
    assert "coordination_failure" in memory["tags"]
