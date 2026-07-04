#!/usr/bin/env python3
"""
RAE Latency Profiler

Performs detailed latency profiling of RAE memory queries:
- Multiple runs for statistical significance
- Latency distribution analysis
- Percentile measurements (P50, P95, P99)
- Outlier detection
- Performance regression detection

Usage:
    python profile_latency.py --query "search query" --runs 100
    python profile_latency.py --benchmark academic_lite.yaml --runs 50
"""

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, cast

import asyncpg
import numpy as np
import yaml

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.memory_api.services.embedding import get_embedding_service


class LatencyProfiler:
    """Profile query latency with statistical analysis"""

    def __init__(self, db_pool: asyncpg.Pool):
        # Lazy import to avoid initialization issues in test environments
        from apps.memory_api.services.vector_store import get_vector_store

        self.pool = db_pool
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store(db_pool)
        self.results: List[Dict[str, Any]] = []

    async def profile_single_query(
        self, query_text: str, tenant_id: str, top_k: int = 5, num_runs: int = 100
    ) -> Dict:
        """
        Profile a single query multiple times

        Args:
            query_text: The search query
            tenant_id: Tenant identifier
            top_k: Number of results to retrieve
            num_runs: Number of times to run the query

        Returns:
            Dict with latency statistics
        """
        print(f"\n🔍 Profiling query: '{query_text}'")
        print(f"   Runs: {num_runs}")
        print(f"   Top-k: {top_k}")

        latencies = []
        embedding_times = []
        search_times = []

        for i in range(num_runs):
            # Measure embedding generation
            embed_start = time.perf_counter()
            query_embedding = self.embedding_service.generate_embeddings([query_text])[
                0
            ]
            embed_time = time.perf_counter() - embed_start
            embedding_times.append(embed_time * 1000)  # Convert to ms

            # Measure vector search
            search_start = time.perf_counter()
            await self.vector_store.search(  # type: ignore
                tenant_id=tenant_id, query_embedding=query_embedding, top_k=top_k
            )
            search_time = time.perf_counter() - search_start
            search_times.append(search_time * 1000)  # Convert to ms

            # Total latency
            total_latency = embed_time + search_time
            latencies.append(total_latency * 1000)  # Convert to ms

            if (i + 1) % 20 == 0:
                print(f"   Progress: {i + 1}/{num_runs} runs completed")

        # Calculate statistics
        latencies_np = np.array(latencies)
        embedding_np = np.array(embedding_times)
        search_np = np.array(search_times)

        stats: Dict[str, Any] = {
            "query": query_text,
            "num_runs": num_runs,
            "total_latency": {
                "mean": float(np.mean(latencies_np)),
                "median": float(np.median(latencies_np)),
                "std": float(np.std(latencies_np)),
                "min": float(np.min(latencies_np)),
                "max": float(np.max(latencies_np)),
                "p50": float(np.percentile(latencies_np, 50)),
                "p90": float(np.percentile(latencies_np, 90)),
                "p95": float(np.percentile(latencies_np, 95)),
                "p99": float(np.percentile(latencies_np, 99)),
            },
            "embedding_time": {
                "mean": float(np.mean(embedding_np)),
                "p95": float(np.percentile(embedding_np, 95)),
            },
            "search_time": {
                "mean": float(np.mean(search_np)),
                "p95": float(np.percentile(search_np, 95)),
            },
            "breakdown": {
                "embedding_pct": float(
                    cast(float, np.mean(embedding_np) / np.mean(latencies_np) * 100)
                ),
                "search_pct": float(
                    cast(float, np.mean(search_np) / np.mean(latencies_np) * 100)
                ),
            },
        }

        # Detect outliers (> 2 std deviations)
        mean = stats["total_latency"]["mean"]
        std = stats["total_latency"]["std"]
        outliers = latencies_np[np.abs(latencies_np - mean) > 2 * std]
        stats["outliers"] = {
            "count": len(outliers),
            "percentage": float(len(outliers) / num_runs * 100),
            "values": outliers.tolist() if len(outliers) > 0 else [],
        }

        return stats

    async def profile_benchmark(
        self, benchmark_file: Path, num_runs_per_query: int = 50
    ) -> Dict:
        """
        Profile all queries in a benchmark file

        Args:
            benchmark_file: Path to benchmark YAML file
            num_runs_per_query: Number of runs per query

        Returns:
            Dict with all query profiles
        """
        print(f"\n📂 Loading benchmark: {benchmark_file.name}")

        with open(benchmark_file, "r") as f:
            benchmark_data = yaml.safe_load(f)

        queries = benchmark_data.get("queries", [])
        tenant_id = "latency_profile_tenant"

        print(f"   Queries to profile: {len(queries)}")

        all_profiles = []

        for idx, query_data in enumerate(queries, 1):
            query_text = query_data["query"]
            print(f"\n[{idx}/{len(queries)}] Processing: {query_text[:50]}...")

            profile = await self.profile_single_query(
                query_text=query_text, tenant_id=tenant_id, num_runs=num_runs_per_query
            )

            profile["query_index"] = idx
            profile["difficulty"] = query_data.get("difficulty", "unknown")
            all_profiles.append(profile)

        # Aggregate statistics
        all_means = [p["total_latency"]["mean"] for p in all_profiles]
        all_p95s = [p["total_latency"]["p95"] for p in all_profiles]

        aggregated = {
            "benchmark": benchmark_data["name"],
            "num_queries": len(queries),
            "num_runs_per_query": num_runs_per_query,
            "total_measurements": len(queries) * num_runs_per_query,
            "aggregate_stats": {
                "mean_of_means": float(np.mean(all_means)),
                "mean_of_p95s": float(np.mean(all_p95s)),
                "fastest_query_mean": float(np.min(all_means)),
                "slowest_query_mean": float(np.max(all_means)),
            },
            "queries": all_profiles,
        }

        return aggregated

    def print_summary(self, stats: Dict):
        """Print human-readable summary"""
        print("\n" + "=" * 70)
        print("LATENCY PROFILE SUMMARY")
        print("=" * 70)

        if "total_latency" in stats:
            # Single query profile
            total = stats["total_latency"]
            print(f"\nQuery: {stats['query']}")
            print(f"Runs: {stats['num_runs']}")
            print("\nTotal Latency:")
            print(f"  Mean:   {total['mean']:>8.2f} ms")
            print(f"  Median: {total['median']:>8.2f} ms")
            print(f"  Std:    {total['std']:>8.2f} ms")
            print(f"  Min:    {total['min']:>8.2f} ms")
            print(f"  Max:    {total['max']:>8.2f} ms")
            print("\nPercentiles:")
            print(f"  P50:    {total['p50']:>8.2f} ms")
            print(f"  P90:    {total['p90']:>8.2f} ms")
            print(f"  P95:    {total['p95']:>8.2f} ms")
            print(f"  P99:    {total['p99']:>8.2f} ms")

            print("\nBreakdown:")
            print(
                f"  Embedding: {stats['breakdown']['embedding_pct']:>6.1f}% "
                f"({stats['embedding_time']['mean']:>6.2f} ms avg)"
            )
            print(
                f"  Search:    {stats['breakdown']['search_pct']:>6.1f}% "
                f"({stats['search_time']['mean']:>6.2f} ms avg)"
            )

            print("\nOutliers (>2σ):")
            print(
                f"  Count: {stats['outliers']['count']} ({stats['outliers']['percentage']:.1f}%)"
            )

        else:
            # Benchmark profile
            agg = stats["aggregate_stats"]
            print(f"\nBenchmark: {stats['benchmark']}")
            print(f"Queries: {stats['num_queries']}")
            print(f"Runs per query: {stats['num_runs_per_query']}")
            print(f"Total measurements: {stats['total_measurements']}")
            print("\nAggregate Statistics:")
            print(f"  Mean of query means: {agg['mean_of_means']:.2f} ms")
            print(f"  Mean of P95s:        {agg['mean_of_p95s']:.2f} ms")
            print(f"  Fastest query:       {agg['fastest_query_mean']:.2f} ms")
            print(f"  Slowest query:       {agg['slowest_query_mean']:.2f} ms")

        print("=" * 70)

    def save_results(self, stats: Dict, output_file: Path):
        """Save results to JSON file"""
        output_data = {"timestamp": datetime.now().isoformat(), "profile": stats}

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\n💾 Results saved to: {output_file}")

    async def cleanup(self):
        """Cleanup resources"""
        if self.pool:
            await self.pool.close()


async def main():
    parser = argparse.ArgumentParser(description="Profile RAE query latency")
    parser.add_argument("--query", type=str, help="Single query to profile")
    parser.add_argument("--benchmark", type=str, help="Benchmark YAML file to profile")
    parser.add_argument(
        "--runs", type=int, default=100, help="Number of runs per query"
    )
    parser.add_argument(
        "--top-k", type=int, default=5, help="Number of results to retrieve"
    )
    parser.add_argument("--output", type=str, help="Output JSON file")

    args = parser.parse_args()

    if not args.query and not args.benchmark:
        print("❌ Error: Must specify either --query or --benchmark")
        sys.exit(1)

    # Setup database connection
    import os

    db_config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", 5432)),
        "database": os.getenv("POSTGRES_DB", "rae_memory"),
        "user": os.getenv("POSTGRES_USER", "rae_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "rae_password"),
    }

    pool = await asyncpg.create_pool(**db_config, min_size=2, max_size=5)

    profiler = LatencyProfiler(pool)

    try:
        if args.query:
            # Profile single query
            stats = await profiler.profile_single_query(
                query_text=args.query,
                tenant_id="latency_profile_tenant",
                top_k=args.top_k,
                num_runs=args.runs,
            )
        else:
            # Profile benchmark
            project_root = Path(__file__).parent.parent.parent
            benchmark_file = project_root / "benchmarking" / "sets" / args.benchmark
            stats = await profiler.profile_benchmark(
                benchmark_file=benchmark_file, num_runs_per_query=args.runs
            )

        # Print summary
        profiler.print_summary(stats)

        # Save results if output specified
        if args.output:
            output_path = Path(args.output)
            profiler.save_results(stats, output_path)

        print("\n✅ Profiling complete!")

    except Exception as e:
        print(f"\n❌ Profiling failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        await profiler.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
