#!/bin/bash
set -e

# scripts/dev_mode.sh
# Uruchamia pełne środowisko deweloperskie RAE (Infra + API + Reranker + MCP)

echo "🚀 Starting RAE Development Environment..."

# 1. Start Infrastructure (Docker)
echo "🐳 Starting Infrastructure (Postgres, Redis, Qdrant)..."
docker compose up -d postgres redis qdrant otel-collector jaeger

# 2. Check/Start MCP Server
if ! pgrep -f "rae-mcp-server" > /dev/null; then
    # Aktywujemy venv, a następnie uruchamiamy rae-mcp-server
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        nohup rae-mcp-server > rae-mcp.log 2>&1 &
        MCP_PID=$!
        echo "✅ MCP Server started (PID: $MCP_PID). Logs: rae-mcp.log"
    else
        echo "⚠️  Virtual environment not found at .venv/bin/activate. Attempting to start MCP server globally. Ensure it's in PATH."
        nohup rae-mcp-server > rae-mcp.log 2>&1 &
        MCP_PID=$!
        echo "✅ MCP Server started (PID: $MCP_PID). Logs: rae-mcp.log"
    fi
else
    echo "✅ MCP Server already running"
fi

# 3. Start Services with Hot Reload
echo "🔥 Starting RAE API & Reranker (Hot Reload)..."
echo "   - API: http://localhost:8000"
echo "   - Reranker: http://localhost:8001"
echo "   - Press Ctrl+C to stop all."

# Trap Ctrl+C to kill child processes
trap 'kill $(jobs -p); echo "🛑 Stopping services..."; exit' INT TERM EXIT

# Aktywuj venv jeśli nieaktywny
if [ -z "$VIRTUAL_ENV" ] && [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Uruchom Memory API
uvicorn apps.memory_api.main:app --reload --host 0.0.0.0 --port 8000 &

# Uruchom Reranker Service (z nową ścieżką)
# Zmieniliśmy nazwę katalogu na reranker_service, więc import to apps.reranker_service.main
uvicorn apps.reranker_service.main:app --reload --host 0.0.0.0 --port 8001 &

wait
