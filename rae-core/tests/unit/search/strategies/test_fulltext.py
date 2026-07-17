from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from rae_core.search.strategies.fulltext import FullTextStrategy


@pytest.fixture
def storage():
    return AsyncMock()


@pytest.fixture
def strategy(storage):
    return FullTextStrategy(storage)


@pytest.mark.asyncio
async def test_fulltext_strategy_search_basic(strategy, storage):
    uid = uuid4()
    storage.search_memories.return_value = [
        {"id": str(uid), "score": 0.9, "importance": 0.5}
    ]

    results = await strategy.search("test query", "tenant1")

    assert len(results) == 1
    assert results[0] == (uid, 0.9, 0.5)
    storage.search_memories.assert_awaited_with(
        query="test query",
        tenant_id="tenant1",
        limit=10,
        agent_id="default",
        layer=None,
        project=None,
    )


@pytest.mark.asyncio
async def test_fulltext_strategy_search_with_filters(strategy, storage):
    uid = uuid4()
    storage.search_memories.return_value = [
        {"id": uid, "score": 0.8, "importance": 0.7}
    ]

    results = await strategy.search(
        "test query",
        "tenant1",
        filters={"agent_id": "agent1", "layer": "working", "project": "proj1"},
    )

    assert len(results) == 1
    assert results[0] == (uid, 0.8, 0.7)
    storage.search_memories.assert_awaited_with(
        query="test query",
        tenant_id="tenant1",
        limit=10,
        agent_id="agent1",
        layer="working",
        project="proj1",
    )


@pytest.mark.asyncio
async def test_fulltext_strategy_search_with_kwargs(strategy, storage):
    uid = uuid4()
    storage.search_memories.return_value = [
        {"id": uid, "score": 0.8, "importance": 0.7}
    ]

    results = await strategy.search(
        "test query", "tenant1", agent_id="agent2", layer="episodic", project="proj2"
    )

    storage.search_memories.assert_awaited_with(
        query="test query",
        tenant_id="tenant1",
        limit=10,
        agent_id="agent2",
        layer="episodic",
        project="proj2",
    )


@pytest.mark.asyncio
async def test_fulltext_strategy_invalid_id(strategy, storage):
    storage.search_memories.return_value = [
        {"id": 12345, "score": 0.8}  # Not str or UUID
    ]
    results = await strategy.search("test", "tenant1")
    assert results == []


def test_get_strategy_name(strategy):
    assert strategy.get_strategy_name() == "fulltext"


def test_get_strategy_weight(strategy):
    assert strategy.get_strategy_weight() == 1.0
