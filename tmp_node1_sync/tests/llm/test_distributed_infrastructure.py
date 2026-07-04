"""
Distributed Infrastructure Tests.

Verifies connectivity and functionality of:
1. Local Node1 (Ollama/DeepSeek)
2. Cloud Anthropic (Claude)

Uses configuration similar to profiles/distributed_test.yaml.
"""

import os

import pytest

from apps.llm import LLMMessage, LLMRequest, LLMResponse
from apps.llm.providers.anthropic_provider import AnthropicProvider
from apps.llm.providers.deepseek_provider import DeepSeekProvider

# Configuration
NODE1_URL = "http://100.66.252.117:11434/v1"  # OpenAI compatible endpoint on Ollama
NODE1_MODEL = "deepseek-coder:1.3b"  # Verify model name from verification script
CLAUDE_MODEL = "claude-3-haiku-20240307"


@pytest.mark.asyncio
@pytest.mark.llm
class TestDistributedInfrastructure:
    async def test_node1_connectivity(self):
        """Verify Node1 (DeepSeek/Ollama) is reachable and responding."""
        # Ollama doesn't need a real key, but the client might require non-empty
        provider = DeepSeekProvider(api_key="ollama", api_base=NODE1_URL)

        request = LLMRequest(
            model=NODE1_MODEL,
            messages=[
                LLMMessage(role="user", content="Print 'Hello Node1' in Python.")
            ],
            temperature=0.1,
            max_tokens=50,
        )

        try:
            response = await provider.complete(request)
            assert isinstance(response, LLMResponse)
            assert response.text
            print(f"\nNode1 Response: {response.text}")
            assert "print" in response.text.lower() or "hello" in response.text.lower()
        except Exception as e:
            pytest.fail(f"Node1 connectivity failed: {e}")

    async def test_anthropic_connectivity(self):
        """Verify Anthropic (Claude) is reachable."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not found in environment")

        provider = AnthropicProvider(api_key=api_key)

        request = LLMRequest(
            model=CLAUDE_MODEL,
            messages=[LLMMessage(role="user", content="Say 'Hello Claude'")],
            temperature=0.5,
            max_tokens=20,
        )

        try:
            response = await provider.complete(request)
            assert isinstance(response, LLMResponse)
            assert response.text
            print(f"\nClaude Response: {response.text}")
            assert "Hello" in response.text
        except Exception as e:
            print(f"\nClaude Error: {e}")
            pytest.fail(f"Anthropic connectivity failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
