"""
Tests for run_benchmark.py

Tests cover:
- Benchmark metrics calculation
- YAML loading
- Result formatting
- Error handling
"""

# Mock problematic imports before importing run_benchmark
import sys
from pathlib import Path
from typing import List, Tuple
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Mock the problematic imports
sys.modules["apps.memory_api.services.embedding"] = Mock()
sys.modules["apps.memory_api.services.vector_store"] = Mock()

from run_benchmark import BenchmarkMetrics  # noqa: E402


class TestBenchmarkMetrics:
    """Test benchmark metric calculations"""

    def test_calculate_mrr_perfect_score(self):
        """Test MRR calculation with perfect results (all rank 1)"""
        # All expected docs appear at rank 1
        results = [
            (["doc1"], ["doc1", "doc2", "doc3"]),
            (["doc2"], ["doc2", "doc1", "doc3"]),
            (["doc3"], ["doc3", "doc1", "doc2"]),
        ]

        mrr = BenchmarkMetrics.calculate_mrr(results)
        assert mrr == 1.0, "MRR should be 1.0 when all results are at rank 1"

    def test_calculate_mrr_mixed_ranks(self):
        """Test MRR calculation with mixed result ranks"""
        results = [
            (["doc1"], ["doc1", "doc2", "doc3"]),  # Rank 1: RR = 1.0
            (["doc2"], ["doc1", "doc2", "doc3"]),  # Rank 2: RR = 0.5
            (["doc3"], ["doc1", "doc2", "doc3"]),  # Rank 3: RR = 0.333
        ]

        mrr = BenchmarkMetrics.calculate_mrr(results)
        expected_mrr = (1.0 + 0.5 + 0.333) / 3
        assert abs(mrr - expected_mrr) < 0.01, f"MRR should be {expected_mrr:.3f}"

    def test_calculate_mrr_no_results(self):
        """Test MRR calculation when no relevant results found"""
        results = [
            (["doc1"], ["doc2", "doc3", "doc4"]),  # No match: RR = 0
            (["doc2"], ["doc3", "doc4", "doc5"]),  # No match: RR = 0
        ]

        mrr = BenchmarkMetrics.calculate_mrr(results)
        assert mrr == 0.0, "MRR should be 0.0 when no relevant results found"

    def test_calculate_mrr_multiple_expected(self):
        """Test MRR calculation with multiple expected documents"""
        results = [
            (["doc1", "doc2"], ["doc3", "doc2", "doc1"]),  # First match at rank 2
            (["doc3", "doc4"], ["doc1", "doc3", "doc2"]),  # First match at rank 2
        ]

        mrr = BenchmarkMetrics.calculate_mrr(results)
        expected_mrr = (0.5 + 0.5) / 2
        assert abs(mrr - expected_mrr) < 0.01, f"MRR should be {expected_mrr:.3f}"

    def test_calculate_hit_rate_perfect(self):
        """Test Hit Rate@5 with all queries having hits"""
        results = [
            (["doc1"], ["doc1", "doc2", "doc3", "doc4", "doc5"]),
            (["doc2"], ["doc2", "doc1", "doc3", "doc4", "doc5"]),
            (["doc3"], ["doc3", "doc1", "doc2", "doc4", "doc5"]),
        ]

        hit_rate = BenchmarkMetrics.calculate_hit_rate(results, k=5)
        assert hit_rate == 1.0, "Hit rate should be 1.0 when all queries have hits"

    def test_calculate_hit_rate_partial(self):
        """Test Hit Rate@5 with some queries missing hits"""
        results = [
            (["doc1"], ["doc1", "doc2", "doc3", "doc4", "doc5"]),  # Hit
            (["doc2"], ["doc3", "doc4", "doc5", "doc6", "doc7"]),  # No hit
            (["doc3"], ["doc3", "doc1", "doc2", "doc4", "doc5"]),  # Hit
            (["doc4"], ["doc5", "doc6", "doc7", "doc8", "doc9"]),  # No hit
        ]

        hit_rate = BenchmarkMetrics.calculate_hit_rate(results, k=5)
        assert hit_rate == 0.5, "Hit rate should be 0.5 (2 out of 4 queries)"

    def test_calculate_hit_rate_at_different_k(self):
        """Test Hit Rate at different k values"""
        results = [
            (["doc1"], ["doc2", "doc3", "doc1", "doc4", "doc5"]),  # At rank 3
        ]

        hit_rate_3 = BenchmarkMetrics.calculate_hit_rate(results, k=3)
        hit_rate_2 = BenchmarkMetrics.calculate_hit_rate(results, k=2)

        assert hit_rate_3 == 1.0, "Should find hit at k=3"
        assert hit_rate_2 == 0.0, "Should not find hit at k=2"

    def test_calculate_precision_at_k_perfect(self):
        """Test Precision@5 with all relevant results"""
        results = [
            (["doc1", "doc2", "doc3"], ["doc1", "doc2", "doc3", "doc4", "doc5"]),  # 3/5
            (["doc1", "doc2"], ["doc1", "doc2", "doc3", "doc4", "doc5"]),  # 2/5
        ]

        precision = BenchmarkMetrics.calculate_precision_at_k(results, k=5)
        expected_precision = ((3 / 5) + (2 / 5)) / 2
        assert (
            abs(precision - expected_precision) < 0.01
        ), f"Precision should be {expected_precision:.3f}"

    def test_calculate_precision_at_k_no_relevant(self):
        """Test Precision@5 with no relevant results"""
        results = [
            (["doc1"], ["doc2", "doc3", "doc4", "doc5", "doc6"]),
            (["doc2"], ["doc3", "doc4", "doc5", "doc6", "doc7"]),
        ]

        precision = BenchmarkMetrics.calculate_precision_at_k(results, k=5)
        assert precision == 0.0, "Precision should be 0.0 when no relevant results"

    def test_calculate_recall_at_k_perfect(self):
        """Test Recall@5 with all expected docs retrieved"""
        results = [
            (["doc1", "doc2"], ["doc1", "doc2", "doc3", "doc4", "doc5"]),  # 2/2 = 1.0
            (
                ["doc1", "doc2", "doc3"],
                ["doc1", "doc2", "doc3", "doc4", "doc5"],
            ),  # 3/3 = 1.0
        ]

        recall = BenchmarkMetrics.calculate_recall_at_k(results, k=5)
        assert recall == 1.0, "Recall should be 1.0 when all expected docs retrieved"

    def test_calculate_recall_at_k_partial(self):
        """Test Recall@5 with partial coverage"""
        results = [
            (["doc1", "doc2", "doc3"], ["doc1", "doc4", "doc5", "doc6", "doc7"]),  # 1/3
            (["doc1", "doc2"], ["doc1", "doc2", "doc3", "doc4", "doc5"]),  # 2/2
        ]

        recall = BenchmarkMetrics.calculate_recall_at_k(results, k=5)
        expected_recall = ((1 / 3) + (2 / 2)) / 2
        assert (
            abs(recall - expected_recall) < 0.01
        ), f"Recall should be {expected_recall:.3f}"

    def test_empty_results(self):
        """Test all metrics with empty results"""
        results: List[Tuple[List[str], List[str]]] = []

        mrr = BenchmarkMetrics.calculate_mrr(results)
        hit_rate = BenchmarkMetrics.calculate_hit_rate(results, k=5)
        precision = BenchmarkMetrics.calculate_precision_at_k(results, k=5)
        recall = BenchmarkMetrics.calculate_recall_at_k(results, k=5)

        assert mrr == 0.0, "MRR should be 0.0 for empty results"
        assert hit_rate == 0.0, "Hit rate should be 0.0 for empty results"
        assert precision == 0.0, "Precision should be 0.0 for empty results"
        assert recall == 0.0, "Recall should be 0.0 for empty results"

    def test_single_query_result(self):
        """Test metrics with single query result"""
        results = [
            (["doc1"], ["doc2", "doc1", "doc3"]),  # Rank 2
        ]

        mrr = BenchmarkMetrics.calculate_mrr(results)
        hit_rate = BenchmarkMetrics.calculate_hit_rate(results, k=5)
        precision = BenchmarkMetrics.calculate_precision_at_k(results, k=5)
        recall = BenchmarkMetrics.calculate_recall_at_k(results, k=5)

        assert mrr == 0.5, "MRR should be 0.5 for rank 2"
        assert hit_rate == 1.0, "Hit rate should be 1.0 when doc found in top 5"
        assert precision == 0.2, "Precision should be 1/5"
        assert recall == 1.0, "Recall should be 1.0 when all expected docs found"

    def test_large_k_value(self):
        """Test metrics with k larger than result set"""
        results = [
            (["doc1"], ["doc1"]),  # Only 1 result, k=10
        ]

        hit_rate = BenchmarkMetrics.calculate_hit_rate(results, k=10)
        precision = BenchmarkMetrics.calculate_precision_at_k(results, k=10)
        recall = BenchmarkMetrics.calculate_recall_at_k(results, k=10)

        assert hit_rate == 1.0, "Hit rate should be 1.0 when doc found"
        assert precision == 0.1, "Precision should handle k larger than results"
        assert recall == 1.0, "Recall should be 1.0 when all expected docs found"


class TestBenchmarkIntegration:
    """Integration tests for benchmark system"""

    def test_yaml_files_exist(self):
        """Test that all benchmark YAML files exist"""
        benchmark_dir = Path(__file__).parent.parent / "sets"

        assert (
            benchmark_dir / "academic_lite.yaml"
        ).exists(), "academic_lite.yaml should exist"
        assert (
            benchmark_dir / "academic_extended.yaml"
        ).exists(), "academic_extended.yaml should exist"
        assert (
            benchmark_dir / "industrial_small.yaml"
        ).exists(), "industrial_small.yaml should exist"

    def test_results_directory_writable(self):
        """Test that results directory can be written to"""
        results_dir = Path(__file__).parent.parent / "results"
        results_dir.mkdir(exist_ok=True)

        test_file = results_dir / "test_write.txt"
        test_file.write_text("test")
        assert test_file.exists(), "Should be able to write to results directory"
        test_file.unlink()  # Cleanup

    def test_scripts_directory_exists(self):
        """Test that scripts directory and files exist"""
        scripts_dir = Path(__file__).parent.parent / "scripts"

        assert (
            scripts_dir / "run_benchmark.py"
        ).exists(), "run_benchmark.py should exist"
        assert (
            scripts_dir / "compare_runs.py"
        ).exists(), "compare_runs.py should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
