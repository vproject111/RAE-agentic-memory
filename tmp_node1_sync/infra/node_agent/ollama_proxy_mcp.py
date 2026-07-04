import os

import httpx
from mcp.server.fastmcp import FastMCP

# Configuration
# Default to Piotrek's IP if not set
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://172.30.15.11:11434")
NODE_NAME = os.getenv("NODE_NAME", "Node3 (Piotrek)")

mcp = FastMCP(NODE_NAME)


@mcp.tool()
async def list_models() -> str:
    """List available models on the remote Ollama instance."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
            if resp.status_code != 200:
                return f"Error: HTTP {resp.status_code}"

            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return f"Available models on {OLLAMA_URL}:\n" + "\n".join(models)
        except Exception as e:
            return f"Error connecting to Ollama at {OLLAMA_URL}: {e}"


@mcp.tool()
async def chat(model: str, prompt: str) -> str:
    """Generate a chat completion using the remote model."""
    async with httpx.AsyncClient() as client:
        try:
            payload = {"model": model, "prompt": prompt, "stream": False}
            resp = await client.post(
                f"{OLLAMA_URL}/api/generate", json=payload, timeout=300.0
            )
            if resp.status_code != 200:
                return f"Error: HTTP {resp.status_code} - {resp.text}"

            return resp.json().get("response", "No response content")
        except Exception as e:
            return f"Error generating: {e}"


if __name__ == "__main__":
    mcp.run()
