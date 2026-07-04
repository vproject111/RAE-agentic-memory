# RAE Benchmarking Suite - Quick Start Guide

Welcome to the RAE Benchmarking Suite! This guide will help you quickly evaluate the performance and quality of your RAE Memory system.

## 🎯 What is this?

The RAE Benchmarking Suite is a comprehensive evaluation framework that measures:

- **Search Quality**: MRR, Hit Rate, Precision, Recall
- **Performance**: Latency (avg, P95, P99), Throughput
- **System Behavior**: Multi-tenancy, GraphRAG, Reflection impact

## 📦 What's Included?

```
benchmarking/
├── sets/                    # Benchmark datasets (YAML)
│   ├── academic_lite.yaml          # Quick test (10 memories, 7 queries) - <10s
│   ├── academic_extended.yaml      # Medium test (50 memories, 20 queries) - ~30s
│   └── industrial_small.yaml       # Real-world test (100+ memories) - ~2min
│
├── scripts/                 # Execution scripts
│   ├── run_benchmark.py            # Main benchmark runner
│   └── compare_runs.py             # Compare two results
│
└── results/                 # Output directory (auto-created)
    ├── *.json                      # Machine-readable results
    └── *.md                        # Human-readable reports
```

## 🚀 Quick Start (3 minutes)

### 1. Prerequisites

Ensure you have:
- RAE database running (PostgreSQL)
- Python environment with dependencies installed
- API server running (optional, benchmarks can use direct DB access)

```bash
# Verify database is accessible
psql -h localhost -U rae_user -d rae_memory -c "SELECT 1"

# Ensure Python dependencies are installed
pip install -r requirements.txt
```

### 2. Run Your First Benchmark

```bash
# Run the lite benchmark (fastest, good for quick verification)
python benchmarking/scripts/run_benchmark.py --set academic_lite.yaml

# Expected output:
# 🚀 RAE Benchmark Runner
# ============================================================
# 📂 Loading benchmark: academic_lite.yaml
#    Name: academic_lite
#    Description: Lightweight academic benchmark for RAE quality testing
#    Memories: 10
#    Queries: 7
# ...
# ✅ Benchmark complete!
```

### 3. View Results

Results are saved in `benchmarking/results/`:

```bash
# View the latest report
cat benchmarking/results/academic_lite_*.md

# Or view JSON for programmatic access
cat benchmarking/results/academic_lite_*.json
```

## 📊 Understanding the Results

### Quality Metrics

| Metric | Description | Good Score | Excellent Score |
|--------|-------------|------------|-----------------|
| **MRR** (Mean Reciprocal Rank) | Average position of first relevant result | > 0.6 | > 0.8 |
| **Hit Rate @5** | % queries with relevant result in top 5 | > 0.7 | > 0.9 |
| **Precision @5** | Accuracy of top 5 results | > 0.5 | > 0.7 |
| **Recall @5** | Coverage of relevant results in top 5 | > 0.6 | > 0.8 |
| **Overall Quality** | Weighted combination of above | > 0.65 | > 0.85 |

### Performance Metrics

| Metric | Description | Good | Excellent |
|--------|-------------|------|-----------|
| **Avg Query Time** | Average search latency | < 100ms | < 50ms |
| **P95 Query Time** | 95th percentile latency | < 200ms | < 100ms |
| **P99 Query Time** | 99th percentile latency | < 300ms | < 150ms |
| **Avg Insert Time** | Average memory insertion time | < 200ms | < 100ms |

## 🔬 Running Different Benchmarks

### Academic Lite (Recommended for CI/CD)

**Purpose:** Quick sanity check
**Duration:** < 10 seconds
**Use Case:** PR validation, smoke tests

```bash
python benchmarking/scripts/run_benchmark.py --set academic_lite.yaml
```

### Academic Extended (Comprehensive Testing)

**Purpose:** Thorough quality evaluation
**Duration:** ~30 seconds
**Use Case:** Pre-release testing, regression detection

```bash
python benchmarking/scripts/run_benchmark.py --set academic_extended.yaml
```

### Industrial Small (Real-World Simulation)

**Purpose:** Production-like "dirty data" testing
**Duration:** ~2 minutes
**Use Case:** Performance testing, GraphRAG evaluation

```bash
python benchmarking/scripts/run_benchmark.py --set industrial_small.yaml
```

## 🔄 Comparing Benchmarks

Compare two runs to detect improvements or regressions:

```bash
# Run baseline
python benchmarking/scripts/run_benchmark.py --set academic_extended.yaml

# Make changes to your system...

# Run comparison
python benchmarking/scripts/run_benchmark.py --set academic_extended.yaml

# Compare results
python benchmarking/scripts/compare_runs.py \
    benchmarking/results/academic_extended_20241206_100000.json \
    benchmarking/results/academic_extended_20241206_103000.json \
    --output comparison_report.md
```

Expected output:
```
📊 BENCHMARK COMPARISON SUMMARY
============================================================
📈 Overall:
   Improvements: 8
   Regressions: 2
   Unchanged: 5

🎯 Quality Metrics:
   ✅ MRR: 0.6543 → 0.7234 (+10.56%)
   ✅ Overall Quality: 0.7012 → 0.7543 (+7.57%)

⚡ Performance Metrics:
   ✅ avg_query_time_ms: 145.32ms → 98.45ms (-32.25%)
```

## 🎨 Using Make Targets (Convenience)

Once integrated with Makefile (see setup below):

```bash
# Quick smoke test
make benchmark-lite

# Full academic evaluation
make benchmark-full

# Industrial/production test
make benchmark-industrial

# Run all benchmarks
make benchmark-all
```

## 🔧 Advanced Usage

### Custom Benchmark Sets

Create your own benchmark YAML file:

```yaml
name: "my_custom_benchmark"
description: "Testing specific use case"
version: "1.0"

memories:
  - id: "mem_1"
    text: "Your memory content here"
    tags: ["tag1", "tag2"]
    metadata:
      source: "My Source"
      importance: 0.8

queries:
  - query: "Your test query"
    expected_source_ids: ["mem_1"]
    difficulty: "medium"
```

Run it:
```bash
python benchmarking/scripts/run_benchmark.py --set my_custom_benchmark.yaml
```

### Environment Configuration

Configure via environment variables:

```bash
# Database connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=rae_memory
export POSTGRES_USER=rae_user
export POSTGRES_PASSWORD=rae_password

# Run benchmark
python benchmarking/scripts/run_benchmark.py --set academic_lite.yaml
```

### Telemetry Configuration (Enable/Disable OpenTelemetry)

RAE benchmarks respect the global OpenTelemetry configuration via environment variables:

**To run benchmarks WITH telemetry (default):**
```bash
export OTEL_TRACES_ENABLED=true
python benchmarking/scripts/run_benchmark_math.py --set academic_lite.yaml
```

**To run benchmarks WITHOUT telemetry (faster, cleaner output):**
```bash
export OTEL_TRACES_ENABLED=false
python benchmarking/scripts/run_benchmark_math.py --set academic_lite.yaml
```

**Or disable for a single run:**
```bash
OTEL_TRACES_ENABLED=false python benchmarking/scripts/run_benchmark_math.py --set academic_lite.yaml
```

**Why disable telemetry?**
- **Faster execution**: No trace collection overhead (~5-10% performance gain)
- **Cleaner output**: No OTLP export warnings or trace logs
- **CI/CD optimization**: Reduce noise in automated test runs
- **Local development**: Simplify debugging without trace data

**Why keep telemetry enabled?**
- **Performance analysis**: Identify bottlenecks in query/insert operations
- **Production simulation**: Test with the same observability stack as production
- **Debugging**: Trace context helps correlate benchmark operations with system behavior

See [Observability Documentation](../docs/reference/deployment/observability.md) for complete OpenTelemetry configuration options.

### API-Based Benchmarking (Future)

Currently, benchmarks use direct database access for maximum accuracy. API-based benchmarking coming soon:

```bash
# Future feature
python benchmarking/scripts/run_benchmark.py \
    --set academic_lite.yaml \
    --api-url http://localhost:8000 \
    --api-key your_api_key
```

## 📈 Interpreting Results

### Example Good Run

```markdown
## Quality Metrics
- MRR: 0.8234 ✅
- Hit Rate @5: 0.9143 ✅
- Overall Quality: 0.8543 ✅

## Performance Metrics
- Avg Query Time: 45.23ms ✅
- P95 Query Time: 78.45ms ✅
```

**Interpretation:** Excellent! Search quality is high and performance is fast.

### Example Problem Run

```markdown
## Quality Metrics
- MRR: 0.4521 ❌
- Hit Rate @5: 0.5714 ⚠️
- Overall Quality: 0.5123 ❌

## Performance Metrics
- Avg Query Time: 245.67ms ❌
- P95 Query Time: 456.23ms ❌
```

**Interpretation:** Issues detected. Check:
1. Embedding model quality
2. Database query optimization
3. Vector index configuration
4. Memory content quality

## 🐛 Troubleshooting

### Problem: "Database connection failed"

**Solution:**
```bash
# Verify database is running
docker ps | grep postgres

# Check connection
psql -h localhost -U rae_user -d rae_memory -c "SELECT 1"

# Verify environment variables
echo $POSTGRES_HOST $POSTGRES_PORT
```

### Problem: "No results returned for queries"

**Solution:**
- Check if memories were inserted successfully
- Verify embedding service is working
- Check vector store configuration
- Review relevance score threshold in config

### Problem: "Benchmark runs too slowly"

**Solution:**
- Use `academic_lite.yaml` for quick tests
- Check database indexes
- Monitor system resources (CPU, RAM)
- Consider reducing dataset size

## 🎓 Best Practices

### For Development

1. **Run lite benchmark frequently** during development
2. **Run extended benchmark** before commits/PRs
3. **Compare results** after changes to detect regressions
4. **Use CI/CD integration** for automatic validation

### For Research

1. **Use academic_extended** for paper results
2. **Document configuration** in your reports
3. **Run multiple times** and report average + stddev
4. **Compare against baselines** from literature

### For Production

1. **Run industrial_small** before deployments
2. **Track metrics over time** to detect drift
3. **Set SLO thresholds** based on benchmark results
4. **Monitor P95/P99** latency, not just averages

## 📚 Next Steps

1. ✅ Run your first benchmark with `academic_lite.yaml`
2. 📊 Review the results and understand the metrics
3. 🔄 Make changes and compare results
4. 🚀 Integrate benchmarks into your CI/CD pipeline
5. 📈 Track improvements over time

## 🤝 Contributing

Want to add more benchmark sets?

1. Create new YAML file in `benchmarking/sets/`
2. Follow the schema from existing files
3. Test with `run_benchmark.py`
4. Submit PR with description

## 📞 Support

- **Documentation:** See `BENCHMARK_REPORT_TEMPLATE.md` for report format
- **Issues:** Open GitHub issues for bugs or feature requests
- **Questions:** Check project README or discussions

---

**Ready to benchmark?** Start with:

```bash
python benchmarking/scripts/run_benchmark.py --set academic_lite.yaml
```

🎉 Happy benchmarking!
