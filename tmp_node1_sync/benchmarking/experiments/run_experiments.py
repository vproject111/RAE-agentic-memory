#!/usr/bin/env python3
"""
RAE Research Experiments Runner

Runs all experimental validations for the mathematical memory model.

Usage:
    python run_experiments.py --experiment structural_stability
    python run_experiments.py --experiment all
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from benchmarking.experiments.exp_drift_dynamics import DriftDynamicsExperiment
from benchmarking.experiments.exp_reflection_gain import ReflectionGainExperiment
from benchmarking.experiments.exp_structural_stability import (
    StructuralStabilityExperiment,
)


class ExperimentRunner:
    """Main experiment runner"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.experiments = {
            "structural_stability": StructuralStabilityExperiment,
            "drift_dynamics": DriftDynamicsExperiment,
            "reflection_gain": ReflectionGainExperiment,
        }

    async def run_experiment(self, experiment_name: str) -> Dict[str, Any]:
        """Run a single experiment"""
        if experiment_name not in self.experiments:
            raise ValueError(f"Unknown experiment: {experiment_name}")

        print(f"\n{'=' * 60}")
        print(f"🧪 Running Experiment: {experiment_name}")
        print(f"{'=' * 60}\n")

        experiment_class = self.experiments[experiment_name]
        experiment = experiment_class(output_dir=self.output_dir)

        try:
            results = await experiment.run()

            # Save results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = self.output_dir / f"{experiment_name}_{timestamp}.json"

            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)

            print("\n✅ Experiment complete!")
            print(f"📊 Results saved to: {results_file}")

            return results

        except Exception as e:
            print(f"\n❌ Experiment failed: {e}")
            import traceback

            traceback.print_exc()
            raise

    async def run_all_experiments(self):
        """Run all experiments sequentially"""
        print("🚀 Running All RAE Mathematical Experiments")
        print(f"Output directory: {self.output_dir}")

        all_results = {}

        for exp_name in self.experiments.keys():
            try:
                results = await self.run_experiment(exp_name)
                all_results[exp_name] = {
                    "status": "success",
                    "results": results,
                }
            except Exception as e:
                all_results[exp_name] = {
                    "status": "failed",
                    "error": str(e),
                }

        # Save summary
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"experiments_summary_{timestamp}.json"

        with open(summary_file, "w") as f:
            json.dump(all_results, f, indent=2)

        print(f"\n📊 Full summary saved to: {summary_file}")

        return all_results


async def main():
    parser = argparse.ArgumentParser(description="Run RAE mathematical experiments")
    parser.add_argument(
        "--experiment",
        type=str,
        default="all",
        help="Experiment to run (structural_stability, drift_dynamics, reflection_gain, all)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="benchmarking/experiments/results",
        help="Output directory for results",
    )

    args = parser.parse_args()

    # Resolve paths
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / args.output

    runner = ExperimentRunner(output_dir=output_dir)

    try:
        if args.experiment == "all":
            await runner.run_all_experiments()
        else:
            await runner.run_experiment(args.experiment)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
