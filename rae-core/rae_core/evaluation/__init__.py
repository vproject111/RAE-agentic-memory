"""Evaluation and benchmarking module for RAE retrieval."""

from rae_core.evaluation.golden_queries import (
    BenchmarkSummary,
    GoldenQueryCase,
    MetricResult,
    QueryCategory,
)
from rae_core.evaluation.retrieval_benchmark import RetrievalBenchmarkEngine

__all__ = [
    "QueryCategory",
    "GoldenQueryCase",
    "MetricResult",
    "BenchmarkSummary",
    "RetrievalBenchmarkEngine",
]
