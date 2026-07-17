from uuid import uuid4

import pytest

from rae_core.search.rerankers.api import ApiReranker
from rae_core.search.rerankers.mcp import McpReranker


class TestApiReranker:
    @pytest.mark.asyncio
    async def test_rerank_basic(self):
        reranker = ApiReranker(api_url="http://example.com/rerank", api_key="test_key")
        candidates = [(uuid4(), 0.9, 0.8), (uuid4(), 0.7, 0.6)]
        result = await reranker.rerank(
            "test query", candidates, tenant_id="tenant1", limit=1
        )
        assert len(result) == 1
        assert result[0] == candidates[0]

    @pytest.mark.asyncio
    async def test_rerank_no_key(self):
        reranker = ApiReranker(api_url="http://example.com/rerank")
        assert reranker.api_key is None
        candidates = [(uuid4(), 0.9, 0.8)]
        result = await reranker.rerank("test query", candidates, tenant_id="tenant1")
        assert result == candidates


class TestMcpReranker:
    @pytest.mark.asyncio
    async def test_rerank_basic(self):
        reranker = McpReranker(tool_name="my_reranker")
        assert reranker.tool_name == "my_reranker"
        candidates = [(uuid4(), 0.9, 0.8), (uuid4(), 0.7, 0.6)]
        result = await reranker.rerank(
            "test query", candidates, tenant_id="tenant1", limit=1
        )
        assert len(result) == 1
        assert result[0] == candidates[0]

    @pytest.mark.asyncio
    async def test_rerank_default_tool(self):
        reranker = McpReranker()
        assert reranker.tool_name == "rerank"
        candidates = [(uuid4(), 0.9, 0.8)]
        result = await reranker.rerank("test query", candidates, tenant_id="tenant1")
        assert result == candidates
