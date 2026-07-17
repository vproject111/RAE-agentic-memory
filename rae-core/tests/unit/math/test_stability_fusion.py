from uuid import uuid4

import pytest

from rae_core.math.fusion import Legacy416Strategy


@pytest.mark.asyncio
async def test_rrf_basic():
    id1, id2, id3 = uuid4(), uuid4(), uuid4()
    list1 = [(id1, 0.9, 0.0), (id2, 0.8, 0.0)]
    list2 = [(id2, 0.9, 0.0), (id3, 0.7, 0.0)]

    fusion = Legacy416Strategy()
    strategy_results = {"s1": list1, "s2": list2}

    fused = await fusion.fuse(strategy_results, query="")

    assert len(fused) == 3
    # id2 is in both, so it should be first
    assert fused[0][0] == id2
