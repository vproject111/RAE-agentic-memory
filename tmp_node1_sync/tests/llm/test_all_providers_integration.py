"""
Integration tests for all available LLM providers in the RAE ecosystem.

Covers:
1. Local Ollama (localhost)
2. Node1 Ollama (Distributed Compute)
3. Anthropic (Cloud)
4. Gemini (Cloud - Google)
5. OpenAI (Cloud - if available)
"""

import os

import httpx
import pytest

from apps.llm import LLMMessage, LLMRequest
from apps.llm.providers.anthropic_provider import AnthropicProvider
from apps.llm.providers.gemini_provider import GeminiProvider
from apps.llm.providers.ollama_provider import OllamaProvider
from apps.llm.providers.openai_provider import OpenAIProvider

# Configuration
LOCAL_OLLAMA_URL = "http://localhost:11434"
NODE1_OLLAMA_URL = "http://100.66.252.117:11434"
# Models
OLLAMA_MODEL = "deepseek-coder:1.3b"
CLAUDE_MODEL = "claude-3-haiku-20240307"
GEMINI_MODEL = "gemini-1.5-flash"
OPENAI_MODEL = "gpt-3.5-turbo"


@pytest.mark.asyncio
@pytest.mark.llm
class TestAllProvidersIntegration:
    async def test_local_ollama_connectivity(self):
        """Verify Local Ollama is reachable."""
        print(f"\nTesting Local Ollama at {LOCAL_OLLAMA_URL}...")
        provider = OllamaProvider(api_url=LOCAL_OLLAMA_URL)

        request = LLMRequest(
            model=OLLAMA_MODEL,
            messages=[LLMMessage(role="user", content="Say 'Local Ollama OK'")],
            temperature=0.1,
            max_tokens=20,
        )

        try:
            # Check if model exists first (optional but good for debug)
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{LOCAL_OLLAMA_URL}/api/tags")
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json()["models"]]
                    print(f"  Available models: {models}")
                    if (
                        OLLAMA_MODEL not in models
                        and f"{OLLAMA_MODEL}:latest" not in models
                    ):
                        print(f"  Warning: {OLLAMA_MODEL} not found in local tags.")

            response = await provider.complete(request)
            print(f"  Response: {response.text}")
            assert response.text
        except Exception as e:
            pytest.fail(f"Local Ollama failed: {e}")

    async def test_node1_ollama_connectivity(self):
        """Verify Node1 (Distributed) Ollama is reachable."""
        print(f"\nTesting Node1 Ollama at {NODE1_OLLAMA_URL}...")
        provider = OllamaProvider(api_url=NODE1_OLLAMA_URL)

        request = LLMRequest(
            model=OLLAMA_MODEL,
            messages=[LLMMessage(role="user", content="Say 'Node1 Ollama OK'")],
            temperature=0.1,
            max_tokens=20,
        )

        try:
            response = await provider.complete(request)
            print(f"  Response: {response.text}")
            assert response.text
        except Exception as e:
            pytest.fail(f"Node1 Ollama failed: {e}")

    @pytest.mark.skip("Requires ANTHROPIC_API_KEY")
    async def test_anthropic_connectivity(self):
        """Verify Anthropic (Claude) connectivity."""
        print("\nTesting Anthropic...")
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY not found")

        provider = AnthropicProvider(api_key=api_key)
        request = LLMRequest(
            model=CLAUDE_MODEL,
            messages=[LLMMessage(role="user", content="Say 'Claude OK'")],
            max_tokens=20,
        )

        try:
            response = await provider.complete(request)
            print(f"  Response: {response.text}")
            assert response.text
        except Exception as e:
            pytest.fail(f"Anthropic failed: {e}")

    @pytest.mark.skip("Requires GEMINI_API_KEY")
    async def test_gemini_connectivity(self):
        """Verify Google Gemini connectivity."""
        print("\nTesting Gemini...")
        api_key = os.environ.get("GEMINI_API_KEY")

        # If API key is a placeholder, ignore it to force built-in Token/ADC logic
        if api_key and (api_key.startswith("your-") or "gemini-key" in api_key):
            print(
                "  Ignoring placeholder GEMINI_API_KEY, will use built-in Token/ADC fallback..."
            )
            api_key = None

        try:
            # GeminiProvider now automatically tries: args -> ~/.gemini/oauth_creds.json -> ADC
            provider = GeminiProvider(api_key=api_key)
            request = LLMRequest(
                model=GEMINI_MODEL,
                messages=[LLMMessage(role="user", content="Say 'Gemini OK'")],
                max_tokens=20,
            )
            response = await provider.complete(request)
            print(f"  Response: {response.text}")
            assert response.text
        except ValueError as e:
            # Raised by GeminiProvider if no auth found
            print(f"  Gemini authentication not configured: {e}")
            pytest.skip(f"Gemini credentials not found: {e}")
        except Exception as e:
            print(f"  Gemini Error detail: {e}")
            # If it's an auth error from the API (not our local check), we might still want to skip in some environments
            if (
                "api key not valid" in str(e).lower()
                or "authentication" in str(e).lower()
            ):
                pytest.skip(f"Gemini authentication failed (invalid key/token): {e}")
            pytest.fail(f"Gemini failed: {e}")

    @pytest.mark.skip("Requires OPENAI_API_KEY")
    async def test_openai_connectivity(self):
        """Verify OpenAI connectivity."""
        print("\nTesting OpenAI...")
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY not found")

        provider = OpenAIProvider(api_key=api_key)
        request = LLMRequest(
            model=OPENAI_MODEL,
            messages=[LLMMessage(role="user", content="Say 'OpenAI OK'")],
            max_tokens=20,
        )

        try:
            response = await provider.complete(request)
            print(f"  Response: {response.text}")
            assert response.text
        except Exception as e:
            pytest.fail(f"OpenAI failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
