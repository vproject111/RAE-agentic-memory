"""
Experiment 2: Drift Dynamics Test

Tests semantic and structural drift over time.

Procedure:
1. Create snapshot t0
2. Run 100 queries (simulated interactions)
3. Create snapshot t1
4. Calculate: MDI, Structural Drift, Retention Curve

Expected Results:
- Low drift (< 0.3) indicating stability
- Maintained structural coherence
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from benchmarking.experiments.exp_structural_stability import (
    StructuralStabilityExperiment,
)
from benchmarking.math_metrics import (
    MemoryDriftIndex,
    StructuralDriftMetric,
)


class DriftDynamicsExperiment(StructuralStabilityExperiment):
    """Drift dynamics experiment implementation"""

    def __init__(self, output_dir: Path):
        super().__init__(output_dir)
        self.tenant_id = "exp_drift_dynamics"

        # Drift metrics
        self.mdi_metric = MemoryDriftIndex()
        self.drift_metric = StructuralDriftMetric()

    async def simulate_queries(self, num_queries: int = 50):
        """Simulate memory queries (without actual retrieval)"""
        print(f"   Simulating {num_queries} queries...")
        # In full implementation, this would:
        # - Run actual search queries
        # - Trigger memory updates
        # - Potentially run reflections
        # For now, we just simulate passage of time
        await asyncio.sleep(0.1)

    async def run(self) -> Dict[str, Any]:
        """Run the drift dynamics experiment"""
        print("🔬 Drift Dynamics Experiment")
        print("Testing memory drift over interactions")

        await self.setup_database()

        try:
            # Clean up
            assert self.pool is not None
            async with self.pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM memories WHERE tenant_id = $1", self.tenant_id
                )

            # Insert initial memories
            print("\n📌 Phase 1: Initial State")
            await self.insert_test_memories(30, prefix="initial")
            snapshot_t0 = await self.capture_snapshot()
            print(f"   ✅ Snapshot t0: {snapshot_t0.num_memories} memories")

            # Simulate interactions
            print("\n📌 Phase 2: Simulated Interactions")
            await self.simulate_queries(100)

            # Add some new memories (simulating memory updates)
            await self.insert_test_memories(5, prefix="updated")

            snapshot_t1 = await self.capture_snapshot()
            print(f"   ✅ Snapshot t1: {snapshot_t1.num_memories} memories")

            # Calculate drift metrics
            print("\n📊 Calculating drift metrics...")
            mdi = self.mdi_metric.calculate(snapshot_t0, snapshot_t1)
            structural_drift = self.drift_metric.calculate(snapshot_t0, snapshot_t1)

            print(f"   Memory Drift Index (MDI): {mdi:.4f}")
            print(f"   Structural Drift: {structural_drift:.4f}")

            # Results
            results = {
                "experiment": "drift_dynamics",
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "initial_memories": 30,
                    "added_memories": 5,
                    "simulated_queries": 100,
                },
                "drift_metrics": {
                    "memory_drift_index": mdi,
                    "structural_drift": structural_drift,
                },
                "snapshots": {
                    "t0": snapshot_t0.to_dict(),
                    "t1": snapshot_t1.to_dict(),
                },
                "conclusion": self._analyze_drift(mdi, structural_drift),
            }

            return results

        finally:
            await self.cleanup_database()

    def _analyze_drift(self, mdi: float, structural_drift: float) -> str:
        """Analyze drift results"""
        conclusions = []

        if mdi < 0.3:
            conclusions.append("✅ Low semantic drift - stable memory content")
        else:
            conclusions.append("⚠️ High semantic drift - significant content changes")

        if structural_drift < 0.3:
            conclusions.append("✅ Low structural drift - stable graph topology")
        else:
            conclusions.append(
                "⚠️ High structural drift - significant structural changes"
            )

        return " | ".join(conclusions)
