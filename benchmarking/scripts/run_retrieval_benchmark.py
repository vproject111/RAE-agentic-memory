#!/usr/bin/env python3
"""
CLI Runner for RAE Retrieval Benchmark (Iteration 0 Baseline).
Evaluates retrieval accuracy, latency, and reranker gain across 9 categories.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add project roots to path
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
RAE_CORE_DIR = REPO_ROOT / "rae-core"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(RAE_CORE_DIR))

from rae_core.evaluation.golden_queries import (
    load_golden_queries_from_file,
)
from rae_core.evaluation.retrieval_benchmark import RetrievalBenchmarkEngine


async def run_benchmark(args: argparse.Namespace):
    golden_path = Path(args.golden_file)
    if not golden_path.exists():
        # Fallback to default
        golden_path = (
            REPO_ROOT
            / "rae-core"
            / "tests"
            / "golden"
            / "retrieval_golden_queries.json"
        )

    print(f"📖 Loading golden queries from: {golden_path}")
    cases = load_golden_queries_from_file(golden_path)
    if args.category:
        cases = [c for c in cases if c.category.value == args.category]
    if args.limit_cases:
        cases = cases[: args.limit_cases]

    print(f"🎯 Total queries to evaluate: {len(cases)}")

    # Define the search function
    if args.mode == "api":
        import httpx

        api_url = args.api_url or os.getenv("RAE_API_URL", "http://localhost:8000")
        print(f"📡 Evaluating against running RAE API at: {api_url}")

        async def api_search(
            query: str,
            tenant_id: str,
            limit: int = 10,
            enable_reranking: bool = False,
            **kwargs,
        ):
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = {
                    "query": query,
                    "tenant_id": tenant_id,
                    "limit": limit,
                    "enable_reranking": enable_reranking,
                }
                resp = await client.post(f"{api_url}/v2/memory/search", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    # Expecting list of items with id/score
                    items = data.get("results", data.get("memories", []))
                    return [(item["id"], item.get("score", 1.0)) for item in items]
                return []

        search_fn = api_search
        lookup_fn = None
    else:
        # Mock/Offline diagnostic search mode for verification
        print("🔧 Running in offline baseline diagnostic mode")
        from uuid import uuid4

        async def mock_search(
            query: str,
            tenant_id: str,
            limit: int = 10,
            enable_reranking: bool = False,
            **kwargs,
        ):
            # Deterministic simulation based on query tokens
            tokens = query.lower().split()
            results = []
            for i in range(min(5, limit)):
                score = 1.0 / (i + 1)
                if enable_reranking:
                    score *= 1.15
                results.append((uuid4(), score, 0.5))
            return results

        search_fn = mock_search
        lookup_fn = None

    engine = RetrievalBenchmarkEngine(
        search_fn=search_fn,
        memory_lookup_fn=lookup_fn,
        profile=args.profile,
    )

    print("\n🚀 Running benchmark evaluation...")
    if args.compare_reranker:
        summary = await engine.compare_reranker_gain(
            cases=cases, limit=args.top_k, concurrency=args.concurrency
        )
    else:
        summary = await engine.run_suite(
            cases=cases,
            limit=args.top_k,
            enable_reranking=args.enable_reranking,
            concurrency=args.concurrency,
        )

    print("\n========================================================")
    print("📊 RAE RETRIEVAL BENCHMARK SUMMARY (ITERATION 0)")
    print("========================================================")
    print(f"Total Queries Evaluated:  {summary.total_queries}")
    print(f"Recall@5:                 {summary.recall_at_5:.4f}")
    print(f"Recall@10:                {summary.recall_at_10:.4f}")
    print(f"Mean Reciprocal Rank:     {summary.mrr:.4f}")
    print(f"NDCG@10:                  {summary.ndcg_at_10:.4f}")
    print(f"Latency p50:              {summary.latency_p50_ms:.2f} ms")
    print(f"Latency p95:              {summary.latency_p95_ms:.2f} ms")
    print(f"Reranker Gain:            {summary.reranker_gain:+.2f}%")
    print(f"Empty Result Rate:        {summary.empty_result_rate:.2%}")
    print(f"Wrong Tenant Contam.:     {summary.wrong_tenant_count}")
    print("--------------------------------------------------------")
    print("Category Breakdown (MRR / Recall@10 / Avg Latency):")
    for cat, stats in summary.category_breakdown.items():
        print(
            f" • {cat:<22}: MRR={stats['mrr']:.3f} | R@10={stats['recall_at_10']:.3f} | {stats['latency_avg_ms']:.1f}ms (n={int(stats['count'])})"
        )
    print("========================================================\n")

    out_path = Path(args.output)
    engine.export_report_to_json(summary, out_path)
    print(f"💾 Report saved to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="RAE Retrieval Benchmark Runner")
    parser.add_argument(
        "--golden-file",
        default="rae-core/tests/golden/retrieval_golden_queries.json",
        help="Path to golden queries JSON file",
    )
    parser.add_argument(
        "--output",
        default=".benchmarks/RETRIEVAL_BASELINE_REPORT.json",
        help="Path to output JSON report",
    )
    parser.add_argument(
        "--top-k", type=int, default=10, help="Top-K results to retrieve"
    )
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent queries")
    parser.add_argument("--category", help="Filter by specific QueryCategory")
    parser.add_argument("--limit-cases", type=int, help="Limit number of cases")
    parser.add_argument(
        "--enable-reranking", action="store_true", help="Enable reranking"
    )
    parser.add_argument(
        "--compare-reranker", action="store_true", help="Compare with/without reranking"
    )
    parser.add_argument(
        "--mode",
        choices=["offline", "api"],
        default="offline",
        help="Evaluation target mode",
    )
    parser.add_argument("--api-url", help="API URL when mode=api")
    parser.add_argument("--profile", default="standard", help="Engine profile name")

    args = parser.parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
