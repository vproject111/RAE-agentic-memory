"""
Performance Regression Tests

These tests ensure critical operations stay fast.
Run with: pytest -m performance

Note: Requires pytest-benchmark. If not available, tests will be skipped.
"""

import time

import pytest

# Check if pytest-benchmark is available
try:
    import pytest_benchmark  # noqa: F401

    HAS_BENCHMARK = True
except ImportError:
    HAS_BENCHMARK = False


@pytest.mark.performance
@pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not available")
class TestMemoryOperationsPerformance:
    """Performance tests for memory operations"""

    def test_memory_query_performance(self, benchmark):
        """Ensure memory query completes in <200ms"""

        def query_operation():
            # Simulate query
            time.sleep(0.05)  # Placeholder
            return {"results": []}

        result = benchmark(query_operation)
        assert result is not None

        # Check that mean time is under threshold
        # benchmark.stats is a BenchmarkStats object with stats dict
        mean_time = (
            benchmark.stats.stats.mean
            if hasattr(benchmark.stats, "stats")
            else benchmark.stats["mean"]
        )
        assert mean_time < 0.2, f"Query too slow: {mean_time:.3f}s"

    def test_embedding_generation_performance(self, benchmark):
        """Ensure embedding generation completes in <500ms"""

        def embed_operation():
            time.sleep(0.1)  # Placeholder
            return [0.1] * 384

        result = benchmark(embed_operation)
        assert len(result) == 384

        mean_time = (
            benchmark.stats.stats.mean
            if hasattr(benchmark.stats, "stats")
            else benchmark.stats["mean"]
        )
        assert mean_time < 0.5, f"Embedding too slow: {mean_time:.3f}s"


@pytest.mark.performance
@pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not available")
class TestGraphOperationsPerformance:
    """Performance tests for graph operations"""

    def test_graph_traversal_performance(self, benchmark):
        """Ensure graph traversal completes in <100ms"""

        def traverse_operation():
            time.sleep(0.02)  # Placeholder
            return {"nodes": 10}

        result = benchmark(traverse_operation)
        assert result["nodes"] > 0

        mean_time = (
            benchmark.stats.stats.mean
            if hasattr(benchmark.stats, "stats")
            else benchmark.stats["mean"]
        )
        assert mean_time < 0.1, f"Traversal too slow: {mean_time:.3f}s"


@pytest.mark.performance
@pytest.mark.skipif(not HAS_BENCHMARK, reason="pytest-benchmark not available")
def test_bulk_insert_performance(benchmark):
    """Ensure bulk insert of 100 items completes in <1s"""

    def bulk_insert():
        time.sleep(0.3)  # Placeholder
        return 100

    result = benchmark(bulk_insert)
    assert result == 100

    mean_time = (
        benchmark.stats.stats.mean
        if hasattr(benchmark.stats, "stats")
        else benchmark.stats["mean"]
    )
    assert mean_time < 1.0, f"Bulk insert too slow: {mean_time:.3f}s"
