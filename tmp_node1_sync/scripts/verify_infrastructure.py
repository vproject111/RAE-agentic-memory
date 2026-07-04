import asyncio
import os
import sys

# Ensure rae-core is in path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "rae-core"))

from rae_core.interfaces.llm import ILLMProvider
from rae_core.llm.config import LLMConfig
from rae_core.llm.orchestrator import LLMOrchestrator

# We need a concrete implementation of ILLMProvider that uses LiteLLM
# Since rae-core defines the interface but apps/memory_api usually implements it,
# I will create a minimal LitellmProvider here for verification.

try:
    from litellm import acompletion
except ImportError:
    print("Error: litellm not installed. Please install it.")
    sys.exit(1)


class LiteLLMProvider(ILLMProvider):
    def __init__(
        self, name: str, model: str, api_base: str = None, api_key: str = None
    ):
        self.name = name
        self.model = model
        self.api_base = api_base
        self.api_key = api_key

    async def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = await acompletion(
                model=self.model,
                messages=messages,
                api_base=self.api_base,
                api_key=self.api_key,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error calling {self.name}: {e}")
            raise

    async def generate_with_context(self, messages: list[dict], **kwargs) -> str:
        response = await acompletion(
            model=self.model,
            messages=messages,
            api_base=self.api_base,
            api_key=self.api_key,
            **kwargs,
        )
        return response.choices[0].message.content

    async def count_tokens(self, text: str) -> int:
        return len(text) // 4  # Rough estimate

    def supports_function_calling(self) -> bool:
        return False

    async def extract_entities(self, text: str) -> list[dict]:
        return []

    async def summarize(self, text: str, max_length: int = 200) -> str:
        return text[:max_length]


async def verify():
    print("=== Starting Infrastructure Verification ===")

    # 1. Configure Providers
    print("\n1. Configuring Providers...")

    # Claude (Anthropic)
    claude_key = os.environ.get("ANTHROPIC_API_KEY")
    if not claude_key:
        print("SKIP: ANTHROPIC_API_KEY not found")
        claude_provider = None
    else:
        claude_provider = LiteLLMProvider(
            name="claude",
            model="claude-3-opus-20240229",  # Or sonnet
            api_key=claude_key,
        )
        print("  - Claude Provider Configured")

    # DeepSeek (Ollama on Node1)
    ollama_url = "http://100.66.252.117:11434"
    deepseek_provider = LiteLLMProvider(
        name="deepseek", model="ollama/deepseek-coder:1.3b", api_base=ollama_url
    )
    print(f"  - DeepSeek Provider Configured (Node1: {ollama_url})")

    # 2. Test Calls
    print("\n2. Testing Connectivity...")

    if claude_provider:
        print("  > Sending ping to Claude...")
        try:
            resp = await claude_provider.generate(
                "Hello, reply with 'Pong from Claude'", max_tokens=20
            )
            print(f"  < Claude Response: {resp}")
        except Exception as e:
            print(f"  ! Claude Check Failed: {e}")

    print("  > Sending ping to DeepSeek (Node1)...")
    try:
        resp = await deepseek_provider.generate(
            "print('Hello from DeepSeek')", max_tokens=50
        )
        print(f"  < DeepSeek Response: {resp}")
    except Exception as e:
        print(f"  ! DeepSeek Check Failed: {e}")

    # 3. Setup RAE Orchestrator
    print("\n3. Verifying RAE Orchestrator...")

    providers = {}
    if claude_provider:
        providers["claude"] = claude_provider
    providers["deepseek"] = deepseek_provider

    config = LLMConfig(
        providers={},  # We inject instances directly
        default_provider="deepseek",  # Default to local for safety/cost in test
        enable_fallback=True,
    )

    orchestrator = LLMOrchestrator(config, providers=providers)

    print("  > Orchestrator initialized. Testing generic generation (default)...")
    res, provider = await orchestrator.generate("What is 2+2?")
    print(f"  < Orchestrator Result: '{res.strip()}' (via {provider})")

    if "claude" in providers:
        print("  > Orchestrator forced routing to Claude...")
        res, provider = await orchestrator.generate(
            "What is 3+3?", provider_name="claude"
        )
        print(f"  < Orchestrator Result: '{res.strip()}' (via {provider})")

    print("\n=== Verification Complete ===")


if __name__ == "__main__":
    asyncio.run(verify())
