"""
RAE Mathematical Metrics Module

Five-tier mathematical model for agent memory analysis (BENCHMARKS_v1 compliant):
1. Structure Metrics - geometry of memory (graph connectivity, coherence, entropy)
2. Dynamics Metrics - evolution over time (drift, retention, reflection gain)
3. Policy Metrics - decision optimization (retrieval quality, cost-quality frontier)
4. Operational Metrics - production performance (cost, storage, telemetry, workers)
5. Reflection Metrics - insight quality (precision, stability, latency, detection)

This module provides research-grade mathematical analysis tools for RAE benchmarks.
"""

from .base import MathMetricBase, MemorySnapshot
from .decision_engine import (
    DEFAULT_THRESHOLDS,
    Action,
    ActionType,
    MathematicalDecisionEngine,
    Priority,
)
from .dynamics_metrics import (
    CompressionFidelityRatio,
    MemoryDriftIndex,
    ReflectionGainScore,
    RetentionCurve,
)
from .memory_metrics import WorkingMemoryPrecisionRecall
from .operational_metrics import (
    LLMCostIndex,
    StoragePressureIndex,
    TelemetryEventCorrelation,
    WorkerSaturationIndex,
)
from .policy_metrics import (
    CostQualityFrontier,
    CrossLayerMathematicalConsistency,
    OptimalRetrievalRatio,
    ReflectionPolicyEfficiency,
)
from .structure_metrics import (
    GraphConnectivityScore,
    GraphEntropyMetric,
    SemanticCoherenceScore,
    StructuralDriftMetric,
)

# Try importing reflection metrics (may not exist yet if agent is still working)
try:
    from .reflection_metrics import (  # noqa: F401
        ContradictionAvoidanceScore,
        CriticalEventDetectionScore,
        InsightPrecision,
        InsightStability,
        ReflectionLatency,
    )

    _REFLECTION_METRICS_AVAILABLE = True
except ImportError:
    _REFLECTION_METRICS_AVAILABLE = False

__all__ = [
    # Base classes
    "MathMetricBase",
    "MemorySnapshot",
    # Structure metrics
    "GraphConnectivityScore",
    "SemanticCoherenceScore",
    "GraphEntropyMetric",
    "StructuralDriftMetric",
    # Dynamics metrics
    "MemoryDriftIndex",
    "RetentionCurve",
    "ReflectionGainScore",
    "CompressionFidelityRatio",
    # Policy metrics
    "OptimalRetrievalRatio",
    "CostQualityFrontier",
    "ReflectionPolicyEfficiency",
    "CrossLayerMathematicalConsistency",
    # Memory metrics
    "WorkingMemoryPrecisionRecall",
    # Operational metrics
    "LLMCostIndex",
    "StoragePressureIndex",
    "TelemetryEventCorrelation",
    "WorkerSaturationIndex",
    # Decision engine
    "MathematicalDecisionEngine",
    "Action",
    "ActionType",
    "Priority",
    "DEFAULT_THRESHOLDS",
]

# Add reflection metrics to __all__ if available
if _REFLECTION_METRICS_AVAILABLE:
    __all__.extend(
        [
            "ReflectionLatency",
            "InsightPrecision",
            "InsightStability",
            "CriticalEventDetectionScore",
            "ContradictionAvoidanceScore",
        ]
    )

__version__ = "2.0.0"  # Major version bump for BENCHMARKS_v1 compliance
