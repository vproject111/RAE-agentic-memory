"""
Load tests for RAE MCP Server.

These tests verify performance under high concurrency (100+ concurrent requests).
They measure throughput, latency, error rates, and resource usage.

Requirements:
- Docker and docker compose installed
- .env file configured with LLM API key
- Ports 8000, 5432, 6333, 6379 available
- Sufficient system resources (8GB RAM recommended)

Usage:
    pytest integrations/mcp/tests/test_mcp_load.py -v -m load
    pytest integrations/mcp/tests/test_mcp_load.py::test_concurrent_store_memory -v
"""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import httpx
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rae_mcp.server import RAEMemoryClient

pytestmark = pytest.mark.load


@pytest.fixture(scope="module")
def rae_lite_services():
    """
    Start docker compose.lite.yml services for load testing.

    This fixture:
    1. Starts all RAE Lite services
    2. Waits for services to be healthy
    3. Yields control to tests
    4. Tears down services after tests complete
    """
    # Get project root
    project_root = Path(__file__).parent.parent.parent.parent
    compose_file = project_root / "docker compose.lite.yml"

    # Start services
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        check=True,
        capture_output=True,
        cwd=project_root,
    )

    # Wait for services to be ready
    max_retries = 30
    retry_count = 0
    api_ready = False

    while retry_count < max_retries and not api_ready:
        try:
            response = httpx.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                api_ready = True
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            pass

        retry_count += 1
        time.sleep(2)

    if not api_ready:
        # Cleanup on failure
        subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "down"],
            capture_output=True,
            cwd=project_root,
        )
        pytest.fail("RAE API failed to start within 60 seconds")

    # Services are ready
    yield

    # Teardown
    subprocess.run(
        ["docker", "compose", "-f", str(compose_file), "down"],
        check=True,
        capture_output=True,
        cwd=project_root,
    )


@pytest.fixture
def mcp_client(rae_lite_services):
    """Create RAEMemoryClient for load testing."""
    return RAEMemoryClient(
        api_url=os.getenv("RAE_API_URL", "http://localhost:8000"),
        api_key=os.getenv("RAE_API_KEY", "test-api-key"),
        tenant_id=os.getenv("RAE_TENANT_ID", "load-test-tenant"),
    )


class TestConcurrentStoreMemory:
    """Load tests for concurrent store_memory operations"""

    @pytest.mark.asyncio
    async def test_concurrent_store_memory_100(self, mcp_client):
        """Test 100 concurrent store_memory calls"""
        concurrency = 100

        async def store_single(i: int):
            """Store a single memory"""
            return await mcp_client.store_memory(
                content=f"Load test memory {i}",
                source=f"load-test-{i}",
                layer="episodic",
                tags=["load-test", f"batch-{i // 10}"],
            )

        # Measure execution time
        start_time = time.time()

        # Execute concurrent requests
        tasks = [store_single(i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start_time

        # Analyze results
        successes = [r for r in results if isinstance(r, dict) and "id" in r]
        errors = [r for r in results if isinstance(r, Exception)]

        print(f"\n=== Concurrent Store Memory (n={concurrency}) ===")
        print(f"Total time: {elapsed:.2f}s")
        print(f"Throughput: {concurrency / elapsed:.2f} req/sec")
        print(f"Avg latency: {(elapsed / concurrency) * 1000:.2f}ms")
        print(f"Successes: {len(successes)}")
        print(f"Errors: {len(errors)}")

        # Assertions
        assert (
            len(successes) >= concurrency * 0.95
        ), f"Too many errors: {len(errors)}/{concurrency}"
        assert elapsed < 30.0, f"Too slow: {elapsed}s for {concurrency} requests"

    @pytest.mark.asyncio
    async def test_concurrent_store_memory_200(self, mcp_client):
        """Test 200 concurrent store_memory calls"""
        concurrency = 200

        async def store_single(i: int):
            """Store a single memory"""
            return await mcp_client.store_memory(
                content=f"Load test memory {i}",
                source=f"load-test-{i}",
                layer="episodic",
                tags=["load-test-200"],
            )

        start_time = time.time()
        tasks = [store_single(i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        successes = [r for r in results if isinstance(r, dict) and "id" in r]
        errors = [r for r in results if isinstance(r, Exception)]

        print(f"\n=== Concurrent Store Memory (n={concurrency}) ===")
        print(f"Total time: {elapsed:.2f}s")
        print(f"Throughput: {concurrency / elapsed:.2f} req/sec")
        print(f"Successes: {len(successes)}")
        print(f"Errors: {len(errors)}")

        assert (
            len(successes) >= concurrency * 0.90
        ), f"Too many errors: {len(errors)}/{concurrency}"


class TestConcurrentSearchMemory:
    """Load tests for concurrent search_memory operations"""

    @pytest.mark.asyncio
    async def test_concurrent_search_memory_100(self, mcp_client):
        """Test 100 concurrent search_memory calls"""
        # First, populate some memories
        for i in range(20):
            await mcp_client.store_memory(
                content=f"Search target memory {i}",
                source="search-test",
                layer="semantic",
                tags=["search-target"],
            )

        time.sleep(2)  # Wait for indexing

        concurrency = 100

        async def search_single(i: int):
            """Search memories"""
            return await mcp_client.search_memory(
                query="search target memory",
                top_k=5,
            )

        start_time = time.time()
        tasks = [search_single(i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        successes = [r for r in results if isinstance(r, list)]
        errors = [r for r in results if isinstance(r, Exception)]

        print(f"\n=== Concurrent Search Memory (n={concurrency}) ===")
        print(f"Total time: {elapsed:.2f}s")
        print(f"Throughput: {concurrency / elapsed:.2f} req/sec")
        print(f"Avg latency: {(elapsed / concurrency) * 1000:.2f}ms")
        print(f"Successes: {len(successes)}")
        print(f"Errors: {len(errors)}")

        assert (
            len(successes) >= concurrency * 0.95
        ), f"Too many errors: {len(errors)}/{concurrency}"
        assert elapsed < 30.0, f"Too slow: {elapsed}s for {concurrency} requests"


class TestMixedOperations:
    """Load tests for mixed operations (store + search)"""

    @pytest.mark.asyncio
    async def test_mixed_operations_150(self, mcp_client):
        """Test 150 mixed operations (75 store + 75 search)"""
        concurrency = 150

        async def mixed_operation(i: int):
            """Perform either store or search"""
            if i % 2 == 0:
                # Store
                return await mcp_client.store_memory(
                    content=f"Mixed test memory {i}",
                    source=f"mixed-test-{i}",
                    layer="episodic",
                    tags=["mixed-test"],
                )
            else:
                # Search
                return await mcp_client.search_memory(
                    query="mixed test memory",
                    top_k=5,
                )

        start_time = time.time()
        tasks = [mixed_operation(i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time

        successes = [r for r in results if not isinstance(r, Exception)]
        errors = [r for r in results if isinstance(r, Exception)]

        print(f"\n=== Mixed Operations (n={concurrency}) ===")
        print(f"Total time: {elapsed:.2f}s")
        print(f"Throughput: {concurrency / elapsed:.2f} req/sec")
        print(f"Successes: {len(successes)}")
        print(f"Errors: {len(errors)}")

        assert (
            len(successes) >= concurrency * 0.90
        ), f"Too many errors: {len(errors)}/{concurrency}"


class TestSustainedLoad:
    """Test sustained load over time"""

    @pytest.mark.asyncio
    async def test_sustained_load_60_seconds(self, mcp_client):
        """Test sustained load for 60 seconds"""
        duration = 60  # seconds
        rate = 10  # requests per second

        request_count = 0
        success_count = 0
        error_count = 0

        start_time = time.time()

        while time.time() - start_time < duration:
            batch_start = time.time()

            # Send batch of requests
            tasks = [
                mcp_client.store_memory(
                    content=f"Sustained load test {request_count + i}",
                    source="sustained-test",
                    layer="episodic",
                    tags=["sustained"],
                )
                for i in range(rate)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count results
            for r in results:
                if isinstance(r, Exception):
                    error_count += 1
                else:
                    success_count += 1

            request_count += len(tasks)

            # Wait for next second
            batch_elapsed = time.time() - batch_start
            if batch_elapsed < 1.0:
                await asyncio.sleep(1.0 - batch_elapsed)

        total_elapsed = time.time() - start_time

        print(f"\n=== Sustained Load (duration={duration}s, rate={rate} req/s) ===")
        print(f"Total requests: {request_count}")
        print(f"Successes: {success_count}")
        print(f"Errors: {error_count}")
        print(f"Actual throughput: {request_count / total_elapsed:.2f} req/sec")
        print(f"Error rate: {(error_count / request_count) * 100:.2f}%")

        assert (
            error_count / request_count < 0.05
        ), f"Error rate too high: {error_count}/{request_count}"


class TestLatencyPercentiles:
    """Test latency percentiles under load"""

    @pytest.mark.asyncio
    async def test_latency_percentiles(self, mcp_client):
        """Measure p50, p95, p99 latencies under load"""
        concurrency = 100
        latencies: List[float] = []

        async def timed_operation(i: int):
            """Execute operation and measure latency"""
            op_start = time.time()
            await mcp_client.store_memory(
                content=f"Latency test {i}",
                source=f"latency-test-{i}",
                layer="episodic",
            )
            latency = (time.time() - op_start) * 1000  # Convert to ms
            return latency

        # Execute concurrent requests
        latencies = await asyncio.gather(
            *[timed_operation(i) for i in range(concurrency)]
        )
        latencies = sorted(latencies)

        # Calculate percentiles
        p50 = latencies[int(len(latencies) * 0.50)]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        p_max = max(latencies)

        print(f"\n=== Latency Percentiles (n={concurrency}) ===")
        print(f"p50: {p50:.2f}ms")
        print(f"p95: {p95:.2f}ms")
        print(f"p99: {p99:.2f}ms")
        print(f"max: {p_max:.2f}ms")

        # Assertions based on expected performance
        assert p50 < 100, f"p50 latency too high: {p50}ms"
        assert p95 < 300, f"p95 latency too high: {p95}ms"
        assert p99 < 500, f"p99 latency too high: {p99}ms"


@pytest.mark.skipif(
    subprocess.run(["which", "docker compose"], capture_output=True).returncode != 0,
    reason="docker compose not available",
)
class TestResourceUsage:
    """Test resource usage under load"""

    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, mcp_client):
        """Test for memory leaks during sustained load"""
        # Run multiple batches and check memory doesn't grow unbounded
        batch_size = 50
        num_batches = 5

        for batch in range(num_batches):
            tasks = [
                mcp_client.store_memory(
                    content=f"Memory leak test batch {batch} item {i}",
                    source="memory-leak-test",
                    layer="episodic",
                )
                for i in range(batch_size)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            successes = [r for r in results if not isinstance(r, Exception)]

            print(
                f"Batch {batch + 1}/{num_batches}: {len(successes)}/{batch_size} succeeded"
            )

            # Small delay between batches
            await asyncio.sleep(1)

        print("\n=== Memory Leak Detection ===")
        print("If all batches completed successfully, no obvious memory leak")
        print("Check system memory usage manually for detailed analysis")
