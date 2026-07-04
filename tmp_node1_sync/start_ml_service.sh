#!/bin/bash
# start_ml_service.sh - Stable runner for RAE ML Service on Node1

PROJECT_ROOT="/home/operator/rae-node-agent"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

cd $PROJECT_ROOT

# Ensure PYTHONPATH includes the project root for proper module discovery
export PYTHONPATH=$PROJECT_ROOT

# Configure LiteLLM / Ollama
export OLLAMA_API_BASE="http://localhost:11434"
export ML_SERVICE_PORT=8001

echo "🚀 Starting RAE ML Service (API-First) on port $ML_SERVICE_PORT..."
exec $VENV_PYTHON apps/ml_service/main.py
