#!/usr/bin/env python3
"""
RAE Full Lifecycle Tracker (Time Warp)

This script simulates months of operation in minutes by "warping" time in the database.
It tracks how memories flow all the way to LTM.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

import asyncpg
import matplotlib.pyplot as plt
import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.memory_api.services.memory_consolidation import MemoryConsolidationService
from apps.memory_api.services.rae_core_service import RAECoreService


class FullLifecycleTracker:
    def __init__(self, benchmark_file: str, kubus_ip: Optional[str] = None):
        self.benchmark_file = Path(benchmark_file)
        self.kubus_ip = kubus_ip
        self.tenant_id = "lifecycle_test_tenant"
        self.tenant_uuid = UUID("00000000-0000-0000-0000-000000000001")

        self.history: Dict[str, List[int]] = {
            "step": [],
            "episodic": [],
            "working": [],
            "semantic": [],
            "ltm": [],
        }

    async def setup(self):
        host = (
            self.kubus_ip if self.kubus_ip else os.getenv("POSTGRES_HOST", "localhost")
        )
        print(f"🔌 Connecting to database at {host}...")
        self.pool = await asyncpg.create_pool(
            host=host,
            user=os.getenv("POSTGRES_USER", "rae"),
            password=os.getenv("POSTGRES_PASSWORD", "rae_password"),
            database=os.getenv("POSTGRES_DB", "rae"),
        )
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM memories WHERE tenant_id = $1", self.tenant_id
            )

        self.rae_service = RAECoreService(self.pool)
        self.consolidation_service = MemoryConsolidationService(self.rae_service)

    async def warp_time(self, days: int):
        """Artificially age memories in the database"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE memories
                SET created_at = created_at - interval '1 day' * $1
                WHERE tenant_id = $2
            """,
                days,
                self.tenant_id,
            )

    async def run(self):
        with open(self.benchmark_file, "r") as f:
            data = yaml.safe_load(f)
        memories = data.get("memories", [])[:1000]

        batch_size = 50
        print(f"🚀 Starting lifecycle simulation with {len(memories)} memories...")

        for i in range(0, len(memories), batch_size):
            batch = memories[i : i + batch_size]

            # 1. Insert new memories (today)
            for mem in batch:
                await self.rae_service.store_memory(
                    tenant_id=self.tenant_id,
                    content=mem["text"],
                    layer="episodic",
                    importance=0.9,  # High importance to ensure LTM promotion
                    source="benchmark",
                    project="default",
                )

            # 2. Warp time and consolidate
            # We warp 40 days to exceed all thresholds (7d, 30d)
            print(f"⏩ Warping time +40 days and consolidating (Step {i})...")
            await self.warp_time(40)
            await self.consolidation_service.run_automatic_consolidation(
                self.tenant_uuid
            )

            # 3. Collect stats
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT layer, COUNT(*) as count FROM memories WHERE tenant_id = $1 GROUP BY layer",
                    self.tenant_id,
                )
                stats = {row["layer"]: row["count"] for row in rows}

            self.history["step"].append(i + len(batch))
            for layer in ["episodic", "working", "semantic", "ltm"]:
                self.history[layer].append(stats.get(layer, 0))

    def plot(self):
        plt.figure(figsize=(12, 7))
        layers = ["ltm", "semantic", "working", "episodic"]
        colors = ["#1b4332", "#2d6a4f", "#52b788", "#b7e4c7"]

        data = [self.history[layer] for layer in layers]
        plt.stackplot(
            self.history["step"], data, labels=layers, colors=colors, alpha=0.8
        )

        plt.title(
            "RAE Full Memory Lifecycle (Warped Time)", fontsize=16, fontweight="bold"
        )
        plt.xlabel("Total Memories Processed", fontsize=12)
        plt.ylabel("Memory Count (Consolidated)", fontsize=12)
        plt.legend(loc="upper left")
        plt.grid(True, alpha=0.2)

        output_file = "benchmarking/plots/memory_lifecycle_full.png"
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"✅ Full lifecycle plot saved to: {output_file}")


async def main():
    tracker = FullLifecycleTracker(
        "benchmarking/sets/industrial_large.yaml", "100.66.252.117"
    )
    await tracker.setup()
    await tracker.run()
    tracker.plot()
    await tracker.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
