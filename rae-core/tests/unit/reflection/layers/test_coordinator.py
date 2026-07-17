import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rae_core.reflection.layers.coordinator import ReflectionCoordinator


@pytest.mark.asyncio
async def test_coordinator_init():
    coordinator = ReflectionCoordinator(
        mode="advanced",
        enforce_hard_frames=False,
        llm_model="test-model",
        strategy="hybrid",
    )
    assert coordinator.mode == "advanced"
    assert coordinator.enforce_hard_frames is False
    assert coordinator.strategy == "hybrid"
    assert coordinator.l4.model_name == "test-model"


@pytest.mark.asyncio
async def test_run_reflections_l1_block():
    coordinator = ReflectionCoordinator(enforce_hard_frames=True)
    coordinator.l1.reflect = MagicMock(
        return_value={"block": True, "reason": "l1-violation"}
    )

    payload = {"data": "test"}
    result = await coordinator.run_reflections(payload)

    assert result["final_decision"] == "blocked"
    assert "L1 Operational constraints violated" in result["block_reasons"]
    assert result["l1_operational"] == {"block": True, "reason": "l1-violation"}


@pytest.mark.asyncio
async def test_run_reflections_standard_mode():
    coordinator = ReflectionCoordinator(mode="standard")
    coordinator.l1.reflect = MagicMock(return_value={"block": False})
    coordinator.l2.reflect = MagicMock(return_value={"structural_ok": True})

    payload = {"data": "test"}
    result = await coordinator.run_reflections(payload)

    assert result["final_decision"] == "pass"
    assert result["l2_structural"] == {"structural_ok": True}
    assert result["l3_meta_field"] == {}


@pytest.mark.asyncio
async def test_run_reflections_advanced_mode_l3_block():
    coordinator = ReflectionCoordinator(mode="advanced", enforce_hard_frames=True)
    coordinator.l1.reflect = MagicMock(return_value={"block": False})
    coordinator.l2.reflect = MagicMock(return_value={"structural_ok": True})
    coordinator.l3.reflect = MagicMock(return_value={"block": True, "fsi": 0.5})

    payload = {"data": "test"}
    result = await coordinator.run_reflections(payload)

    assert result["final_decision"] == "blocked"
    assert "L3 Meta-Field anomalies critical" in result["block_reasons"]
    assert result["l3_meta_field"] == {"block": True, "fsi": 0.5}


@pytest.mark.asyncio
async def test_run_reflections_hybrid_strategy():
    coordinator = ReflectionCoordinator(strategy="hybrid")
    coordinator.l1.reflect = MagicMock(return_value={"block": False})

    mock_l4_res = {
        "status": "success",
        "insight": {"lesson": "test-lesson", "confidence": 0.9, "tags": ["tag1"]},
    }
    coordinator.l4.reflect = AsyncMock(return_value=mock_l4_res)

    payload = {"data": "test"}
    result = await coordinator.run_reflections(payload)

    assert result["final_decision"] == "pass"
    assert result["l4_cognitive"] == mock_l4_res
    coordinator.l4.reflect.assert_awaited_once_with(payload)


@pytest.mark.asyncio
async def test_run_and_store_reflections_basic():
    storage = AsyncMock()
    coordinator = ReflectionCoordinator(storage=storage)

    payload = {"query_id": "q1", "metadata": {"project": "p1"}}
    tenant_id = "t1"

    # Mock run_reflections
    result_mock = {
        "l1_operational": {"ok": True},
        "l2_structural": {},
        "l3_meta_field": {"field_stability_index": 0.95},
        "l4_cognitive": {"status": "none"},
        "final_decision": "pass",
    }

    with patch.object(
        ReflectionCoordinator, "run_reflections", AsyncMock(return_value=result_mock)
    ):
        res = await coordinator.run_and_store_reflections(payload, tenant_id)

        storage.store_reflection_audit.assert_awaited_once()
        args = storage.store_reflection_audit.call_args.kwargs
        assert args["query_id"] == "q1"
        assert args["tenant_id"] == "t1"
        assert args["fsi_score"] == 0.95
        assert args["final_decision"] == "pass"
        assert args["metadata"]["project"] == "p1"
        assert args["metadata"]["strategy"] == coordinator.strategy


@pytest.mark.asyncio
async def test_run_and_store_reflections_l4_success_with_callback():
    storage = AsyncMock()
    coordinator = ReflectionCoordinator(storage=storage, strategy="hybrid")

    payload = {"metadata": {"project": "p1"}}
    tenant_id = "t1"
    agent_id = "a1"
    store_callback = AsyncMock()

    result_mock = {
        "l1_operational": {},
        "l2_structural": {},
        "l3_meta_field": {},
        "l4_cognitive": {
            "status": "success",
            "insight": {"lesson": "test-lesson", "confidence": 0.9, "tags": ["tag1"]},
        },
        "final_decision": "pass",
    }

    with patch.object(
        ReflectionCoordinator, "run_reflections", AsyncMock(return_value=result_mock)
    ):
        res = await coordinator.run_and_store_reflections(
            payload, tenant_id, agent_id=agent_id, store_callback=store_callback
        )

        # Wait for background task
        await asyncio.sleep(0.1)

        store_callback.assert_awaited_once()
        args = store_callback.call_args.kwargs
        assert "LESSON LEARNED: test-lesson" in args["content"]
        assert args["layer"] == "reflective"
        assert args["tenant_id"] == "t1"
        assert args["agent_id"] == "a1"
        assert "tag1" in args["tags"]
        assert "l4_lesson" in args["tags"]
        assert args["metadata"]["confidence"] == 0.9


@pytest.mark.asyncio
async def test_run_and_store_reflections_l4_success_no_callback():
    storage = AsyncMock()
    coordinator = ReflectionCoordinator(storage=storage, strategy="hybrid")

    payload = {"metadata": {"project": "p1"}}
    tenant_id = "t1"

    result_mock = {
        "l1_operational": {},
        "l2_structural": {},
        "l3_meta_field": {},
        "l4_cognitive": {
            "status": "success",
            "insight": {"lesson": "test-lesson", "confidence": 0.9, "tags": []},
        },
        "final_decision": "pass",
    }

    with patch.object(
        ReflectionCoordinator, "run_reflections", AsyncMock(return_value=result_mock)
    ):
        res = await coordinator.run_and_store_reflections(payload, tenant_id)

        # Wait for background task
        await asyncio.sleep(0.1)

        storage.store_memory.assert_awaited_once()
        args = storage.store_memory.call_args.kwargs
        assert "LESSON LEARNED: test-lesson" in args["content"]
        assert args["agent_id"] == "l4_sage"  # default when agent_id is None


@pytest.mark.asyncio
async def test_run_and_store_reflections_l4_background_fail():
    storage = AsyncMock()
    coordinator = ReflectionCoordinator(storage=storage, strategy="hybrid")

    # storage.store_memory fails
    storage.store_memory.side_effect = Exception("db_error")

    payload = {"metadata": {}}
    tenant_id = "t1"

    result_mock = {
        "l1_operational": {},
        "l2_structural": {},
        "l3_meta_field": {},
        "l4_cognitive": {
            "status": "success",
            "insight": {"lesson": "fail-lesson", "confidence": 0.5, "tags": []},
        },
        "final_decision": "pass",
    }

    with patch.object(
        ReflectionCoordinator, "run_reflections", AsyncMock(return_value=result_mock)
    ):
        # Should not raise exception as it's in background task
        await coordinator.run_and_store_reflections(payload, tenant_id)

        # Wait for background task
        await asyncio.sleep(0.1)

        storage.store_memory.assert_called_once()
