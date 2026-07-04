#!/bin/bash
# RAE 30-Minute Fast Benchmark Session
# Skips industrial_large to avoid long runtime

set -e

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
SESSION_LOG="benchmarking/session_30min_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 RAE 30-Minute Fast Benchmark Session" | tee -a "$SESSION_LOG"
echo "Start time: $(date)" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

run_benchmark() {
    local benchmark=$1
    local iteration=$2
    local phase=$3

    echo "  [Phase $phase] $benchmark (iter $iteration)..." | tee -a "$SESSION_LOG"

    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set ${benchmark}.yaml \
        --output benchmarking/results/ 2>&1 | \
        grep -E "MRR:|Hit Rate @5:|Average query time:|Overall Quality" | \
        tee -a "$SESSION_LOG"

    echo "" | tee -a "$SESSION_LOG"
}

# Phase 1: Quick validation (5 min)
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "PHASE 1: Quick Validation" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"

PHASE1_START=$(date +%s)

run_benchmark "academic_lite" 1 1
run_benchmark "academic_extended" 1 1
run_benchmark "industrial_small" 1 1
run_benchmark "stress_memory_drift" 1 1

PHASE1_END=$(date +%s)
PHASE1_DURATION=$((PHASE1_END - PHASE1_START))
echo "✅ Phase 1: ${PHASE1_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

# Phase 2: Statistical validation - 10 iterations (25 min)
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "PHASE 2: Statistical Validation (10 iterations)" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"

PHASE2_START=$(date +%s)

for i in {2..10}; do
    echo "───────────────────────────────────────────────────────────" | tee -a "$SESSION_LOG"
    echo "Iteration $i/10" | tee -a "$SESSION_LOG"
    echo "───────────────────────────────────────────────────────────" | tee -a "$SESSION_LOG"

    run_benchmark "academic_lite" $i 2
    run_benchmark "academic_extended" $i 2
    run_benchmark "industrial_small" $i 2

    sleep 2
done

PHASE2_END=$(date +%s)
PHASE2_DURATION=$((PHASE2_END - PHASE2_START))
echo "✅ Phase 2: ${PHASE2_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"

# Session summary
SESSION_END=$(date +%s)
SESSION_DURATION=$((SESSION_END - SESSION_START))
SESSION_MINUTES=$((SESSION_DURATION / 60))

echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "SESSION COMPLETE!" | tee -a "$SESSION_LOG"
echo "═══════════════════════════════════════════════════════════" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "End time: $(date)" | tee -a "$SESSION_LOG"
echo "Total: ${SESSION_MINUTES} min (${SESSION_DURATION}s)" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "Phase 1 (1x all): ${PHASE1_DURATION}s" | tee -a "$SESSION_LOG"
echo "Phase 2 (10x small): ${PHASE2_DURATION}s" | tee -a "$SESSION_LOG"
echo "" | tee -a "$SESSION_LOG"
echo "Results: benchmarking/results/" | tee -a "$SESSION_LOG"
echo "Log: $SESSION_LOG" | tee -a "$SESSION_LOG"
