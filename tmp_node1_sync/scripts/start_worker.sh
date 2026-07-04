#!/bin/bash
# Script to start Celery worker and beat locally (outside of Docker)
# Usage: ./scripts/start_worker.sh [worker|beat|all]

MODE=${1:-all}

# Ensure we are in the root directory
cd "$(dirname "$0")/.."

# Check if redis is running
if ! pgrep redis-server > /dev/null; then
    echo "⚠️  Redis does not seem to be running. Workers need Redis."
    echo "    Run 'docker compose up -d redis' or start a local redis-server."
fi

# Set python path
export PYTHONPATH=$PYTHONPATH:.

if [ "$MODE" = "worker" ] || [ "$MODE" = "all" ]; then
    echo "🚀 Starting Celery Worker..."
    celery -A apps.memory_api.celery_app worker --loglevel=info &
    WORKER_PID=$!
fi

if [ "$MODE" = "beat" ] || [ "$MODE" = "all" ]; then
    echo "⏰ Starting Celery Beat..."
    celery -A apps.memory_api.celery_app beat --loglevel=info &
    BEAT_PID=$!
fi

# Function to kill processes on exit
cleanup() {
    echo "Shutting down..."
    [ -n "$WORKER_PID" ] && kill $WORKER_PID
    [ -n "$BEAT_PID" ] && kill $BEAT_PID
}

trap cleanup SIGINT SIGTERM

echo "Press Ctrl+C to stop."
wait
