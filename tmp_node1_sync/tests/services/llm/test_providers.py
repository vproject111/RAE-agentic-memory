from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.memory_api.services.llm.openai import OpenAIProvider


@pytest.mark.asyncio
async def test_openai_generate():
    with patch("apps.memory_api.services.llm.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        mock_resp = MagicMock()
        mock_resp.choices = [
            MagicMock(message=MagicMock(content="Hello"), finish_reason="stop")
        ]
        mock_resp.usage.prompt_tokens = 10
        mock_resp.usage.completion_tokens = 10
        mock_resp.usage.total_tokens = 20

        mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)

        provider = OpenAIProvider(api_key="test")
        res = await provider.generate(system="sys", prompt="user", model="gpt-4")

        assert res.text == "Hello"
