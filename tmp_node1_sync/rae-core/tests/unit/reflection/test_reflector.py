from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from rae_core.interfaces.llm import ILLMProvider
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.reflection.reflector import Reflector


@pytest.fixture
def mock_storage():
    storage = Mock(spec=IMemoryStorage)
    storage.store_memory = AsyncMock(return_value=uuid4())
    storage.get_memory = AsyncMock()
    storage.list_memories = AsyncMock(return_value=[])
    return storage


@pytest.fixture
def mock_llm():
    llm = Mock(spec=ILLMProvider)
    llm.generate = AsyncMock(return_value="LLM Generated Reflection")
    llm.summarize = AsyncMock(return_value="LLM Summary")
    return llm


@pytest.fixture
def reflector_with_llm(mock_storage, mock_llm):
    return Reflector(memory_storage=mock_storage, llm_provider=mock_llm)


@pytest.fixture
def reflector_rule_based(mock_storage):
    return Reflector(memory_storage=mock_storage, llm_provider=None)


@pytest.mark.asyncio
async def test_generate_consolidation_llm(reflector_with_llm, mock_storage, mock_llm):
    id1, id2 = uuid4(), uuid4()
    mock_storage.get_memory.side_effect = [
        {"id": id1, "content": "Memory 1", "tags": ["tag1"]},
        {"id": id2, "content": "Memory 2", "tags": ["tag1", "tag2"]},
    ]

    result = await reflector_with_llm.generate_reflection(
        memory_ids=[id1, id2],
        tenant_id="t",
        agent_id="a",
        reflection_type="consolidation",
    )

    assert result["success"] is True
    assert result["type"] == "consolidation"
    assert result["content"] == "LLM Summary"

    # Verify LLM call
    mock_llm.summarize.assert_called_once()

    # Verify storage
    mock_storage.store_memory.assert_called_once()
    assert mock_storage.store_memory.call_args.kwargs["layer"] == "reflective"


@pytest.mark.asyncio
async def test_generate_consolidation_fallback(reflector_rule_based, mock_storage):
    id1, id2 = uuid4(), uuid4()
    mock_storage.get_memory.side_effect = [
        {"id": id1, "content": "Memory 1", "tags": ["tag1"]},
        {"id": id2, "content": "Memory 2", "tags": ["tag1", "tag2"]},
    ]

    result = await reflector_rule_based.generate_reflection(
        memory_ids=[id1, id2],
        tenant_id="t",
        agent_id="a",
        reflection_type="consolidation",
    )

    assert result["success"] is True
    assert "Consolidated 2 memories" in result["content"]
    assert "tag1" in result["content"]

    mock_storage.store_memory.assert_called_once()


@pytest.mark.asyncio
async def test_generate_pattern_reflection(reflector_rule_based, mock_storage):
    # Setup memories with common tag
    memories = [
        {"id": uuid4(), "content": f"Mem {i}", "tags": ["repeated_pattern"]}
        for i in range(3)
    ]
    mock_storage.get_memory.side_effect = memories

    result = await reflector_rule_based.generate_reflection(
        memory_ids=[m["id"] for m in memories],
        tenant_id="t",
        agent_id="a",
        reflection_type="pattern",
    )

    assert result["success"] is True
    assert "tag_pattern:repeated_pattern" in result["patterns"]


@pytest.mark.asyncio
async def test_identify_reflection_candidates(reflector_rule_based, mock_storage):
    # Setup list of memories with tags
    mock_storage.list_memories.return_value = [
        {"id": str(uuid4()), "tags": ["topic_a"]},
        {"id": str(uuid4()), "tags": ["topic_a"]},
        {"id": str(uuid4()), "tags": ["topic_a"]},  # 3 memories with topic_a
        {"id": str(uuid4()), "tags": ["topic_b"]},
    ]

    # Set min_memories=3
    candidates = await reflector_rule_based.identify_reflection_candidates(
        tenant_id="t", min_memories=3
    )

    assert len(candidates) == 1
    assert candidates[0]["tag"] == "topic_a"
    assert candidates[0]["count"] == 3
