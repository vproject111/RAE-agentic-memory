#!/bin/bash
# RAE 2-Hour Comprehensive Benchmark Session
# Generated: 2025-12-07

set -e  # Exit on error

export POSTGRES_USER=rae
export POSTGRES_PASSWORD=rae_password
export POSTGRES_DB=rae
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432

# Ensure we are in the project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 1
source .venv/bin/activate

SESSION_START=$(date +%s)
SESSION_LOG="benchmarking/session_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 RAE 2-Hour Benchmark Session Starting..." | tee -a "$SESSION_LOG"
echo "Start time: $(date)" | tee -a "$SESSION_LOG"
echo "Log file: $SESSION_LOG" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

# Function to run benchmark
run_benchmark() {
    local benchmark=$1
    local iteration=$2
    local phase=$3

    echo "  [Phase $phase] Running $benchmark (iteration $iteration)..." | tee -a "$SESSION_LOG"

    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set ${benchmark}.yaml \
        --output benchmarking/results/ 2>&1 | \
        grep -E "MRR:|Hit Rate @5:|Average query time:|Overall Quality" | \
        tee -a "$SESSION_LOG"

    echo "" | tee -a "$SESSION_LOG"
}

# Phase 1: Quick Validation (20 min)
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "PHASE 1: Quick Validation (0:00 - 0:20)" | tee -a "$SESSION_LOG"
echo "Goal: Verify all benchmarks work correctly" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

PHASE1_START=$(date +%s)

run_benchmark "academic_lite" 1 1
run_benchmark "academic_extended" 1 1
run_benchmark "industrial_small" 1 1
run_benchmark "stress_memory_drift" 1 1

PHASE1_END=$(date +%s)
PHASE1_DURATION=$((PHASE1_END - PHASE1_START))
echo "✅ Phase 1 complete in ${PHASE1_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

# Phase 2: Statistical Validation (40 min)
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "PHASE 2: Statistical Validation (0:20 - 1:00)" | tee -a "$SESSION_LOG"
echo "Goal: Run 5 iterations for statistical confidence" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

PHASE2_START=$(date +%s)

for i in {2..5}; do
    echo "───────────────────────────────────────────────────────────" | tee -a "$SESSION_LOG"
    echo "Iteration $i/5" | tee -a "$SESSION_LOG"
    echo "───────────────────────────────────────────────────────────" | tee -a "$SESSION_LOG"

    run_benchmark "academic_lite" $i 2
    run_benchmark "academic_extended" $i 2
    run_benchmark "industrial_small" $i 2

    echo "Cooldown 5s..." | tee -a "$SESSION_LOG"
    sleep 5
done

PHASE2_END=$(date +%s)
PHASE2_DURATION=$((PHASE2_END - PHASE2_START))
echo "✅ Phase 2 complete in ${PHASE2_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

# Phase 3: Scale Testing (40 min)
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "PHASE 3: Scale Testing (1:00 - 1:40)" | tee -a "$SESSION_LOG"
echo "Goal: Test performance at scale with 1000 memories" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

PHASE3_START=$(date +%s)

for i in {1..3}; do
    echo "───────────────────────────────────────────────────────────" | tee -a "$SESSION_LOG"
    echo "Large-scale test $i/3" | tee -a "$SESSION_LOG"
    echo "───────────────────────────────────────────────────────────" | tee -a "$SESSION_LOG"

    run_benchmark "industrial_large" $i 3

    echo "Cooldown 10s..." | tee -a "$SESSION_LOG"
    sleep 10
done

PHASE3_END=$(date +%s)
PHASE3_DURATION=$((PHASE3_END - PHASE3_START))
echo "✅ Phase 3 complete in ${PHASE3_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

# Session Summary
SESSION_END=$(date +%s)
SESSION_DURATION=$((SESSION_END - SESSION_START))
SESSION_MINUTES=$((SESSION_DURATION / 60))

echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "SESSION COMPLETE!" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "End time: $(date)" | tee -a "$SESSION_LOG"
echo "Total duration: ${SESSION_MINUTES} minutes (${SESSION_DURATION}s)" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "Phase 1: ${PHASE1_DURATION}s" | tee -a "$SESSION_LOG"
echo "Phase 2: ${PHASE2_DURATION}s" | tee -a "$SESSION_LOG"
echo "Phase 3: ${PHASE3_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "Results saved to: benchmarking/results/" | tee -a "$SESSION_LOG"
echo "Session log: $SESSION_LOG" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "Next steps:" | tee -a "$SESSION_LOG"
echo "  1. Review results: ls -lh benchmarking/results/*$(date +%Y%m%d)*" | tee -a "$SESSION_LOG"
echo "  2. Analyze: python benchmarking/scripts/analyze_results.py" | tee -a "$SESSION_LOG"
echo "  3. Compare: git diff benchmarking/results/*.md" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
