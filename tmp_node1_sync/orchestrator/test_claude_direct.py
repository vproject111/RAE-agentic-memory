"""Test Claude API directly."""

import asyncio
import os

from providers.claude import ClaudeProvider


async def test_claude():
    """Test Claude with simple prompt."""
    print("🧪 Test: Claude API Direct")
    print("=" * 60)

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment")
        return False

    print(f"✅ API key found: {api_key[:20]}...")

    # Create provider
    provider = ClaudeProvider(api_key=api_key)

    # Simple test
    prompt = "What is 2+2? Answer in one word."
    print(f"\n📤 Prompt: {prompt}")
    print("⏳ Calling Claude API...")

    result = await provider.generate(
        model="claude-sonnet-4-5-20250929",
        prompt=prompt,
        max_tokens=50,
    )

    if result.error:
        print(f"\n❌ Error: {result.error}")
        return False

    print("\n✅ Success!")
    print(f"📥 Response: {result.content}")

    if result.usage:
        print(
            f"Token usage: {result.usage.input_tokens} in, {result.usage.output_tokens} out"
        )
        cost = (
            result.usage.input_tokens * 0.003 + result.usage.output_tokens * 0.015
        ) / 1000
        print(f"Cost: ${cost:.4f}")

    return True


if __name__ == "__main__":
    success = asyncio.run(test_claude())
    exit(0 if success else 1)
