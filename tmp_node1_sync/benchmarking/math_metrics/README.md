# RAE Mathematical Metrics Module

Three-tier mathematical model for agent memory analysis.

## Overview

This module provides research-grade mathematical analysis tools for RAE benchmarks, implementing three layers of metrics:

1. **Structure Metrics** - Geometry of memory (graph topology, semantic coherence)
2. **Dynamics Metrics** - Evolution over time (drift, retention, reflection gain)
3. **Policy Metrics** - Decision optimization (retrieval quality, cost-efficiency)

## Quick Start

```python
from benchmarking.math_metrics import (
    MemorySnapshot,
    GraphConnectivityScore,
    MemoryDriftIndex,
    OptimalRetrievalRatio,
)

# Create memory snapshot
snapshot = MemorySnapshot(
    timestamp=datetime.now(),
    memory_ids=["mem_1", "mem_2", "mem_3"],
    embeddings=embeddings_array,
    graph_edges=[("mem_1", "mem_2", 0.8)],
)

# Calculate structure metrics
gcs = GraphConnectivityScore()
score = gcs.calculate(num_nodes=3, edges=snapshot.graph_edges)
print(f"Graph Connectivity: {score:.4f}")
```

## Structure Metrics

### Graph Connectivity Score (GCS)

Measures how well-connected the memory graph is.

**Formula:** `GCS = average_degree / log(|nodes|)`

**Range:** 0.0 (disconnected) to unbounded (highly connected)
**Good value:** > 1.0

```python
gcs_metric = GraphConnectivityScore()
score = gcs_metric.calculate(num_nodes=100, edges=edge_list)
```

### Semantic Coherence Score (SCS)

Average semantic similarity between connected memories.

**Formula:** `SCS = mean(cosine_similarity(emb_u, emb_v)) for all edges`

**Range:** 0.0 (incoherent) to 1.0 (perfectly coherent)
**Good value:** > 0.6

```python
scs_metric = SemanticCoherenceScore()
score = scs_metric.calculate(snapshot)
```

### Graph Entropy

Organization and structure of information.

**Low entropy:** Hierarchical, organized structure
**High entropy:** Flat, disorganized structure

```python
entropy_metric = GraphEntropyMetric()
entropy = entropy_metric.calculate(num_nodes=100, edges=edge_list)
```

### Structural Drift

Change in graph topology between snapshots.

**Formula:** `Drift = 1 - Jaccard(edges_t0, edges_t1)`

**Range:** 0.0 (no change) to 1.0 (completely different)
**Good value:** < 0.3

```python
drift_metric = StructuralDriftMetric()
drift = drift_metric.calculate(snapshot_t0, snapshot_t1)
```

## Dynamics Metrics

### Memory Drift Index (MDI)

Semantic drift in memory content.

**Formula:** `MDI = cosine_distance(mean_emb_t0, mean_emb_t1)`

**Range:** 0.0 (no drift) to 2.0 (complete reversal)
**Good value:** < 0.3

```python
mdi_metric = MemoryDriftIndex()
drift = mdi_metric.calculate(snapshot_t0, snapshot_t1)
```

### Retention Curve

Memory retention quality over time (area under curve).

**Range:** 0.0 (no retention) to 1.0 (perfect retention)

```python
retention_metric = RetentionCurve()
auc = retention_metric.calculate(
    time_points=[0, 1, 2, 3],
    mrr_values=[1.0, 0.9, 0.8, 0.7],
)
```

### Reflection Gain Score (RG)

Quality improvement from reflection.

**Formula:** `RG = MRR_after - MRR_before`

**Range:** -1.0 to 1.0
**Good value:** > 0.1

```python
rg_metric = ReflectionGainScore()
gain = rg_metric.calculate(
    mrr_before=0.7,
    mrr_after=0.85,
    tokens_used=1000,
)
```

### Compression Fidelity Ratio (CFR)

Information preservation during compression.

**Range:** 0.0 (total loss) to 1.0 (perfect preservation)
**Good value:** > 0.8

```python
cfr_metric = CompressionFidelityRatio()
fidelity = cfr_metric.calculate(
    original_embeddings=orig_list,
    compressed_embeddings=comp_list,
)
```

## Policy Metrics

### Optimal Retrieval Ratio (ORR)

Frequency of optimal memory retrieval.

**Range:** 0.0 (never optimal) to 1.0 (always optimal)
**Good value:** > 0.7

```python
orr_metric = OptimalRetrievalRatio()
ratio = orr_metric.calculate(query_results, k=5)
```

### Cost-Quality Frontier (CQF)

Quality improvement per unit cost.

**Formula:** `CQF = reflection_gain / tokens_used * 1000`

**Units:** Quality improvement per 1000 tokens
**Good value:** > 0.01

```python
cqf_metric = CostQualityFrontier()
efficiency = cqf_metric.calculate(
    reflection_gain=0.15,
    tokens_used=1000,
)
```

### Reflection Policy Efficiency

Accuracy of reflection trigger decisions.

**Range:** 0.0 (poor policy) to 1.0 (perfect policy)
**Good value:** > 0.8

```python
rpe_metric = ReflectionPolicyEfficiency()
efficiency = rpe_metric.calculate(
    reflection_events=event_list,
    gain_threshold=0.05,
)
```

## Integration with Benchmarks

### Using Mathematical Benchmark Runner

```bash
# Run benchmark with mathematical metrics
python benchmarking/scripts/run_benchmark_math.py \
    --set academic_lite.yaml \
    --enable-math

# Outputs:
# - academic_lite_TIMESTAMP.json (main results)
# - academic_lite_TIMESTAMP_structure.json
# - academic_lite_TIMESTAMP_dynamics.json
# - academic_lite_TIMESTAMP_policy.json
# - academic_lite_TIMESTAMP_snapshots.json
```

### Generate Report

```bash
python benchmarking/scripts/generate_math_report.py \
    --results benchmarking/results/academic_lite_*.json \
    --output benchmarking/results/math_report.md
```

## Running Experiments

```bash
# Run single experiment
python benchmarking/experiments/run_experiments.py \
    --experiment structural_stability

# Run all experiments
python benchmarking/experiments/run_experiments.py \
    --experiment all
```

Available experiments:
- `structural_stability` - Memory structure evolution
- `drift_dynamics` - Semantic and structural drift
- `reflection_gain` - Quality improvement from reflection

## Architecture

```
benchmarking/math_metrics/
├── __init__.py              # Public API
├── base.py                  # Base classes and utilities
├── structure_metrics.py     # Structure layer
├── dynamics_metrics.py      # Dynamics layer
└── policy_metrics.py        # Policy layer
```

## Testing

```bash
# Run all tests
pytest --no-cov benchmarking/tests/test_math_metrics.py -v

# Run specific test class
pytest --no-cov benchmarking/tests/test_math_metrics.py::TestGraphConnectivityScore -v
```

## Decision Engine

The Mathematical Decision Engine transforms metrics into actionable intelligence:

```python
from benchmarking.math_metrics import MathematicalDecisionEngine

# Initialize engine
engine = MathematicalDecisionEngine()

# Analyze and get recommendations
actions = await engine.analyze_and_decide(
    snapshot_current=current_snapshot,
    snapshot_previous=previous_snapshot,
    query_results=recent_queries,
)

# Review recommendations
for action in actions:
    print(f"[{action.priority.name}] {action.type.value}")
    print(f"  Reason: {action.reason}")
    print(f"  Params: {action.params}")
```

**Decision Flow:**
```
Measure → Analyze → Decide → Act → Measure (loop)

Structure Metrics → Organization Actions (add connections, cluster)
Dynamics Metrics  → Maintenance Actions (consolidate, reflect)
Policy Metrics    → Optimization Actions (improve search, tune)
```

See [MATH_DECISION_ENGINE.md](../../docs/project-design/active/MATH_DECISION_ENGINE.md) for complete documentation.

## Scientific Foundation

This module implements the three-tier mathematical model described in:
- `docs/project-design/active/MATH_LAYER_OVERVIEW.md` - Core mathematical model
- `docs/project-design/active/MATH_DECISION_ENGINE.md` - **Decision algorithm**
- `docs/project-design/active/BENCHMARK_MATH_EXTENSION.md` - Benchmark integration
- `docs/project-design/active/MATH_EXPERIMENTS_PLAN.md` - Research experiments

### Key Concepts

1. **Memory as Geometry** - Structure metrics quantify the shape and connectivity of memory
2. **Memory as Physics** - Dynamics metrics model memory evolution and stability
3. **Memory as Economics** - Policy metrics optimize cost-quality trade-offs
4. **Memory as Intelligence** - Decision engine turns measurements into actions

## Contributing

When adding new metrics:

1. Inherit from `MathMetricBase`
2. Implement `calculate()` method
3. Store results in `_last_value` and `_last_metadata`
4. Add comprehensive tests
5. Update this README with formula and usage

Example:

```python
class NewMetric(MathMetricBase):
    def __init__(self):
        super().__init__(
            name="new_metric",
            description="What this metric measures"
        )

    def calculate(self, data) -> float:
        # Calculate metric
        value = compute_value(data)

        self._last_value = value
        self._last_metadata = {
            "data_size": len(data),
            "computation_time": elapsed,
        }

        return value
```

## Version

**Version:** 1.0.0
**Status:** Production Ready
**License:** See project LICENSE
