# Evaluation Framework

## Overview

The RAE Evaluation Framework provides comprehensive tools for benchmarking performance, measuring quality, and analyzing costs.

**Location**: `eval/`

## Framework Components

| Component | Purpose | Output |
|-----------|---------|--------|
| `benchmark_suite.py` | Performance benchmarks | Latency, throughput metrics |
| `quality_metrics.py` | RAG quality evaluation | Precision, recall, F1, NDCG |
| `cost_analysis.py` | Cost pattern analysis | Cost reports, optimization recommendations |
| `datasets/` | Test datasets | QA pairs, benchmark queries |

## Running Evaluations

### Performance Benchmarks

```bash
# Full benchmark suite
python eval/benchmark_suite.py \
  --config eval/configs/standard.yaml \
  --output results/benchmark_$(date +%Y%m%d).json

# Specific tests
python eval/benchmark_suite.py \
  --tests semantic_search,graph_traversal \
  --iterations 100
```

**Benchmark Tests**:

1. **Semantic Search**
   - Embedding generation speed
   - Vector search latency (p50, p95, p99)
   - Throughput (queries/second)

2. **GraphRAG**
   - Multi-hop query latency
   - Graph traversal performance
   - Community detection time

3. **Reflection Generation**
   - LLM call latency
   - End-to-end reflection time
   - Storage time

4. **Memory Storage**
   - Write latency
   - Batch insert performance
   - Index update time

### Quality Evaluation

```bash
# Evaluate RAG quality
python eval/quality_metrics.py \
  --test-set eval/datasets/qa_benchmark.json \
  --output results/quality_$(date +%Y%m%d).json
```

**Quality Metrics**:

- **Precision@K**: Relevance of top-K results
- **Recall@K**: Coverage of relevant results in top-K
- **F1 Score**: Harmonic mean of precision and recall
- **MRR**: Mean Reciprocal Rank of first relevant result
- **NDCG**: Normalized Discounted Cumulative Gain
- **Accuracy**: Exact match for factual queries

### Cost Analysis

```bash
# Analyze cost patterns
python eval/cost_analysis.py \
  --tenant-id tenant-123 \
  --start-date 2025-11-01 \
  --end-date 2025-12-01 \
  --output reports/cost_analysis.html
```

**Cost Insights**:
- Cost per operation type
- Most expensive LLM profiles
- Token usage patterns
- Optimization recommendations

## Test Datasets

### QA Benchmark Dataset

**Location**: `eval/datasets/qa_benchmark.json`

```json
{
  "questions": [
    {
      "id": "q1",
      "query": "How does the authentication system work?",
      "expected_answer": "The system uses JWT tokens...",
      "relevant_memory_ids": ["mem-123", "mem-456"],
      "category": "technical"
    }
  ]
}
```

### Synthetic Workload

Generate synthetic test data:

```bash
python eval/generate_synthetic_data.py \
  --size 10000 \
  --output eval/datasets/synthetic_10k.json
```

## Metrics Reference

### Performance Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **p50 latency** | Median response time | <100ms (search) |
| **p95 latency** | 95th percentile latency | <500ms (search) |
| **p99 latency** | 99th percentile latency | <1000ms (search) |
| **Throughput** | Requests per second | >100 req/s (search) |
| **Memory usage** | RAM per query | <500MB |

### Quality Metrics

| Metric | Formula | Ideal Value |
|--------|---------|-------------|
| **Precision@K** | relevant_in_k / k | 1.0 |
| **Recall@K** | relevant_in_k / total_relevant | 1.0 |
| **F1@K** | 2 × (P × R) / (P + R) | 1.0 |
| **MRR** | 1 / rank_first_relevant | 1.0 |
| **NDCG@K** | DCG@K / IDCG@K | 1.0 |

### Cost Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **Cost per query** | Average USD per search | <$0.001 |
| **Cost per memory** | Average USD per store | <$0.0005 |
| **Monthly cost** | Total monthly spend | <Budget |
| **Token efficiency** | Relevant tokens / total tokens | >0.8 |

## Continuous Evaluation

### CI/CD Integration

Add evaluation to CI pipeline:

```yaml
# .github/workflows/eval.yml
name: Run Evaluations

on:
  pull_request:
    branches: [main]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run benchmarks
        run: |
          python eval/benchmark_suite.py \
            --tests semantic_search \
            --output results/pr_benchmark.json
      - name: Compare to baseline
        run: |
          python eval/compare_results.py \
            --current results/pr_benchmark.json \
            --baseline results/main_baseline.json \
            --threshold 0.95  # Fail if >5% regression
```

### Regression Detection

Automatically detect performance regressions:

```python
# eval/compare_results.py
def compare_benchmarks(current, baseline, threshold=0.95):
    """
    Compare benchmark results and fail if regression detected.

    Args:
        current: Current benchmark results
        baseline: Baseline to compare against
        threshold: Acceptable ratio (0.95 = 5% regression allowed)

    Returns:
        True if acceptable, False if regression detected
    """
```

## Reporting

### Generate HTML Report

```bash
python eval/generate_report.py \
  --benchmark results/benchmark.json \
  --quality results/quality.json \
  --cost results/cost.json \
  --output reports/full_report.html
```

**Report Sections**:
1. Executive Summary
2. Performance Benchmarks (charts, tables)
3. Quality Metrics (precision/recall curves)
4. Cost Analysis (cost breakdown, trends)
5. Recommendations

### Export to CSV

```bash
# Export metrics for analysis
python eval/export_metrics.py \
  --input results/*.json \
  --output metrics.csv
```

## Best Practices

### 1. Baseline Establishment

Always establish baselines before optimization:

```bash
# Create baseline
python eval/benchmark_suite.py \
  --output baselines/v1.0_baseline.json

# After optimization, compare
python eval/compare_results.py \
  --current results/optimized.json \
  --baseline baselines/v1.0_baseline.json
```

### 2. Realistic Test Data

Use production-like data for accurate results:
- Real query patterns
- Actual memory distribution
- Production data volumes

### 3. Warm-up Runs

Always run warm-up iterations:

```python
# Skip first 10 queries for accurate timing
for i in range(iterations + 10):
    result = run_query(query)
    if i >= 10:  # Skip warm-up
        metrics.append(result.latency)
```

### 4. Multiple Runs

Run benchmarks multiple times for statistical significance:

```bash
# Run 5 times and average
for i in {1..5}; do
  python eval/benchmark_suite.py \
    --output results/run_$i.json
done

python eval/aggregate_runs.py \
  --input "results/run_*.json" \
  --output results/aggregated.json
```

## Related Documentation

- [Dev Tools and Scripts](./DEV_TOOLS_AND_SCRIPTS.md) - Related tools
- [Testing Status](../TESTING_STATUS.md) - Test coverage
- [Performance Tuning](./PERFORMANCE_TUNING.md) - Optimization guide
