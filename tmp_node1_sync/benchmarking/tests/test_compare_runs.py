"""
Tests for compare_runs.py

Tests cover:
- Change calculation between runs
- Improvement/regression detection
- Report generation
- Edge cases
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, cast

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from compare_runs import BenchmarkComparator


class TestBenchmarkComparator:
    """Test benchmark comparison functionality"""

    @pytest.fixture
    def sample_baseline_data(self) -> Dict:
        """Create sample baseline benchmark data"""
        return {
            "benchmark": {
                "name": "academic_extended",
                "description": "Test benchmark",
                "version": "1.0",
            },
            "execution": {
                "timestamp": "2024-12-01T10:00:00",
                "num_memories": 50,
                "num_queries": 20,
                "total_time_seconds": 30.0,
            },
            "metrics": {
                "mrr": 0.7500,
                "hit_rate": {"@3": 0.7000, "@5": 0.8000, "@10": 0.9000},
                "precision": {"@3": 0.6000, "@5": 0.6500, "@10": 0.7000},
                "recall": {"@3": 0.6500, "@5": 0.7500, "@10": 0.8500},
                "overall_quality_score": 0.7200,
                "performance": {
                    "avg_insert_time_ms": 100.0,
                    "avg_query_time_ms": 50.0,
                    "p95_query_time_ms": 80.0,
                    "p99_query_time_ms": 100.0,
                },
            },
        }

    @pytest.fixture
    def sample_improved_data(self, sample_baseline_data) -> Dict[str, Any]:
        """Create sample improved benchmark data"""
        improved = sample_baseline_data.copy()
        improved["execution"]["timestamp"] = "2024-12-06T10:00:00"
        improved["metrics"] = {
            "mrr": 0.8500,  # +13.33%
            "hit_rate": {
                "@3": 0.8000,
                "@5": 0.9000,
                "@10": 0.9500,
            },
            "precision": {
                "@3": 0.7000,  # +16.67%
                "@5": 0.7500,  # +15.38%
                "@10": 0.8000,  # +14.29%
            },
            "recall": {
                "@3": 0.7500,  # +15.38%
                "@5": 0.8500,  # +13.33%
                "@10": 0.9000,  # +5.88%
            },
            "overall_quality_score": 0.8200,  # +13.89%
            "performance": {
                "avg_insert_time_ms": 80.0,  # -20%
                "avg_query_time_ms": 40.0,  # -20%
                "p95_query_time_ms": 65.0,  # -18.75%
                "p99_query_time_ms": 80.0,  # -20%
            },
        }
        return cast(Dict[str, Any], improved)

    @pytest.fixture
    def sample_regressed_data(self, sample_baseline_data) -> Dict[str, Any]:
        """Create sample regressed benchmark data"""
        regressed = sample_baseline_data.copy()
        regressed["execution"]["timestamp"] = "2024-12-06T10:00:00"
        regressed["metrics"] = {
            "mrr": 0.6500,  # -13.33%
            "hit_rate": {
                "@3": 0.6000,  # -14.29%
                "@5": 0.7000,  # -12.50%
                "@10": 0.8500,  # -5.56%
            },
            "precision": {
                "@3": 0.5000,  # -16.67%
                "@5": 0.5500,  # -15.38%
                "@10": 0.6000,  # -14.29%
            },
            "recall": {
                "@3": 0.5500,  # -15.38%
                "@5": 0.6500,  # -13.33%
                "@10": 0.8000,  # -5.88%
            },
            "overall_quality_score": 0.6200,  # -13.89%
            "performance": {
                "avg_insert_time_ms": 120.0,  # +20%
                "avg_query_time_ms": 60.0,  # +20%
                "p95_query_time_ms": 96.0,  # +20%
                "p99_query_time_ms": 120.0,  # +20%
            },
        }
        return cast(Dict[str, Any], regressed)

    def test_improvements_detected(
        self, tmp_path, sample_baseline_data, sample_improved_data
    ):
        """Test that improvements are correctly detected"""
        # Write test files
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "improved.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_improved_data, f)

        # Create comparator and load results
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Verify improvements detected
        assert changes["summary"]["improvements"] > 0, "Should detect improvements"
        assert changes["quality"]["mrr"]["percent_change"] > 0, "MRR should improve"
        assert (
            changes["performance"]["avg_query_time_ms"]["improved"] is True
        ), "Latency should improve"

    def test_regressions_detected(
        self, tmp_path, sample_baseline_data, sample_regressed_data
    ):
        """Test that regressions are correctly detected"""
        # Write test files
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "regressed.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_regressed_data, f)

        # Create comparator and load results
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Verify regressions detected
        assert changes["summary"]["regressions"] > 0, "Should detect regressions"
        assert changes["quality"]["mrr"]["percent_change"] < 0, "MRR should regress"
        assert (
            changes["performance"]["avg_query_time_ms"]["improved"] is False
        ), "Latency should regress"

    def test_unchanged_metrics(self, tmp_path, sample_baseline_data):
        """Test that unchanged metrics are correctly identified"""
        # Write identical files
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "same.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_baseline_data, f)

        # Create comparator and load results
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Verify no changes detected (within threshold)
        assert (
            changes["quality"]["mrr"]["percent_change"] == 0.0
        ), "MRR should be unchanged"
        assert (
            changes["quality"]["mrr"]["absolute_change"] == 0.0
        ), "MRR absolute change should be 0"

    def test_change_percentage_calculation(
        self, tmp_path, sample_baseline_data, sample_improved_data
    ):
        """Test that percentage changes are calculated correctly"""
        # Write test files
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "improved.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_improved_data, f)

        # Create comparator and load results
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # MRR: 0.7500 → 0.8500 = +13.33%
        mrr_change = changes["quality"]["mrr"]["percent_change"]
        assert (
            abs(mrr_change - 13.33) < 0.1
        ), f"MRR change should be ~13.33%, got {mrr_change:.2f}%"

        # Query time: 50.0 → 40.0 = -20%
        latency_change = changes["performance"]["avg_query_time_ms"]["percent_change"]
        assert (
            abs(latency_change - (-20.0)) < 0.1
        ), f"Latency change should be ~-20%, got {latency_change:.2f}%"

    def test_markdown_report_generation(
        self, tmp_path, sample_baseline_data, sample_improved_data
    ):
        """Test that Markdown report is generated correctly"""
        # Write test files
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "improved.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_improved_data, f)

        # Create comparator and generate report
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        output_file = tmp_path / "comparison_report.md"
        comparator.generate_markdown_report(output_file, changes)

        # Verify report was created and has content
        assert output_file.exists(), "Report file should be created"
        content = output_file.read_text()
        assert len(content) > 0, "Report should have content"
        assert (
            "# RAE Benchmark Comparison Report" in content
        ), "Report should have title"
        assert "Summary" in content, "Report should have summary section"
        assert "Quality Metrics" in content, "Report should have quality section"
        assert (
            "Performance Metrics" in content
        ), "Report should have performance section"

    def test_summary_counts(self, tmp_path, sample_baseline_data, sample_improved_data):
        """Test that summary counts (improvements/regressions/unchanged) are correct"""
        # Write test files
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "improved.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_improved_data, f)

        # Create comparator
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Verify counts
        total = (
            changes["summary"]["improvements"]
            + changes["summary"]["regressions"]
            + changes["summary"]["unchanged"]
        )

        assert total > 0, "Should have some metrics counted"
        assert (
            changes["summary"]["improvements"] > 0
        ), "Should have improvements in this test data"

    def test_zero_baseline_handling(self, tmp_path, sample_baseline_data):
        """Test handling of zero baseline values"""
        # Create data with zero baseline
        baseline_data = sample_baseline_data.copy()
        baseline_data["metrics"]["mrr"] = 0.0

        improved_data = sample_baseline_data.copy()
        improved_data["metrics"]["mrr"] = 0.5

        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "improved.json"

        with open(baseline_file, "w") as f:
            json.dump(baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(improved_data, f)

        # Create comparator
        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Should handle zero baseline gracefully (percent_change = 0 by default)
        mrr_change = changes["quality"]["mrr"]["percent_change"]
        assert mrr_change == 0.0, "Should handle zero baseline without error"

    def test_performance_improvement_detection(
        self, tmp_path, sample_baseline_data, sample_improved_data
    ):
        """Test that performance improvements (lower latency) are detected correctly"""
        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "improved.json"

        with open(baseline_file, "w") as f:
            json.dump(sample_baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(sample_improved_data, f)

        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Lower latency = improvement
        for key in ["avg_query_time_ms", "p95_query_time_ms"]:
            perf_change = changes["performance"][key]
            assert (
                perf_change["comparison"] < perf_change["baseline"]
            ), f"{key} should decrease"
            assert (
                perf_change["improved"] is True
            ), f"{key} should be marked as improved"


class TestComparisonEdgeCases:
    """Test edge cases in benchmark comparison"""

    def test_missing_metrics_handled(self, tmp_path):
        """Test handling of missing metrics in comparison"""
        baseline_data = {
            "benchmark": {"name": "test", "description": "test", "version": "1.0"},
            "execution": {
                "timestamp": "2024-12-01",
                "num_memories": 10,
                "num_queries": 5,
                "total_time_seconds": 5.0,
            },
            "metrics": {
                "mrr": 0.75,
                "hit_rate": {"@5": 0.8},
                "precision": {"@5": 0.7},
                "recall": {"@5": 0.75},
                "overall_quality_score": 0.75,
                "performance": {"avg_query_time_ms": 50.0, "p95_query_time_ms": 80.0},
            },
        }

        comparison_data = baseline_data.copy()

        baseline_file = tmp_path / "baseline.json"
        comparison_file = tmp_path / "comparison.json"

        with open(baseline_file, "w") as f:
            json.dump(baseline_data, f)
        with open(comparison_file, "w") as f:
            json.dump(comparison_data, f)

        comparator = BenchmarkComparator(baseline_file, comparison_file)
        comparator.load_results()
        changes = comparator.calculate_changes()

        # Should complete without error
        assert "quality" in changes
        assert "performance" in changes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
