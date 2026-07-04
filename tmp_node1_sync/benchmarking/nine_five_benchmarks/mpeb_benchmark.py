"""
MPEB - Math-3 Policy Evolution Benchmark

Evaluates the quality and evolution of Math-3 layer decision policies over time.

Measures:
- Policy quality progression over 1000+ iterations
- Convergence rate to optimal strategies
- Adaptation speed to changing conditions
- Policy stability under various scenarios

Research-grade implementation for academic evaluation of RAE memory systems.
"""

import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class PolicyAction(Enum):
    """Actions available to the policy."""

    RETRIEVE = "retrieve"
    STORE = "store"
    COMPRESS = "compress"
    REFLECT = "reflect"
    ARCHIVE = "archive"
    SKIP = "skip"


class EnvironmentState(Enum):
    """Environment states for MDP."""

    LOW_MEMORY = "low_memory"
    MEDIUM_MEMORY = "medium_memory"
    HIGH_MEMORY = "high_memory"
    CRITICAL_MEMORY = "critical_memory"
    IDLE = "idle"
    ACTIVE = "active"


@dataclass
class PolicyState:
    """State of the policy at a point in time."""

    iteration: int
    state: EnvironmentState
    action_values: Dict[PolicyAction, float]  # Q-values
    selected_action: PolicyAction
    reward: float
    cumulative_reward: float
    epsilon: float  # Exploration rate


@dataclass
class PolicySnapshot:
    """Snapshot of policy performance."""

    iteration: int
    quality_score: float  # Mean Q-value
    optimal_action_rate: float  # How often optimal action selected
    convergence_metric: float  # Distance from optimal policy
    stability_metric: float  # Variance in recent decisions
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MPEBResults:
    """Results from MPEB benchmark."""

    benchmark_name: str = "MPEB"
    version: str = "1.0.0"

    # Primary metrics
    policy_quality: List[float] = field(default_factory=list)  # Quality over time
    convergence_rate: float = 0.0
    adaptation_score: float = 0.0
    stability_index: float = 0.0

    # Detailed metrics
    total_iterations: int = 0
    final_quality: float = 0.0
    optimal_actions: int = 0
    suboptimal_actions: int = 0

    # Learning curves
    reward_curve: List[float] = field(default_factory=list)
    quality_curve: List[float] = field(default_factory=list)
    convergence_curve: List[float] = field(default_factory=list)

    # Snapshots
    snapshots: List[Dict[str, Any]] = field(default_factory=list)

    # Timing
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "version": self.version,
            "primary_metrics": {
                "convergence_rate": self.convergence_rate,
                "adaptation_score": self.adaptation_score,
                "stability_index": self.stability_index,
                "final_quality": self.final_quality,
            },
            "detailed_metrics": {
                "total_iterations": self.total_iterations,
                "optimal_actions": self.optimal_actions,
                "suboptimal_actions": self.suboptimal_actions,
            },
            "learning_curves": {
                "reward_curve": self.reward_curve[-100:],  # Last 100
                "quality_curve": self.quality_curve[-100:],
                "convergence_curve": self.convergence_curve,
            },
            "snapshots": self.snapshots[-20:],  # Last 20 snapshots
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
        }


class PolicyEnvironment:
    """
    Simulated environment for policy learning.

    Models RAE's memory management decisions as an MDP.
    """

    def __init__(
        self,
        seed: Optional[int] = None,
    ):
        self.seed = seed
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        self.current_state = EnvironmentState.IDLE
        self.memory_pressure = 0.3
        self.activity_level = 0.5

        # Optimal policy for each state (for benchmarking)
        self.reward_structure: Dict[Tuple[EnvironmentState, PolicyAction], float] = {}
        self.optimal_policy: Dict[EnvironmentState, PolicyAction] = {
            EnvironmentState.LOW_MEMORY: PolicyAction.STORE,
            EnvironmentState.MEDIUM_MEMORY: PolicyAction.RETRIEVE,
            EnvironmentState.HIGH_MEMORY: PolicyAction.COMPRESS,
            EnvironmentState.CRITICAL_MEMORY: PolicyAction.ARCHIVE,
            EnvironmentState.IDLE: PolicyAction.REFLECT,
            EnvironmentState.ACTIVE: PolicyAction.RETRIEVE,
        }
        self._compute_optimal_policy()

    def _compute_optimal_policy(self):
        """Update optimal policy based on reward structure if it exists."""
        if not self.reward_structure:
            return

        for state in EnvironmentState:
            best_action = max(
                PolicyAction,
                key=lambda a: self.reward_structure.get((state, a), -100.0),
            )
            self.optimal_policy[state] = best_action

    def reset(self) -> EnvironmentState:
        """Reset environment to initial state."""
        self.memory_pressure = random.uniform(0.2, 0.4)
        self.activity_level = random.uniform(0.3, 0.6)
        self._update_state()
        return self.current_state

    def get_state(self) -> EnvironmentState:
        """Get current environment state."""
        return self.current_state

    def _update_state(self):
        """Update state based on internal metrics."""
        if self.memory_pressure > 0.9:
            self.current_state = EnvironmentState.CRITICAL_MEMORY
        elif self.memory_pressure > 0.7:
            self.current_state = EnvironmentState.HIGH_MEMORY
        elif self.memory_pressure > 0.4:
            self.current_state = EnvironmentState.MEDIUM_MEMORY
        elif self.activity_level > 0.6:
            self.current_state = EnvironmentState.ACTIVE
        elif self.activity_level < 0.3:
            self.current_state = EnvironmentState.IDLE
        else:
            self.current_state = EnvironmentState.LOW_MEMORY

    def step(
        self,
        action: PolicyAction,
    ) -> Tuple[EnvironmentState, float, bool]:
        """
        Execute action and return (next_state, reward, done).

        Reward function based on action appropriateness for state.
        """
        # Base reward for taking any action
        reward = 0.0

        # Optimal action reward
        optimal_action = self.optimal_policy.get(self.current_state)
        if action == optimal_action:
            reward = 1.0
        elif action in self._get_acceptable_actions(self.current_state):
            reward = 0.5
        else:
            reward = -0.5

        # State transition dynamics
        if action == PolicyAction.STORE:
            self.memory_pressure += random.uniform(0.05, 0.15)
        elif action == PolicyAction.COMPRESS:
            self.memory_pressure -= random.uniform(0.1, 0.2)
        elif action == PolicyAction.ARCHIVE:
            self.memory_pressure -= random.uniform(0.2, 0.3)
        elif action == PolicyAction.RETRIEVE:
            self.activity_level += random.uniform(0.05, 0.1)
        elif action == PolicyAction.REFLECT:
            self.activity_level -= random.uniform(0.05, 0.1)

        # Add environmental noise
        self.memory_pressure += random.gauss(0, 0.05)
        self.activity_level += random.gauss(0, 0.05)

        # Clamp values
        self.memory_pressure = max(0.0, min(1.0, self.memory_pressure))
        self.activity_level = max(0.0, min(1.0, self.activity_level))

        self._update_state()

        return self.current_state, reward, False

    def _get_acceptable_actions(
        self,
        state: EnvironmentState,
    ) -> List[PolicyAction]:
        """Get acceptable (not optimal but okay) actions for state."""
        acceptable = {
            EnvironmentState.LOW_MEMORY: [PolicyAction.STORE, PolicyAction.RETRIEVE],
            EnvironmentState.MEDIUM_MEMORY: [PolicyAction.RETRIEVE, PolicyAction.STORE],
            EnvironmentState.HIGH_MEMORY: [PolicyAction.COMPRESS, PolicyAction.ARCHIVE],
            EnvironmentState.CRITICAL_MEMORY: [
                PolicyAction.ARCHIVE,
                PolicyAction.COMPRESS,
            ],
            EnvironmentState.IDLE: [PolicyAction.REFLECT, PolicyAction.SKIP],
            EnvironmentState.ACTIVE: [PolicyAction.RETRIEVE, PolicyAction.STORE],
        }
        return acceptable.get(state, list(PolicyAction))


class QLearningPolicy:
    """
    Q-Learning policy for Math-3 layer decisions.

    Implements standard Q-learning with epsilon-greedy exploration.
    """

    def __init__(
        self,
        learning_rate: float = 0.12,
        discount_factor: float = 0.95,
        initial_epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01,
    ):
        self.lr = learning_rate
        self.gamma = discount_factor
        self.epsilon = initial_epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon

        # Initialize Q-table
        self.q_table: Dict[EnvironmentState, Dict[PolicyAction, float]] = {}
        for state in EnvironmentState:
            self.q_table[state] = {action: 0.0 for action in PolicyAction}

    def select_action(
        self,
        state: EnvironmentState,
    ) -> PolicyAction:
        """Select action using epsilon-greedy strategy."""
        if random.random() < self.epsilon:
            return random.choice(list(PolicyAction))
        else:
            # Greedy selection
            q_values = self.q_table[state]
            max_q = max(q_values.values())
            best_actions = [a for a, q in q_values.items() if q == max_q]
            return random.choice(best_actions)

    def update(
        self,
        state: EnvironmentState,
        action: PolicyAction,
        reward: float,
        next_state: EnvironmentState,
    ):
        """Update Q-value using Q-learning update rule."""
        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state].values())

        new_q = current_q + self.lr * (reward + self.gamma * max_next_q - current_q)
        self.q_table[state][action] = new_q

    def decay_epsilon(self):
        """Decay exploration rate."""
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def get_q_values(self, state: EnvironmentState) -> Dict[PolicyAction, float]:
        """Get Q-values for state."""
        return self.q_table[state].copy()

    def get_quality_score(self) -> float:
        """Get overall policy quality (mean Q-value)."""
        all_q: List[float] = []
        for state_q in self.q_table.values():
            all_q.extend(state_q.values())
        return float(np.mean(all_q))

    def get_mean_q_value(self) -> float:
        """Alias for get_quality_score."""
        return self.get_quality_score()

    def reset_exploration(self, epsilon: float = 1.0):
        """Reset exploration rate."""
        self.epsilon = epsilon


class MPEBBenchmark:
    """
    Math-3 Policy Evolution Benchmark (MPEB)

    Evaluates the learning and adaptation of Math-3 layer MDP policies.

    Key Metrics:
    1. Policy Quality - How good are the learned Q-values?
    2. Convergence Rate - How fast does policy converge to optimal?
    3. Adaptation Score - How quickly does policy adapt to changes?
    4. Stability Index - How stable are policy decisions?

    Mathematical Framework:
    - Quality = mean(Q(s,a)) over all state-action pairs
    - Convergence = correlation(learned_policy, optimal_policy)
    - Adaptation = 1 / steps_to_adapt_to_change
    - Stability = 1 - variance(recent_actions)

    Example:
        >>> mpeb = MPEBBenchmark()
        >>> results = mpeb.run(num_iterations=1000)
        >>> print(f"Convergence: {results.convergence_rate:.4f}")
        >>> print(f"Stability: {results.stability_index:.4f}")
    """

    def __init__(
        self,
        learning_rate: float = 0.12,
        discount_factor: float = 0.95,
        snapshot_interval: int = 100,
        seed: Optional[int] = 42,
    ):
        """
        Initialize MPEB benchmark.

        Args:
            learning_rate: Q-learning learning rate
            discount_factor: Q-learning discount factor
            snapshot_interval: Iterations between snapshots
            seed: Random seed for reproducibility
        """
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.snapshot_interval = snapshot_interval
        self.seed = seed

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # Components
        self.env = PolicyEnvironment(seed=seed)
        self.policy = QLearningPolicy(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
        )

        # Tracking
        self.policy_states: List[PolicyState] = []
        self.snapshots: List[PolicySnapshot] = []

    def _calculate_convergence(self) -> float:
        """Calculate convergence to optimal policy."""
        agreements = 0
        total = 0

        for state in EnvironmentState:
            optimal_action = self.env.optimal_policy.get(state)
            q_values = self.policy.get_q_values(state)

            if q_values:
                learned_action = max(q_values.items(), key=lambda x: x[1])[0]
                if learned_action == optimal_action:
                    agreements += 1
                total += 1

        return agreements / total if total > 0 else 0.0

    def _calculate_stability(self, window: int = 100) -> float:
        """Calculate policy stability over recent decisions."""
        if len(self.policy_states) < window:
            return 0.0

        recent_actions = [ps.selected_action for ps in self.policy_states[-window:]]
        action_counts: Dict[PolicyAction, int] = {}
        for action in recent_actions:
            action_counts[action] = action_counts.get(action, 0) + 1

        # Calculate entropy (lower = more stable)
        probs = [count / len(recent_actions) for count in action_counts.values()]
        entropy = -sum(p * np.log(p + 1e-10) for p in probs)
        max_entropy = np.log(len(PolicyAction))

        # Stability = 1 - normalized_entropy
        stability = 1.0 - (entropy / max_entropy)
        return float(stability)

    def _take_snapshot(self, iteration: int) -> PolicySnapshot:
        """Take a policy snapshot."""
        quality = self.policy.get_quality_score()
        convergence = self._calculate_convergence()
        stability = self._calculate_stability()

        # Optimal action rate
        if self.policy_states:
            window = min(100, len(self.policy_states))
            recent = self.policy_states[-window:]
            optimal_count = sum(
                1
                for ps in recent
                if ps.selected_action == self.env.optimal_policy.get(ps.state)
            )
            optimal_rate = optimal_count / len(recent)
        else:
            optimal_rate = 0.0

        snapshot = PolicySnapshot(
            iteration=iteration,
            quality_score=quality,
            optimal_action_rate=optimal_rate,
            convergence_metric=convergence,
            stability_metric=stability,
            metadata={
                "epsilon": self.policy.epsilon,
                "total_states": len(self.policy_states),
            },
        )

        self.snapshots.append(snapshot)
        return snapshot

    def _run_episode(
        self,
        max_steps: int = 100,
    ) -> float:
        """Run one learning episode."""
        state = self.env.reset()
        total_reward = 0.0

        for step in range(max_steps):
            # Select action
            action = self.policy.select_action(state)

            # Take step
            next_state, reward, done = self.env.step(action)

            # Update policy
            self.policy.update(state, action, reward, next_state)

            # Track state
            cumulative = sum(ps.reward for ps in self.policy_states) + reward
            policy_state = PolicyState(
                iteration=len(self.policy_states),
                state=state,
                action_values=self.policy.get_q_values(state),
                selected_action=action,
                reward=reward,
                cumulative_reward=cumulative,
                epsilon=self.policy.epsilon,
            )
            self.policy_states.append(policy_state)

            total_reward += reward
            state = next_state

            if done:
                break

        # Decay epsilon
        self.policy.decay_epsilon()

        return total_reward

    def run(
        self,
        num_iterations: int = 1000,
        episode_length: int = 50,
        verbose: bool = True,
    ) -> MPEBResults:
        """
        Run the MPEB benchmark.

        Args:
            num_iterations: Number of learning iterations (episodes)
            episode_length: Steps per episode
            verbose: Whether to print progress

        Returns:
            MPEBResults with all metrics
        """
        start_time = datetime.now()

        if verbose:
            print("Starting MPEB Benchmark")
            print(f"  Iterations: {num_iterations}")
            print(f"  Episode length: {episode_length}")
            print(f"  Learning rate: {self.learning_rate}")
            print("=" * 60)

        # Reset state
        self.policy_states.clear()
        self.snapshots.clear()
        self.policy = QLearningPolicy(
            learning_rate=self.learning_rate,
            discount_factor=self.discount_factor,
        )

        # Learning curves
        reward_curve = []
        quality_curve = []

        # Initial snapshot
        self._take_snapshot(0)

        # Run episodes
        for episode in range(num_iterations):
            episode_reward = self._run_episode(max_steps=episode_length)
            reward_curve.append(episode_reward)
            quality_curve.append(self.policy.get_quality_score())

            # Take snapshot at intervals
            if (episode + 1) % self.snapshot_interval == 0:
                snapshot = self._take_snapshot(episode + 1)
                if verbose:
                    print(
                        f"  Iteration {episode + 1:,}: "
                        f"Quality={snapshot.quality_score:.4f}, "
                        f"Convergence={snapshot.convergence_metric:.4f}, "
                        f"Optimal Rate={snapshot.optimal_action_rate:.4f}"
                    )

        # Final snapshot
        if num_iterations % self.snapshot_interval != 0:
            self._take_snapshot(num_iterations)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Calculate final metrics
        self._calculate_convergence()
        final_stability = self._calculate_stability()
        final_quality = self.policy.get_quality_score()

        # Convergence rate (how fast did it converge?)
        convergence_values = [s.convergence_metric for s in self.snapshots]
        if len(convergence_values) >= 2:
            # Find iteration where convergence first exceeds 0.8
            convergence_iteration = num_iterations
            for s in self.snapshots:
                if s.convergence_metric >= 0.8:
                    convergence_iteration = s.iteration
                    break
            convergence_rate = 1.0 - (convergence_iteration / num_iterations)
        else:
            convergence_rate = 0.0

        # Adaptation score (based on how quickly policy improved)
        if len(quality_curve) >= 10:
            early_quality = float(np.mean(quality_curve[:10]))
            late_quality = float(np.mean(quality_curve[-10:]))
            adaptation_score = (late_quality - early_quality) / max(
                abs(late_quality), 1e-6
            )
            adaptation_score = max(0.0, min(1.0, adaptation_score))
        else:
            adaptation_score = 0.0

        # Optimal/suboptimal action counts
        optimal_count = 0
        suboptimal_count = 0
        for ps in self.policy_states:
            optimal_action = self.env.optimal_policy.get(ps.state)
            if ps.selected_action == optimal_action:
                optimal_count += 1
            else:
                suboptimal_count += 1

        results = MPEBResults(
            policy_quality=quality_curve,
            convergence_rate=convergence_rate,
            adaptation_score=adaptation_score,
            stability_index=final_stability,
            total_iterations=num_iterations,
            final_quality=final_quality,
            optimal_actions=optimal_count,
            suboptimal_actions=suboptimal_count,
            reward_curve=reward_curve,
            quality_curve=quality_curve,
            convergence_curve=convergence_values,
            snapshots=[
                {
                    "iteration": s.iteration,
                    "quality_score": s.quality_score,
                    "optimal_action_rate": s.optimal_action_rate,
                    "convergence_metric": s.convergence_metric,
                    "stability_metric": s.stability_metric,
                }
                for s in self.snapshots
            ],
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
        )

        if verbose:
            print("=" * 60)
            print("MPEB Results:")
            print(f"  Final Quality: {final_quality:.4f}")
            print(f"  Convergence Rate: {convergence_rate:.4f}")
            print(f"  Adaptation Score: {adaptation_score:.4f}")
            print(f"  Stability Index: {final_stability:.4f}")
            print(
                f"  Optimal Actions: {optimal_count}/{optimal_count + suboptimal_count}"
            )
            print(f"\n  Duration: {duration:.2f}s")

        return results

    def run_multi_episode(
        self,
        num_episodes: int = 3,
        iterations_per_episode: int = 100,
        episode_length: int = 50,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """Run multi-episode adaptation test.

        Tests policy adaptation across changing rule sets:
        - Episode 1-N: Different rule sets
        - Each episode has slightly different optimal policies
        - Measures adaptation speed without catastrophic forgetting

        Args:
            num_episodes: Number of episodes with different rule sets
            iterations_per_episode: Learning iterations per episode
            episode_length: Steps per learning iteration
            verbose: Print progress

        Returns:
            Dict with multi-episode metrics:
            - episode_adaptations: Adaptation rate for each episode
            - average_adaptation_rate: Mean adaptation across episodes
            - forgetting_metric: How much previous learning was retained
            - final_quality: Final policy quality after all episodes

        Example:
            >>> mpeb = MPEBBenchmark()
            >>> results = mpeb.run_multi_episode(num_episodes=3)
            >>> print(f"Avg adaptation: {results['average_adaptation_rate']:.4f}")
        """
        if verbose:
            print(f"\nRunning multi-episode adaptation test ({num_episodes} episodes)")
            print("=" * 60)

        episode_results = []
        adaptation_rates = []

        for episode_num in range(1, num_episodes + 1):
            if verbose:
                print(
                    f"\nEpisode {episode_num}/{num_episodes}: Learning new rule set..."
                )

            # Modify environment rules for this episode
            self._modify_environment_rules(episode_num)

            # Reset exploration for new episode
            self.policy.reset_exploration()

            # Track initial quality
            initial_quality = self.policy.get_mean_q_value()

            # Run learning for this episode
            episode_start = time.time()
            for iter_num in range(iterations_per_episode):
                for _ in range(episode_length):
                    state = self.env.get_state()
                    action = self.policy.select_action(state)
                    next_state, reward, _ = self.env.step(action)
                    self.policy.update(state, action, reward, next_state)

                # Track convergence to new rule set
                convergence = self._calculate_convergence()

                if verbose and (iter_num + 1) % 20 == 0:
                    print(
                        f"  Iteration {iter_num + 1}/{iterations_per_episode}: "
                        f"Convergence={convergence:.3f}"
                    )

            episode_duration = time.time() - episode_start

            # Final quality for this episode
            final_quality = self.policy.get_mean_q_value()
            final_convergence = self._calculate_convergence()

            # Adaptation rate: how quickly quality improved
            quality_gain = final_quality - initial_quality
            adaptation_rate = quality_gain / iterations_per_episode

            adaptation_rates.append(adaptation_rate)

            episode_results.append(
                {
                    "episode": episode_num,
                    "initial_quality": initial_quality,
                    "final_quality": final_quality,
                    "quality_gain": quality_gain,
                    "adaptation_rate": adaptation_rate,
                    "final_convergence": final_convergence,
                    "duration_seconds": episode_duration,
                }
            )

            if verbose:
                print(f"  Episode {episode_num} complete:")
                print(f"    Quality gain: {quality_gain:.4f}")
                print(f"    Adaptation rate: {adaptation_rate:.4f}")
                print(f"    Final convergence: {final_convergence:.4f}")

        # Calculate aggregate metrics
        average_adaptation = float(np.mean(adaptation_rates))

        # Forgetting metric: compare first episode vs last episode quality
        # If quality drops significantly, catastrophic forgetting occurred
        first_episode_quality = episode_results[0]["final_quality"]
        last_episode_quality = episode_results[-1]["final_quality"]
        forgetting_metric = last_episode_quality / (first_episode_quality + 1e-6)

        overall_results = {
            "num_episodes": num_episodes,
            "iterations_per_episode": iterations_per_episode,
            "episode_length": episode_length,
            "episode_results": episode_results,
            "episode_adaptations": adaptation_rates,
            "average_adaptation_rate": average_adaptation,
            "forgetting_metric": forgetting_metric,
            "final_quality": last_episode_quality,
        }

        if verbose:
            print("\n" + "=" * 60)
            print("Multi-Episode Results:")
            print(f"  Average Adaptation Rate: {average_adaptation:.4f}")
            print(f"  Forgetting Metric: {forgetting_metric:.4f}")
            print(f"  Final Quality: {last_episode_quality:.4f}")
            print()

        return overall_results

    def _modify_environment_rules(self, episode_num: int):
        """Modify environment rules for multi-episode testing.

        Args:
            episode_num: Current episode number (1-indexed)

        Modifies:
            - Reward structure
            - State transition probabilities
            - Optimal policy (slightly)
        """
        # Rotate optimal policy by changing reward weights
        # This simulates changing task requirements
        base_rewards = {
            PolicyAction.RETRIEVE: 10.0,
            PolicyAction.STORE: 8.0,
            PolicyAction.COMPRESS: 6.0,
            PolicyAction.REFLECT: 5.0,
            PolicyAction.ARCHIVE: 3.0,
            PolicyAction.SKIP: -2.0,
        }

        # Apply episode-specific modifications
        modification_factor = 1.0 + (episode_num % 3) * 0.2

        for state in EnvironmentState:
            for action in PolicyAction:
                base_reward = base_rewards[action]
                # Vary rewards based on episode
                modified_reward = base_reward * modification_factor
                # Add some noise
                modified_reward += np.random.uniform(-1.0, 1.0)
                self.env.reward_structure[(state, action)] = modified_reward

        # Update optimal policy based on new rewards
        self.env._compute_optimal_policy()

    def save_results(
        self,
        results: MPEBResults,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save benchmark results to JSON."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "results" / "nine_five"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"mpeb_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        return output_file


def main():
    """Run MPEB benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run MPEB benchmark")
    parser.add_argument(
        "--iterations",
        type=int,
        default=1000,
        help="Number of learning iterations",
    )
    parser.add_argument(
        "--episode-length",
        type=int,
        default=50,
        help="Steps per episode",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=0.12,
        help="Q-learning learning rate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory",
    )

    args = parser.parse_args()

    benchmark = MPEBBenchmark(
        learning_rate=args.learning_rate,
        seed=args.seed,
    )

    results = benchmark.run(
        num_iterations=args.iterations,
        episode_length=args.episode_length,
    )

    output_dir = Path(args.output) if args.output else None
    output_file = benchmark.save_results(results, output_dir)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
