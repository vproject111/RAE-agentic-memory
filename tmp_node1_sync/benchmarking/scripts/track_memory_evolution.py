#!/usr/bin/env python3
"""
RAE Memory Evolution Tracker

This script inserts memories in batches and tracks how they flow between layers:
Episodic -> Working -> Semantic -> LTM

It generates a visualization showing the occupancy of each layer over time.
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

from apps.memory_api.services.embedding import get_embedding_service
from apps.memory_api.services.memory_consolidation import MemoryConsolidationService
from apps.memory_api.services.rae_core_service import RAECoreService


class EvolutionTracker:
    def __init__(self, benchmark_file: str, kubus_ip: Optional[str] = None):
        self.benchmark_file = Path(benchmark_file)
        self.kubus_ip = kubus_ip
        self.tenant_id = "evolution_test_tenant"
        self.tenant_uuid = UUID("00000000-0000-0000-0000-000000000000")

        # Stats history
        self.history: Dict[str, List[int]] = {
            "step": [],
            "episodic": [],
            "working": [],
            "semantic": [],
            "ltm": [],
        }

    async def setup(self):
        # Database connection
        host = (
            self.kubus_ip if self.kubus_ip else os.getenv("POSTGRES_HOST", "localhost")
        )
        print(f"🔌 Connecting to database at {host}...")

        self.pool = await asyncpg.create_pool(
            host=host,
            user=os.getenv("POSTGRES_USER", "rae"),
            password=os.getenv("POSTGRES_PASSWORD", "rae_password"),
            database=os.getenv("POSTGRES_DB", "rae"),
            min_size=1,
            max_size=5,
        )

        # Cleanup old data for this tenant
        async with self.pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM memories WHERE tenant_id = $1", self.tenant_id
            )

        # Initialize services
        self.rae_service = RAECoreService(self.pool)
        self.consolidation_service = MemoryConsolidationService(self.rae_service)
        self.embedding_service = get_embedding_service()

    async def get_layer_stats(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT layer, COUNT(*) as count
                FROM memories
                WHERE tenant_id = $1
                GROUP BY layer
            """,
                self.tenant_id,
            )

            stats = {row["layer"]: row["count"] for row in rows}
            return stats

    async def run(self, batch_size: int = 50):
        print(f"📂 Loading benchmark: {self.benchmark_file.name}")
        with open(self.benchmark_file, "r") as f:
            data = yaml.safe_load(f)

        memories = data.get("memories", [])
        total = len(memories)
        print(f"📝 Total memories to process: {total}")

        for i in range(0, total, batch_size):
            batch = memories[i : i + batch_size]
            print(f"🚀 Processing batch {i // batch_size + 1} ({i}/{total})...")

            # 1. Insert memories into episodic layer
            for mem in batch:
                content = mem["text"]
                # For this test, we simplify by skipping vector store if needed,
                # but let's do it properly via rae_service if possible
                try:
                    await self.rae_service.store_memory(
                        tenant_id=self.tenant_id,
                        content=content,
                        layer="episodic",  # Start at episodic
                        importance=mem.get("metadata", {}).get("importance", 0.5),
                        source="benchmark",
                        project="default",
                    )
                except Exception as e:
                    print(f"⚠️ Error inserting: {e}")

            # 2. Trigger Consolidation (Force flow between layers)
            # In RAE, consolidation moves: Episodic -> Working -> Semantic -> LTM
            print("🔄 Triggering memory consolidation...")
            try:
                await self.consolidation_service.run_automatic_consolidation(
                    self.tenant_uuid
                )
            except Exception as e:
                print(f"⚠️ Consolidation error: {e}")

            # 3. Collect stats
            stats = await self.get_layer_stats()
            self.history["step"].append(i + len(batch))
            self.history["episodic"].append(stats.get("episodic", 0))
            self.history["working"].append(stats.get("working", 0))
            self.history["semantic"].append(stats.get("semantic", 0))
            self.history["ltm"].append(stats.get("ltm", 0))

    def plot(self):
        print("📊 Generating evolution plot...")
        plt.figure(figsize=(12, 7))

        steps = self.history["step"]
        layers = ["ltm", "semantic", "working", "episodic"]
        data = [self.history[layer] for layer in layers]

        plt.stackplot(steps, data, labels=layers, alpha=0.8)

        plt.title(
            "RAE Memory Layer Evolution Over Time", fontsize=16, fontweight="bold"
        )
        plt.xlabel("Total Memories Ingested", fontsize=12)
        plt.ylabel("Memory Count per Layer", fontsize=12)
        plt.legend(loc="upper left")
        plt.grid(True, alpha=0.3)

        output_file = "benchmarking/plots/memory_evolution.png"
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"✅ Plot saved to: {output_file}")


async def main():
    tracker = EvolutionTracker(
        benchmark_file="benchmarking/sets/industrial_large.yaml",
        kubus_ip="100.66.252.117",
    )
    await tracker.setup()
    await tracker.run(batch_size=100)
    tracker.plot()
    await tracker.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
