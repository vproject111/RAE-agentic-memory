import asyncio
import os

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI


async def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API Key not found!")
        return

    print(f"🔄 Testing OpenAI (Key: {api_key[:10]}...)...")
    try:
        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, say 'OpenAI OK'"}],
            max_tokens=10,
        )
        content = response.choices[0].message.content
        print(f"✅ OpenAI Success: {content}")
    except Exception as e:
        print(f"❌ OpenAI Failed: {e}")


async def test_anthropic():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Anthropic API Key not found!")
        return

    print(f"🔄 Testing Anthropic (Key: {api_key[:10]}...)...")
    try:
        client = AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=10,
            messages=[{"role": "user", "content": "Hello, say 'Anthropic OK'"}],
        )
        block = response.content[0]
        content = getattr(block, "text", str(block))
        print(f"✅ Anthropic Success: {content}")
    except Exception as e:
        print(f"❌ Anthropic Failed: {e}")


async def main():
    print("🚀 Starting LLM Connection Test...")
    await test_openai()
    await test_anthropic()


if __name__ == "__main__":
    asyncio.run(main())
