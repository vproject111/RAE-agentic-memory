"""
RAE Metrics System - Track MDP performance and information bottleneck metrics.

Metrics Categories:
  1. MDP Metrics: Rewards, transitions, policy performance
  2. Information Bottleneck: I(Z;Y), I(Z;X), compression ratios
  3. Cost Metrics: Token usage, dollar cost, latency
  4. Graph Metrics: Convergence, structure quality
"""

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import numpy as np
import structlog

from apps.memory_api.core.actions import Action
from apps.memory_api.core.reward import RewardComponents
from apps.memory_api.core.state import RAEState

logger = structlog.get_logger(__name__)


@dataclass
class MDPMetrics:
    """Metrics for MDP performance tracking"""

    # Reward statistics
    avg_reward_per_action: Dict[str, float] = field(default_factory=dict)
    cumulative_reward: float = 0.0
    reward_history: List[float] = field(default_factory=list)

    # Transition statistics
    total_transitions: int = 0
    transitions_by_action: Dict[str, int] = field(default_factory=dict)

    # Budget tracking
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: int = 0

    # Policy performance
    avg_quality_score: float = 0.0
    budget_efficiency: float = 0.0  # Quality per dollar spent

    def to_dict(self) -> Dict:
        return {
            "avg_reward_per_action": self.avg_reward_per_action,
            "cumulative_reward": self.cumulative_reward,
            "total_transitions": self.total_transitions,
            "transitions_by_action": self.transitions_by_action,
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "avg_quality_score": self.avg_quality_score,
            "budget_efficiency": self.budget_efficiency,
        }


@dataclass
class InformationBottleneckMetrics:
    """Metrics for information bottleneck performance"""

    # Mutual information estimates
    I_Z_Y: float = 0.0  # Information between context Z and output Y
    I_Z_X: float = 0.0  # Information between context Z and full memory X

    # Compression metrics
    compression_ratio: float = 0.0  # |Z| / |X|
    context_efficiency: float = 0.0  # I(Z;Y) / |Z| (information per token)

    # History
    compression_history: List[float] = field(default_factory=list)
    efficiency_history: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "I_Z_Y": self.I_Z_Y,
            "I_Z_X": self.I_Z_X,
            "compression_ratio": self.compression_ratio,
            "context_efficiency": self.context_efficiency,
            "avg_compression": (
                np.mean(self.compression_history) if self.compression_history else 0.0
            ),
            "avg_efficiency": (
                np.mean(self.efficiency_history) if self.efficiency_history else 0.0
            ),
        }


@dataclass
class GraphMetrics:
    """Metrics for knowledge graph evolution"""

    # Structure metrics
    node_count: int = 0
    edge_count: int = 0
    avg_degree: float = 0.0
    clustering_coefficient: float = 0.0

    # Evolution metrics
    nodes_added_per_hour: float = 0.0
    edges_added_per_hour: float = 0.0

    # Convergence indicators
    spectral_gap: float = 0.0
    is_converging: bool = False

    def to_dict(self) -> Dict:
        return {
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "avg_degree": self.avg_degree,
            "clustering_coefficient": self.clustering_coefficient,
            "spectral_gap": self.spectral_gap,
            "is_converging": self.is_converging,
        }


class MetricsTracker:
    """
    Centralized metrics tracking for RAE system.

    Usage:
        tracker = MetricsTracker(window_size=1000)

        # After each action execution
        tracker.record_transition(
            state_before=s_t,
            action=a_t,
            state_after=s_next,
            reward=reward_components
        )

        # Get current metrics
        metrics = tracker.get_current_metrics()

        # Export for monitoring
        prometheus_metrics = tracker.export_prometheus()
    """

    def __init__(self, window_size: int = 1000, enable_prometheus: bool = False):
        """
        Initialize metrics tracker.

        Args:
            window_size: Size of rolling window for statistics
            enable_prometheus: Whether to export to Prometheus
        """
        self.window_size = window_size

        # MDP metrics
        self.mdp_metrics = MDPMetrics()
        self.reward_window: deque[float] = deque(maxlen=window_size)
        self.quality_window: deque[float] = deque(maxlen=window_size)

        # Action-specific tracking
        self.action_rewards: Dict[str, List[float]] = defaultdict(list)
        self.action_counts: Dict[str, int] = defaultdict(int)

        # Information bottleneck
        self.ib_metrics = InformationBottleneckMetrics()

        # Graph metrics
        self.graph_metrics = GraphMetrics()

        # Prometheus export
        self.enable_prometheus = enable_prometheus

        logger.info(
            "metrics_tracker_initialized",
            window_size=window_size,
            prometheus_enabled=enable_prometheus,
        )

    def record_transition(
        self,
        state_before: RAEState,
        action: Action,
        state_after: RAEState,
        reward: RewardComponents,
    ) -> None:
        """
        Record a state-action-state transition with reward.

        Args:
            state_before: State before action
            action: Action taken
            state_after: State after action
            reward: Computed reward components
        """
        action_type = action.action_type.value

        # Update MDP metrics
        self.mdp_metrics.total_transitions += 1
        self.mdp_metrics.cumulative_reward += reward.total_reward
        self.mdp_metrics.reward_history.append(reward.total_reward)

        # Update transitions by action
        if action_type not in self.mdp_metrics.transitions_by_action:
            self.mdp_metrics.transitions_by_action[action_type] = 0
        self.mdp_metrics.transitions_by_action[action_type] += 1

        # Update budget tracking
        self.mdp_metrics.total_tokens_used += int(reward.token_cost)
        self.mdp_metrics.total_cost_usd += (
            reward.token_cost * 0.000001
        )  # Rough estimate
        self.mdp_metrics.total_latency_ms += int(reward.latency_cost)

        # Rolling windows
        self.reward_window.append(reward.total_reward)
        self.quality_window.append(reward.quality_score)

        # Action-specific tracking
        self.action_rewards[action_type].append(reward.total_reward)
        self.action_counts[action_type] += 1

        # Update averages
        self._update_averages()

        logger.debug(
            "transition_recorded",
            action_type=action_type,
            reward=reward.total_reward,
            cumulative_reward=self.mdp_metrics.cumulative_reward,
            total_transitions=self.mdp_metrics.total_transitions,
        )

    def record_information_bottleneck(
        self, I_Z_Y: float, I_Z_X: float, context_size: int, full_memory_size: int
    ) -> None:
        """
        Record information bottleneck metrics.

        Args:
            I_Z_Y: Mutual information between context and output
            I_Z_X: Mutual information between context and full memory
            context_size: Size of selected context (tokens)
            full_memory_size: Size of full memory (tokens)
        """
        self.ib_metrics.I_Z_Y = I_Z_Y
        self.ib_metrics.I_Z_X = I_Z_X

        # Compression ratio
        if full_memory_size > 0:
            self.ib_metrics.compression_ratio = context_size / full_memory_size
        else:
            self.ib_metrics.compression_ratio = 0.0

        # Context efficiency: information per token
        if context_size > 0:
            self.ib_metrics.context_efficiency = I_Z_Y / context_size
        else:
            self.ib_metrics.context_efficiency = 0.0

        # Update history
        self.ib_metrics.compression_history.append(self.ib_metrics.compression_ratio)
        self.ib_metrics.efficiency_history.append(self.ib_metrics.context_efficiency)

        # Keep history bounded
        if len(self.ib_metrics.compression_history) > self.window_size:
            self.ib_metrics.compression_history.pop(0)
        if len(self.ib_metrics.efficiency_history) > self.window_size:
            self.ib_metrics.efficiency_history.pop(0)

        logger.debug(
            "ib_metrics_recorded",
            I_Z_Y=I_Z_Y,
            I_Z_X=I_Z_X,
            compression_ratio=self.ib_metrics.compression_ratio,
            context_efficiency=self.ib_metrics.context_efficiency,
        )

    def record_graph_state(
        self,
        node_count: int,
        edge_count: int,
        avg_degree: Optional[float] = None,
        spectral_gap: Optional[float] = None,
    ) -> None:
        """
        Record knowledge graph metrics.

        Args:
            node_count: Number of nodes in graph
            edge_count: Number of edges in graph
            avg_degree: Average node degree
            spectral_gap: Spectral gap (for convergence analysis)
        """
        self.graph_metrics.node_count = node_count
        self.graph_metrics.edge_count = edge_count

        if avg_degree is not None:
            self.graph_metrics.avg_degree = avg_degree
        elif node_count > 0:
            self.graph_metrics.avg_degree = (2 * edge_count) / node_count
        else:
            self.graph_metrics.avg_degree = 0.0

        if spectral_gap is not None:
            self.graph_metrics.spectral_gap = spectral_gap

        # Simple convergence heuristic
        self.graph_metrics.is_converging = (
            spectral_gap is not None and spectral_gap < 0.5 and node_count > 10
        )

        logger.debug(
            "graph_metrics_recorded",
            node_count=node_count,
            edge_count=edge_count,
            avg_degree=self.graph_metrics.avg_degree,
            is_converging=self.graph_metrics.is_converging,
        )

    def _update_averages(self) -> None:
        """Update rolling averages"""
        # Average reward per action
        for action_type, rewards in self.action_rewards.items():
            if rewards:
                self.mdp_metrics.avg_reward_per_action[action_type] = float(
                    np.mean(rewards[-self.window_size :])
                )

        # Average quality score
        if self.quality_window:
            self.mdp_metrics.avg_quality_score = float(np.mean(self.quality_window))

        # Budget efficiency: quality per dollar
        if self.mdp_metrics.total_cost_usd > 0:
            total_quality = sum(self.quality_window)
            self.mdp_metrics.budget_efficiency = (
                total_quality / self.mdp_metrics.total_cost_usd
            )
        else:
            self.mdp_metrics.budget_efficiency = 0.0

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics snapshot.

        Returns:
            Dictionary with all current metrics
        """
        return {
            "mdp": self.mdp_metrics.to_dict(),
            "information_bottleneck": self.ib_metrics.to_dict(),
            "graph": self.graph_metrics.to_dict(),
            "metadata": {
                "window_size": self.window_size,
                "timestamp": datetime.now().isoformat(),
            },
        }

    def get_best_actions(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Get best performing actions by average reward.

        Args:
            top_k: Number of top actions to return

        Returns:
            List of (action_type, avg_reward, count) tuples
        """
        action_stats = []

        for action_type, avg_reward in self.mdp_metrics.avg_reward_per_action.items():
            count = self.action_counts[action_type]
            action_stats.append(
                {"action_type": action_type, "avg_reward": avg_reward, "count": count}
            )

        # Sort by average reward
        action_stats_sorted = sorted(
            action_stats, key=lambda x: cast(float, x["avg_reward"]), reverse=True
        )

        return action_stats_sorted[:top_k]

    def get_worst_actions(self, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Get worst performing actions by average reward.

        Args:
            top_k: Number of worst actions to return

        Returns:
            List of (action_type, avg_reward, count) tuples
        """
        action_stats = []

        for action_type, avg_reward in self.mdp_metrics.avg_reward_per_action.items():
            count = self.action_counts[action_type]
            action_stats.append(
                {"action_type": action_type, "avg_reward": avg_reward, "count": count}
            )

        # Sort by average reward ascending
        action_stats_sorted = sorted(
            action_stats, key=lambda x: cast(float, x["avg_reward"])
        )

        return action_stats_sorted[:top_k]

    def export_prometheus(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Metrics formatted for Prometheus scraping
        """
        if not self.enable_prometheus:
            return ""

        lines = []

        # MDP metrics
        lines.append("# HELP rae_cumulative_reward Total cumulative reward")
        lines.append("# TYPE rae_cumulative_reward counter")
        lines.append(f"rae_cumulative_reward {self.mdp_metrics.cumulative_reward}")

        lines.append("# HELP rae_total_transitions Total number of transitions")
        lines.append("# TYPE rae_total_transitions counter")
        lines.append(f"rae_total_transitions {self.mdp_metrics.total_transitions}")

        lines.append("# HELP rae_avg_quality_score Average quality score")
        lines.append("# TYPE rae_avg_quality_score gauge")
        lines.append(f"rae_avg_quality_score {self.mdp_metrics.avg_quality_score}")

        # Budget metrics
        lines.append("# HELP rae_total_tokens_used Total tokens consumed")
        lines.append("# TYPE rae_total_tokens_used counter")
        lines.append(f"rae_total_tokens_used {self.mdp_metrics.total_tokens_used}")

        # IB metrics
        lines.append(
            "# HELP rae_ib_compression_ratio Information bottleneck compression ratio"
        )
        lines.append("# TYPE rae_ib_compression_ratio gauge")
        lines.append(f"rae_ib_compression_ratio {self.ib_metrics.compression_ratio}")

        lines.append(
            "# HELP rae_ib_context_efficiency Context efficiency (I(Z;Y) / tokens)"
        )
        lines.append("# TYPE rae_ib_context_efficiency gauge")
        lines.append(f"rae_ib_context_efficiency {self.ib_metrics.context_efficiency}")

        # Graph metrics
        lines.append("# HELP rae_graph_node_count Number of nodes in knowledge graph")
        lines.append("# TYPE rae_graph_node_count gauge")
        lines.append(f"rae_graph_node_count {self.graph_metrics.node_count}")

        lines.append("# HELP rae_graph_edge_count Number of edges in knowledge graph")
        lines.append("# TYPE rae_graph_edge_count gauge")
        lines.append(f"rae_graph_edge_count {self.graph_metrics.edge_count}")

        return "\n".join(lines)

    def reset(self) -> None:
        """Reset all metrics (for testing or new session)"""
        self.mdp_metrics = MDPMetrics()
        self.ib_metrics = InformationBottleneckMetrics()
        self.graph_metrics = GraphMetrics()
        self.reward_window.clear()
        self.quality_window.clear()
        self.action_rewards.clear()
        self.action_counts.clear()

        logger.info("metrics_tracker_reset")
