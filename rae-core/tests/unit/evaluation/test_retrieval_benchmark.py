"""Unit tests for RAE retrieval evaluation and benchmark engine."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from rae_core.evaluation.golden_queries import (
    BenchmarkSummary,
    GoldenQueryCase,
    MetricResult,
    QueryCategory,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_recall_at_k,
    compute_relevance_vector,
    load_golden_queries_from_file,
)
from rae_core.evaluation.retrieval_benchmark import RetrievalBenchmarkEngine

# ==============================================================================
# METRIC CALCULATION TESTS
# ==============================================================================


def test_calculate_recall_at_k():
    # Perfect recall
    rel = [1, 1, 0, 0]
    assert calculate_recall_at_k(rel, k=2, total_expected=2) == 1.0

    # Partial recall
    assert calculate_recall_at_k(rel, k=1, total_expected=2) == 0.5

    # Zero recall
    assert calculate_recall_at_k([0, 0, 0], k=3, total_expected=2) == 0.0

    # Total expected <= 0 edge case
    assert calculate_recall_at_k([], k=5, total_expected=0) == 1.0


def test_calculate_mrr():
    # First hit at rank 1
    assert calculate_mrr([1, 0, 1]) == 1.0

    # First hit at rank 2
    assert calculate_mrr([0, 1, 0]) == 0.5

    # First hit at rank 4
    assert calculate_mrr([0, 0, 0, 1]) == 0.25

    # No hits
    assert calculate_mrr([0, 0, 0]) == 0.0
    assert calculate_mrr([]) == 0.0


def test_calculate_ndcg_at_k():
    # No relevant items
    assert calculate_ndcg_at_k([0, 0, 0], k=3, total_expected=2) == 0.0

    # Perfect ranking (relevant items first)
    score_perfect = calculate_ndcg_at_k([1, 1, 0, 0], k=4, total_expected=2)
    assert pytest.approx(score_perfect, rel=1e-3) == 1.0

    # Suboptimal ranking (relevant items at ranks 2 and 3)
    score_sub = calculate_ndcg_at_k([0, 1, 1, 0], k=4, total_expected=2)
    assert 0.0 < score_sub < 1.0

    # Total expected <= 0
    assert calculate_ndcg_at_k([1], k=1, total_expected=0) == 0.0


def test_compute_relevance_vector():
    uid1 = uuid4()
    uid2 = uuid4()
    uid3 = uuid4()

    # Match by ID
    returned = [(uid1, 0.9), (uid2, 0.7), (uid3, 0.5)]
    rel = compute_relevance_vector(
        returned, expected_sources=[], expected_memory_ids=[uid1, uid3]
    )
    assert rel == [1, 0, 1]

    # Match by source lookup substring
    lookup = {
        uid1: "path/to/HybridSearchEngine.py",
        uid2: "path/to/other.py",
        uid3: "apps/memory_api/services/rae_core_service.py",
    }
    rel_src = compute_relevance_vector(
        returned, expected_sources=["HybridSearchEngine"], item_source_lookup=lookup
    )
    assert rel_src == [1, 0, 0]


# ==============================================================================
# DATA LOADING AND BENCHMARK ENGINE TESTS
# ==============================================================================


def test_load_golden_queries_from_file(tmp_path: Path):
    sample = {
        "queries": [
            {
                "query_id": "test_01",
                "query": "Where is HybridSearchEngine instantiated?",
                "category": "semantic_code",
                "tenant_id": "tenant-1",
                "expected_sources": ["apps/memory_api/services/rae_core_service.py"],
            }
        ]
    }
    file_path = tmp_path / "test_golden.json"
    file_path.write_text(json.dumps(sample), encoding="utf-8")

    cases = load_golden_queries_from_file(file_path)
    assert len(cases) == 1
    assert cases[0].query_id == "test_01"
    assert cases[0].category == QueryCategory.SEMANTIC_CODE


def test_load_golden_queries_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_golden_queries_from_file("non_existent_file_path.json")


@pytest.mark.asyncio
async def test_evaluate_single_case_success():
    uid_target = uuid4()
    uid_other = uuid4()

    async def mock_search(query: str, tenant_id: str, limit: int = 10, **kwargs):
        return [(uid_target, 0.95), (uid_other, 0.40)]

    engine = RetrievalBenchmarkEngine(search_fn=mock_search)
    case = GoldenQueryCase(
        query_id="case_1",
        query="test query",
        category=QueryCategory.EXACT_IDENTIFIER,
        tenant_id="tenant-test",
        expected_memory_ids=[uid_target],
    )

    result = await engine.evaluate_single_case(case, limit=5)
    assert isinstance(result, MetricResult)
    assert result.query_id == "case_1"
    assert result.recall_at_5 == 1.0
    assert result.mrr == 1.0
    assert result.ndcg_at_10 == 1.0
    assert result.empty is False


@pytest.mark.asyncio
async def test_evaluate_single_case_empty():
    async def mock_search_empty(query: str, tenant_id: str, limit: int = 10, **kwargs):
        return []

    engine = RetrievalBenchmarkEngine(search_fn=mock_search_empty)
    case = GoldenQueryCase(
        query_id="case_empty",
        query="nothing",
        category=QueryCategory.CODE_SYMBOL,
        tenant_id="tenant-test",
        expected_sources=["missing"],
    )

    result = await engine.evaluate_single_case(case)
    assert result.empty is True
    assert result.mrr == 0.0
    assert result.recall_at_10 == 0.0


@pytest.mark.asyncio
async def test_evaluate_single_case_error_handling():
    async def mock_search_error(query: str, tenant_id: str, limit: int = 10, **kwargs):
        raise RuntimeError("Database connection timed out")

    engine = RetrievalBenchmarkEngine(search_fn=mock_search_error)
    case = GoldenQueryCase(
        query_id="case_err",
        query="crash",
        category=QueryCategory.HISTORICAL_DECISION,
        tenant_id="tenant-test",
        expected_sources=["some_source"],
    )

    result = await engine.evaluate_single_case(case)
    assert result.empty is True
    assert result.mrr == 0.0


@pytest.mark.asyncio
async def test_run_suite_and_summary(tmp_path: Path):
    uid1 = uuid4()
    uid2 = uuid4()

    async def mock_search(query: str, tenant_id: str, limit: int = 10, **kwargs):
        if "fast" in query:
            return [(uid1, 0.99)]
        return [(uid2, 0.80)]

    engine = RetrievalBenchmarkEngine(search_fn=mock_search, profile="test_profile")
    cases = [
        GoldenQueryCase(
            query_id="c1",
            query="fast query",
            category=QueryCategory.EXACT_IDENTIFIER,
            tenant_id="t1",
            expected_memory_ids=[uid1],
        ),
        GoldenQueryCase(
            query_id="c2",
            query="slow query",
            category=QueryCategory.CODE_SYMBOL,
            tenant_id="t1",
            expected_memory_ids=[uuid4()],  # No match
        ),
    ]

    summary = await engine.run_suite(cases, concurrency=2)
    assert isinstance(summary, BenchmarkSummary)
    assert summary.total_queries == 2
    assert summary.recall_at_10 == 0.5  # 1 hit out of 2 queries
    assert summary.mrr == 0.5
    assert summary.empty_result_rate == 0.0
    assert summary.engine_profile == "test_profile"
    assert "exact_identifier" in summary.category_breakdown
    assert "code_symbol" in summary.category_breakdown

    # Test JSON export
    out_file = tmp_path / "benchmark_summary.json"
    engine.export_report_to_json(summary, out_file)
    assert out_file.exists()
    loaded_data = json.loads(out_file.read_text(encoding="utf-8"))
    assert loaded_data["total_queries"] == 2


@pytest.mark.asyncio
async def test_compare_reranker_gain():
    uid1 = uuid4()

    async def mock_search(
        query: str,
        tenant_id: str,
        limit: int = 10,
        enable_reranking: bool = False,
        **kwargs,
    ):
        # When reranking enabled, put relevant item at rank 1, else at rank 2
        if enable_reranking:
            return [(uid1, 0.95), (uuid4(), 0.50)]
        else:
            return [(uuid4(), 0.90), (uid1, 0.60)]

    engine = RetrievalBenchmarkEngine(search_fn=mock_search)
    cases = [
        GoldenQueryCase(
            query_id="c_gain",
            query="test reranker gain",
            category=QueryCategory.SEMANTIC_CODE,
            tenant_id="t1",
            expected_memory_ids=[uid1],
        )
    ]

    summary = await engine.compare_reranker_gain(cases, limit=5)
    assert summary.reranker_gain > 0.0
