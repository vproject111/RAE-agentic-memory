# 2-Hour Comprehensive Benchmark Session

## Overview

The `run_2hour_comprehensive.sh` script runs a complete 2-hour benchmark session covering all available benchmark sets with maximum coverage.

## What It Does

### Benchmark Coverage

| Benchmark | Memories | Queries | Est. Time | Type |
|-----------|----------|---------|-----------|------|
| `academic_lite.yaml` | 10 | 7 | ~4s | Quick validation |
| `academic_extended.yaml` | 45 | 20 | ~11s | Semantic noise testing |
| `industrial_small.yaml` | 35 | 20 | ~9s | Real-world edge cases |
| `stress_memory_drift.yaml` | 19 | 17 | ~6s | Stability under updates |
| `industrial_large.yaml` | 1000 | 100 | ~203s | Scale testing |

**Total single-pass time:** ~233 seconds (~4 minutes)

### Execution Strategy

1. **Phase 1: Initial Validation (0-20 min)**
   - Run each benchmark once for baseline
   - Verify all benchmarks work correctly
   - Establish baseline metrics

2. **Phase 2: Iterative Testing (20-120 min)**
   - Rotate through all benchmarks continuously
   - Prioritize faster benchmarks (more iterations)
   - Skip `industrial_large` when <5 minutes remaining
   - Maximize statistical confidence

## Usage

### Quick Start

```bash
# Run 2-hour comprehensive session
chmod +x benchmarking/run_2hour_comprehensive.sh
./benchmarking/run_2hour_comprehensive.sh
```

### Background Execution

```bash
# Run in background with logging
nohup bash benchmarking/run_2hour_comprehensive.sh > benchmarking/results/session.log 2>&1 &

# Monitor progress
tail -f benchmarking/results/session.log

# Check process
ps aux | grep benchmark
```

## Output Structure

### Results Directory

```
benchmarking/results/session_comprehensive_YYYYMMDD_HHMMSS/
├── academic_lite_YYYYMMDD_HHMMSS.json              # Main results
├── academic_lite_YYYYMMDD_HHMMSS.md                # Human-readable report
├── academic_lite_YYYYMMDD_HHMMSS_structure.json    # Math-1 metrics
├── academic_lite_YYYYMMDD_HHMMSS_dynamics.json     # Math-2 metrics
├── academic_lite_YYYYMMDD_HHMMSS_policy.json       # Math-3 metrics
├── academic_lite_YYYYMMDD_HHMMSS_decisions.json    # Controller decisions
├── academic_lite_YYYYMMDD_HHMMSS_snapshots.json    # Memory snapshots
├── [... repeated for each benchmark run ...]
└── SESSION_SUMMARY.md                              # Complete session summary
```

### Session Summary

The script automatically generates `SESSION_SUMMARY.md` containing:

- Session metadata (ID, start/end time, duration)
- Execution statistics (total runs, failures, success rate)
- Benchmark coverage table
- Result file locations
- Recommended next steps

## Metrics Collected

### Standard Metrics

- **MRR (Mean Reciprocal Rank)**: Ranking quality (0.0-1.0)
- **Hit Rate @5**: Percentage of queries with relevant results in top-5
- **Precision @K**: Precision at various K values (1, 3, 5, 10)
- **Recall @K**: Recall at various K values
- **NDCG @K**: Normalized Discounted Cumulative Gain
- **Query Latency**: Average, P95, P99 response times

### Mathematical Metrics

**Math-1: Structure Metrics**
- Graph Connectivity Score
- Semantic Coherence Score
- Graph Entropy
- Cluster Consistency

**Math-2: Dynamics Metrics**
- Memory Drift Index
- Structural Drift
- Retention Curve
- Reflection Gain Score

**Math-3: Policy Metrics**
- Cost-Quality Frontier
- Optimal Retrieval Ratio
- Reflection Policy Efficiency
- Level Selection Accuracy

## Configuration

### Environment Variables

```bash
export POSTGRES_USER=rae
export POSTGRES_PASSWORD=rae_password
export POSTGRES_DB=rae
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export OTEL_TRACES_ENABLED=false  # Disable telemetry for speed
```

### Timing

- **Session Duration**: 7200 seconds (2 hours)
- **Cooldown Between Benchmarks**: 2 seconds
- **Cooldown Between Iterations**: 3 seconds
- **industrial_large Skip Threshold**: 300 seconds (5 minutes)

## Monitoring Progress

### Real-time Log Monitoring

```bash
# Follow session log
tail -f benchmarking/results/session.log

# Count completed benchmarks
ls benchmarking/results/session_comprehensive_*/\*.json | wc -l

# Show latest results
ls -lht benchmarking/results/session_comprehensive_*/ | head -10
```

### Process Status

```bash
# Check if session is running
ps aux | grep run_2hour_comprehensive

# Check Python benchmark processes
ps aux | grep "run_benchmark_math.py"

# Monitor system resources
top -p $(pgrep -f run_2hour_comprehensive)
```

## Expected Results

### Phase 1 (Initial Validation)

- **academic_lite**: MRR > 0.8, Hit Rate > 80%
- **academic_extended**: MRR > 0.7, Hit Rate > 70%
- **industrial_small**: MRR > 0.6, Hit Rate > 60%
- **stress_memory_drift**: MRR > 0.5, Hit Rate > 50%
- **industrial_large**: MRR > 0.5, Hit Rate > 50%

### Phase 2 (Iterative Testing)

- **Statistical Confidence**: 5-30 iterations per benchmark
- **Consistency**: std deviation < 0.05 for stable metrics
- **Performance**: Query latency < 20ms avg

## After Session Completion

### 1. Review Summary

```bash
cat benchmarking/results/session_comprehensive_*/SESSION_SUMMARY.md
```

### 2. Analyze Results

```bash
# List all JSON results
ls benchmarking/results/session_comprehensive_*/*.json

# Count runs per benchmark
ls benchmarking/results/session_comprehensive_*/academic_lite*.json | wc -l
```

### 3. Save to Repository

```bash
# Add results directory
git add benchmarking/results/session_comprehensive_*/

# Commit with session summary
git commit -m "test: comprehensive 2-hour benchmark session

Session ID: comprehensive_YYYYMMDD_HHMMSS
Duration: 120 minutes
Total benchmarks: [count]
Success rate: [percentage]%

Results include:
- academic_lite: [n] runs
- academic_extended: [n] runs
- industrial_small: [n] runs
- stress_memory_drift: [n] runs
- industrial_large: [n] runs

All metrics: MRR, Hit Rate, Latency, Math-1/2/3"

# Push to repository
git push origin develop
```

## Troubleshooting

### Session Stops Prematurely

**Check logs:**
```bash
tail -100 benchmarking/results/session.log
```

**Common issues:**
- Database connection failure → Check PostgreSQL is running
- Out of memory → Reduce concurrent load or increase system RAM
- Python errors → Check virtual environment activation

### Low Success Rate

**Potential causes:**
- Qdrant service not running
- Database schema mismatch
- Missing dependencies

**Solutions:**
```bash
# Check services
docker ps

# Verify database connection
PGPASSWORD=rae_password psql -h localhost -U rae -d rae -c "SELECT 1"

# Check Qdrant
curl http://localhost:6333/health
```

### Performance Issues

**If benchmarks are too slow:**
```bash
# Reduce telemetry overhead
export OTEL_TRACES_ENABLED=false

# Check system resources
htop

# Monitor database connections
watch "ps aux | grep postgres | wc -l"
```

## Advanced Usage

### Custom Duration

Modify `DURATION_SECONDS` in script:
```bash
DURATION_SECONDS=3600  # 1 hour
DURATION_SECONDS=14400  # 4 hours
```

### Selective Benchmarks

Comment out benchmarks in `BENCHMARK_ROTATION` array:
```bash
BENCHMARK_ROTATION=(
    "academic_lite.yaml"
    # "academic_extended.yaml"  # Skip this one
    "industrial_small.yaml"
    # ...
)
```

### Result Aggregation

```bash
# Extract all MRR values
jq '.metrics.mrr' benchmarking/results/session_*/academic_lite*.json

# Calculate average MRR
jq -s 'map(.metrics.mrr) | add/length' \
    benchmarking/results/session_*/academic_lite*.json

# Extract Math-3 policy decisions
jq '.decisions[]' benchmarking/results/session_*/*_decisions.json
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Nightly Benchmarks

on:
  schedule:
    - cron: '0 2 * * *'  # Every night at 2 AM

jobs:
  comprehensive-benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup environment
        run: |
          docker compose up -d postgres qdrant redis
      - name: Run 2-hour benchmark session
        run: |
          ./benchmarking/run_2hour_comprehensive.sh
      - name: Upload results
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmarking/results/session_comprehensive_*/
```

## See Also

- [BENCHMARK_STARTER.md](BENCHMARK_STARTER.md) - Quick start guide
- [BENCHMARK_SESSION_PLAN.md](BENCHMARK_SESSION_PLAN.md) - Original session plan
- [BENCHMARKS_v1.md](../docs/project-design/active/BENCHMARKS_v1.md) - Metrics specification
- [Mathematical Layer Overview](../docs/project-design/active/MATH_LAYER_OVERVIEW.md) - Math layers documentation

---

**Generated:** 2025-12-07
**Maintained By:** RAE Development Team
