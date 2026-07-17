from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.search.strategies.anchor import AnchorStrategy


@pytest.fixture
def storage():
    return AsyncMock()


@pytest.fixture
def strategy(storage):
    return AnchorStrategy(storage)


@pytest.mark.asyncio
async def test_anchor_strategy_no_anchors(strategy):
    results = await strategy.search("Just some text with no anchors", "tenant1")
    assert results == []


@pytest.mark.asyncio
async def test_anchor_strategy_with_uuid(strategy, storage):
    uid = uuid4()
    query = f"Searching for {uid}"

    storage.search_memories.return_value = [
        {"id": str(uid), "score": 1.0, "importance": 0.8}
    ]

    results = await strategy.search(query, "tenant1")

    assert len(results) == 1
    assert results[0][0] == uid
    # current_boost = weight_mod / self.default_weight = 100.0 / 100.0 = 1.0
    assert results[0][1] == 1.0
    storage.search_memories.assert_awaited_with(
        query=f'"{uid}"', tenant_id="tenant1", limit=10
    )


@pytest.mark.asyncio
async def test_anchor_strategy_with_ticket_id(strategy, storage):
    uid = uuid4()
    query = "Fix bug #123"

    storage.search_memories.return_value = [{"id": uid, "score": 1.0}]

    results = await strategy.search(query, "tenant1")

    # "bug #123" matches pattern r"\b(ticket|issue|pr|bug)[\s#_-]+(\d{3,})\b"
    # m[0] = "bug", m[1] = "123"
    # Extracts "bug 123" and "bug123"
    assert len(results) == 1
    assert results[0][0] == uid
    assert storage.search_memories.call_count == 2  # "bug 123" and "bug123"


@pytest.mark.asyncio
async def test_anchor_strategy_with_soft_anchor(strategy, storage):
    uid = uuid4()
    query = "Status 404 error"

    storage.search_memories.return_value = [{"id": uid, "score": 1.0}]

    results = await strategy.search(query, "tenant1")

    assert len(results) == 1
    # 404 has weight 5.0. 5.0 / 100.0 = 0.05
    assert results[0][1] == 0.05


@pytest.mark.asyncio
async def test_anchor_strategy_multiple_anchors_same_doc(strategy, storage):
    uid = uuid4()
    query = f"Error 0x404 on {uid}"

    # 0x404 -> 100.0 (boost 1.0)
    # uuid -> 100.0 (boost 1.0)

    storage.search_memories.return_value = [{"id": uid, "score": 1.0}]

    results = await strategy.search(query, "tenant1")
    assert len(results) == 1
    assert results[0][1] == 1.0


@pytest.mark.asyncio
async def test_anchor_strategy_id_as_uuid_object(strategy, storage):
    uid = uuid4()
    storage.search_memories.return_value = [{"id": uid, "score": 1.0}]
    results = await strategy.search("0x12345", "tenant1")
    assert results[0][0] == uid


def test_get_strategy_name(strategy):
    assert strategy.get_strategy_name() == "anchor"


def test_get_strategy_weight(strategy):
    assert strategy.get_strategy_weight() == 100.0
