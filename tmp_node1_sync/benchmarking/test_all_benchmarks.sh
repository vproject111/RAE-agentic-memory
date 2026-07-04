#!/bin/bash
# Quick test of all benchmarks to verify they work in sequence
set -e

source .venv/bin/activate

export POSTGRES_USER=rae
export POSTGRES_PASSWORD=rae_password
export POSTGRES_DB=rae
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export OTEL_TRACES_ENABLED=false

SESSION_ID="test_$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="benchmarking/results/session_${SESSION_ID}"
mkdir -p "$RESULTS_DIR"

BENCHMARKS=(
    "academic_lite.yaml"
    "academic_extended.yaml"
    "industrial_small.yaml"
    "stress_memory_drift.yaml"
    "industrial_large.yaml"
)

total_run=0
total_failed=0

echo "=========================================="
echo "Testing All Benchmarks in Sequence"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Start time: $(date)"
echo ""

for benchmark in "${BENCHMARKS[@]}"; do
    echo "----------------------------------------"
    echo "Running: $benchmark"
    echo "----------------------------------------"

    BENCHMARK_LOG="$RESULTS_DIR/benchmark_${benchmark%.yaml}.log"

    if PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set "$benchmark" \
        --output "$RESULTS_DIR/" > "$BENCHMARK_LOG" 2>&1; then
        echo "✅ $benchmark completed successfully"
        total_run=$((total_run + 1))
    else
        echo "❌ $benchmark failed (see $BENCHMARK_LOG)"
        total_failed=$((total_failed + 1))
        # Don't exit on error, continue with remaining benchmarks
    fi

    echo ""
    sleep 1
done

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo "Total run: $total_run/${#BENCHMARKS[@]}"
echo "Failed: $total_failed"
echo ""
echo "Results: $RESULTS_DIR"
echo "Session log available for each benchmark"
