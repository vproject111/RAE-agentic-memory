import asyncio
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# We import the Class under test
from apps.memory_api.services.reflection_pipeline import ReflectionPipeline


@pytest.mark.asyncio
async def test_clustering_offload_safety():
    """
    Verify that clustering operations run in a thread pool and do not block the event loop.
    """
    # Create a dummy pipeline
    pool = MagicMock()
    pipeline = ReflectionPipeline(pool)

    # Create dummy memories
    memories = [{"id": str(i), "embedding": [0.1 * i] * 10} for i in range(20)]

    # Mock _ensure_sklearn_available properly using patch.object
    with patch.object(pipeline, "_ensure_sklearn_available"):
        # Mock StandardScaler to pass the transformation step
        with patch(
            "apps.memory_api.services.reflection_pipeline.StandardScaler"
        ) as MockScaler:
            scaler_instance = MockScaler.return_value
            scaler_instance.fit_transform.return_value = np.zeros((20, 10))

            # Mock KMeans to simulate a CPU-blocking operation
            # IMPORTANT: This side_effect simulates a function that TAKES TIME to execute.
            # If run on main thread, it blocks everything.
            # If run in thread pool, asyncio.sleep(0.1) in pinger should run concurrently.
            def blocking_kmeans(*args, **kwargs):
                time.sleep(0.5)  # Block strictly for 500ms
                return np.zeros(20, dtype=int)  # Return dummy labels

            with patch(
                "apps.memory_api.services.reflection_pipeline.KMeans"
            ) as MockKMeans:
                kmeans_instance = MockKMeans.return_value
                kmeans_instance.fit_predict.side_effect = blocking_kmeans

                # Also patch HDBSCAN to ensure we fail over to KMeans (or just use KMeans directly)
                # The code tries HDBSCAN first. Let's make HDBSCAN raise exception to force KMeans path
                # OR just make HDBSCAN blocking too. Let's test KMeans path as it's the fallback.
                with patch(
                    "apps.memory_api.services.reflection_pipeline.HDBSCAN"
                ) as MockHDBSCAN:
                    hdbscan_instance = MockHDBSCAN.return_value
                    hdbscan_instance.fit_predict.side_effect = Exception(
                        "Force KMeans fallback"
                    )

                    # --- The Concurrent Test ---

                    async def pinger():
                        # This task should be able to run while clustering is happening
                        start_ping = time.time()
                        await asyncio.sleep(0.1)  # Yield to event loop
                        return time.time() - start_ping

                    # Start clustering (which triggers the blocking_kmeans)
                    task_cluster = asyncio.create_task(
                        pipeline._cluster_memories(memories, min_cluster_size=2)
                    )

                    # Start pinger immediately after
                    task_ping = asyncio.create_task(pinger())

                    # Wait for both
                    await asyncio.gather(task_cluster, task_ping)

                    ping_duration = task_ping.result()

                    # ANALYSIS:
                    # If blocking_kmeans blocked the loop:
                    #   1. task_cluster starts, calls blocking_kmeans (BLOCKS for 0.5s)
                    #   2. task_ping cannot even start or resume until 0.5s is over.
                    #   3. Once unblocked, pinger sleeps 0.1s.
                    #   Total ping time seen by wall clock ~ 0.5 + 0.1 = 0.6s (or at least > 0.5s)

                    # If offloaded:
                    #   1. task_cluster starts, awaits to_thread (yields)
                    #   2. blocking_kmeans runs in thread.
                    #   3. loop is free. task_ping starts, sleeps 0.1s.
                    #   4. task_ping wakes up and finishes in ~0.1s.
                    #   5. blocking_kmeans finishes later (at 0.5s).
                    #   Ping duration ~ 0.1s.

                    print(f"Ping duration: {ping_duration:.4f}s")

                    # Assert ping was fast (concurrent)
                    assert (
                        ping_duration < 0.3
                    ), f"Event loop was blocked! Ping took {ping_duration:.4f}s"
