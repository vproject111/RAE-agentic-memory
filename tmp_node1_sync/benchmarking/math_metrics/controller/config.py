"""
Configuration system for MathLayerController

MathControllerConfig: Complete configuration
load_config: Load from YAML file
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .types import MathLevel


@dataclass
class LoggingConfig:
    """Logging configuration"""

    enabled: bool = True
    file_path: Optional[str] = "eval/math_policy_logs/decisions.jsonl"
    level: str = "INFO"
    save_outcomes: bool = True
    outcome_file_path: Optional[str] = "eval/math_policy_logs/outcomes.jsonl"
    include_features: bool = True
    retention_days: int = 90


@dataclass
class SafetyConfig:
    """Safety configuration"""

    max_exploration_rate: float = 0.2
    error_rate_threshold: float = 0.1
    consecutive_error_limit: int = 3
    l3_blacklist_profiles: List[str] = field(
        default_factory=lambda: ["production", "cheap"]
    )


@dataclass
class MathControllerConfig:
    """
    Complete configuration for MathLayerController.

    Can be loaded from YAML or constructed programmatically.
    """

    profile: str = "research"
    policy_version: int = 1
    bandit_enabled: bool = False
    default_level: MathLevel = MathLevel.L1
    allowed_levels: List[MathLevel] = field(
        default_factory=lambda: [MathLevel.L1, MathLevel.L2, MathLevel.L3]
    )
    thresholds: Dict[str, float] = field(default_factory=dict)
    strategies: Dict[MathLevel, List[str]] = field(default_factory=dict)
    strategy_params: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    bandit: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Apply defaults if not set"""
        if not self.thresholds:
            # Import here to avoid circular dependency
            try:
                from ..decision_engine import DEFAULT_THRESHOLDS

                self.thresholds = DEFAULT_THRESHOLDS.copy()
            except ImportError:
                self.thresholds = {}

            # Add controller-specific thresholds
            self.thresholds.update(
                {
                    "l2_memory_threshold": 50,
                    "l2_entropy_threshold": 0.7,
                    "l3_memory_threshold": 500,
                    "l3_session_threshold": 10,
                    "importance_threshold": 0.3,
                }
            )

        if not self.strategies:
            self.strategies = {
                MathLevel.L1: ["default", "relevance_scoring", "importance_scoring"],
                MathLevel.L2: [
                    "default",
                    "entropy_minimization",
                    "information_bottleneck",
                    "mutual_information",
                ],
                MathLevel.L3: ["hybrid_default", "weighted_combination"],
            }


def load_config(config_path: str) -> MathControllerConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        MathControllerConfig instance
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        raw_config = yaml.safe_load(f)

    # Get active profile
    profile = raw_config.get("profile", "research")

    # Apply profile overrides
    if "profiles" in raw_config and profile in raw_config["profiles"]:
        profile_overrides = raw_config["profiles"][profile]
        for key, value in profile_overrides.items():
            if key in raw_config:
                if isinstance(raw_config[key], dict):
                    raw_config[key].update(value)
                else:
                    raw_config[key] = value
            else:
                raw_config[key] = value

    # Parse allowed levels
    allowed_levels = []
    for level_str in raw_config.get("allowed_levels", ["deterministic_heuristic"]):
        allowed_levels.append(MathLevel(level_str))

    # Parse default level
    default_level = MathLevel(
        raw_config.get("default_level", "deterministic_heuristic")
    )

    # Parse strategies
    strategies = {}
    for level_str, strats in raw_config.get("strategies", {}).items():
        try:
            level = MathLevel(level_str)
            strategies[level] = strats
        except ValueError:
            pass  # Skip invalid levels

    # Parse logging config
    logging_raw = raw_config.get("logging", {})
    logging_config = LoggingConfig(
        enabled=logging_raw.get("enabled", True),
        file_path=logging_raw.get("file_path"),
        level=logging_raw.get("level", "INFO"),
        save_outcomes=logging_raw.get("save_outcomes", True),
        outcome_file_path=logging_raw.get("outcome_file_path"),
        include_features=logging_raw.get("include_features", True),
        retention_days=logging_raw.get("retention_days", 90),
    )

    # Parse safety config
    safety_raw = raw_config.get("safety", {})
    safety_config = SafetyConfig(
        max_exploration_rate=safety_raw.get("max_exploration_rate", 0.2),
        error_rate_threshold=safety_raw.get("error_rate_threshold", 0.1),
        consecutive_error_limit=safety_raw.get("consecutive_error_limit", 3),
        l3_blacklist_profiles=safety_raw.get(
            "l3_blacklist_profiles", ["production", "cheap"]
        ),
    )

    return MathControllerConfig(
        profile=profile,
        default_level=default_level,
        allowed_levels=allowed_levels,
        thresholds=raw_config.get("thresholds", {}),
        strategies=strategies,
        strategy_params=raw_config.get("strategy_params", {}),
        logging=logging_config,
        safety=safety_config,
    )
