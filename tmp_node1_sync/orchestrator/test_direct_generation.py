"""Direct test of Gemini generation without full orchestrator."""

import asyncio

from providers.gemini import GeminiProvider


async def test_simple_generation():
    """Test Gemini with a very simple prompt."""
    print("🧪 Test: Direct Gemini Generation")
    print("=" * 60)

    provider = GeminiProvider(
        cli_path="gemini",
        rate_limit_delay=False,  # Disable for testing
    )

    # Very simple prompt
    prompt = "Write a Python function that returns 'Hello, World!'. Just the code, no explanation."

    print(f"\n📤 Prompt: {prompt}\n")
    print("⏳ Calling Gemini...")

    result = await provider.generate(
        model="gemini-2.5-flash",
        prompt=prompt,
        max_tokens=200,
    )

    if result.error:
        print(f"\n❌ Error: {result.error}\n")
        return False

    print("\n✅ Success!")
    print(f"\n📥 Response:\n{result.content}\n")

    if result.usage:
        print(
            f"Token usage: {result.usage.input_tokens} in, {result.usage.output_tokens} out"
        )

    return True


if __name__ == "__main__":
    success = asyncio.run(test_simple_generation())
    exit(0 if success else 1)
