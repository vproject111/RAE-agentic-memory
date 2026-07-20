import asyncio
from datetime import datetime, timezone
import pytest
from pydantic import BaseModel
from rae_core.interfaces.adapter import (
    IKnowledgeAdapter,
    RetrievalContext,
    RetrievedKnowledge,
    compute_content_checksum,
)
from rae_core.models.knowledge import AuthorityLevel, KnowledgeSourceType
from rae_core.governance.adapter_broker import AdapterBroker
from rae_adapters.openapi_adapter import OpenAPIAdapter, OpenAPIQueryParams
from rae_adapters.git_adapter import GitRuntimeAdapter
from rae_adapters.rae_memory_adapter import RAEAgenticMemoryAdapter, RAEMemoryQueryParams


# 1. Mocks and Test Classes

class DummyParams(BaseModel):
    pass


class MockSlowAdapter(IKnowledgeAdapter[DummyParams]):
    adapter_id = "mock-slow"
    source_type = KnowledgeSourceType.TEST

    def __init__(self, delay: float = 0.5):
        self.delay = delay

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        context: RetrievalContext[DummyParams],
    ) -> list[RetrievedKnowledge]:
        await asyncio.sleep(self.delay)
        content = f"Result for {query}"
        return [
            RetrievedKnowledge(
                evidence_id="slow-1",
                content=content,
                source_ref="test://slow",
                source_type=self.source_type,
                authority_level=AuthorityLevel.OBSERVED,
                score=0.8,
                observed_at=datetime.now(timezone.utc),
                checksum=compute_content_checksum(content),
            )
        ]


class MockFastAdapter(IKnowledgeAdapter[DummyParams]):
    adapter_id = "mock-fast"
    source_type = KnowledgeSourceType.TEST

    async def retrieve(
        self,
        query: str,
        *,
        limit: int,
        context: RetrievalContext[DummyParams],
    ) -> list[RetrievedKnowledge]:
        content = f"Fast result for {query}"
        return [
            RetrievedKnowledge(
                evidence_id="fast-1",
                content=content,
                source_ref="test://fast",
                source_type=self.source_type,
                authority_level=AuthorityLevel.OBSERVED,
                score=0.9,
                observed_at=datetime.now(timezone.utc),
                checksum=compute_content_checksum(content),
            )
        ]


# 2. Broker Tests

@pytest.mark.asyncio
async def test_broker_retrieval_success():
    fast = MockFastAdapter()
    broker = AdapterBroker([fast])
    context = RetrievalContext(
        tenant_id="t1",
        request_id="r1",
        timeout_seconds=2.0,
    )
    res = await broker.retrieve("hello", context=context)
    assert len(res) == 1
    assert "hello" in res[0].content


@pytest.mark.asyncio
async def test_broker_timeout_handling():
    slow = MockSlowAdapter(delay=0.5)
    broker = AdapterBroker([slow])
    # Set context timeout lower than adapter delay
    context = RetrievalContext(
        tenant_id="t1",
        request_id="r1",
        timeout_seconds=0.1,
    )
    res = await broker.retrieve("hello", context=context)
    assert len(res) == 0  # Should time out gracefully and return empty list


@pytest.mark.asyncio
async def test_broker_deduplication():
    # Return duplicate items with different scores
    item1 = RetrievedKnowledge(
        evidence_id="id-1",
        content="Dup content",
        source_ref="test://dup",
        source_type=KnowledgeSourceType.TEST,
        authority_level=AuthorityLevel.OBSERVED,
        score=0.5,
        observed_at=datetime.now(timezone.utc),
        checksum="abcd" * 16,
    )
    item2 = RetrievedKnowledge(
        evidence_id="id-2",
        content="Dup content",
        source_ref="test://dup",
        source_type=KnowledgeSourceType.TEST,
        authority_level=AuthorityLevel.OBSERVED,
        score=0.9,  # Higher score
        observed_at=datetime.now(timezone.utc),
        checksum="abcd" * 16,
    )
    deduped = AdapterBroker._deduplicate([item1, item2])
    assert len(deduped) == 1
    assert deduped[0].score == 0.9


# 3. OpenAPIAdapter Tests

def test_openapi_adapter_indexing(tmp_path):
    spec_content = """
openapi: 3.0.0
info:
  title: Test API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
    post:
      summary: Create user
  /roles:
    get:
      summary: List roles
"""
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text(spec_content, encoding="utf-8")

    adapter = OpenAPIAdapter(str(spec_file))
    assert len(adapter._index) == 2
    assert adapter._index[0][0] == "/users"
    assert "/roles" in [item[0] for item in adapter._index]


@pytest.mark.asyncio
async def test_openapi_adapter_retrieve(tmp_path):
    spec_content = """
openapi: 3.0.0
paths:
  /users:
    get:
      summary: Get list
"""
    spec_file = tmp_path / "openapi.yaml"
    spec_file.write_text(spec_content, encoding="utf-8")
    adapter = OpenAPIAdapter(str(spec_file))

    context = RetrievalContext(
        tenant_id="t1",
        request_id="r1",
        params=OpenAPIQueryParams(method_filter="get"),
    )
    results = await adapter.retrieve("users", limit=5, context=context)
    assert len(results) == 1
    assert results[0].source_type == KnowledgeSourceType.OPENAPI
    assert "users" in results[0].evidence_id


# 4. RAEAgenticMemoryAdapter Tests

class MockRAECoreService:
    def __init__(self, search_results):
        self.search_results = search_results

    async def search_memories(self, query, tenant_id, limit, layer=None):
        self.last_query = query
        self.last_tenant_id = tenant_id
        self.last_layer = layer
        return self.search_results


@pytest.mark.asyncio
async def test_rae_memory_adapter_retrieval():
    mock_data = [
        {
            "id": "12345678-1234-1234-1234-123456789abc",
            "content": "Episodic memory details",
            "content_hash": "a" * 64,
            "info_class": "restricted",
            "math_score": 0.85,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]
    service = MockRAECoreService(mock_data)
    adapter = RAEAgenticMemoryAdapter(service)

    context = RetrievalContext(
        tenant_id="t1",
        request_id="r1",
        params=RAEMemoryQueryParams(layer_filter="working"),
    )

    results = await adapter.retrieve("search query", limit=2, context=context)
    assert len(results) == 1
    assert results[0].content == "Episodic memory details"
    # Restricted memories should map to UNTRUSTED authority
    assert results[0].authority_level == AuthorityLevel.UNTRUSTED
    assert results[0].score == 0.85

    assert service.last_query == "search query"
    assert service.last_tenant_id == "t1"
    assert service.last_layer == "working"


@pytest.mark.asyncio
async def test_git_adapter_retrieval():
    import os
    repo_path = os.getcwd()
    adapter = GitRuntimeAdapter(repo_path)
    context = RetrievalContext(
        tenant_id="t1",
        request_id="r1",
    )
    results = await adapter.retrieve("commit", limit=1, context=context)
    assert len(results) == 1
    assert results[0].source_type == KnowledgeSourceType.GIT
    assert "HEAD commit" in results[0].content
    assert len(results[0].checksum) == 64
