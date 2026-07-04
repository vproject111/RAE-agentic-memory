#!/bin/bash
# run_research_mode.sh
# Starts RAE in Research Mode with full Telemetry (OTEL + Jaeger)

echo "🔬 Starting RAE in Research Mode (Full Telemetry)..."

# Set environment variables for Research Mode
export RAE_PROFILE=research
export OTEL_TRACES_ENABLED=true
export RAE_TELEMETRY_MODE=external

# Start infrastructure with telemetry overlay
docker-compose \
    -f docker-compose.yml \
    -f docker-compose.telemetry.yml \
    up -d --build

echo "✅ Research Mode Active!"
echo "📊 Jaeger UI: http://localhost:16686"
echo "📈 Prometheus (via OTel): http://localhost:8888/metrics"
echo "🧠 RAE API: http://localhost:8000"
