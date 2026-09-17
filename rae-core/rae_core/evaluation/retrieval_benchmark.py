"""Retrieval benchmark engine for RAE search evaluation."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from uuid import UUID

import numpy as np
import structlog

from rae_core.evaluation.golden_queries import (
    BenchmarkSummary,
    GoldenQueryCase,
    MetricResult,
    QueryCategory,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_recall_at_k,
    compute_relevance_vector,
)

logger = structlog.get_logger(__name__)


class RetrievalBenchmarkEngine:
    """Automated benchmark runner for HybridSearchEngine and retrieval components."""

    def __init__(
        self,
        search_fn: Callable[..., Any],
        memory_lookup_fn: Callable[[list[UUID], str], Any] | None = None,
        profile: str = "standard",
    ):
        """
        Initialize the benchmark engine.

        Args:
            search_fn: Async callable taking (query=str, tenant_id=str, limit=int, **kwargs)
                       and returning list of tuples (UUID, float, ...).
            memory_lookup_fn: Optional async callable taking (list[UUID], tenant_id) and returning
                              dict of UUID -> source string (e.g. content or file path).
            profile: Profile name for reporting.
        """
        self.search_fn = search_fn
        self.memory_lookup_fn = memory_lookup_fn
        self.profile = profile

    async def evaluate_single_case(
        self,
        case: GoldenQueryCase,
        limit: int = 10,
        enable_reranking: bool = False,
        **kwargs: Any,
    ) -> MetricResult:
        """Run and evaluate a single golden query case."""
        start_t = time.perf_counter()
        try:
            results = await self.search_fn(
                query=case.query,
                tenant_id=case.tenant_id,
                limit=limit,
                enable_reranking=enable_reranking,
                **kwargs,
            )
        except Exception as e:
            logger.error(
                "search_benchmark_failure", query_id=case.query_id, error=str(e)
            )
            results = []
        latency_ms = (time.perf_counter() - start_t) * 1000.0

        if not results:
            return MetricResult(
                query_id=case.query_id,
                category=case.category,
                recall_at_5=0.0,
                recall_at_10=0.0,
                mrr=0.0,
                ndcg_at_10=0.0,
                latency_ms=latency_ms,
                empty=True,
                wrong_tenant_found=False,
            )

        # Extract returned IDs
        returned_ids = [
            r[0] for r in results if len(r) > 0 and isinstance(r[0], (UUID, str))
        ]
        resolved_ids: list[UUID] = []
        for r_id in returned_ids:
            if isinstance(r_id, UUID):
                resolved_ids.append(r_id)
            elif isinstance(r_id, str):
                try:
                    resolved_ids.append(UUID(r_id))
                except ValueError:
                    pass

        # Source lookup if available
        item_source_lookup: dict[UUID, str] = {}
        if self.memory_lookup_fn and resolved_ids:
            try:
                lookup = await self.memory_lookup_fn(resolved_ids, case.tenant_id)
                if isinstance(lookup, dict):
                    item_source_lookup = lookup
            except Exception as e:
                logger.warning("lookup_failed", error=str(e))

        relevance = compute_relevance_vector(
            returned_items=results,
            expected_sources=case.expected_sources,
            expected_memory_ids=case.expected_memory_ids,
            item_source_lookup=item_source_lookup,
        )

        total_expected = max(
            len(case.expected_sources),
            len(case.expected_memory_ids),
            1,
        )

        recall_5 = calculate_recall_at_k(relevance, k=5, total_expected=total_expected)
        recall_10 = calculate_recall_at_k(
            relevance, k=10, total_expected=total_expected
        )
        mrr = calculate_mrr(relevance)
        ndcg_10 = calculate_ndcg_at_k(relevance, k=10, total_expected=total_expected)

        # Check for forbidden sources (e.g. wrong tenant contamination)
        wrong_tenant_found = False
        if case.forbidden_sources and item_source_lookup:
            for src in case.forbidden_sources:
                for content in item_source_lookup.values():
                    if src.lower() in content.lower():
                        wrong_tenant_found = True
                        break

        return MetricResult(
            query_id=case.query_id,
            category=case.category,
            recall_at_5=recall_5,
            recall_at_10=recall_10,
            mrr=mrr,
            ndcg_at_10=ndcg_10,
            latency_ms=latency_ms,
            empty=False,
            wrong_tenant_found=wrong_tenant_found,
        )

    async def run_suite(
        self,
        cases: list[GoldenQueryCase],
        limit: int = 10,
        enable_reranking: bool = False,
        concurrency: int = 5,
        **kwargs: Any,
    ) -> BenchmarkSummary:
        """Run the full benchmark suite with concurrency control."""
        if not cases:
            raise ValueError("Golden query cases list is empty")

        semaphore = asyncio.Semaphore(concurrency)

        async def _eval_with_sem(case: GoldenQueryCase) -> MetricResult:
            async with semaphore:
                return await self.evaluate_single_case(
                    case, limit=limit, enable_reranking=enable_reranking, **kwargs
                )

        tasks = [_eval_with_sem(case) for case in cases]
        results = await asyncio.gather(*tasks)

        # Aggregate metrics
        recalls_5 = [r.recall_at_5 for r in results]
        recalls_10 = [r.recall_at_10 for r in results]
        mrrs = [r.mrr for r in results]
        ndcgs_10 = [r.ndcg_at_10 for r in results]
        latencies = [r.latency_ms for r in results]
        empties = sum(1 for r in results if r.empty)
        wrong_tenants = sum(1 for r in results if r.wrong_tenant_found)

        # Category breakdown
        breakdown: dict[str, dict[str, float]] = {}
        for cat in QueryCategory:
            cat_results = [r for r in results if r.category == cat]
            if cat_results:
                breakdown[cat.value] = {
                    "count": float(len(cat_results)),
                    "recall_at_5": float(np.mean([r.recall_at_5 for r in cat_results])),
                    "recall_at_10": float(
                        np.mean([r.recall_at_10 for r in cat_results])
                    ),
                    "mrr": float(np.mean([r.mrr for r in cat_results])),
                    "ndcg_at_10": float(np.mean([r.ndcg_at_10 for r in cat_results])),
                    "latency_avg_ms": float(
                        np.mean([r.latency_ms for r in cat_results])
                    ),
                }

        p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
        p95 = float(np.percentile(latencies, 95)) if latencies else 0.0

        summary = BenchmarkSummary(
            total_queries=len(results),
            recall_at_5=float(np.mean(recalls_5)),
            recall_at_10=float(np.mean(recalls_10)),
            mrr=float(np.mean(mrrs)),
            ndcg_at_10=float(np.mean(ndcgs_10)),
            latency_p50_ms=p50,
            latency_p95_ms=p95,
            reranker_gain=0.0,
            empty_result_rate=float(empties) / float(len(results)),
            wrong_tenant_count=wrong_tenants,
            category_breakdown=breakdown,
            timestamp=datetime.now(timezone.utc).isoformat(),
            engine_profile=self.profile,
        )
        return summary

    async def compare_reranker_gain(
        self,
        cases: list[GoldenQueryCase],
        limit: int = 10,
        concurrency: int = 5,
    ) -> BenchmarkSummary:
        """Run benchmark without and with reranking to compute reranker_gain."""
        summary_base = await self.run_suite(
            cases=cases, limit=limit, enable_reranking=False, concurrency=concurrency
        )
        summary_rerank = await self.run_suite(
            cases=cases, limit=limit, enable_reranking=True, concurrency=concurrency
        )

        gain = 0.0
        if summary_base.ndcg_at_10 > 0.0:
            gain = (
                (summary_rerank.ndcg_at_10 - summary_base.ndcg_at_10)
                / summary_base.ndcg_at_10
            ) * 100.0

        summary_rerank.reranker_gain = gain
        return summary_rerank

    @staticmethod
    def export_report_to_json(
        summary: BenchmarkSummary, output_path: str | Path
    ) -> None:
        """Export summary to JSON file."""
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(summary.model_dump_json(indent=2))
        logger.info("benchmark_report_exported", path=str(p))
