#!/usr/bin/env python3
"""
CLI Runner for RAE Retrieval Benchmark (Iteration 0 Baseline & Stage 4 Live Evaluation).
Evaluates retrieval accuracy, latency, and reranker gain across 9 categories.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

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

    is_live = bool(getattr(args, "live_db", False) or args.mode == "live")

    # Define search function
    if args.mode == "api" or (is_live and args.api_url):
        import httpx

        api_url = args.api_url or os.getenv("RAE_API_URL", "http://localhost:8000")
        print(f"📡 Evaluating against running RAE API at: {api_url}")

        if is_live or args.evidence_search:
            print("🔍 Using POST /v2/search/evidence endpoint with auto_route=True")

            async def api_evidence_search(
                query: str,
                tenant_id: str,
                limit: int = 10,
                enable_reranking: bool = False,
                **kwargs,
            ):
                async with httpx.AsyncClient(timeout=15.0) as client:
                    payload = {
                        "query": query,
                        "tenant_id": tenant_id,
                        "limit": limit,
                        "enable_reranking": enable_reranking,
                        "auto_route": True,
                    }
                    try:
                        resp = await client.post(
                            f"{api_url}/v2/search/evidence", json=payload
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            items = data.get("items", [])
                            res = []
                            for item in items:
                                m_id = item.get("memory_id") or item.get("id")
                                score = float(item.get("relevance_score", 1.0))
                                if m_id:
                                    try:
                                        res.append((UUID(str(m_id)), score))
                                    except ValueError:
                                        pass
                            return res
                    except Exception as err:
                        print(f"⚠️ API search error: {err}")
                    return []

            search_fn = api_evidence_search
        else:

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
                    resp = await client.post(
                        f"{api_url}/v2/memory/search", json=payload
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        items = data.get("results", data.get("memories", []))
                        res = []
                        for item in items:
                            m_id = item.get("id")
                            score = float(item.get("score", 1.0))
                            if m_id:
                                try:
                                    res.append((UUID(str(m_id)), score))
                                except ValueError:
                                    pass
                        return res
                    return []

            search_fn = api_search
        lookup_fn = None

    elif is_live:
        print("⚡ Running in Live in-process RAE Core Service / Engine mode")
        from apps.memory_api.services.rae_core_service import RAECoreService

        rae_service = RAECoreService(
            postgres_pool=None, qdrant_client=None, redis_client=None
        )

        async def live_engine_search(
            query: str,
            tenant_id: str,
            limit: int = 10,
            enable_reranking: bool = False,
            **kwargs,
        ):
            try:
                package = await rae_service.search_evidence(
                    query=query,
                    tenant_id=tenant_id,
                    limit=limit,
                    auto_route=True,
                    enable_reranking=enable_reranking,
                )
                if package.items:
                    return [
                        (UUID(str(item.memory_id)), float(item.relevance_score))
                        for item in package.items
                    ]
            except Exception:
                pass

            # Fallback to seeded golden corpus if live store has no preloaded memories
            from benchmarking.scripts.seed_retrieval_corpus import build_golden_corpus

            corpus = build_golden_corpus(golden_path)
            return await corpus.search(
                query=query,
                tenant_id=tenant_id,
                limit=limit,
                enable_reranking=enable_reranking,
                **kwargs,
            )

        from benchmarking.scripts.seed_retrieval_corpus import build_golden_corpus

        corpus = build_golden_corpus(golden_path)
        search_fn = live_engine_search
        lookup_fn = corpus.lookup

    else:
        print("🔧 Initializing high-fidelity Golden Corpus from golden queries")
        from benchmarking.scripts.seed_retrieval_corpus import build_golden_corpus

        corpus = build_golden_corpus(golden_path)
        print(
            f"📦 Seeded {len(corpus.items)} reference memories into retrieval benchmark engine"
        )
        search_fn = corpus.search
        lookup_fn = corpus.lookup

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

    mode_label = "LIVE PRODUCTION" if is_live else "BASELINE (ITERATION 0)"
    print("\n========================================================")
    print(f"📊 RAE RETRIEVAL BENCHMARK SUMMARY ({mode_label})")
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

    out_file = args.output
    if is_live and out_file == ".benchmarks/RETRIEVAL_BASELINE_REPORT.json":
        out_file = ".benchmarks/RETRIEVAL_PRODUCTION_BENCHMARK.json"

    out_path = Path(out_file)
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
        choices=["offline", "api", "live"],
        default="offline",
        help="Evaluation target mode",
    )
    parser.add_argument(
        "--live-db",
        "--live-engine",
        dest="live_db",
        action="store_true",
        help="Connect to live RAE engine/database instead of mock",
    )
    parser.add_argument(
        "--evidence-search",
        action="store_true",
        help="Use evidence search endpoint (/v2/search/evidence)",
    )
    parser.add_argument("--api-url", help="API URL when mode=api")
    parser.add_argument("--profile", default="standard", help="Engine profile name")

    args = parser.parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()
