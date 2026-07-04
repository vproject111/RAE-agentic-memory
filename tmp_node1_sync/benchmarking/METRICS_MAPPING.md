# RAE Benchmarks - Metrics Mapping & Implementation Plan

**Document Version:** 1.0
**Date:** 2025-12-07
**Status:** Active Implementation Plan

## Executive Summary

This document maps existing `math_metrics` implementations to the BENCHMARKS_v1.md specification and outlines the implementation plan for missing metrics.

**Current Coverage:**
- ✅ **Fully Implemented:** 8/25 metrics (32%)
- ⚠️  **Partially Implemented:** 5/25 metrics (20%)
- ❌ **Not Implemented:** 12/25 metrics (48%)

---

## 1. Memory Benchmarks (Status: 20% Complete)

### Specified Metrics vs. Implementation

| BENCHMARKS_v1 Metric | Status | Existing Implementation | Notes |
|---------------------|--------|------------------------|-------|
| **Context Quality Score (CQS)** | ⚠️ PARTIAL | `context_provenance_service.py:305` | Exists but not in benchmark suite |
| **Semantic Retention Score (SRS)** | ✅ **MAPPED** | → `MemoryDriftIndex (MDI)` | MDI measures semantic stability; inverse can be SRS |
| **Working Memory P/R (WM-P/R)** | ❌ MISSING | - | **TO IMPLEMENT** |
| **Latency per Memory Layer (LPM)** | ⚠️ PARTIAL | `run_benchmark.py` generic latency | **TO ENHANCE** - split by layer |
| **Information Loss Ratio (ILR)** | ✅ **MAPPED** | → `CompressionFidelityRatio (CFR)` | CFR measures info preservation; 1-CFR = ILR |

### Mapping Details

```python
# SRS ← MDI (inverse relationship)
# MDI measures drift (bad), SRS measures retention (good)
SRS = 1.0 - normalize(MDI)

# ILR ← CFR (inverse relationship)
# CFR measures fidelity (good), ILR measures loss (bad)
ILR = 1.0 - CFR
```

---

## 2. Graph Memory Benchmarks (Status: 40% Complete)

| BENCHMARKS_v1 Metric | Status | Existing Implementation | Notes |
|---------------------|--------|------------------------|-------|
| **Graph Coherence Index (GCI)** | ✅ **MAPPED** | → `SemanticCoherenceScore (SCS)` | Direct 1:1 mapping |
| **Neighborhood Density Score (NDS)** | ✅ **MAPPED** | → `GraphConnectivityScore (GCS)` | GCS measures connectivity density |
| **Insert Latency (IL)** | ✅ IMPLEMENTED | `run_benchmark.py:234-303` | Fully implemented |
| **Query Latency (QL)** | ✅ IMPLEMENTED | `run_benchmark.py:305-366` | Fully implemented |
| **Graph Stability Under Update (GSU)** | ✅ **MAPPED** | → `StructuralDriftMetric` | Measures topology changes |

### Mapping Details

```python
# Direct mappings - no transformation needed
GCI = SCS  # Both measure semantic coherence of graph
NDS = GCS  # Both measure connectivity density
GSU = 1.0 - StructuralDriftMetric  # Stability = inverse of drift
```

---

## 3. Reflection Benchmarks (Status: 0% Complete)

| BENCHMARKS_v1 Metric | Status | Existing Implementation | Notes |
|---------------------|--------|------------------------|-------|
| **Insight Precision (IP)** | ⚠️ **PARTIAL MAPPED** | → `ReflectionGainScore (RG)` | RG measures quality gain; needs precision calc |
| **Insight Stability (IS)** | ❌ MISSING | - | **TO IMPLEMENT** - track insight consistency |
| **Reflection Latency (RL)** | ❌ MISSING | - | **TO IMPLEMENT** - measure reflection time |
| **Critical-Event Detection Score (CEDS)** | ❌ MISSING | - | **TO IMPLEMENT** - event detection accuracy |
| **Contradiction Avoidance Score (CAS)** | ❌ MISSING | - | **TO IMPLEMENT** - logical consistency check |

### Implementation Priority: **HIGH**

Reflection is a core RAE feature but has no dedicated benchmarks. These metrics are critical for v1.0 release.

---

## 4. Math Layer Benchmarks (Status: 0% Formal / 100% Foundation)

| BENCHMARKS_v1 Metric | Status | Existing Implementation | Notes |
|---------------------|--------|------------------------|-------|
| **Math Accuracy Score (MAS)** | ⚠️ **CAN MAP** | Multiple metrics available | Aggregate of GCS, SCS, ORR |
| **Decision Coherence Ratio (DCR)** | ⚠️ **CAN MAP** | → `OptimalRetrievalRatio (ORR)` | ORR measures decision quality |
| **Operator Stability Index (OSI)** | ⚠️ **CAN MAP** | → `GraphEntropy` + `StructuralDrift` | Stability from entropy + drift |
| **Cross-Layer Math Consistency (CMC)** | ❌ MISSING | - | **TO IMPLEMENT** - verify math coherence across layers |

### Composite Mapping

```python
# MAS as composite metric
MAS = (GCS * 0.3 + SCS * 0.3 + ORR * 0.4)

# DCR directly from ORR
DCR = ORR

# OSI from entropy and drift
OSI = (1.0 - normalize(GraphEntropy)) * (1.0 - StructuralDrift)
```

---

## 5. Performance Benchmarks (Status: 20% Complete)

| BENCHMARKS_v1 Metric | Status | Existing Implementation | Notes |
|---------------------|--------|------------------------|-------|
| **End-to-End Latency (E2E-L)** | ✅ IMPLEMENTED | `run_benchmark.py:431` | `total_time_seconds` |
| **Storage Pressure Index (SPI)** | ❌ MISSING | - | **TO IMPLEMENT** - DB/vector store size |
| **LLM Cost Index (LCI)** | ❌ MISSING | - | **TO IMPLEMENT** - track API costs |
| **Telemetry Event Correlation (TEC)** | ❌ MISSING | - | **TO IMPLEMENT** - OpenTelemetry integration |
| **Worker Saturation Index (WSI)** | ❌ MISSING | - | **TO IMPLEMENT** - worker queue metrics |

### Implementation Priority: **MEDIUM-HIGH**

LCI and SPI are critical for production deployments. TEC and WSI are important for observability.

---

## 6. "9/5" Advanced Benchmarks (Status: 0% - Designed Only)

### Research-Grade Benchmarks

| Benchmark | Status | Description | Complexity |
|-----------|--------|-------------|-----------|
| **LECT** (Long-term Episodic Consistency) | ❌ DESIGNED | 10k+ cycle stability test | 🔴 VERY HIGH |
| **MMIT** (Multi-Layer Memory Interference) | ❌ DESIGNED | Cross-layer interference detection | 🔴 VERY HIGH |
| **GRDT** (Graph Reasoning Depth Test) | ❌ DESIGNED | Chain-of-thought on graph | 🟡 HIGH |
| **RST** (Reflective Stability Test) | ❌ DESIGNED | Chaos resistance for insights | 🟡 HIGH |
| **MPEB** (Math-3 Policy Evolution) | ❌ DESIGNED | Policy learning quality | 🔴 VERY HIGH |
| **ORB** (OpenTelemetry Research Benchmark) | ❌ DESIGNED | Auto-generated quality curves | 🟡 HIGH |

### Implementation Priority: **LOW** (Post-v1.0)

These are research benchmarks for academic publications and "9/5" claims. Implement after core metrics are complete.

---

## Implementation Roadmap

### Phase 1: Quick Wins (1-2 days) ✅ IN PROGRESS

1. ✅ Create mapping document (this file)
2. ⏳ Update `run_benchmark_math.py` to expose mapped metrics:
   - Add `--show-v1-metrics` flag
   - Output BENCHMARKS_v1 metric names
   - Include mapping metadata
3. ⏳ Create alias functions for clarity:
   ```python
   def calculate_gci(snapshot): return calculate_scs(snapshot)
   def calculate_nds(snapshot): return calculate_gcs(snapshot)
   def calculate_srs(snapshot): return 1.0 - normalize(calculate_mdi(snapshot))
   ```

### Phase 2: Reflection Benchmarks (3-4 days) 🎯 NEXT

**Priority: CRITICAL**

1. Implement `ReflectionLatencyMetric`
2. Implement `InsightPrecisionMetric`
3. Implement `InsightStabilityMetric`
4. Implement `CriticalEventDetectionScore`
5. Implement `ContradictionAvoidanceScore`

### Phase 3: Operational Metrics (2-3 days)

**Priority: HIGH**

1. Implement `LLMCostIndex`
2. Implement `StoragePressureIndex`
3. Implement `TelemetryEventCorrelation`
4. Implement `WorkerSaturationIndex`

### Phase 4: Memory Layer Specifics (2-3 days)

**Priority: MEDIUM**

1. Enhance `run_benchmark.py` for layer-specific latency
2. Implement `WorkingMemoryPrecisionRecall`
3. Implement `CrossLayerMathematicalConsistency`

### Phase 5: "9/5" Research Benchmarks (2-3 weeks)

**Priority: LOW** (Post-v1.0)

Design and implement advanced research benchmarks for academic validation and "9/5" claims.

---

## Integration Points

### Existing Files to Modify

1. **`benchmarking/scripts/run_benchmark_math.py`**
   - Add BENCHMARKS_v1 metric name aliases
   - Add `--format v1` output option
   - Include mapping metadata in JSON output

2. **`benchmarking/math_metrics/reflection_metrics.py`** [NEW]
   - Create new module for reflection benchmarks
   - Implement 5 reflection metrics

3. **`benchmarking/math_metrics/operational_metrics.py`** [NEW]
   - Create new module for operational metrics
   - Implement SPI, LCI, TEC, WSI

4. **`benchmarking/BENCHMARK_SESSION_PLAN.md`**
   - Update with BENCHMARKS_v1 metric names
   - Add sections for reflection and operational metrics

### CI/CD Integration

```yaml
# .github/workflows/benchmarks.yml
- name: Run BENCHMARKS_v1 Suite
  run: |
    python benchmarking/scripts/run_benchmark_math.py \
      --set academic_extended.yaml \
      --format v1 \
      --output benchmarking/results/

    # Check thresholds
    python benchmarking/scripts/check_v1_thresholds.py
```

---

## Metric Reference Table

### Complete Mapping

| BENCHMARKS_v1 | Implementation | Type | Status |
|--------------|----------------|------|--------|
| CQS | context_provenance_service | Direct | ⚠️ Partial |
| SRS | 1.0 - normalize(MDI) | Derived | ✅ Mapped |
| WM-P/R | [new] | Direct | ❌ Missing |
| LPM | enhance run_benchmark.py | Enhanced | ⚠️ Partial |
| ILR | 1.0 - CFR | Derived | ✅ Mapped |
| GCI | SCS | Alias | ✅ Mapped |
| NDS | GCS | Alias | ✅ Mapped |
| IL | run_benchmark.py | Direct | ✅ Implemented |
| QL | run_benchmark.py | Direct | ✅ Implemented |
| GSU | 1.0 - StructuralDrift | Derived | ✅ Mapped |
| IP | enhance RG | Enhanced | ⚠️ Partial |
| IS | [new] | Direct | ❌ Missing |
| RL | [new] | Direct | ❌ Missing |
| CEDS | [new] | Direct | ❌ Missing |
| CAS | [new] | Direct | ❌ Missing |
| MAS | composite(GCS, SCS, ORR) | Composite | ⚠️ Can Map |
| DCR | ORR | Alias | ✅ Mapped |
| OSI | composite(entropy, drift) | Composite | ⚠️ Can Map |
| CMC | [new] | Direct | ❌ Missing |
| E2E-L | run_benchmark.py | Direct | ✅ Implemented |
| SPI | [new] | Direct | ❌ Missing |
| LCI | [new] | Direct | ❌ Missing |
| TEC | [new] | Direct | ❌ Missing |
| WSI | [new] | Direct | ❌ Missing |

---

## Success Criteria

### Phase 1 Complete When:
- [x] Mapping document created
- [ ] All "mapped" metrics accessible via v1 names
- [ ] Baseline test run produces v1-formatted output

### Phase 2 Complete When:
- [ ] All 5 reflection metrics implemented
- [ ] Reflection benchmarks integrated into CI
- [ ] Documentation updated with examples

### Phase 3 Complete When:
- [ ] All 4 operational metrics implemented
- [ ] Production monitoring dashboard shows metrics
- [ ] Cost tracking operational

### Final v1.0 Complete When:
- [ ] 23/25 metrics implemented (92% coverage)
- [ ] All critical (reflection + operational) metrics done
- [ ] CI/CD integration complete
- [ ] Documentation finalized

---

## Appendix: Math Formulas

### Derived Metrics

```python
# Semantic Retention Score from Memory Drift Index
def calculate_srs(mdi: float, max_drift: float = 2.0) -> float:
    """
    SRS measures how well semantic meaning is retained.
    MDI measures drift (higher = more change).
    """
    normalized_mdi = min(mdi / max_drift, 1.0)
    return 1.0 - normalized_mdi

# Information Loss Ratio from Compression Fidelity Ratio
def calculate_ilr(cfr: float) -> float:
    """
    ILR measures information loss during compression.
    CFR measures fidelity (higher = better preservation).
    """
    return 1.0 - cfr

# Graph Stability Under Update from Structural Drift
def calculate_gsu(structural_drift: float) -> float:
    """
    GSU measures stability (higher = more stable).
    StructuralDrift measures change (higher = more unstable).
    """
    return 1.0 - min(structural_drift, 1.0)

# Math Accuracy Score (composite)
def calculate_mas(gcs: float, scs: float, orr: float) -> float:
    """
    MAS aggregates multiple quality signals.
    Weights: connectivity (30%), coherence (30%), retrieval (40%)
    """
    return 0.3 * gcs + 0.3 * scs + 0.4 * orr

# Operator Stability Index (composite)
def calculate_osi(graph_entropy: float, structural_drift: float) -> float:
    """
    OSI combines entropy and drift for operator stability.
    Lower entropy + lower drift = higher stability
    """
    normalized_entropy = min(graph_entropy / 10.0, 1.0)  # Assume max entropy ~10
    stability_from_entropy = 1.0 - normalized_entropy
    stability_from_drift = 1.0 - min(structural_drift, 1.0)
    return (stability_from_entropy + stability_from_drift) / 2.0
```

---

**Document End**
