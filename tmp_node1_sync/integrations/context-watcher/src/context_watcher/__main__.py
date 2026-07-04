"""
RAE Context Watcher - Main Entry Point

Run the watcher daemon with:
    python -m context_watcher

Or after installation:
    context-watcher
"""

import sys

import uvicorn

from .api import app


def main():
    """Start the Context Watcher HTTP server."""
    try:
        print("Starting RAE Context Watcher on http://0.0.0.0:8001")
        print("Press Ctrl+C to stop")
        uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
    except KeyboardInterrupt:
        print("\nContext Watcher stopped by user.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
