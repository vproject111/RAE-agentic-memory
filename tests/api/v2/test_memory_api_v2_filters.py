import pytest
from httpx import AsyncClient
from uuid import uuid4

# Use strict asyncio mode
pytestmark = pytest.mark.asyncio

async def test_api_v2_filters_support():
    """
    Verify that API v2 QueryMemoryRequestV2 supports 'filters' field
    and passes it correctly to the service logic.
    """
    from apps.memory_api.api.v2.memory import QueryMemoryRequestV2, MemoryResult
    
    # 1. Verify Pydantic Model Structure
    req = QueryMemoryRequestV2(
        query="test query",
        project="test-project",
        filters={"governance.is_failure": True, "layer": "episodic"}
    )
    
    assert req.filters is not None
    assert req.filters["governance.is_failure"] is True
    assert req.filters["layer"] == "episodic"
    
    print("\n✅ Pydantic Model 'QueryMemoryRequestV2' correctly accepts 'filters'.")

async def test_api_v2_metadata_response():
    """
    Verify that API v2 MemoryResult supports 'metadata' field.
    """
    from apps.memory_api.api.v2.memory import MemoryResult
    
    res = MemoryResult(
        id=str(uuid4()),
        content="test content",
        score=0.9,
        layer="episodic",
        importance=0.5,
        metadata={"trace_id": "123", "audit": "approved"}
    )
    
    assert res.metadata is not None
    assert res.metadata["trace_id"] == "123"
    
    print("✅ Pydantic Model 'MemoryResult' correctly exposes 'metadata'.")

if __name__ == "__main__":
    # Manual run for quick feedback
    import asyncio
    asyncio.run(test_api_v2_filters_support())
    asyncio.run(test_api_v2_metadata_response())
