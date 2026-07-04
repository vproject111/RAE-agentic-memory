"""Entry point for gemini-mcp-server command."""

import asyncio
import sys

from .server import main as async_main


def main():
    """Entry point for gemini-mcp-server command."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nGemini MCP Server stopped by user.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
