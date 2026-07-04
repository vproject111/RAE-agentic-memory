"""
Mathematical Decision Engine

Transforms metrics into actionable decisions for memory management.

The three-tier metrics don't just measure - they guide intelligent actions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import MemorySnapshot
from .dynamics_metrics import MemoryDriftIndex
from .policy_metrics import CostQualityFrontier, OptimalRetrievalRatio
from .structure_metrics import (
    GraphConnectivityScore,
    GraphEntropyMetric,
    SemanticCoherenceScore,
    StructuralDriftMetric,
)


class ActionType(Enum):
    """Types of actions the decision engine can recommend"""

    # Structure actions
    ADD_CONNECTIONS = "add_connections"
    STRENGTHEN_SEMANTICS = "strengthen_semantics"
    CLUSTER_MEMORIES = "cluster_memories"
    PRUNE_WEAK_EDGES = "prune_weak_edges"

    # Dynamics actions
    CONSOLIDATE_MEMORY = "consolidate_memory"
    TRIGGER_REFLECTION = "trigger_reflection"
    STABILIZE_STRUCTURE = "stabilize_structure"
    INCREASE_IMPORTANCE = "increase_importance"
    REDUCE_COMPRESSION = "reduce_compression"

    # Policy actions
    IMPROVE_SEARCH = "improve_search"
    TUNE_SEARCH = "tune_search"
    REDUCE_REFLECTION_COST = "reduce_reflection_cost"
    RETRAIN_POLICY = "retrain_policy"


class Priority(Enum):
    """Action priority levels"""

    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    NONE = 0


@dataclass
class Action:
    """Recommended action from decision engine"""

    type: ActionType
    priority: Priority
    reason: str
    params: Dict[str, Any]
    metric_values: Optional[Dict[str, float]] = None

    def __lt__(self, other):
        """For priority queue sorting"""
        return self.priority.value > other.priority.value


# Default thresholds for decision making
DEFAULT_THRESHOLDS = {
    # Structure thresholds
    "gcs_low": 1.0,
    "gcs_target": 1.5,
    "gcs_high": 3.0,
    "scs_low": 0.6,
    "scs_target": 0.75,
    "scs_high": 0.9,
    "entropy_high": 0.7,  # as fraction of max entropy
    "entropy_low": 0.3,
    "structural_drift_critical": 0.5,
    "structural_drift_low": 0.1,
    # Dynamics thresholds
    "mdi_moderate": 0.3,
    "mdi_critical": 0.5,
    "mdi_stable": 0.3,
    "retention_poor": 0.6,
    "retention_good": 0.8,
    "rg_low": 0.05,
    "rg_high": 0.15,
    "cfr_low": 0.7,
    "cfr_safe": 0.9,
    # Policy thresholds
    "orr_poor": 0.5,
    "orr_good": 0.7,
    "orr_excellent": 0.85,
    "cqf_inefficient": 0.005,
    "cqf_efficient": 0.01,
    "cqf_highly_efficient": 0.02,
    "rpe_bad": 0.6,
    "rpe_good": 0.8,
}


class MathematicalDecisionEngine:
    """
    Integrated decision engine using all three metric layers.

    This is the "brain" that turns measurements into actionable decisions:
    1. Structure metrics → memory organization actions
    2. Dynamics metrics → maintenance and reflection actions
    3. Policy metrics → optimization actions

    Usage:
        engine = MathematicalDecisionEngine()
        actions = await engine.analyze_and_decide(
            snapshot_current=snapshot,
            snapshot_previous=prev_snapshot,
            query_results=results,
        )
        for action in actions:
            print(f"[{action.priority.name}] {action.reason}")
    """

    def __init__(self, thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize decision engine.

        Args:
            thresholds: Custom threshold values (uses defaults if not provided)
        """
        self.thresholds = {**DEFAULT_THRESHOLDS}
        if thresholds:
            self.thresholds.update(thresholds)

        # Initialize metric calculators
        self.gcs_metric = GraphConnectivityScore()
        self.scs_metric = SemanticCoherenceScore()
        self.entropy_metric = GraphEntropyMetric()
        self.drift_metric = StructuralDriftMetric()
        self.mdi_metric = MemoryDriftIndex()
        self.orr_metric = OptimalRetrievalRatio()
        self.cqf_metric = CostQualityFrontier()

    async def analyze_and_decide(
        self,
        snapshot_current: MemorySnapshot,
        snapshot_previous: Optional[MemorySnapshot] = None,
        query_results: Optional[List[Dict]] = None,
    ) -> List[Action]:
        """
        Main decision loop: analyze metrics and generate prioritized actions.

        Args:
            snapshot_current: Current memory state
            snapshot_previous: Previous memory state (for dynamics analysis)
            query_results: Recent query results (for policy analysis)

        Returns:
            Prioritized list of recommended actions
        """
        actions = []

        # Layer 1: Structure Analysis
        structure_actions = self._analyze_structure(snapshot_current)
        actions.extend(structure_actions)

        # Layer 2: Dynamics Analysis (requires previous snapshot)
        if snapshot_previous:
            dynamics_actions = self._analyze_dynamics(
                snapshot_current, snapshot_previous
            )
            actions.extend(dynamics_actions)

        # Layer 3: Policy Analysis (requires query results)
        if query_results:
            policy_actions = self._analyze_policy(query_results)
            actions.extend(policy_actions)

        # Sort by priority (highest first)
        actions.sort(reverse=True)

        return actions

    def _analyze_structure(self, snapshot: MemorySnapshot) -> List[Action]:
        """
        Analyze structure metrics and generate actions.

        Checks: GCS, SCS, Entropy, and recommends structural improvements.
        """
        actions = []

        # Calculate structure metrics
        gcs = self.gcs_metric.calculate(
            num_nodes=snapshot.num_memories, edges=snapshot.graph_edges
        )

        scs = 0.0
        if len(snapshot.graph_edges) > 0:
            scs = self.scs_metric.calculate(snapshot)

        entropy = self.entropy_metric.calculate(
            num_nodes=snapshot.num_memories, edges=snapshot.graph_edges
        )

        # Rule 1: Graph Connectivity
        if gcs < self.thresholds["gcs_low"]:
            actions.append(
                Action(
                    type=ActionType.ADD_CONNECTIONS,
                    priority=Priority.HIGH,
                    reason=f"Low graph connectivity (GCS={gcs:.3f} < {self.thresholds['gcs_low']})",
                    params={"target_gcs": self.thresholds["gcs_target"]},
                    metric_values={"gcs": gcs},
                )
            )
        elif gcs > self.thresholds["gcs_high"]:
            actions.append(
                Action(
                    type=ActionType.PRUNE_WEAK_EDGES,
                    priority=Priority.MEDIUM,
                    reason=f"Over-connected graph (GCS={gcs:.3f} > {self.thresholds['gcs_high']})",
                    params={"target_gcs": self.thresholds["gcs_target"]},
                    metric_values={"gcs": gcs},
                )
            )

        # Rule 2: Semantic Coherence
        if scs > 0 and scs < self.thresholds["scs_low"]:
            actions.append(
                Action(
                    type=ActionType.STRENGTHEN_SEMANTICS,
                    priority=Priority.HIGH,
                    reason=f"Weak semantic coherence (SCS={scs:.3f} < {self.thresholds['scs_low']})",
                    params={"target_scs": self.thresholds["scs_target"]},
                    metric_values={"scs": scs},
                )
            )

        # Rule 3: Graph Entropy
        max_entropy = self.entropy_metric.get_metadata().get(
            "max_possible_entropy", 1.0
        )
        if max_entropy > 0:
            entropy_ratio = entropy / max_entropy
            if entropy_ratio > self.thresholds["entropy_high"]:
                actions.append(
                    Action(
                        type=ActionType.CLUSTER_MEMORIES,
                        priority=Priority.HIGH,
                        reason=f"High entropy (ratio={entropy_ratio:.3f} > {self.thresholds['entropy_high']})",
                        params={"method": "hierarchical"},
                        metric_values={
                            "entropy": entropy,
                            "entropy_ratio": entropy_ratio,
                        },
                    )
                )

        return actions

    def _analyze_dynamics(
        self, current: MemorySnapshot, previous: MemorySnapshot
    ) -> List[Action]:
        """
        Analyze dynamics metrics and generate actions.

        Checks: MDI, Structural Drift, and recommends maintenance actions.
        """
        actions = []

        # Calculate dynamics metrics
        mdi = self.mdi_metric.calculate(previous, current)
        structural_drift = self.drift_metric.calculate(previous, current)

        # Rule 1: Memory Drift Index
        if mdi > self.thresholds["mdi_critical"]:
            actions.append(
                Action(
                    type=ActionType.CONSOLIDATE_MEMORY,
                    priority=Priority.CRITICAL,
                    reason=f"Critical semantic drift (MDI={mdi:.3f} > {self.thresholds['mdi_critical']})",
                    params={"aggressive": True},
                    metric_values={"mdi": mdi},
                )
            )
        elif mdi > self.thresholds["mdi_moderate"]:
            actions.append(
                Action(
                    type=ActionType.TRIGGER_REFLECTION,
                    priority=Priority.HIGH,
                    reason=f"Moderate semantic drift (MDI={mdi:.3f} > {self.thresholds['mdi_moderate']})",
                    params={"depth": "normal"},
                    metric_values={"mdi": mdi},
                )
            )

        # Rule 2: Structural Drift
        if structural_drift > self.thresholds["structural_drift_critical"]:
            actions.append(
                Action(
                    type=ActionType.STABILIZE_STRUCTURE,
                    priority=Priority.CRITICAL,
                    reason=f"Unstable graph structure (drift={structural_drift:.3f} > {self.thresholds['structural_drift_critical']})",
                    params={},
                    metric_values={"structural_drift": structural_drift},
                )
            )

        return actions

    def _analyze_policy(self, query_results: List[Dict]) -> List[Action]:
        """
        Analyze policy metrics and generate actions.

        Checks: ORR, and recommends policy optimization actions.
        """
        actions = []

        # Calculate policy metrics
        orr = self.orr_metric.calculate(query_results, k=5)

        # Rule 1: Optimal Retrieval Ratio
        if orr < self.thresholds["orr_poor"]:
            actions.append(
                Action(
                    type=ActionType.IMPROVE_SEARCH,
                    priority=Priority.CRITICAL,
                    reason=f"Poor retrieval quality (ORR={orr:.3f} < {self.thresholds['orr_poor']})",
                    params={"reindex": True, "retrain": True},
                    metric_values={"orr": orr},
                )
            )
        elif orr < self.thresholds["orr_good"]:
            actions.append(
                Action(
                    type=ActionType.TUNE_SEARCH,
                    priority=Priority.LOW,
                    reason=f"Suboptimal retrieval (ORR={orr:.3f} < {self.thresholds['orr_good']})",
                    params={"method": "grid_search"},
                    metric_values={"orr": orr},
                )
            )

        return actions

    def update_thresholds(self, new_thresholds: Dict[str, float]):
        """
        Update decision thresholds.

        Useful for adaptive threshold adjustment based on feedback.
        """
        self.thresholds.update(new_thresholds)

    def get_thresholds(self) -> Dict[str, float]:
        """Get current threshold values"""
        return self.thresholds.copy()
