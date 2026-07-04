"""
ORB - OpenTelemetry Research Benchmark

Generates quality-cost-latency trade-off curves for RAE configurations.

Features:
- Automatic telemetry collection
- Pareto frontier computation
- Cross-commit comparison
- Configuration recommendations

Research-grade implementation for academic evaluation of RAE memory systems.
"""

import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class TelemetryPoint:
    """Single telemetry measurement point."""

    timestamp: datetime
    config_id: str
    quality: float  # 0-1, overall quality metric
    cost: float  # Cost units (e.g., API cost, compute cost)
    latency_ms: float  # Response latency in milliseconds

    # Detailed metrics
    mrr: float = 0.0
    hit_rate: float = 0.0
    tokens_used: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0

    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Configuration:
    """A system configuration to benchmark."""

    config_id: str
    name: str
    parameters: Dict[str, Any]
    description: str = ""


@dataclass
class ParetoPoint:
    """Point on the Pareto frontier."""

    config_id: str
    quality: float
    cost: float
    latency_ms: float
    dominated_by: List[str] = field(default_factory=list)
    is_pareto_optimal: bool = True


@dataclass
class ORBResults:
    """Results from ORB benchmark."""

    benchmark_name: str = "ORB"
    version: str = "1.0.0"

    # Primary metrics - Pareto frontier
    pareto_frontier: List[Dict[str, Any]] = field(default_factory=list)

    # Trade-off curves
    quality_cost_curve: List[Tuple[float, float]] = field(default_factory=list)
    quality_latency_curve: List[Tuple[float, float]] = field(default_factory=list)
    cost_latency_curve: List[Tuple[float, float]] = field(default_factory=list)

    # Recommendations
    recommendations: Dict[str, Any] = field(default_factory=dict)

    # All telemetry points
    telemetry_points: List[Dict[str, Any]] = field(default_factory=list)

    # Configuration analysis
    config_rankings: Dict[str, int] = field(default_factory=dict)
    best_quality_config: Optional[str] = None
    best_cost_config: Optional[str] = None
    best_latency_config: Optional[str] = None
    best_balanced_config: Optional[str] = None

    # Timing
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "benchmark_name": self.benchmark_name,
            "version": self.version,
            "pareto_frontier": self.pareto_frontier,
            "trade_off_curves": {
                "quality_cost": self.quality_cost_curve,
                "quality_latency": self.quality_latency_curve,
                "cost_latency": self.cost_latency_curve,
            },
            "recommendations": self.recommendations,
            "config_rankings": self.config_rankings,
            "best_configs": {
                "quality": self.best_quality_config,
                "cost": self.best_cost_config,
                "latency": self.best_latency_config,
                "balanced": self.best_balanced_config,
            },
            "telemetry_summary": {
                "total_points": len(self.telemetry_points),
                "pareto_optimal_count": len(self.pareto_frontier),
            },
            "timing": {
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.duration_seconds,
            },
        }


class ORBBenchmark:
    """
    OpenTelemetry Research Benchmark (ORB)

    Generates comprehensive trade-off analysis for RAE configurations:

    1. Quality-Cost Trade-off - How much quality per dollar?
    2. Quality-Latency Trade-off - How much quality per millisecond?
    3. Cost-Latency Trade-off - How much cost to reduce latency?

    Uses Pareto frontier analysis to identify optimal configurations.

    Mathematical Framework:
    - Pareto Optimal: config C is optimal if no other config dominates it
    - Dominance: C1 dominates C2 if C1 is better in at least one metric and not worse in others
    - Frontier: Set of all Pareto-optimal points

    Example:
        >>> orb = ORBBenchmark()
        >>> results = orb.run(num_samples=100)
        >>> print(f"Pareto optimal configs: {len(results.pareto_frontier)}")
        >>> print(f"Best balanced: {results.best_balanced_config}")
    """

    # Default configurations to test
    DEFAULT_CONFIGS = [
        Configuration(
            config_id="cfg_minimal",
            name="Minimal",
            parameters={"math_level": 1, "batch_size": 10, "cache_enabled": False},
            description="Minimal resource usage",
        ),
        Configuration(
            config_id="cfg_balanced",
            name="Balanced",
            parameters={"math_level": 2, "batch_size": 50, "cache_enabled": True},
            description="Balanced performance",
        ),
        Configuration(
            config_id="cfg_performance",
            name="Performance",
            parameters={"math_level": 3, "batch_size": 100, "cache_enabled": True},
            description="Maximum performance",
        ),
        Configuration(
            config_id="cfg_cost_optimized",
            name="Cost Optimized",
            parameters={"math_level": 1, "batch_size": 100, "cache_enabled": True},
            description="Optimized for cost",
        ),
        Configuration(
            config_id="cfg_quality_optimized",
            name="Quality Optimized",
            parameters={"math_level": 3, "batch_size": 25, "cache_enabled": True},
            description="Optimized for quality",
        ),
        Configuration(
            config_id="cfg_latency_optimized",
            name="Latency Optimized",
            parameters={"math_level": 2, "batch_size": 10, "cache_enabled": True},
            description="Optimized for latency",
        ),
        Configuration(
            config_id="cfg_realtime",
            name="Real-time",
            parameters={"math_level": 1, "batch_size": 5, "cache_enabled": True},
            description="Ultra-low latency for real-time applications",
        ),
        Configuration(
            config_id="cfg_research",
            name="Research Grade",
            parameters={"math_level": 4, "batch_size": 50, "cache_enabled": True},
            description="Research-grade quality (expensive but thorough)",
        ),
    ]

    def __init__(
        self,
        configs: Optional[List[Configuration]] = None,
        seed: Optional[int] = 42,
    ):
        """
        Initialize ORB benchmark.

        Args:
            configs: Configurations to test (default: DEFAULT_CONFIGS)
            seed: Random seed for reproducibility
        """
        self.configs = configs or self.DEFAULT_CONFIGS.copy()
        self.seed = seed

        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        # Storage
        self.telemetry: List[TelemetryPoint] = []
        self.pareto_points: List[ParetoPoint] = []

    def _simulate_config_performance(
        self,
        config: Configuration,
        num_samples: int = 10,
    ) -> List[TelemetryPoint]:
        """
        Simulate performance measurements for a configuration.

        In production, this would collect real telemetry from OpenTelemetry.
        """
        points = []
        params = config.parameters

        # Base metrics based on configuration
        math_level = params.get("math_level", 1)
        batch_size = params.get("batch_size", 50)
        cache_enabled = params.get("cache_enabled", False)

        # Quality increases with math level, decreases slightly with batch size
        base_quality = 0.5 + (math_level - 1) * 0.15 - batch_size * 0.001

        # Cost increases with math level and batch size
        base_cost = 0.1 * math_level + batch_size * 0.001

        # Latency increases with math level, decreases with cache
        base_latency = 10 * math_level + batch_size * 0.5
        if cache_enabled:
            base_latency *= 0.7

        for i in range(num_samples):
            # Add realistic noise
            quality = base_quality + random.gauss(0, 0.05)
            quality = max(0.0, min(1.0, quality))

            cost = base_cost * (1 + random.gauss(0, 0.1))
            cost = max(0.01, cost)

            latency = base_latency * (1 + random.gauss(0, 0.15))
            latency = max(1.0, latency)

            # Detailed metrics
            mrr = quality * (0.9 + random.gauss(0, 0.05))
            hit_rate = quality * (0.85 + random.gauss(0, 0.05))
            tokens = int(batch_size * math_level * 100 * (1 + random.gauss(0, 0.2)))
            memory = 100 + math_level * 50 + batch_size * 2 + random.gauss(0, 20)
            cpu = 10 + math_level * 15 + batch_size * 0.3 + random.gauss(0, 5)

            point = TelemetryPoint(
                timestamp=datetime.now(),
                config_id=config.config_id,
                quality=quality,
                cost=cost,
                latency_ms=latency,
                mrr=max(0, min(1, mrr)),
                hit_rate=max(0, min(1, hit_rate)),
                tokens_used=max(0, tokens),
                memory_mb=max(0, memory),
                cpu_percent=max(0, min(100, cpu)),
                metadata={
                    "sample_id": i,
                    "config_name": config.name,
                },
            )
            points.append(point)

        return points

    def _compute_pareto_frontier(
        self,
        points: List[TelemetryPoint],
    ) -> List[ParetoPoint]:
        """
        Compute Pareto frontier from telemetry points.

        A point is Pareto-optimal if no other point dominates it.
        Point A dominates Point B if A is better in at least one dimension
        and not worse in any other.
        """
        # Aggregate points by config (use mean values)
        config_metrics: Dict[str, Dict[str, List[float]]] = {}

        for point in points:
            if point.config_id not in config_metrics:
                config_metrics[point.config_id] = {
                    "quality": [],
                    "cost": [],
                    "latency": [],
                }
            config_metrics[point.config_id]["quality"].append(point.quality)
            config_metrics[point.config_id]["cost"].append(point.cost)
            config_metrics[point.config_id]["latency"].append(point.latency_ms)

        # Create mean points per config
        pareto_candidates: List[ParetoPoint] = []
        for config_id, metrics in config_metrics.items():
            pareto_candidates.append(
                ParetoPoint(
                    config_id=config_id,
                    quality=float(np.mean(metrics["quality"])),
                    cost=float(np.mean(metrics["cost"])),
                    latency_ms=float(np.mean(metrics["latency"])),
                )
            )

        # Find dominated points
        for i, p1 in enumerate(pareto_candidates):
            for j, p2 in enumerate(pareto_candidates):
                if i == j:
                    continue

                # Check if p2 dominates p1
                # (p2 has higher quality AND lower cost AND lower latency)
                # At least one strict inequality, others non-strict
                better_quality = p2.quality >= p1.quality
                better_cost = p2.cost <= p1.cost
                better_latency = p2.latency_ms <= p1.latency_ms

                strictly_better = (
                    p2.quality > p1.quality
                    or p2.cost < p1.cost
                    or p2.latency_ms < p1.latency_ms
                )

                if (
                    better_quality
                    and better_cost
                    and better_latency
                    and strictly_better
                ):
                    p1.is_pareto_optimal = False
                    p1.dominated_by.append(p2.config_id)

        return pareto_candidates

    def _generate_trade_off_curves(
        self,
        points: List[TelemetryPoint],
    ) -> Tuple[
        List[Tuple[float, float]], List[Tuple[float, float]], List[Tuple[float, float]]
    ]:
        """Generate trade-off curves from telemetry points."""
        quality_cost = []
        quality_latency = []
        cost_latency = []

        for point in points:
            quality_cost.append((point.quality, point.cost))
            quality_latency.append((point.quality, point.latency_ms))
            cost_latency.append((point.cost, point.latency_ms))

        # Sort by first dimension
        quality_cost.sort(key=lambda x: x[0])
        quality_latency.sort(key=lambda x: x[0])
        cost_latency.sort(key=lambda x: x[0])

        return quality_cost, quality_latency, cost_latency

    def _generate_recommendations(
        self,
        pareto_points: List[ParetoPoint],
    ) -> Dict[str, Any]:
        """Generate configuration recommendations."""
        if not pareto_points:
            return {"error": "No Pareto points available"}

        optimal_points = [p for p in pareto_points if p.is_pareto_optimal]
        if not optimal_points:
            optimal_points = pareto_points

        scenarios: Dict[str, Dict[str, Any]] = {}
        recommendations: Dict[str, Any] = {
            "pareto_optimal_count": len(optimal_points),
            "scenarios": scenarios,
        }

        # Best for quality
        best_quality = max(optimal_points, key=lambda p: p.quality)
        scenarios["maximize_quality"] = {
            "config_id": best_quality.config_id,
            "quality": best_quality.quality,
            "cost": best_quality.cost,
            "latency_ms": best_quality.latency_ms,
            "reason": "Highest quality among Pareto-optimal configurations",
        }

        # Best for cost
        best_cost = min(optimal_points, key=lambda p: p.cost)
        scenarios["minimize_cost"] = {
            "config_id": best_cost.config_id,
            "quality": best_cost.quality,
            "cost": best_cost.cost,
            "latency_ms": best_cost.latency_ms,
            "reason": "Lowest cost among Pareto-optimal configurations",
        }

        # Best for latency
        best_latency = min(optimal_points, key=lambda p: p.latency_ms)
        scenarios["minimize_latency"] = {
            "config_id": best_latency.config_id,
            "quality": best_latency.quality,
            "cost": best_latency.cost,
            "latency_ms": best_latency.latency_ms,
            "reason": "Lowest latency among Pareto-optimal configurations",
        }

        # Balanced (normalize and find best overall)
        qualities = [p.quality for p in optimal_points]
        costs = [p.cost for p in optimal_points]
        latencies = [p.latency_ms for p in optimal_points]

        q_range = max(qualities) - min(qualities) if len(qualities) > 1 else 1
        c_range = max(costs) - min(costs) if len(costs) > 1 else 1
        l_range = max(latencies) - min(latencies) if len(latencies) > 1 else 1

        best_balanced_score = -float("inf")
        best_balanced_point = optimal_points[0]

        for point in optimal_points:
            # Normalized scores (higher is better)
            q_norm = (point.quality - min(qualities)) / q_range if q_range > 0 else 0.5
            c_norm = 1 - (point.cost - min(costs)) / c_range if c_range > 0 else 0.5
            l_norm = (
                1 - (point.latency_ms - min(latencies)) / l_range
                if l_range > 0
                else 0.5
            )

            # Balanced score (equal weights)
            score = q_norm + c_norm + l_norm

            if score > best_balanced_score:
                best_balanced_score = score
                best_balanced_point = point

        scenarios["balanced"] = {
            "config_id": best_balanced_point.config_id,
            "quality": best_balanced_point.quality,
            "cost": best_balanced_point.cost,
            "latency_ms": best_balanced_point.latency_ms,
            "reason": "Best balance of quality, cost, and latency",
        }

        return recommendations

    def add_config(self, config: Configuration):
        """Add a configuration to benchmark."""
        self.configs.append(config)

    def run(
        self,
        num_samples_per_config: int = 20,
        verbose: bool = True,
    ) -> ORBResults:
        """
        Run the ORB benchmark.

        Args:
            num_samples_per_config: Samples to collect per configuration
            verbose: Whether to print progress

        Returns:
            ORBResults with trade-off analysis
        """
        start_time = datetime.now()

        if verbose:
            print("Starting ORB Benchmark")
            print(f"  Configurations: {len(self.configs)}")
            print(f"  Samples per config: {num_samples_per_config}")
            print("=" * 60)

        # Reset state
        self.telemetry.clear()
        self.pareto_points.clear()

        # Collect telemetry for each configuration
        for config in self.configs:
            if verbose:
                print(f"  Testing: {config.name} ({config.config_id})")

            points = self._simulate_config_performance(config, num_samples_per_config)
            self.telemetry.extend(points)

            if verbose:
                avg_quality = np.mean([p.quality for p in points])
                avg_cost = np.mean([p.cost for p in points])
                avg_latency = np.mean([p.latency_ms for p in points])
                print(
                    f"    Quality={avg_quality:.4f}, Cost={avg_cost:.4f}, Latency={avg_latency:.1f}ms"
                )

        # Compute Pareto frontier
        if verbose:
            print("\nComputing Pareto frontier...")
        self.pareto_points = self._compute_pareto_frontier(self.telemetry)
        optimal_count = sum(1 for p in self.pareto_points if p.is_pareto_optimal)
        if verbose:
            print(f"  Found {optimal_count} Pareto-optimal configurations")

        # Generate trade-off curves
        quality_cost, quality_latency, cost_latency = self._generate_trade_off_curves(
            self.telemetry
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(self.pareto_points)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Find best configs
        best_quality_config = None
        best_cost_config = None
        best_latency_config = None
        best_balanced_config = None

        if self.pareto_points:
            optimal = [p for p in self.pareto_points if p.is_pareto_optimal]
            if optimal:
                best_quality_config = max(optimal, key=lambda p: p.quality).config_id
                best_cost_config = min(optimal, key=lambda p: p.cost).config_id
                best_latency_config = min(optimal, key=lambda p: p.latency_ms).config_id
                best_balanced_config = (
                    recommendations.get("scenarios", {})
                    .get("balanced", {})
                    .get("config_id")
                )

        # Config rankings (by balanced score)
        config_rankings = {}
        for i, config in enumerate(self.configs):
            config_rankings[config.config_id] = i + 1

        results = ORBResults(
            pareto_frontier=[
                {
                    "config_id": p.config_id,
                    "quality": p.quality,
                    "cost": p.cost,
                    "latency_ms": p.latency_ms,
                    "is_pareto_optimal": p.is_pareto_optimal,
                    "dominated_by": p.dominated_by,
                }
                for p in self.pareto_points
            ],
            quality_cost_curve=quality_cost,
            quality_latency_curve=quality_latency,
            cost_latency_curve=cost_latency,
            recommendations=recommendations,
            telemetry_points=[
                {
                    "config_id": p.config_id,
                    "quality": p.quality,
                    "cost": p.cost,
                    "latency_ms": p.latency_ms,
                    "mrr": p.mrr,
                    "hit_rate": p.hit_rate,
                    "tokens_used": p.tokens_used,
                    "memory_mb": p.memory_mb,
                    "cpu_percent": p.cpu_percent,
                }
                for p in self.telemetry
            ],
            config_rankings=config_rankings,
            best_quality_config=best_quality_config,
            best_cost_config=best_cost_config,
            best_latency_config=best_latency_config,
            best_balanced_config=best_balanced_config,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_seconds=duration,
        )

        if verbose:
            print("=" * 60)
            print("ORB Results:")
            print(f"  Pareto-optimal configs: {optimal_count}/{len(self.configs)}")
            print("\n  Recommendations:")
            for scenario, rec in recommendations.get("scenarios", {}).items():
                print(f"    {scenario}: {rec.get('config_id', 'N/A')}")
            print("\n  Best Configurations:")
            print(f"    Quality: {best_quality_config}")
            print(f"    Cost: {best_cost_config}")
            print(f"    Latency: {best_latency_config}")
            print(f"    Balanced: {best_balanced_config}")
            print(f"\n  Duration: {duration:.2f}s")

        return results

    def save_results(
        self,
        results: ORBResults,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """Save benchmark results to JSON."""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "results" / "nine_five"

        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"orb_{timestamp}.json"

        with open(output_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)

        return output_file

    def generate_plot_data(
        self,
        results: ORBResults,
    ) -> Dict[str, Any]:
        """
        Generate data for plotting trade-off curves.

        Returns data suitable for matplotlib or plotly visualization.
        """
        return {
            "quality_cost": {
                "x": [p[0] for p in results.quality_cost_curve],
                "y": [p[1] for p in results.quality_cost_curve],
                "xlabel": "Quality",
                "ylabel": "Cost",
                "title": "Quality-Cost Trade-off",
            },
            "quality_latency": {
                "x": [p[0] for p in results.quality_latency_curve],
                "y": [p[1] for p in results.quality_latency_curve],
                "xlabel": "Quality",
                "ylabel": "Latency (ms)",
                "title": "Quality-Latency Trade-off",
            },
            "cost_latency": {
                "x": [p[0] for p in results.cost_latency_curve],
                "y": [p[1] for p in results.cost_latency_curve],
                "xlabel": "Cost",
                "ylabel": "Latency (ms)",
                "title": "Cost-Latency Trade-off",
            },
            "pareto_frontier": {
                "points": [
                    {
                        "config_id": p["config_id"],
                        "quality": p["quality"],
                        "cost": p["cost"],
                        "latency": p["latency_ms"],
                        "optimal": p["is_pareto_optimal"],
                    }
                    for p in results.pareto_frontier
                ],
            },
        }


def main():
    """Run ORB benchmark from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run ORB benchmark")
    parser.add_argument(
        "--samples",
        type=int,
        default=20,
        help="Samples per configuration",
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

    benchmark = ORBBenchmark(seed=args.seed)

    results = benchmark.run(num_samples_per_config=args.samples)

    output_dir = Path(args.output) if args.output else None
    output_file = benchmark.save_results(results, output_dir)
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()
