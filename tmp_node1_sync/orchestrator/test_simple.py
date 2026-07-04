"""Simple test to verify orchestrator functionality.

Tests:
1. Provider registry initialization
2. Gemini provider availability (free, no API key)
3. Model listing
4. Simple generation test
"""

import asyncio
import os
import sys
from pathlib import Path

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent))

from providers.config import get_configured_registry
from providers.gemini import GeminiProvider


async def test_registry():
    """Test provider registry initialization."""
    print("=" * 60)
    print("TEST 1: Provider Registry Initialization")
    print("=" * 60)

    try:
        registry = get_configured_registry()
        print("✅ Registry initialized successfully")
        print(f"   Registered providers: {list(registry.list_providers())}")

        # List all models
        models = registry.list_models()
        print(f"   Total models available: {len(models)}")

        for model in models[:5]:  # Show first 5
            print(f"   - {model.display_name} ({model.provider}): {model.tier.value}")

        return True
    except Exception as e:
        print(f"❌ Registry initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_gemini_provider():
    """Test Gemini provider directly (free, no API key)."""
    print("\n" + "=" * 60)
    print("TEST 2: Gemini Provider (Free CLI)")
    print("=" * 60)

    try:
        # Create Gemini provider with rate limiting disabled for testing
        provider = GeminiProvider(
            cli_path="gemini",
            rate_limit_delay=False,  # Disable for faster testing
        )

        print("✅ Gemini provider created")
        print(f"   Provider name: {provider.name}")
        print(f"   Available models: {len(provider.available_models)}")

        # Check CLI availability
        is_available = await provider.is_available()
        print(f"   CLI available: {'✅ Yes' if is_available else '❌ No'}")

        if not is_available:
            print("   ⚠️  Gemini CLI not available - skipping generation test")
            print("   Run: gemini auth login")
            return False

        return True
    except Exception as e:
        print(f"❌ Gemini provider test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_generation():
    """Test simple text generation with Gemini."""
    print("\n" + "=" * 60)
    print("TEST 3: Simple Generation Test (Gemini 2.5 Flash)")
    print("=" * 60)

    try:
        provider = GeminiProvider(
            cli_path="gemini",
            rate_limit_delay=False,  # Fast for testing
        )

        # Check if available first
        if not await provider.is_available():
            print("❌ Gemini CLI not available - run: gemini auth login")
            return False

        print("📤 Sending test prompt to Gemini 2.5 Flash...")
        prompt = "What is 2+2? Answer in one word only."

        result = await provider.generate(
            model="gemini-2.5-flash",
            prompt=prompt,
            max_tokens=10,
        )

        if result.error:
            print(f"❌ Generation failed: {result.error}")
            return False

        print("✅ Generation successful!")
        print(f"   Prompt: {prompt}")
        print(f"   Response: {result.content.strip()}")

        if result.usage:
            print(f"   Input tokens: {result.usage.input_tokens}")
            print(f"   Output tokens: {result.usage.output_tokens}")

        return True
    except Exception as e:
        print(f"❌ Generation test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_claude_provider():
    """Test Claude provider (requires API key)."""
    print("\n" + "=" * 60)
    print("TEST 4: Claude Provider (Requires API Key)")
    print("=" * 60)

    try:
        from providers.claude import ClaudeProvider

        api_key = os.environ.get("ANTHROPIC_API_KEY")

        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY not found in environment")
            print("   Set in .env file or export ANTHROPIC_API_KEY=...")
            return False

        provider = ClaudeProvider(api_key=api_key)

        print("✅ Claude provider created")
        print(f"   Provider name: {provider.name}")
        print(f"   Available models: {len(provider.available_models)}")

        # List models
        for model in provider.available_models:
            cost_str = (
                f"${model.cost_per_1k_input:.4f}/${model.cost_per_1k_output:.4f} per 1K"
            )
            print(f"   - {model.display_name}: {cost_str} ({model.tier.value})")

        print(f"   API key: {api_key[:20]}...{api_key[-10:]}")

        return True
    except Exception as e:
        print(f"❌ Claude provider test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🚀 Orchestrator Functionality Test")
    print("=" * 60)

    results = []

    # Test 1: Registry
    results.append(("Registry", await test_registry()))

    # Test 2: Gemini Provider
    results.append(("Gemini Provider", await test_gemini_provider()))

    # Test 3: Generation (only if Gemini available)
    if results[-1][1]:  # If Gemini provider test passed
        results.append(("Generation", await test_generation()))
    else:
        results.append(("Generation", None))  # Skipped

    # Test 4: Claude Provider
    results.append(("Claude Provider", await test_claude_provider()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for name, result in results:
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        print(f"{status} - {name}")

    passed = sum(1 for _, r in results if r is True)
    total = len([r for r in results if r is not None])

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed! Orchestrator is ready to use.")
        return 0
    elif passed > 0:
        print("\n⚠️  Some tests passed. Check failures above.")
        return 1
    else:
        print("\n❌ All tests failed. Check configuration.")
        return 2


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
