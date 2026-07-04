# RAE Benchmarking Suite

This directory contains the code and logic for performance and quality benchmarks.

## 📊 Benchmark Results & Artifacts
To keep this repository lightweight, all heavy artifacts (PNG plots, large JSON reports) are stored in a dedicated repository:
👉 **[RAE-benchmarks](https://github.com/vproject111/RAE-benchmarks)**

---

## Structure

> **Comprehensive evaluation framework for RAE Memory System**
> *11 benchmarks | 1,100+ test memories | 10,000+ cycle temporal testing | Full telemetry support*

[![Standard Benchmarks](https://img.shields.io/badge/standard_benchmarks-5-blue.svg)](#standard-benchmarks-v1)
[![Research Benchmarks](https://img.shields.io/badge/research_9/5-6-purple.svg)](#research-benchmarks-95)
[![Total Coverage](https://img.shields.io/badge/total_memories-1109-green.svg)](#benchmark-coverage)
[![Temporal Testing](https://img.shields.io/badge/temporal_cycles-10000+-orange.svg)](#temporal-benchmarks)

---

## 🎯 Quick Navigation

**New to benchmarking?** → [Quick Start Guide](#-quick-start-3-minutes)
**Need to choose a benchmark?** → [Decision Tree](#-which-benchmark-should-i-use)
**Want to compare features?** → [Comparison Matrix](#-benchmark-comparison-matrix)
**Looking for documentation?** → [Documentation Links](#-documentation-index)
**Need telemetry info?** → [Telemetry Guide](#-telemetry-configuration)

---

## 📋 Overview

RAE provides **two complementary benchmark suites**:

### 1. **Standard Benchmarks (v1)** - Production Quality Testing
5 benchmark sets testing real-world scenarios with standard metrics (MRR, Hit Rate, Latency)

### 2. **Research Benchmarks (9/5)** - Advanced Research Evaluation
6 specialized benchmarks for academic research and deep system analysis

```
Total System Coverage:
├── 11 different benchmarks
├── 1,109+ test memories
├── 164+ standard queries
├── 10,000+ temporal cycles
├── Pareto frontier analysis
└── Full OpenTelemetry integration
```

---

## 🚀 Quick Start (3 Minutes)

### Prerequisites
```bash
# Ensure database is running
docker compose up -d postgres qdrant

# Activate environment
source .venv/bin/activate
```

### Run Your First Benchmark
```bash
# Quick test (10 seconds) - perfect for CI/CD
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
    --set academic_lite.yaml \
    --output benchmarking/results/

# View results
cat benchmarking/results/academic_lite_*.md
```

### Run All Standard Benchmarks
```bash
# Test all 5 standard benchmarks (2-4 minutes)
./benchmarking/test_all_benchmarks.sh

# Results in: benchmarking/results/session_test_*/
```

### Run 2-Hour Comprehensive Session
```bash
# Maximum coverage - runs continuously for 2 hours
./benchmarking/run_2hour_comprehensive.sh

# Or in background:
nohup ./benchmarking/run_2hour_comprehensive.sh > session.log 2>&1 &
```

---

## 🌳 Which Benchmark Should I Use?

```
START: What do you need?
│
├─ Quick smoke test (CI/CD)? ────────────────────→ academic_lite (10s)
│
├─ Comprehensive quality check? ─────────────────→ academic_extended (30s)
│
├─ Real-world production simulation? ────────────→ industrial_small (2min)
│
├─ Test memory stability over time? ─────────────→ stress_memory_drift (10s)
│                                                  OR LECT (9/5) (5min)
│
├─ Large-scale stress testing? ──────────────────→ industrial_large (4min)
│
├─ Multi-layer memory isolation? ────────────────→ MMIT (9/5) (3min)
│
├─ Graph reasoning capabilities? ────────────────→ GRDT (9/5) (2min)
│
├─ Insight robustness testing? ──────────────────→ RST (9/5) (2min)
│
├─ Policy learning evaluation? ──────────────────→ MPEB (9/5) (3min)
│
└─ Cost-quality-latency analysis? ───────────────→ ORB (9/5) (2min)
```

---

## 📊 Benchmark Comparison Matrix

### Standard Benchmarks (v1)

| Benchmark | Memories | Queries | Runtime | Purpose | Best For |
|-----------|----------|---------|---------|---------|----------|
| **[academic_lite](./sets/academic_lite.yaml)** | 10 | 7 | <10s | Quick validation | CI/CD, smoke tests |
| **[academic_extended](./sets/academic_extended.yaml)** | 45 | 20 | ~30s | Comprehensive quality | Pre-release testing |
| **[industrial_small](./sets/industrial_small.yaml)** | 35 | 20 | ~2min | Real-world messy data | Production readiness |
| **[stress_memory_drift](./sets/stress_memory_drift.yaml)** | 19 | 17 | ~10s | Memory stability | Drift detection |
| **[industrial_large](./sets/industrial_large.yaml)** | 1,000 | 100 | ~4min | **Calibrated retrieval** | Piotrek's SOTA baseline |
| **[industrial_extreme](./sets/industrial_extreme.yaml)** | 10,000 | 200 | ~15min | Enterprise stress | Scale limits |
| **[industrial_ultra](./sets/industrial_ultra.yaml)** | 100,000 | 500 | ~2h | Mega-scale research | GPU Cluster Node1/Node2 |

**Total Standard:** 111,109+ memories | 864+ queries

### Research Benchmarks (9/5)

| Benchmark | Full Name | Runtime | Key Metrics | Purpose | What it verifies |
|-----------|-----------|---------|-------------|---------|------------------|
| **[LECT](./nine_five_benchmarks/README.md#1-lect---long-term-episodic-consistency-test)** | Long-term Episodic Consistency | ~5min | `consistency_score` | Temporal Testing | Verifies if events stored at different times remain logically consistent. |
| **[MMIT](./nine_five_benchmarks/README.md#2-mmit---multi-layer-memory-interference-test)** | Multi-Layer Memory Interference | ~3min | `interference_score` | Isolation | Checks if short-term (STM) memories bleed into long-term (LTM) without processing. |
| **[GRDT](./nine_five_benchmarks/README.md#3-grdt---graph-reasoning-depth-test)** | Graph Reasoning Depth | ~2min | `max_reasoning_depth` | Knowledge Graph | Tests how many "hops" the system can navigate in the graph to find an answer. |
| **[RST](./nine_five_benchmarks/README.md#4-rst---reflective-stability-test)** | Reflective Stability | ~2min | `stability_score` | Meta-cognition | Checks if generated reflections remain stable when new, slightly conflicting data arrives. |
| **[MPEB](./nine_five_benchmarks/README.md#5-mpeb---math-3-policy-evolution-benchmark)** | Math-3 Policy Evolution | ~3min | `convergence_rate` | ML Policy | Evaluates how fast the memory management policy learns to optimize storage. |
| **[ORB](./nine_five_benchmarks/README.md#6-orb---opentelemetry-research-benchmark)** | OpenTelemetry Research | ~2min | `pareto_frontier` | System Optimization | Maps the optimal balance between token cost, query latency, and answer quality. |

### 🧪 Experiments & Specialized Tests

Beyond standard benchmarks, RAE includes scripts for deep system analysis and component validation:

**Experimental Research (`benchmarking/experiments/`)**
- **Drift Dynamics** (`exp_drift_dynamics.py`): Analyzes how memory context shifts over time.
- **Reflection Gain** (`exp_reflection_gain.py`): Measures the qualitative improvement from reflection steps.
- **Structural Stability** (`exp_structural_stability.py`): Tests the resilience of the memory graph structure.

**System Component Tests (`benchmarking/tests/`)**
- **Bandit Algorithm** (`test_bandit.py`): Validates Multi-Armed Bandit decision logic.
- **Math Controller** (`test_math_controller.py`): Tests profile switching (Research vs Cheap) and heuristics.
- **Policy V2** (`test_policy_v2.py`): Verifies memory management policies.

---

## 📚 Documentation Index

### Getting Started
- **[BENCHMARK_STARTER.md](./BENCHMARK_STARTER.md)** - Complete quick start guide with examples
- **[test_all_benchmarks.sh](./test_all_benchmarks.sh)** - One-command testing script

### Standard Benchmarks (v1)
- **[Benchmark Sets](./sets/)** - YAML configuration files
  - [academic_lite.yaml](./sets/academic_lite.yaml)
  - [academic_extended.yaml](./sets/academic_extended.yaml)
  - [industrial_small.yaml](./sets/industrial_small.yaml)
  - [stress_memory_drift.yaml](./sets/stress_memory_drift.yaml)
  - [industrial_large.yaml](./sets/industrial_large.yaml)
- **[Math Metrics Documentation](./math_metrics/README.md)** - Math-1/2/3 layer explanation
- **[METRICS_MAPPING.md](./METRICS_MAPPING.md)** - Metric definitions and aliases

### Research Benchmarks (9/5)
- **[9/5 Suite Overview](./nine_five_benchmarks/README.md)** - Complete research benchmarks guide
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - Technical implementation details

### Session Testing
- **[README_2HOUR_SESSION.md](./README_2HOUR_SESSION.md)** - 2-hour comprehensive testing guide
- **[run_2hour_comprehensive.sh](./run_2hour_comprehensive.sh)** - Automated 2-hour session script
- **[BENCHMARK_SESSION_PLAN.md](./BENCHMARK_SESSION_PLAN.md)** - Session planning guide

### Reporting & Analysis
- **[BENCHMARK_REPORT_TEMPLATE.md](./BENCHMARK_REPORT_TEMPLATE.md)** - Standard report format
- **[scripts/compare_runs.py](./scripts/compare_runs.py)** - Compare benchmark results
- **[scripts/analyze_baseline.py](./scripts/analyze_baseline.py)** - Baseline analysis
- **[scripts/profile_latency.py](./scripts/profile_latency.py)** - Latency profiling
- **[scripts/generate_plots.py](./scripts/generate_plots.py)** - Visualization generation

---

## 🔬 Benchmark Categories

### By Purpose

#### ✅ **Quality Assurance**
- `academic_lite` - Fast smoke tests
- `academic_extended` - Comprehensive validation
- `industrial_small` - Real-world readiness

#### ⚡ **Performance Testing**
- `industrial_large` - Scale & throughput
- `ORB (9/5)` - Cost-latency trade-offs

#### 🧠 **Temporal & Stability**
- `stress_memory_drift` - Short-term drift
- `LECT (9/5)` - Long-term consistency (10,000+ cycles)
- `RST (9/5)` - Insight robustness

#### 🔬 **Research & Analysis**
- `MMIT (9/5)` - Memory layer isolation
- `GRDT (9/5)` - Graph reasoning depth
- `MPEB (9/5)` - Policy evolution

---

## ⚙️ Telemetry Configuration

RAE benchmarks support OpenTelemetry for observability:

### Disable Telemetry (Faster, Recommended for CI/CD)
```bash
export OTEL_TRACES_ENABLED=false
./benchmarking/test_all_benchmarks.sh

# 5-10% performance gain
# Cleaner output
# No OTLP warnings
```

### Enable Telemetry (Production Simulation)
```bash
export OTEL_TRACES_ENABLED=true
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
    --set academic_extended.yaml

# Detailed performance analysis
# Trace context for debugging
# Bottleneck identification
```

### ORB Benchmark - Telemetry Analysis
```bash
# Analyze quality-cost-latency trade-offs
python -m benchmarking.nine_five_benchmarks.orb_benchmark --samples 20

# Generates:
# - Pareto frontier
# - Quality vs Cost curves
# - Configuration recommendations
```

**Documentation:** [BENCHMARK_STARTER.md - Telemetry Section](./BENCHMARK_STARTER.md#telemetry-configuration-enabledisable-opentelemetry)

---

## 📈 Understanding Results

### Standard Metrics (v1)

| Metric | Description | Good | Excellent |
|--------|-------------|------|-----------|
| **MRR** | Mean Reciprocal Rank | > 0.6 | > 0.8 |
| **Hit Rate @5** | % queries with relevant result in top 5 | > 0.7 | > 0.9 |
| **Avg Query Time** | Average search latency | < 100ms | < 50ms |
| **Overall Quality** | Weighted combination | > 0.65 | > 0.85 |

### Mathematical Metrics (Math-1/2/3)

**Math-1 (Structure):** Graph topology, centrality, clustering
**Math-2 (Dynamics):** Drift, retention, semantic coherence
**Math-3 (Policy):** Decision quality, cost optimization

See [METRICS_MAPPING.md](./METRICS_MAPPING.md) for complete definitions.

### Research Metrics (9/5)

**LECT:** `consistency_score > 0.9`, `retention_rate > 0.95`
**MMIT:** `interference_score < 0.1`, `layer_isolation > 0.9`
**GRDT:** `max_depth >= 7`, `coherence > 0.8`
**RST:** `noise_threshold > 0.5`, `stability > 0.8`
**MPEB:** `convergence > 0.8`, `stability > 0.7`
**ORB:** Pareto-optimal configurations

---

## 🎯 Use Cases & Examples

### CI/CD Integration
```bash
# GitHub Actions example
- name: Run Benchmark Tests
  run: |
    export OTEL_TRACES_ENABLED=false
    ./benchmarking/test_all_benchmarks.sh

- name: Verify Quality
  run: |
    python benchmarking/scripts/analyze_baseline.py \
      --results benchmarking/results/session_*/
```

### Pre-Release Validation
```bash
# Before deploying new version
export OTEL_TRACES_ENABLED=false

# 1. Run comprehensive test
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
    --set academic_extended.yaml

# 2. Run large-scale test
PYTHONPATH=. python benchmarking/scripts/run_benchmark_math.py \
    --set industrial_large.yaml

# 3. Compare with baseline
python benchmarking/scripts/compare_runs.py \
    benchmarking/results/academic_extended_baseline.json \
    benchmarking/results/academic_extended_latest.json
```

### Research Paper Data Collection
```bash
# Run all 9/5 research benchmarks
python -m benchmarking.nine_five_benchmarks.runner \
    --benchmark all \
    --output-dir ./research_results/

# Generate visualizations
python benchmarking/scripts/generate_plots.py \
    --input ./research_results/ \
    --output ./figures/
```

### Production Performance Analysis
```bash
# 2-hour comprehensive session with all benchmarks
nohup ./benchmarking/run_2hour_comprehensive.sh > session.log 2>&1 &

# Monitor progress
tail -f session.log

# Results in: benchmarking/results/session_comprehensive_*/
```

---

## 🔄 Continuous Benchmarking

### Nightly Automated Runs
```yaml
# .github/workflows/benchmark-nightly.yml
name: Nightly Benchmarks
on:
  schedule:
    - cron: '0 2 * * *'  # 2 AM UTC daily

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Benchmarks
        run: |
          export OTEL_TRACES_ENABLED=false
          ./benchmarking/test_all_benchmarks.sh
```

### Regression Detection
```bash
# Compare current vs baseline
python benchmarking/scripts/compare_runs.py \
    --baseline benchmarking/results/metrics_reference.json \
    --current benchmarking/results/academic_extended_latest.json \
    --threshold 0.05  # Alert if quality drops >5%
```

---

## 🎓 Academic Research Support

RAE benchmarks are designed for academic papers and research:

### Citation-Ready Metrics
- Reproducible experimental setup
- Standard evaluation protocols
- Statistical significance testing
- Comparison with SOTA baselines

### Available Data
- 1,109+ annotated test memories
- Ground truth query-document pairs
- Temporal consistency datasets (10,000+ cycles)
- Multi-hop reasoning chains

### Research Areas Covered
1. **Memory Systems** - Multi-layer architecture evaluation
2. **Knowledge Graphs** - GraphRAG and reasoning depth
3. **Temporal Consistency** - Long-term memory retention
4. **System Optimization** - Cost-quality trade-off analysis
5. **Robustness** - Noise resilience and stability

**See:** [docs/guides/researchers/INDEX.md](../docs/guides/researchers/INDEX.md) for research documentation

---

## 📊 Benchmark Coverage Summary

```
Standard Benchmarks (v1):
├── academic_lite           10 memories    7 queries    <10s
├── academic_extended       45 memories   20 queries    ~30s
├── industrial_small        35 memories   20 queries    ~2min
├── stress_memory_drift     19 memories   17 queries    ~10s
└── industrial_large     1,000 memories  100 queries    ~4min

    Total: 1,109 memories | 164 queries

Research Benchmarks (9/5):
├── LECT - Long-term consistency (10,000+ cycles)
├── MMIT - Memory layer interference
├── GRDT - Graph reasoning depth
├── RST  - Reflective stability
├── MPEB - Policy evolution
└── ORB  - Telemetry analysis

    Total: 6 advanced research benchmarks
```

---

## 🆘 Troubleshooting

### Common Issues

**Database Connection Errors**
```bash
# Ensure Postgres and Qdrant are running
docker compose up -d postgres qdrant

# Verify connection
psql -h localhost -U rae -d rae -c "SELECT 1"
```

**Slow Benchmark Execution**
```bash
# Disable telemetry for 5-10% speedup
export OTEL_TRACES_ENABLED=false

# Use quick mode for 9/5 benchmarks
python -m benchmarking.nine_five_benchmarks.runner --benchmark all --quick
```

**Missing Dependencies**
```bash
# Reinstall dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

---

## 🤝 Contributing

Want to add a new benchmark?

1. **Standard Benchmark:** Create YAML file in `./sets/`
2. **Research Benchmark:** Follow pattern in `./nine_five_benchmarks/`
3. **Documentation:** Update this README with links
4. **Testing:** Add tests in `./tests/`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

---

## 📝 License

Part of the RAE (Reflective Agentic Memory Engine) project.
Apache 2.0 License - See [LICENSE](../LICENSE) for details.

---

## 🔗 Related Documentation

- **[Main README](../README.md)** - Project overview
- **[Architecture Docs](../docs/reference/architecture/)** - System design
- **[API Documentation](../docs/reference/api/)** - API reference
- **[Deployment Guide](../docs/reference/deployment/)** - Production deployment

---

*Last Updated: 2026-01-03 | Version: 2.1*
*Questions? Open an issue or check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)*
