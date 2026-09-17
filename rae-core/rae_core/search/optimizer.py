"""Adaptive retrieval optimizer for RAE-Core (Stage 4, L7)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from rae_core.math.policy import compute_retrieval_reward


class MaturityMode(StrEnum):
    SHADOW = "shadow"
    ADVISORY = "advisory"
    ACTIVE = "active"


class OptimizationRecommendation(BaseModel):
    mode: MaturityMode
    strategy_weights: dict[str, float]
    predicted_reward: float
    observed_rewards_count: int
    rationale: str


class RetrievalOptimizer:
    """
    Multi-objective retrieval optimizer for RAE-Core.
    Adjusts strategy weights and gate thresholds based on quality, latency, token cost, and failures.
    Supports damped adaptation (alpha=0.05) and strict bounds (+/- 15%) to prevent oscillation.
    """

    def __init__(
        self,
        mode: MaturityMode = MaturityMode.ACTIVE,
        damping_factor: float = 0.05,
        max_deviation: float = 0.15,
        baseline_weights: dict[str, float] | None = None,
    ):
        self.mode = mode
        self.damping_factor = damping_factor
        self.max_deviation = max_deviation
        self.baseline_weights = baseline_weights or {
            "fulltext": 0.5,
            "vector": 0.5,
            "graph": 0.3,
            "visual": 0.2,
        }
        self.current_weights = dict(self.baseline_weights)
        self.history: list[dict[str, Any]] = []

    def compute_reward(
        self,
        quality: float,
        latency_ms: float,
        token_cost: float = 0.0,
        is_failed: bool = False,
        max_acceptable_latency_ms: float = 500.0,
    ) -> float:
        """
        Compute multi-objective reward:
        Reward = 0.65 * Quality - 0.10 * LatencyPenalty - 0.10 * TokenCost - 0.15 * FailedRetrieval
        """
        return compute_retrieval_reward(
            quality=quality,
            latency_ms=latency_ms,
            token_cost=token_cost,
            is_failed=is_failed,
            max_acceptable_latency_ms=max_acceptable_latency_ms,
        )

    def step(
        self,
        strategy_name: str,
        quality: float,
        latency_ms: float,
        token_cost: float = 0.0,
        is_failed: bool = False,
    ) -> OptimizationRecommendation:
        """
        Record observation and update weight if in ACTIVE mode (or recommend if SHADOW/ADVISORY).
        """
        reward = self.compute_reward(quality, latency_ms, token_cost, is_failed)
        self.history.append(
            {
                "strategy": strategy_name,
                "reward": reward,
                "quality": quality,
                "latency_ms": latency_ms,
            }
        )

        # Calculate weight adjustment
        base_w = self.baseline_weights.get(strategy_name, 0.5)
        curr_w = self.current_weights.get(strategy_name, base_w)

        # Gradient: reward > 0.4 indicates positive reinforcement, < 0.4 negative
        gradient = (reward - 0.4) * 0.2
        target_w = curr_w + self.damping_factor * gradient

        # Enforce bounds [base * (1 - max_deviation), base * (1 + max_deviation)]
        lower_bound = base_w * (1.0 - self.max_deviation)
        upper_bound = base_w * (1.0 + self.max_deviation)
        clamped_w = max(lower_bound, min(upper_bound, target_w))

        if self.mode == MaturityMode.ACTIVE:
            self.current_weights[strategy_name] = round(clamped_w, 4)

        rationale = (
            f"Observed reward {reward:.3f} for '{strategy_name}'. "
            f"Adjusted target weight to {clamped_w:.4f} (mode: {self.mode.value})."
        )

        return OptimizationRecommendation(
            mode=self.mode,
            strategy_weights=dict(self.current_weights),
            predicted_reward=reward,
            observed_rewards_count=len(self.history),
            rationale=rationale,
        )

    def get_average_reward(self, last_n: int | None = None) -> float:
        records = self.history[-last_n:] if last_n else self.history
        if not records:
            return 0.0
        return sum(r["reward"] for r in records) / len(records)

    def dump_state(self) -> dict[str, Any]:
        """Serialize optimizer state for persistence."""
        return {
            "mode": self.mode.value,
            "damping_factor": self.damping_factor,
            "max_deviation": self.max_deviation,
            "baseline_weights": dict(self.baseline_weights),
            "current_weights": dict(self.current_weights),
            "history": list(self.history[-100:]),
        }

    def load_state(self, state: dict[str, Any]) -> None:
        """Restore optimizer state from dictionary."""
        if "mode" in state:
            try:
                self.mode = MaturityMode(state["mode"])
            except ValueError:
                pass
        if "damping_factor" in state:
            self.damping_factor = float(state["damping_factor"])
        if "max_deviation" in state:
            self.max_deviation = float(state["max_deviation"])
        if "baseline_weights" in state and isinstance(state["baseline_weights"], dict):
            self.baseline_weights = {
                k: float(v) for k, v in state["baseline_weights"].items()
            }
        if "current_weights" in state and isinstance(state["current_weights"], dict):
            self.current_weights = {
                k: float(v) for k, v in state["current_weights"].items()
            }
        if "history" in state and isinstance(state["history"], list):
            self.history = list(state["history"])

    def save_to_file(self, file_path: str | Any) -> None:
        """Save state to a JSON file."""
        import json
        from pathlib import Path

        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(self.dump_state(), f, indent=2)

    def load_from_file(self, file_path: str | Any) -> bool:
        """Load state from a JSON file if it exists. Returns True if loaded."""
        import json
        from pathlib import Path

        p = Path(file_path)
        if not p.exists():
            return False
        try:
            with open(p, encoding="utf-8") as f:
                state = json.load(f)
            self.load_state(state)
            return True
        except Exception:
            return False
