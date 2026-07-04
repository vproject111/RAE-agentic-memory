#!/usr/bin/env python3
"""ORB Auto-Tuner for finding Pareto-optimal configurations.

Uses grid search to explore parameter space and identify configurations
on the Pareto frontier (optimal quality/cost trade-offs).
"""

import itertools
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from benchmarking.nine_five_benchmarks.orb_benchmark import Configuration


@dataclass
class TuningResult:
    """Result from auto-tuning process."""

    configurations: List[Configuration]
    pareto_frontier: List[Configuration]
    dominated_configs: List[Configuration]
    metrics: Dict[str, Any] = field(default_factory=dict)
    total_tested: int = 0


class ORBAutoTuner:
    """Auto-tuner for ORB benchmark configurations.

    Performs grid search over parameter space to find Pareto-optimal
    configurations (best quality/cost trade-offs).

    Usage:
        tuner = ORBAutoTuner()
        results = tuner.grid_search(
            param_grid={
                "math_level": [1, 2, 3, 4],
                "batch_size": [5, 10, 25, 50, 100],
                "cache_enabled": [True, False],
            },
            quality_fn=lambda cfg: simulate_quality(cfg),
            cost_fn=lambda cfg: simulate_cost(cfg),
        )
        print(f"Found {len(results.pareto_frontier)} Pareto-optimal configs")
    """

    def __init__(self, verbose: bool = True):
        """Initialize auto-tuner.

        Args:
            verbose: Print progress during tuning
        """
        self.verbose = verbose

    def grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        quality_fn: Callable[[Configuration], float],
        cost_fn: Callable[[Configuration], float],
        config_prefix: str = "cfg_tuned",
    ) -> TuningResult:
        """Perform grid search over parameter space.

        Args:
            param_grid: Dictionary mapping parameter name to list of values
                       e.g. {"math_level": [1, 2, 3], "batch_size": [10, 50]}
            quality_fn: Function that takes Configuration and returns quality score
                       (higher is better)
            cost_fn: Function that takes Configuration and returns cost estimate
                    (lower is better)
            config_prefix: Prefix for generated configuration IDs

        Returns:
            TuningResult with all tested configs and Pareto frontier
        """
        # Generate all combinations
        param_names = list(param_grid.keys())
        param_values = [param_grid[name] for name in param_names]
        combinations = list(itertools.product(*param_values))

        if self.verbose:
            print(f"Testing {len(combinations)} parameter combinations...")

        # Test each combination
        configurations = []
        for i, combo in enumerate(combinations):
            # Build parameters dict
            params = dict(zip(param_names, combo))

            # Create configuration
            config = Configuration(
                config_id=f"{config_prefix}_{i}",
                name=f"Tuned Config {i}",
                parameters=params,
                description=f"Auto-tuned: {params}",
            )

            # Evaluate quality and cost
            quality = quality_fn(config)
            cost = cost_fn(config)

            # Store results in config metadata
            config.parameters["_quality"] = quality
            config.parameters["_cost"] = cost

            configurations.append(config)

            if self.verbose and (i + 1) % 10 == 0:
                print(f"  Tested {i + 1}/{len(combinations)} configurations...")

        # Compute Pareto frontier
        pareto_frontier = self._compute_pareto_frontier(configurations)
        dominated = [c for c in configurations if c not in pareto_frontier]

        if self.verbose:
            print(
                f"\nFound {len(pareto_frontier)}/{len(configurations)} Pareto-optimal configs"
            )

        return TuningResult(
            configurations=configurations,
            pareto_frontier=pareto_frontier,
            dominated_configs=dominated,
            total_tested=len(combinations),
            metrics={
                "pareto_ratio": len(pareto_frontier) / len(configurations),
                "avg_quality": sum(c.parameters["_quality"] for c in configurations)
                / len(configurations),
                "avg_cost": sum(c.parameters["_cost"] for c in configurations)
                / len(configurations),
            },
        )

    def _compute_pareto_frontier(
        self, configurations: List[Configuration]
    ) -> List[Configuration]:
        """Compute Pareto frontier (non-dominated solutions).

        A configuration is Pareto-optimal if no other configuration
        has both better quality AND lower cost.

        Args:
            configurations: List of configurations with _quality and _cost

        Returns:
            List of Pareto-optimal configurations
        """
        pareto_frontier = []

        for config in configurations:
            quality = config.parameters["_quality"]
            cost = config.parameters["_cost"]

            # Check if dominated by any other config
            is_dominated = False
            for other in configurations:
                if other is config:
                    continue

                other_quality = other.parameters["_quality"]
                other_cost = other.parameters["_cost"]

                # Other dominates if it has better quality AND lower cost
                if other_quality >= quality and other_cost <= cost:
                    if other_quality > quality or other_cost < cost:
                        is_dominated = True
                        break

            if not is_dominated:
                pareto_frontier.append(config)

        return pareto_frontier

    def visualize_frontier(
        self,
        result: TuningResult,
        output_path: Optional[str] = None,
    ):
        """Visualize Pareto frontier (quality vs cost).

        Requires matplotlib. If output_path provided, saves plot.

        Args:
            result: TuningResult from grid_search
            output_path: Optional path to save plot image
        """
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("matplotlib required for visualization")
            return

        # Extract quality and cost for all configs
        all_quality = [c.parameters["_quality"] for c in result.configurations]
        all_cost = [c.parameters["_cost"] for c in result.configurations]

        # Extract Pareto frontier points
        frontier_quality = [c.parameters["_quality"] for c in result.pareto_frontier]
        frontier_cost = [c.parameters["_cost"] for c in result.pareto_frontier]

        # Create plot
        plt.figure(figsize=(10, 6))
        plt.scatter(all_cost, all_quality, alpha=0.3, label="All configs", s=50)
        plt.scatter(
            frontier_cost,
            frontier_quality,
            color="red",
            s=100,
            label="Pareto frontier",
            edgecolors="black",
        )

        plt.xlabel("Cost (lower is better)", fontsize=12)
        plt.ylabel("Quality (higher is better)", fontsize=12)
        plt.title("ORB Configuration Pareto Frontier", fontsize=14)
        plt.legend()
        plt.grid(True, alpha=0.3)

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            print(f"Saved visualization to {output_path}")
        else:
            plt.show()

    def export_configs(
        self,
        result: TuningResult,
        output_path: str,
        export_type: str = "pareto",
    ):
        """Export configurations to JSON file.

        Args:
            result: TuningResult from grid_search
            output_path: Path to save JSON file
            export_type: "pareto" (only frontier), "all" (all configs),
                        "dominated" (only dominated configs)
        """
        if export_type == "pareto":
            configs_to_export = result.pareto_frontier
        elif export_type == "all":
            configs_to_export = result.configurations
        elif export_type == "dominated":
            configs_to_export = result.dominated_configs
        else:
            raise ValueError(f"Unknown export_type: {export_type}")

        # Convert to JSON-serializable format
        export_data = {
            "configs": [
                {
                    "config_id": c.config_id,
                    "name": c.name,
                    "parameters": c.parameters,
                    "description": c.description,
                }
                for c in configs_to_export
            ],
            "metrics": result.metrics,
            "total_tested": result.total_tested,
        }

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path_obj, "w") as f:
            json.dump(export_data, f, indent=2)

        print(f"Exported {len(configs_to_export)} configurations to {output_path}")


def main():
    """Example usage of ORB auto-tuner."""
    print("ORB Auto-Tuner Example")
    print("=" * 60)

    # Define parameter grid
    param_grid: Dict[str, List[Any]] = {
        "math_level": [1, 2, 3, 4],
        "batch_size": [5, 10, 25, 50, 100],
        "cache_enabled": [True, False],
    }

    # Simple quality/cost functions for demonstration
    def quality_fn(config: Configuration) -> float:
        """Simulate quality score based on parameters."""
        math_level = config.parameters["math_level"]
        batch_size = config.parameters["batch_size"]
        cache = config.parameters["cache_enabled"]

        # Higher math_level = better quality
        # Moderate batch_size = better quality
        # Cache helps quality slightly
        quality = math_level * 25
        quality += min(batch_size, 50) / 50 * 15  # Diminishing returns
        quality += 10 if cache else 0

        return float(quality)

    def cost_fn(config: Configuration) -> float:
        """Simulate cost based on parameters."""
        math_level = config.parameters["math_level"]
        batch_size = config.parameters["batch_size"]
        cache = config.parameters["cache_enabled"]

        # Higher math_level = higher cost
        # Larger batch_size = higher cost
        # Cache adds cost
        cost = math_level * 10
        cost += batch_size * 0.5
        cost += 15 if cache else 0

        return float(cost)

    # Run auto-tuner
    tuner = ORBAutoTuner(verbose=True)
    results = tuner.grid_search(
        param_grid=param_grid,
        quality_fn=quality_fn,
        cost_fn=cost_fn,
    )

    # Print results
    print("\n" + "=" * 60)
    print("Results:")
    print(f"  Total configurations tested: {results.total_tested}")
    print(f"  Pareto-optimal configs: {len(results.pareto_frontier)}")
    print(f"  Pareto ratio: {results.metrics['pareto_ratio']:.1%}")

    print("\nPareto Frontier:")
    for config in results.pareto_frontier:
        quality = config.parameters["_quality"]
        cost = config.parameters["_cost"]
        print(f"  {config.config_id}: Quality={quality:.1f}, Cost={cost:.1f}")

    # Export
    tuner.export_configs(results, "pareto_configs.json", export_type="pareto")


if __name__ == "__main__":
    main()
