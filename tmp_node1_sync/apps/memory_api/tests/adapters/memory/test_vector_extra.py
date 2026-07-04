from uuid import uuid4

import pytest

from rae_adapters.memory.vector import InMemoryVectorStore


@pytest.mark.asyncio
async def test_in_memory_vector_store_extra():
    store = InMemoryVectorStore()

    # Test update_vector with metadata (163)
    mid = uuid4()
    await store.store_vector(mid, [1.0, 0.0], "t1", {"agent_id": "a1"})
    await store.update_vector(mid, [0.0, 1.0], "t1", {"agent_id": "a2"})

    vec = await store.get_vector(mid, "t1")
    assert vec == [0.0, 1.0]

    # Test search_similar with zero vector (109)
    mid2 = uuid4()
    await store.store_vector(mid2, [0.0, 0.0], "t1")
    results = await store.search_similar([1.0, 0.0], "t1")
    assert mid2 not in [r[0] for r in results]

    # Test search_similar with zero query norm
    assert await store.search_similar([0.0, 0.0], "t1") == []
