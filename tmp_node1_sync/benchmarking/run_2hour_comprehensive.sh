#!/bin/bash
# RAE Comprehensive 2-Hour Benchmark Session
# Runs maximum coverage of all available benchmarks in 120 minutes

set -e

# Activate virtual environment
source .venv/bin/activate

# Configuration
export POSTGRES_USER=rae
export POSTGRES_PASSWORD=rae_password
export POSTGRES_DB=rae
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export OTEL_TRACES_ENABLED=false  # Faster execution without telemetry

DURATION_SECONDS=7200  # 2 hours
START_TIME=$(date +%s)
SESSION_ID="comprehensive_$(date +%Y%m%d_%H%M%S)"
RESULTS_DIR="benchmarking/results/session_${SESSION_ID}"

mkdir -p "$RESULTS_DIR"

echo "=========================================="
echo "RAE 2-Hour Comprehensive Benchmark Session"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Start time: $(date)"
echo "Duration: 2 hours (7200 seconds)"
echo "Results directory: $RESULTS_DIR"
echo ""

# Available benchmarks with estimated times
declare -A BENCHMARKS=(
    ["academic_lite.yaml"]="4s"
    ["academic_extended.yaml"]="11s"
    ["industrial_small.yaml"]="9s"
    ["stress_memory_drift.yaml"]="6s"
    ["industrial_large.yaml"]="203s"
)

# Benchmark rotation strategy: fast benchmarks first, then scale tests
BENCHMARK_ROTATION=(
    "academic_lite.yaml"
    "academic_extended.yaml"
    "industrial_small.yaml"
    "stress_memory_drift.yaml"
    "industrial_large.yaml"
)

iteration=1
total_benchmarks_run=0
failed_benchmarks=0

echo "Phase 1: Initial validation (all benchmarks once)"
echo "=================================================="
echo ""

# Phase 1: Run each benchmark once for baseline
for benchmark in "${BENCHMARK_ROTATION[@]}"; do
    current_time=$(date +%s)
    elapsed=$((current_time - START_TIME))

    if [ $elapsed -ge $DURATION_SECONDS ]; then
        echo "Time limit reached. Stopping session."
        break
    fi

    remaining=$((DURATION_SECONDS - elapsed))
    echo "[$(date +%H:%M:%S)] Running: $benchmark (Elapsed: ${elapsed}s, Remaining: ${remaining}s)"

    # Run benchmark and capture output to temp file
    BENCHMARK_LOG="$RESULTS_DIR/benchmark_${benchmark%.yaml}_$(date +%Y%m%d_%H%M%S).log"
    if PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set "$benchmark" \
        --output "$RESULTS_DIR/" > "$BENCHMARK_LOG" 2>&1; then
        echo "✅ $benchmark completed successfully"
        total_benchmarks_run=$((total_benchmarks_run + 1))
    else
        echo "❌ $benchmark failed (see $BENCHMARK_LOG)"
        failed_benchmarks=$((failed_benchmarks + 1))
    fi

    echo ""
    sleep 2  # Brief cooldown
done

echo ""
echo "Phase 1 complete. Starting iterative testing..."
echo ""

# Phase 2: Iterative testing until time runs out
echo "Phase 2: Iterative testing (continuous until timeout)"
echo "======================================================"
echo ""

while true; do
    current_time=$(date +%s)
    elapsed=$((current_time - START_TIME))

    if [ $elapsed -ge $DURATION_SECONDS ]; then
        echo "Time limit reached. Stopping session."
        break
    fi

    ((iteration++))
    echo "=== Iteration $iteration ==="
    echo ""

    # Rotate through benchmarks, prioritizing faster ones
    for benchmark in "${BENCHMARK_ROTATION[@]}"; do
        current_time=$(date +%s)
        elapsed=$((current_time - START_TIME))

        if [ $elapsed -ge $DURATION_SECONDS ]; then
            echo "Time limit reached during iteration. Stopping."
            break 2
        fi

        remaining=$((DURATION_SECONDS - elapsed))

        # Skip industrial_large if less than 5 minutes remaining (it takes ~3.5 min)
        if [ "$benchmark" == "industrial_large.yaml" ] && [ $remaining -lt 300 ]; then
            echo "[$(date +%H:%M:%S)] Skipping $benchmark (insufficient time remaining: ${remaining}s)"
            continue
        fi

        echo "[$(date +%H:%M:%S)] Iteration $iteration: $benchmark (Remaining: ${remaining}s)"

        # Run benchmark and capture output to temp file
        BENCHMARK_LOG="$RESULTS_DIR/benchmark_${benchmark%.yaml}_iter${iteration}_$(date +%Y%m%d_%H%M%S).log"
        if PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
            --set "$benchmark" \
            --output "$RESULTS_DIR/" > "$BENCHMARK_LOG" 2>&1; then
            echo "✅ $benchmark completed"
            total_benchmarks_run=$((total_benchmarks_run + 1))
        else
            echo "❌ $benchmark failed (see $BENCHMARK_LOG)"
            failed_benchmarks=$((failed_benchmarks + 1))
        fi

        echo ""
    done

    sleep 3  # Cooldown between iterations
done

END_TIME=$(date +%s)
TOTAL_DURATION=$((END_TIME - START_TIME))

echo ""
echo "=========================================="
echo "Session Complete"
echo "=========================================="
echo "Session ID: $SESSION_ID"
echo "Total duration: ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60)) minutes)"
echo "Total benchmarks run: $total_benchmarks_run"
echo "Failed benchmarks: $failed_benchmarks"
echo "Success rate: $(awk "BEGIN {printf \"%.1f\", ($total_benchmarks_run - $failed_benchmarks) / $total_benchmarks_run * 100}")%"
echo ""
echo "Results saved to: $RESULTS_DIR"
echo ""

# Generate summary report
SUMMARY_FILE="$RESULTS_DIR/SESSION_SUMMARY.md"

cat > "$SUMMARY_FILE" << EOF
# RAE 2-Hour Comprehensive Benchmark Session Summary

**Session ID:** \`$SESSION_ID\`
**Start Time:** $(date -d "@$START_TIME" "+%Y-%m-%d %H:%M:%S")
**End Time:** $(date -d "@$END_TIME" "+%Y-%m-%d %H:%M:%S")
**Duration:** ${TOTAL_DURATION}s ($(($TOTAL_DURATION / 60)) minutes)

## Execution Statistics

- **Total benchmarks executed:** $total_benchmarks_run
- **Failed benchmarks:** $failed_benchmarks
- **Success rate:** $(awk "BEGIN {printf \"%.1f\", ($total_benchmarks_run - $failed_benchmarks) / $total_benchmarks_run * 100}")%
- **Iterations completed:** $((iteration - 1))

## Benchmark Coverage

| Benchmark | Est. Time | Runs Completed |
|-----------|-----------|----------------|
EOF

for benchmark in "${BENCHMARK_ROTATION[@]}"; do
    count=$(find "$RESULTS_DIR" -name "*${benchmark%.yaml}*.json" | wc -l)
    echo "| \`$benchmark\` | ${BENCHMARKS[$benchmark]} | $count |" >> "$SUMMARY_FILE"
done

cat >> "$SUMMARY_FILE" << EOF

## Result Files

All benchmark results are stored in JSON format:
\`\`\`
$RESULTS_DIR/*.json
\`\`\`

## Logs

Execution logs available:
\`\`\`
$RESULTS_DIR/*.log
\`\`\`

## Next Steps

1. Review JSON results for MRR, Hit Rate, Latency metrics
2. Compare iterations for stability and consistency
3. Analyze Math layer decision patterns
4. Check for memory drift indicators

---

**Generated:** $(date)
EOF

echo "Summary report generated: $SUMMARY_FILE"
echo ""
echo "To view results:"
echo "  cat $SUMMARY_FILE"
echo "  ls -lh $RESULTS_DIR/"
echo ""
