"""
BENCHMARKS_v1 Metric Aliases

This module provides BENCHMARKS_v1-compliant metric names and mappings
to the underlying mathematical metrics implementation.

Maps official BENCHMARKS_v1.md metric names to math_metrics classes.
"""

from typing import Any, Dict, Optional

from .memory_metrics import WorkingMemoryPrecisionRecall
from .operational_metrics import (
    LLMCostIndex,
    StoragePressureIndex,
    TelemetryEventCorrelation,
    WorkerSaturationIndex,
)
from .policy_metrics import CrossLayerMathematicalConsistency, OptimalRetrievalRatio
from .structure_metrics import (
    GraphConnectivityScore,
    SemanticCoherenceScore,
)

# Try importing reflection metrics (conditional)
try:
    from .reflection_metrics import (
        ContradictionAvoidanceScore,
        CriticalEventDetectionScore,
        InsightPrecision,
        InsightStability,
        ReflectionLatency,
    )

    _REFLECTION_AVAILABLE = True
except ImportError:
    _REFLECTION_AVAILABLE = False


# ==============================================================================
# BENCHMARKS_v1 METRIC ALIASES
# ==============================================================================

# Graph Memory Benchmarks (Section 3 of BENCHMARKS_v1.md)
# Direct 1:1 mappings
GCI = SemanticCoherenceScore  # Graph Coherence Index
NDS = GraphConnectivityScore  # Neighborhood Density Score


# Memory Benchmarks (Section 2 of BENCHMARKS_v1.md)
# Derived metrics requiring transformation functions


def calculate_srs(mdi_value: float, max_drift: float = 2.0) -> float:
    """
    Semantic Retention Score (SRS) from Memory Drift Index.

    SRS measures retention (higher is better).
    MDI measures drift (higher is worse).

    Formula: SRS = 1.0 - normalize(MDI)

    Args:
        mdi_value: Memory Drift Index (0.0 to 2.0)
        max_drift: Maximum expected drift (default: 2.0)

    Returns:
        SRS value (0.0 to 1.0, higher is better)
    """
    normalized_mdi = min(mdi_value / max_drift, 1.0)
    return 1.0 - normalized_mdi


def calculate_ilr(cfr_value: float) -> float:
    """
    Information Loss Ratio (ILR) from Compression Fidelity Ratio.

    ILR measures information loss (lower is better).
    CFR measures fidelity (higher is better).

    Formula: ILR = 1.0 - CFR

    Args:
        cfr_value: Compression Fidelity Ratio (0.0 to 1.0)

    Returns:
        ILR value (0.0 to 1.0, lower is better)
    """
    return 1.0 - cfr_value


def calculate_gsu(structural_drift: float) -> float:
    """
    Graph Stability Under Update (GSU) from Structural Drift.

    GSU measures stability (higher is better).
    StructuralDrift measures change (higher is worse).

    Formula: GSU = 1.0 - normalize(StructuralDrift)

    Args:
        structural_drift: Structural Drift metric (0.0 to ~1.0)

    Returns:
        GSU value (0.0 to 1.0, higher is better)
    """
    return 1.0 - min(structural_drift, 1.0)


# Memory Benchmarks (Section 2 of BENCHMARKS_v1.md)
# Working Memory metrics

WM_PR = WorkingMemoryPrecisionRecall  # Working Memory Precision/Recall


# Math Layer Benchmarks (Section 5 of BENCHMARKS_v1.md)
# Composite metrics

CMC = CrossLayerMathematicalConsistency  # Cross-Layer Mathematical Consistency


def calculate_mas(gcs: float, scs: float, orr: float) -> float:
    """
    Math Accuracy Score (MAS) - composite metric.

    Combines connectivity, coherence, and retrieval quality.

    Formula: MAS = 0.3*GCS + 0.3*SCS + 0.4*ORR

    Args:
        gcs: Graph Connectivity Score
        scs: Semantic Coherence Score
        orr: Optimal Retrieval Ratio

    Returns:
        MAS value (0.0 to ~2.0, higher is better)
    """
    return 0.3 * gcs + 0.3 * scs + 0.4 * orr


DCR = OptimalRetrievalRatio  # Decision Coherence Ratio (direct mapping)


def calculate_osi(
    graph_entropy: float, structural_drift: float, max_entropy: float = 10.0
) -> float:
    """
    Operator Stability Index (OSI) - composite metric.

    Combines entropy and drift for operator stability assessment.

    Formula: OSI = avg(1 - normalize(entropy), 1 - drift)

    Args:
        graph_entropy: Graph Entropy metric
        structural_drift: Structural Drift metric
        max_entropy: Maximum expected entropy (default: 10.0)

    Returns:
        OSI value (0.0 to 1.0, higher is better)
    """
    normalized_entropy = min(graph_entropy / max_entropy, 1.0)
    stability_from_entropy = 1.0 - normalized_entropy
    stability_from_drift = 1.0 - min(structural_drift, 1.0)
    return (stability_from_entropy + stability_from_drift) / 2.0


# Performance Benchmarks (Section 6 of BENCHMARKS_v1.md)
# Direct mappings for operational metrics

LCI = LLMCostIndex  # LLM Cost Index
SPI = StoragePressureIndex  # Storage Pressure Index
TEC = TelemetryEventCorrelation  # Telemetry Event Correlation
WSI = WorkerSaturationIndex  # Worker Saturation Index


# Reflection Benchmarks (Section 4 of BENCHMARKS_v1.md)
# Conditional aliases (only if reflection_metrics module exists)

if _REFLECTION_AVAILABLE:
    RL = ReflectionLatency  # Reflection Latency
    IP = InsightPrecision  # Insight Precision
    IS = InsightStability  # Insight Stability
    CEDS = CriticalEventDetectionScore  # Critical-Event Detection Score
    CAS = ContradictionAvoidanceScore  # Contradiction Avoidance Score


# ==============================================================================
# METRIC REGISTRY
# ==============================================================================

BENCHMARKS_V1_METRICS: Dict[str, Dict[str, Any]] = {
    # Memory Benchmarks
    "CQS": {
        "name": "Context Quality Score",
        "impl": "context_provenance_service",  # External service
        "type": "direct",
        "status": "partial",
    },
    "SRS": {
        "name": "Semantic Retention Score",
        "impl": calculate_srs,
        "type": "derived",
        "source": "MemoryDriftIndex",
        "status": "implemented",
    },
    "WM-P/R": {
        "name": "Working Memory Precision/Recall",
        "impl": WM_PR,
        "type": "alias",
        "source": "WorkingMemoryPrecisionRecall",
        "status": "implemented",
    },
    "LPM": {
        "name": "Latency per Memory Layer",
        "impl": None,
        "type": "direct",
        "status": "partial",
    },
    "ILR": {
        "name": "Information Loss Ratio",
        "impl": calculate_ilr,
        "type": "derived",
        "source": "CompressionFidelityRatio",
        "status": "implemented",
    },
    # Graph Memory Benchmarks
    "GCI": {
        "name": "Graph Coherence Index",
        "impl": GCI,
        "type": "alias",
        "source": "SemanticCoherenceScore",
        "status": "implemented",
    },
    "NDS": {
        "name": "Neighborhood Density Score",
        "impl": NDS,
        "type": "alias",
        "source": "GraphConnectivityScore",
        "status": "implemented",
    },
    "IL": {
        "name": "Insert Latency",
        "impl": "run_benchmark.py",  # External script
        "type": "direct",
        "status": "implemented",
    },
    "QL": {
        "name": "Query Latency",
        "impl": "run_benchmark.py",  # External script
        "type": "direct",
        "status": "implemented",
    },
    "GSU": {
        "name": "Graph Stability Under Update",
        "impl": calculate_gsu,
        "type": "derived",
        "source": "StructuralDriftMetric",
        "status": "implemented",
    },
    # Reflection Benchmarks
    "IP": {
        "name": "Insight Precision",
        "impl": IP if _REFLECTION_AVAILABLE else None,
        "type": "direct",
        "status": "implemented" if _REFLECTION_AVAILABLE else "in_progress",
    },
    "IS": {
        "name": "Insight Stability",
        "impl": IS if _REFLECTION_AVAILABLE else None,
        "type": "direct",
        "status": "implemented" if _REFLECTION_AVAILABLE else "in_progress",
    },
    "RL": {
        "name": "Reflection Latency",
        "impl": RL if _REFLECTION_AVAILABLE else None,
        "type": "direct",
        "status": "implemented" if _REFLECTION_AVAILABLE else "in_progress",
    },
    "CEDS": {
        "name": "Critical-Event Detection Score",
        "impl": CEDS if _REFLECTION_AVAILABLE else None,
        "type": "direct",
        "status": "implemented" if _REFLECTION_AVAILABLE else "in_progress",
    },
    "CAS": {
        "name": "Contradiction Avoidance Score",
        "impl": CAS if _REFLECTION_AVAILABLE else None,
        "type": "direct",
        "status": "implemented" if _REFLECTION_AVAILABLE else "in_progress",
    },
    # Math Layer Benchmarks
    "MAS": {
        "name": "Math Accuracy Score",
        "impl": calculate_mas,
        "type": "composite",
        "sources": ["GCS", "SCS", "ORR"],
        "status": "implemented",
    },
    "DCR": {
        "name": "Decision Coherence Ratio",
        "impl": DCR,
        "type": "alias",
        "source": "OptimalRetrievalRatio",
        "status": "implemented",
    },
    "OSI": {
        "name": "Operator Stability Index",
        "impl": calculate_osi,
        "type": "composite",
        "sources": ["GraphEntropy", "StructuralDrift"],
        "status": "implemented",
    },
    "CMC": {
        "name": "Cross-Layer Mathematical Consistency",
        "impl": CMC,
        "type": "alias",
        "source": "CrossLayerMathematicalConsistency",
        "status": "implemented",
    },
    # Performance Benchmarks
    "E2E-L": {
        "name": "End-to-End Latency",
        "impl": "run_benchmark.py",  # External script
        "type": "direct",
        "status": "implemented",
    },
    "SPI": {
        "name": "Storage Pressure Index",
        "impl": SPI,
        "type": "direct",
        "status": "implemented",
    },
    "LCI": {
        "name": "LLM Cost Index",
        "impl": LCI,
        "type": "direct",
        "status": "implemented",
    },
    "TEC": {
        "name": "Telemetry Event Correlation",
        "impl": TEC,
        "type": "direct",
        "status": "implemented",
    },
    "WSI": {
        "name": "Worker Saturation Index",
        "impl": WSI,
        "type": "direct",
        "status": "implemented",
    },
}


def get_metric_info(metric_code: str) -> Optional[Dict[str, Any]]:
    """
    Get information about a BENCHMARKS_v1 metric.

    Args:
        metric_code: Metric code (e.g., "GCI", "SRS", "LCI")

    Returns:
        Dict with metric information or None if not found
    """
    return BENCHMARKS_V1_METRICS.get(metric_code)


def get_all_metrics() -> Dict[str, Dict[str, Any]]:
    """Get all BENCHMARKS_v1 metrics"""
    return BENCHMARKS_V1_METRICS


def get_implemented_metrics() -> Dict[str, Dict[str, Any]]:
    """Get only implemented metrics"""
    return {
        code: info
        for code, info in BENCHMARKS_V1_METRICS.items()
        if info["status"] in ("implemented", "partial")
    }


def get_missing_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics that are not yet implemented"""
    return {
        code: info
        for code, info in BENCHMARKS_V1_METRICS.items()
        if info["status"] == "missing"
    }


def print_metric_coverage():
    """Print BENCHMARKS_v1 metric coverage summary"""
    all_metrics = BENCHMARKS_V1_METRICS
    implemented = get_implemented_metrics()
    missing = get_missing_metrics()

    total = len(all_metrics)
    impl_count = len(implemented)
    missing_count = len(missing)

    print("=" * 70)
    print("BENCHMARKS_v1 Metric Coverage")
    print("=" * 70)
    print(f"Total Metrics:       {total}")
    print(f"Implemented:         {impl_count} ({impl_count / total * 100:.1f}%)")
    print(f"Missing:             {missing_count} ({missing_count / total * 100:.1f}%)")
    print("=" * 70)

    print("\n✅ IMPLEMENTED METRICS:")
    for code, info in implemented.items():
        print(f"  {code:6s} - {info['name']}")

    if missing:
        print("\n❌ MISSING METRICS:")
        for code, info in missing.items():
            print(f"  {code:6s} - {info['name']}")

    print("=" * 70)


if __name__ == "__main__":
    print_metric_coverage()
