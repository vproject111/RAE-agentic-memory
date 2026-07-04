# RAE Benchmark Session Plan - 2 Hours

**Date:** 2025-12-07
**Duration:** 120 minutes
**Goal:** Comprehensive quality and performance validation of RAE memory system

---

## Available Benchmarks Summary

| Benchmark | Memories | Queries | Est. Time | Type |
|-----------|----------|---------|-----------|------|
| academic_lite | 10 | 7 | ~4s | Quick validation |
| academic_extended | 45 | 20 | ~11s | Semantic noise testing |
| industrial_small | 35 | 20 | ~9s | Real-world edge cases |
| stress_memory_drift | 19 | 17 | ~6s | Stability under updates |
| industrial_large | 1000 | 100 | ~203s | Scale testing |

**Total single-pass time:** ~3.9 minutes (233 seconds)

---

## Recommended 2-Hour Session Plan

### Phase 1: Quick Validation (0:00 - 0:20, 20 min)

**Goal:** Verify all benchmarks work correctly after the Qdrant cleanup fix

Run each benchmark once to establish baseline:

```bash
# 1. Academic Lite (4s) - Already verified ✅
export POSTGRES_USER=rae POSTGRES_PASSWORD=rae_password POSTGRES_DB=rae
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py --set academic_lite.yaml --output benchmarking/results/

# 2. Academic Extended (11s)
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py --set academic_extended.yaml --output benchmarking/results/

# 3. Industrial Small (9s)
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py --set industrial_small.yaml --output benchmarking/results/

# 4. Stress Memory Drift (6s)
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py --set stress_memory_drift.yaml --output benchmarking/results/
```

**Expected Metrics:**
- MRR: > 0.8 for academic, > 0.6 for industrial
- Hit Rate @5: > 80%
- Query latency: < 15ms avg

---

### Phase 2: Statistical Validation (0:20 - 1:00, 40 min)

**Goal:** Run each benchmark 5x to get statistical confidence

Run 5 iterations of fast benchmarks:

```bash
#!/bin/bash
export POSTGRES_USER=rae POSTGRES_PASSWORD=rae_password POSTGRES_DB=rae

for i in {1..5}; do
    echo "=== Iteration $i/5 ==="

    echo "Running academic_lite..."
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set academic_lite.yaml \
        --output benchmarking/results/

    echo "Running academic_extended..."
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set academic_extended.yaml \
        --output benchmarking/results/

    echo "Running industrial_small..."
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set industrial_small.yaml \
        --output benchmarking/results/

    sleep 5  # Cool down between iterations
done
```

**Metrics to Collect:**
- Mean MRR with std deviation
- P95/P99 latency consistency
- Math layer decision patterns
- Memory drift indicators

---

### Phase 3: Scale Testing (1:00 - 1:40, 40 min)

**Goal:** Test performance at scale with industrial_large

```bash
# Run industrial_large 3 times (3 × ~203s = ~10 minutes)
export POSTGRES_USER=rae POSTGRES_PASSWORD=rae_password POSTGRES_DB=rae

for i in {1..3}; do
    echo "=== Large-scale test $i/3 ==="

    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set industrial_large.yaml \
        --output benchmarking/results/

    echo "Completed iteration $i"
    sleep 10
done
```

**Critical Metrics:**
- Latency degradation with 1000 memories
- Memory usage patterns
- Qdrant query performance at scale
- Graph connectivity metrics
- Math layer optimal retrieval ratio

---

### Phase 4: Analysis & Report (1:40 - 2:00, 20 min)

**Goal:** Aggregate results and generate insights

```bash
# Aggregate results
PYTHONPATH=. python << 'EOF'
import json
from pathlib import Path
from collections import defaultdict
import statistics

results_dir = Path("benchmarking/results")
benchmarks = defaultdict(list)

# Collect all results from today
for result_file in results_dir.glob("*_20251207_*.json"):
    with open(result_file) as f:
        data = json.load(f)
        benchmark_name = data['benchmark']['name']
        benchmarks[benchmark_name].append(data)

# Generate summary
print("=" * 80)
print("RAE BENCHMARK SESSION SUMMARY")
print("=" * 80)

for name, runs in benchmarks.items():
    if not runs:
        continue

    mrr_values = [r['metrics']['mrr'] for r in runs]
    hit_rate_5 = [r['metrics']['hit_rate']['@5'] for r in runs]
    avg_query_ms = [r['metrics']['performance']['avg_query_time_ms'] for r in runs]

    print(f"\n{name.upper()}:")
    print(f"  Runs: {len(runs)}")
    print(f"  MRR: {statistics.mean(mrr_values):.3f} ± {statistics.stdev(mrr_values) if len(mrr_values) > 1 else 0:.3f}")
    print(f"  Hit@5: {statistics.mean(hit_rate_5):.1%}")
    print(f"  Latency: {statistics.mean(avg_query_ms):.2f}ms (p95: {max(avg_query_ms):.2f}ms)")

print("=" * 80)
EOF
```

---

## Success Criteria

### Quality Metrics
- ✅ **MRR > 0.9** on academic benchmarks
- ✅ **MRR > 0.7** on industrial benchmarks
- ✅ **Hit Rate @5 > 85%** across all benchmarks
- ✅ **Std deviation < 0.05** across 5 runs (consistency)

### Performance Metrics
- ✅ **Query latency < 15ms** avg for small datasets (< 50 memories)
- ✅ **Query latency < 50ms** avg for large datasets (1000 memories)
- ✅ **P99 latency < 100ms** for all benchmarks
- ✅ **No memory leaks** (stable RSS over iterations)

### Math Layer Validation
- ✅ **Deterministic heuristic** (L1) selected for > 90% of queries
- ✅ **Optimal retrieval ratio > 0.8** (correct level selection)
- ✅ **Graph connectivity score > 0.5** where applicable
- ✅ **Memory drift index < 0.1** (stable semantics)

---

## Alternative: Fast 30-Minute Session

If 2 hours is too long, here's a compressed plan:

```bash
#!/bin/bash
export POSTGRES_USER=rae POSTGRES_PASSWORD=rae_password POSTGRES_DB=rae

# Run each benchmark once (0-5 min)
for benchmark in academic_lite academic_extended industrial_small stress_memory_drift; do
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set ${benchmark}.yaml \
        --output benchmarking/results/
done

# Run academic_lite 10 times for statistical validation (5-10 min)
for i in {1..10}; do
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set academic_lite.yaml \
        --output benchmarking/results/
done

# Run industrial_large once (10-13 min)
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
    --set industrial_large.yaml \
    --output benchmarking/results/

# Analyze (13-15 min)
python benchmarking/scripts/analyze_results.py
```

---

## Czy to ma sens?

### ✅ **TAK - Bardzo ma sens!**

**Powody:**

1. **Weryfikacja poprawki** - Właśnie naprawiliśmy krytyczny bug w cleanup. Musimy sprawdzić czy wszystkie benchmarki działają.

2. **Baseline dla przyszłości** - Przed wdrożeniem nowych feature (Multi-Armed Bandits w produkcji) potrzebujemy solidnego baseline.

3. **Wykrycie regresji** - 5 iteracji każdego benchmarku pokaże czy są problemy ze stabilnością.

4. **Walidacja skali** - industrial_large (1000 memories) pokaże czy system skaluje się dobrze.

5. **Dokumentacja jakości** - Wyniki możemy załączyć do release notes v0.4.0.

6. **CI/CD benchmark** - Możemy użyć tych wyników do konfiguracji automated benchmark threshold w CI.

### Rekomendacja:

**Uruchom pełną 2-godzinną sesję**, ponieważ:
- Dopiero co naprawiliśmy poważny bug
- Nie masz jeszcze comprehensive baseline
- To jednorazowy koszt, który da Ci confidence w systemie
- Możesz zostawić to na noc/background

---

## Quick Start Command

```bash
#!/bin/bash
# Save this as: benchmarking/run_full_session.sh

export POSTGRES_USER=rae POSTGRES_PASSWORD=rae_password POSTGRES_DB=rae
# Ensure you are in the project root
# cd /path/to/RAE-agentic-memory

echo "🚀 RAE 2-Hour Benchmark Session Starting..."
echo "Start time: $(date)"

# Phase 1: Quick validation
echo -e "\n=== PHASE 1: Quick Validation (20 min) ==="
for benchmark in academic_extended industrial_small stress_memory_drift; do
    echo "Running $benchmark..."
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set ${benchmark}.yaml \
        --output benchmarking/results/ 2>&1 | tail -20
done

# Phase 2: Statistical validation
echo -e "\n=== PHASE 2: Statistical Validation (40 min) ==="
for i in {1..5}; do
    echo -e "\n--- Iteration $i/5 ---"
    for benchmark in academic_lite academic_extended industrial_small; do
        echo "  $benchmark run $i..."
        PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
            --set ${benchmark}.yaml \
            --output benchmarking/results/ 2>&1 | grep -E "MRR:|Hit Rate|Average query"
    done
    sleep 5
done

# Phase 3: Scale testing
echo -e "\n=== PHASE 3: Scale Testing (40 min) ==="
for i in {1..3}; do
    echo -e "\n--- Large-scale run $i/3 ---"
    PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
        --set industrial_large.yaml \
        --output benchmarking/results/ 2>&1 | tail -30
    sleep 10
done

echo -e "\n✅ Benchmark session complete!"
echo "End time: $(date)"
echo "Results saved to: benchmarking/results/"
echo "Run analysis: python benchmarking/scripts/analyze_results.py"
```

**To run:**
```bash
chmod +x benchmarking/run_full_session.sh
./benchmarking/run_full_session.sh | tee benchmarking_session_$(date +%Y%m%d_%H%M%S).log
```
