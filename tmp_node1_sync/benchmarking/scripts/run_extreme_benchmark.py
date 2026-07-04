#!/usr/bin/env python3
"""
RAE Extreme Scale Benchmark Runner

Optimized for 100k+ memories:
- Batch embedding generation
- Batch DB insertion
- Reduced logging
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.memory_api.services.embedding import get_embedding_service
from benchmarking.scripts.run_benchmark import RAEBenchmarkRunner


class ExtremeBenchmarkRunner(RAEBenchmarkRunner):
    async def insert_memories(self):
        """Insert memories into RAE in large batches"""
        assert self.benchmark_data is not None
        memories = self.benchmark_data["memories"]
        total = len(memories)
        print(f"\n🚀 Inserting {total} memories (EXTREME MODE)...")

        embedding_service = get_embedding_service()
        batch_size = 100

        start_insert_all = time.time()

        for i in range(0, total, batch_size):
            batch = memories[i : i + batch_size]
            batch_start = time.time()

            try:
                # 1. Batch generate embeddings
                texts = [m["text"] for m in batch]
                embeddings = await embedding_service.generate_embeddings_async(texts)

                # 2. Batch insert into PostgreSQL
                # Prepare data for executemany
                insert_data = []
                for m, emb in zip(batch, embeddings):
                    # Convert embedding to string format for pgvector if not registered
                    emb_str = "[" + ",".join(map(str, emb)) + "]"
                    insert_data.append(
                        (
                            self.tenant_id,
                            m["text"],
                            m.get("metadata", {}).get("source", "benchmark"),
                            m.get("metadata", {}).get("importance", 0.5),
                            "ltm",
                            m.get("tags", []),
                            self.project_id,
                            emb_str,
                        )
                    )

                async with self.pool.acquire() as conn:
                    await conn.executemany(
                        """
                        INSERT INTO memories (
                            tenant_id, content, source, importance,
                            layer, tags, project, embedding
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        insert_data,
                    )

                batch_elapsed = time.time() - batch_start
                # Spread elapsed time across batch for metrics
                for _ in range(len(batch)):
                    self.insert_times.append(batch_elapsed / len(batch))

                if (i + len(batch)) % 1000 == 0 or (i + len(batch)) == total:
                    pct = (i + len(batch)) / total * 100
                    elapsed_total = time.time() - start_insert_all
                    eta = (elapsed_total / (i + len(batch))) * (
                        total - (i + len(batch))
                    )
                    print(
                        f"   ✅ Progress: {i + len(batch)}/{total} ({pct:.1f}%) | "
                        f"   Elapsed: {elapsed_total:.1f}s | ETA: {eta:.1f}s"
                    )

            except Exception as e:
                print(f"   ❌ Error in batch starting at {i}: {e}")
                raise

    async def run_queries(self):
        """Run queries sequentially (performance measurement)"""
        assert self.benchmark_data is not None
        queries = self.benchmark_data.get("queries", [])
        print(f"\n🔍 Running {len(queries)} queries...")

        # Silence noisy logs during benchmark
        import logging

        structlog_logger = logging.getLogger(
            "apps.memory_api.services.rae_core_service"
        )
        structlog_logger.setLevel(logging.ERROR)

        # Warm up
        if queries:
            await self._run_single_query(queries[0])

        for i, q in enumerate(queries, 1):
            start_time = time.time()
            results = await self._run_single_query(q)
            elapsed = time.time() - start_time

            self.query_times.append(elapsed)
            # Correct format for calculate_metrics
            self.results.append(
                {"expected": q["expected_source_ids"], "retrieved": results}
            )

            if i % 100 == 0 or i == len(queries):
                print(f"   ✅ Processed {i}/{len(queries)} queries")

    async def _run_single_query(self, query_data: Dict) -> List[str]:
        """Run a single query directly against RAECoreService or via search_service"""
        # For scaling tests, we use the fastest path
        from apps.memory_api.config import settings
        from apps.memory_api.services.rae_core_service import RAECoreService

        # Ensure we use pgvector for this benchmark (as data is inserted only to PG)
        settings.RAE_VECTOR_BACKEND = "pgvector"

        rae_service = RAECoreService(self.pool)

        # Corrected signature: k instead of limit, requires project
        assert self.benchmark_data is not None
        response = await rae_service.query_memories(
            tenant_id=self.tenant_id,
            project=self.project_id,
            query=query_data["query"],
            k=self.benchmark_data["config"].get("top_k", 10),
        )

        return [str(r.memory_id) for r in response.results]


async def main():
    parser = argparse.ArgumentParser(description="Run EXTREME RAE scale benchmarks")
    parser.add_argument("--set", type=str, required=True)
    parser.add_argument("--output", type=str, default="benchmarking/results")
    parser.add_argument(
        "--skip-insert", action="store_true", help="Skip memory insertion phase"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.parent
    benchmark_file = project_root / "benchmarking" / "sets" / args.set
    output_dir = project_root / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 RAE EXTREME Scale Benchmark Runner")
    print("=" * 60)

    runner = ExtremeBenchmarkRunner(
        benchmark_file=benchmark_file, output_dir=output_dir, use_direct_db=True
    )

    try:
        await runner.load_benchmark()
        await runner.setup_database()

        if not args.skip_insert:
            await runner.cleanup_test_data()
            start_time = time.time()
            await runner.insert_memories()
            insert_done = time.time()
            print(f"   Insert Time: {insert_done - start_time:.1f}s")
        else:
            print("   ⏩ Skipping insertion phase (reusing existing data)")
            # Set a dummy tenant id to match what's in the DB if needed,
            # but cleanup_test_data was already called in previous run with default
            insert_done = time.time()

        await runner.run_queries()
        queries_done = time.time()

        metrics = runner.calculate_metrics()
        runner.save_results(metrics)

        print("\n✅ Scale Benchmark Complete!")
        assert runner.benchmark_data is not None
        print(f"   Total Memories: {len(runner.benchmark_data['memories'])}")
        print(f"   Query Time: {queries_done - insert_done:.1f}s")
        print("=" * 60)

    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
