"""Gemini MCP Server - enables Claude Code to use Gemini CLI as a tool.

This server integrates with RAE Memory to track all Claude<->Gemini interactions,
enabling the system to learn from multi-agent collaboration patterns.
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
import structlog
from mcp import types
from mcp.server import Server

logger = structlog.get_logger(__name__)

# Configuration from environment
RAE_API_URL = os.getenv("RAE_API_URL", "http://localhost:8000")
RAE_API_KEY = os.getenv("RAE_API_KEY", "dev-key")
RAE_PROJECT_ID = os.getenv("RAE_PROJECT_ID", "claude-code-project")
RAE_TENANT_ID = os.getenv("RAE_TENANT_ID", "claude-code")

# Initialize MCP server
server = Server("gemini-mcp")


class RAEMemoryClient:
    """Client for RAE Memory API - tracks Claude<->Gemini interactions."""

    def __init__(
        self,
        api_url: str = RAE_API_URL,
        api_key: str = RAE_API_KEY,
        tenant_id: str = RAE_TENANT_ID,
    ):
        self.api_url = api_url
        self.headers = {
            "X-API-Key": api_key,
            "X-Tenant-Id": tenant_id,
            "Content-Type": "application/json",
        }
        self.base_url = f"{api_url}/v1"

    async def store_memory(
        self,
        content: str,
        source: str,
        layer: str = "episodic",
        tags: Optional[List[str]] = None,
        project: str = RAE_PROJECT_ID,
    ) -> Dict[str, Any]:
        """Store a memory in RAE.

        Args:
            content: Memory content
            source: Source identifier
            layer: Memory layer (episodic, working, semantic, ltm)
            tags: Optional list of tags
            project: Project identifier

        Returns:
            Response dict with memory ID
        """
        payload = {
            "content": content,
            "source": source,
            "layer": layer,
            "tags": tags or [],
            "project": project,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/memory/store",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                result = response.json()

                logger.info(
                    "memory_stored",
                    memory_id=result.get("id"),
                    source=source,
                    layer=layer,
                )

                return result  # type: ignore[no-any-return]

        except httpx.HTTPStatusError as e:
            logger.error(
                "memory_store_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            # Don't fail the entire operation if RAE is down
            return {"error": str(e)}
        except Exception as e:
            logger.error("memory_store_error", error=str(e))
            return {"error": str(e)}


# Initialize RAE client (will be used to log all interactions)
rae_client = RAEMemoryClient()


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Gemini CLI tools.

    Returns:
        List of available tools that Claude Code can invoke
    """
    return [
        types.Tool(
            name="run_gemini",
            description=(
                "Run Gemini CLI to execute a task or answer a question. "
                "Use this tool when you want to delegate simple tasks to Gemini "
                "to save costs (Gemini is FREE within quota, Claude is paid). "
                "Good for: planning, simple questions, code review, documentation. "
                "Avoid for: complex reasoning, precise code generation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt to send to Gemini CLI",
                    },
                    "model": {
                        "type": "string",
                        "description": (
                            "Gemini model to use. Options: 'flash' (fast, cheap) "
                            "or 'pro' (smarter, slower). Default: flash"
                        ),
                        "enum": ["flash", "pro"],
                        "default": "flash",
                    },
                },
                "required": ["prompt"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any]
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool invocation from Claude Code.

    Args:
        name: Tool name to invoke
        arguments: Tool arguments

    Returns:
        Tool execution result
    """
    if name == "run_gemini":
        return await _run_gemini(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def _run_gemini(
    arguments: dict[str, Any],
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Execute Gemini CLI with given prompt.

    This function:
    1. Records Claude's request to RAE (episodic memory)
    2. Calls Gemini CLI
    3. Records Gemini's response to RAE
    4. Returns response to Claude

    This creates a full audit trail of Claude<->Gemini collaboration in RAE.

    Args:
        arguments: Tool arguments containing 'prompt' and optional 'model'

    Returns:
        Gemini CLI response as TextContent
    """
    prompt = arguments.get("prompt")
    model = arguments.get("model", "flash")

    if not prompt:
        return [
            types.TextContent(
                type="text",
                text="❌ Error: 'prompt' parameter is required",
            )
        ]

    logger.info("run_gemini", model=model, prompt_len=len(prompt))

    # Step 1: Record Claude's delegation to RAE
    await rae_client.store_memory(
        content=f"Claude delegated task to Gemini ({model}):\n\n{prompt[:500]}...",
        source="gemini-mcp:delegation",
        layer="episodic",
        tags=["claude", "gemini", "delegation", model],
        project=RAE_PROJECT_ID,
    )

    try:
        # Call Gemini CLI (using same approach as orchestrator)
        # No -m flag (causes 404), run from /tmp, parse JSON response
        proc = await asyncio.create_subprocess_exec(
            "gemini",
            prompt,  # Positional argument
            "--output-format",
            "json",
            cwd="/tmp",  # Avoid loading project context
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return [
                types.TextContent(
                    type="text",
                    text="❌ Gemini CLI timed out after 120 seconds",
                )
            ]

        if proc.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error("gemini_cli_error", error=error_msg)

            # Detect quota/rate limit errors
            if any(
                keyword in error_msg.lower()
                for keyword in [
                    "quota",
                    "rate limit",
                    "resource exhausted",
                    "429",
                    "too many requests",
                    "limit exceeded",
                ]
            ):
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            "⚠️  GEMINI QUOTA LIMIT EXCEEDED ⚠️\n\n"
                            "Limit dzienny wyczerpany na obecnym koncie.\n\n"
                            "Aby kontynuować:\n"
                            "1. Przełącz konto Gemini: .local/switch-gemini.sh [grzegorz|lili|marcel]\n"
                            "2. Uruchom ponownie zadanie\n\n"
                            f"Szczegóły błędu: {error_msg}"
                        ),
                    )
                ]

            # Detect authentication errors
            if any(
                keyword in error_msg.lower()
                for keyword in [
                    "unauthenticated",
                    "unauthorized",
                    "401",
                    "403",
                    "404",
                    "authentication",
                    "permission denied",
                    "not found",
                    "entity was not found",
                ]
            ):
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            "⚠️  GEMINI AUTHENTICATION ERROR ⚠️\n\n"
                            "Problem z autoryzacją konta Gemini.\n\n"
                            "Aby naprawić:\n"
                            "1. Uruchom: gemini /auth\n"
                            "2. Zaloguj się w przeglądarce\n"
                            "3. Uruchom ponownie zadanie\n\n"
                            f"Szczegóły błędu: {error_msg}"
                        ),
                    )
                ]

            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Gemini CLI failed: {error_msg}",
                )
            ]

        # Parse JSON response
        # Gemini CLI may output extra lines before JSON (like "Loaded cached credentials.")
        stdout_text = stdout.decode()

        # Find first { to start of JSON
        json_start = stdout_text.find("{")
        if json_start == -1:
            logger.warning("no_json_in_response", stdout=stdout_text[:200])
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ No JSON found in Gemini response: {stdout_text[:200]}",
                )
            ]

        try:
            response_data = json.loads(stdout_text[json_start:])
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), stdout=stdout_text[:200])
            return [
                types.TextContent(
                    type="text",
                    text=f"❌ Failed to parse Gemini response: {e}",
                )
            ]

        # Extract output (Gemini CLI format may vary)
        output = _extract_output(response_data)

        logger.info("gemini_success", output_len=len(output))

        # Step 3: Record Gemini's response to RAE
        await rae_client.store_memory(
            content=f"Gemini ({model}) completed task:\n\nOriginal request: {prompt[:200]}...\n\nResponse: {output[:500]}...",
            source="gemini-mcp:response",
            layer="episodic",
            tags=["claude", "gemini", "completion", model],
            project=RAE_PROJECT_ID,
        )

        return [
            types.TextContent(
                type="text",
                text=f"✅ Gemini ({model}) response:\n\n{output}",
            )
        ]

    except FileNotFoundError:
        logger.error("gemini_not_found")
        return [
            types.TextContent(
                type="text",
                text=(
                    "❌ Gemini CLI not found\n\n"
                    "Please install Gemini CLI:\n"
                    "npm install -g @google/generative-ai-cli\n\n"
                    "Or ensure 'gemini' is in your PATH"
                ),
            )
        ]
    except Exception as e:
        logger.exception("unexpected_error", error=str(e))
        return [
            types.TextContent(
                type="text",
                text=f"❌ Unexpected error: {e}",
            )
        ]


def _extract_output(response_data: dict) -> str:
    """Extract output text from Gemini CLI response.

    Args:
        response_data: Parsed JSON response

    Returns:
        Output text
    """
    # Gemini CLI may return different structures
    # Try common fields
    if "text" in response_data:
        return str(response_data["text"])
    elif "content" in response_data:
        return str(response_data["content"])
    elif "response" in response_data:
        return str(response_data["response"])
    else:
        return json.dumps(response_data, indent=2)


async def main():
    """Main entry point for MCP server."""
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )

    logger.info("gemini_mcp_server_starting", version="1.0.0")

    # Run MCP server
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    import logging

    asyncio.run(main())
