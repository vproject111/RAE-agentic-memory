# RAE 9/5 Research Benchmarks

Advanced benchmark suite for comprehensive evaluation of RAE (Reflective Agentic Memory Engine).

**Version:** 1.0.0
**Status:** Research-Grade Implementation

---

## Overview

The 9/5 Benchmark Suite provides 6 advanced benchmarks designed to test RAE's memory system beyond standard metrics:

| Benchmark | Full Name | Purpose |
|-----------|-----------|---------|
| **LECT** | Long-term Episodic Consistency Test | Memory consistency over 10,000+ cycles |
| **MMIT** | Multi-Layer Memory Interference Test | Layer isolation and contamination detection |
| **GRDT** | Graph Reasoning Depth Test | Multi-hop reasoning capabilities |
| **RST** | Reflective Stability Test | Insight robustness under noise |
| **MPEB** | Math-3 Policy Evolution Benchmark | Policy learning and adaptation |
| **ORB** | OpenTelemetry Research Benchmark | Quality-cost-latency trade-off analysis |

---

## Installation

The benchmarks are part of the RAE benchmarking module. No additional installation required.

```bash
# From RAE root directory
cd benchmarking
```

---

## Quick Start

### Run All Benchmarks

```bash
# Full suite (takes 5-10 minutes)
python -m benchmarking.nine_five_benchmarks.runner --benchmark all

# Quick mode (reduced iterations, 1-2 minutes)
python -m benchmarking.nine_five_benchmarks.runner --benchmark all --quick
```

### Run Individual Benchmarks

```bash
# LECT - Long-term Consistency
python -m benchmarking.nine_five_benchmarks.lect_benchmark --cycles 10000

# MMIT - Memory Interference
python -m benchmarking.nine_five_benchmarks.mmit_benchmark --operations 5000

# GRDT - Graph Reasoning
python -m benchmarking.nine_five_benchmarks.grdt_benchmark --queries 100

# RST - Reflective Stability
python -m benchmarking.nine_five_benchmarks.rst_benchmark --insights 50

# MPEB - Policy Evolution
python -m benchmarking.nine_five_benchmarks.mpeb_benchmark --iterations 1000

# ORB - OpenTelemetry Analysis
python -m benchmarking.nine_five_benchmarks.orb_benchmark --samples 20
```

### Python API

```python
from benchmarking.nine_five_benchmarks import (
    LECTBenchmark,
    MMITBenchmark,
    GRDTBenchmark,
    RSTBenchmark,
    MPEBBenchmark,
    ORBBenchmark,
    run_all_benchmarks,
    NineFiveBenchmarkRunner,
)

# Run single benchmark
lect = LECTBenchmark(seed=42)
results = lect.run(num_cycles=10000)
print(f"Consistency: {results.consistency_score:.4f}")

# Run all benchmarks
all_results = run_all_benchmarks(verbose=True)

# Custom runner
runner = NineFiveBenchmarkRunner(output_dir="./results", seed=42)
results = runner.run_all(lect_cycles=5000, mmit_operations=2000)
runner.save_results(results)
runner.generate_report(results)
```

---

## Benchmark Details

### 1. LECT - Long-term Episodic Consistency Test

**Purpose:** Verify knowledge consistency after 10,000+ interaction cycles.

**Metrics:**
- `consistency_score` (0-1): How well key memories maintain their original semantic meaning
- `retention_rate` (0-1): Percentage of key memories still accessible
- `degradation_curve`: Consistency score over time

**Mathematical Framework:**
```
Consistency = mean(cosine_sim(embedding_t0, embedding_t)) for key memories
Retention = |retained_memories| / |original_key_memories|
```

**Parameters:**
- `num_cycles`: Number of interaction cycles (default: 10000)
- `checkpoint_interval`: Cycles between measurements (default: 1000)
- `drift_factor`: Base drift rate per update (default: 0.001)

**Expected Results:**
- Good system: consistency > 0.9, retention > 0.95
- Acceptable: consistency > 0.7, retention > 0.8
- Poor: consistency < 0.5

---

### 2. MMIT - Multi-Layer Memory Interference Test

**Purpose:** Detect leakage and contamination between RAE's 4 memory layers.

**Memory Layers:**
- Episodic: Short-term recent events
- Working: Active task context
- Semantic: Knowledge graph
- Long-Term (LTM): Persistent storage

**Metrics:**
- `interference_score` (0-1): Overall interference level (0 = no interference)
- `layer_isolation`: Per-layer isolation scores
- `contamination_events`: Detected leakage events

**Mathematical Framework:**
```
Interference = illegitimate_leakages / total_memories
Isolation = 1 - (leakage_in + leakage_out) / (2 * layer_size)
```

**Legitimate Transfer Paths:**
- Episodic -> Working (recent events to context)
- Working -> Semantic (processed info to knowledge)
- Working -> LTM (important info to long-term)
- Semantic -> Working (knowledge retrieval)
- LTM -> Working (memory retrieval)

**Expected Results:**
- Good: interference < 0.1, all layers > 0.9 isolation
- Acceptable: interference < 0.3
- Poor: interference > 0.5

---

### 3. GRDT - Graph Reasoning Depth Test

**Purpose:** Test multi-hop reasoning on knowledge graphs.

**Metrics:**
- `max_reasoning_depth`: Maximum depth of correct reasoning chains
- `reasoning_accuracy`: Accuracy at each depth level
- `chain_coherence`: Logical consistency of reasoning paths

**Mathematical Framework:**
```
Accuracy@d = correct_queries_at_depth_d / total_queries_at_depth_d
Coherence = coherent_paths / total_paths
```

**Parameters:**
- `num_queries`: Number of reasoning queries (default: 100)
- `min_depth`: Minimum path depth (default: 3)
- `max_depth`: Maximum path depth (default: 10)
- `noise_level`: Error probability (default: 0.1)

**Expected Results:**
- Good: max_depth >= 7, coherence > 0.8
- Acceptable: max_depth >= 5, coherence > 0.6
- Poor: max_depth < 4

---

### 4. RST - Reflective Stability Test

**Purpose:** Test insight robustness under noisy input conditions.

**Noise Types:**
- `gaussian`: Random embedding perturbations
- `adversarial`: Intentionally misleading information
- `missing`: Dropped data points
- `contradictory`: Conflicting information

**Metrics:**
- `stability_score`: Stability at each noise level (10%, 30%, 50%)
- `insight_consistency`: Overall consistency across conditions
- `noise_threshold`: Level where insights break down

**Mathematical Framework:**
```
Stability = mean(cosine_sim(insight_clean, insight_noisy))
Threshold = min(noise_level) where stability < 0.5
```

**Expected Results:**
- Good: threshold > 0.5, consistency > 0.8
- Acceptable: threshold > 0.3
- Poor: threshold < 0.2

---

### 5. MPEB - Math-3 Policy Evolution Benchmark

**Purpose:** Evaluate Math-3 layer MDP policy learning.

**Metrics:**
- `policy_quality`: Q-value progression over iterations
- `convergence_rate`: Speed of convergence to optimal
- `adaptation_score`: Learning speed
- `stability_index`: Decision stability

**Mathematical Framework:**
```
Quality = mean(Q(s,a)) over all state-action pairs
Convergence = correlation(learned_policy, optimal_policy)
Stability = 1 - variance(recent_actions)
```

**Policy Environment:**
- States: LOW_MEMORY, MEDIUM_MEMORY, HIGH_MEMORY, CRITICAL_MEMORY, IDLE, ACTIVE
- Actions: RETRIEVE, STORE, COMPRESS, REFLECT, ARCHIVE, SKIP

**Expected Results:**
- Good: convergence > 0.8, stability > 0.7
- Acceptable: convergence > 0.6
- Poor: convergence < 0.4

---

### 6. ORB - OpenTelemetry Research Benchmark

**Purpose:** Generate quality-cost-latency trade-off curves.

**Metrics:**
- `pareto_frontier`: Pareto-optimal configurations
- `quality_cost_curve`: Quality vs cost trade-off
- `quality_latency_curve`: Quality vs latency trade-off
- `recommendations`: Optimal configurations for different scenarios

**Mathematical Framework:**
```
Pareto Optimal: config C is optimal if no other config dominates it
Dominance: C1 dominates C2 if C1 is better in at least one metric
           and not worse in any other
```

**Default Configurations:**
- Minimal: Math-1, small batch, no cache
- Balanced: Math-2, medium batch, with cache
- Performance: Math-3, large batch, with cache
- Cost Optimized: Math-1, large batch, with cache
- Quality Optimized: Math-3, small batch, with cache
- Latency Optimized: Math-2, small batch, with cache

---

## Output Format

### JSON Results

All benchmarks output JSON files with consistent structure:

```json
{
  "benchmark_name": "LECT",
  "version": "1.0.0",
  "primary_metrics": {
    "consistency_score": 0.95,
    "retention_rate": 0.98,
    "degradation_curve": [0.99, 0.98, 0.97, ...]
  },
  "detailed_metrics": {
    "total_cycles": 10000,
    "memories_created": 3000,
    ...
  },
  "timing": {
    "start_time": "2025-12-07T10:00:00",
    "end_time": "2025-12-07T10:05:00",
    "duration_seconds": 300.0
  }
}
```

### Markdown Reports

The runner generates human-readable reports:

```markdown
# RAE 9/5 Research Benchmark Report

## Summary Scores
| Metric | Value |
|--------|-------|
| lect_consistency | 0.9500 |
| mmit_interference | 0.0500 |
...
```

---

## Integration with RAE

### Using with Math Metrics

```python
from benchmarking.math_metrics import MemoryDriftIndex, SemanticCoherenceScore
from benchmarking.nine_five_benchmarks import LECTBenchmark

# LECT uses similar drift detection as MemoryDriftIndex
lect = LECTBenchmark()
results = lect.run()

# Compare with existing metrics
mdi = MemoryDriftIndex()
# ... run MDI analysis
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Run 9/5 Benchmarks
  run: |
    python -m benchmarking.nine_five_benchmarks.runner --benchmark all --quick

- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: benchmark-results
    path: benchmarking/results/nine_five/
```

---

## Extending the Suite

### Adding Custom Configurations (ORB)

```python
from benchmarking.nine_five_benchmarks.orb_benchmark import ORBBenchmark, Configuration

orb = ORBBenchmark()
orb.add_config(Configuration(
    config_id="cfg_custom",
    name="Custom Config",
    parameters={"math_level": 2, "batch_size": 75, "cache_enabled": True},
    description="Custom configuration for testing",
))
results = orb.run()
```

### Creating New Benchmarks

Follow the existing pattern:

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CustomResults:
    benchmark_name: str = "CUSTOM"
    # ... metrics

    def to_dict(self) -> Dict[str, Any]:
        return { ... }

class CustomBenchmark:
    def __init__(self, seed: int = 42):
        self.seed = seed

    def run(self, verbose: bool = True) -> CustomResults:
        # Implementation
        pass

    def save_results(self, results: CustomResults) -> Path:
        # Save to JSON
        pass
```

---

## Research Applications

These benchmarks are designed for academic research:

1. **Memory Systems Analysis**
   - Use LECT for long-term memory retention studies
   - Use MMIT for multi-store memory architecture research

2. **Reasoning Capabilities**
   - Use GRDT for chain-of-thought reasoning evaluation
   - Compare with human reasoning benchmarks

3. **Robustness Testing**
   - Use RST for adversarial robustness analysis
   - Test against various noise distributions

4. **Policy Learning**
   - Use MPEB for RL policy analysis
   - Compare different learning algorithms

5. **System Optimization**
   - Use ORB for configuration optimization
   - Find Pareto-optimal system settings

---

## References

- RAE Architecture: `docs/project-design/RAE_ARCHITECTURE.md`
- BENCHMARKS_v1: `docs/project-design/active/BENCHMARKS_v1.md`
- Math Metrics: `benchmarking/math_metrics/README.md`

---

## License

Part of the RAE (Reflective Agentic Memory Engine) project.

---

*Document Version: 1.0.0*
*Last Updated: 2025-12-07*
