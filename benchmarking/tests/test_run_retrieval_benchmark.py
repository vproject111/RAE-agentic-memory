"""Tests for benchmarking/scripts/run_retrieval_benchmark.py."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pytest

# Ensure repo root and rae-core are on sys.path
CURRENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = CURRENT_DIR.parents[1]
RAE_CORE_DIR = REPO_ROOT / "rae-core"
SCRIPTS_DIR = CURRENT_DIR.parent / "scripts"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(RAE_CORE_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from run_retrieval_benchmark import run_benchmark


@pytest.mark.asyncio
async def test_run_retrieval_benchmark_offline_mode(tmp_path):
    output_file = tmp_path / "test_report.json"
    args = argparse.Namespace(
        golden_file=str(
            REPO_ROOT
            / "rae-core"
            / "tests"
            / "golden"
            / "retrieval_golden_queries.json"
        ),
        output=str(output_file),
        top_k=5,
        concurrency=2,
        category=None,
        limit_cases=3,
        enable_reranking=False,
        compare_reranker=False,
        mode="offline",
        live_db=False,
        live_engine=False,
        evidence_search=False,
        api_url=None,
        profile="standard",
    )

    await run_benchmark(args)
    assert output_file.exists()
    import json

    with open(output_file, "r") as f:
        data = json.load(f)
    assert data["total_queries"] == 3
    assert "category_breakdown" in data


@pytest.mark.asyncio
async def test_run_retrieval_benchmark_live_engine_mode(tmp_path):
    output_file = tmp_path / "test_live_report.json"
    args = argparse.Namespace(
        golden_file=str(
            REPO_ROOT
            / "rae-core"
            / "tests"
            / "golden"
            / "retrieval_golden_queries.json"
        ),
        output=str(output_file),
        top_k=5,
        concurrency=2,
        category="exact_identifier",
        limit_cases=2,
        enable_reranking=False,
        compare_reranker=False,
        mode="offline",
        live_db=True,
        live_engine=True,
        evidence_search=False,
        api_url=None,
        profile="standard",
    )

    await run_benchmark(args)
    assert output_file.exists()
    import json

    with open(output_file, "r") as f:
        data = json.load(f)
    assert data["total_queries"] == 2
    assert "exact_identifier" in data["category_breakdown"]
