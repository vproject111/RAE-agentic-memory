"""
Traced Qdrant Client Wrapper

This module provides OpenTelemetry tracing for Qdrant operations.
Since Qdrant doesn't have native OTEL instrumentation, this wrapper
adds custom spans for all vector database operations.

Traces include:
- Collection operations (create, delete, info)
- Vector operations (upsert, search, retrieve, delete)
- Scroll and batch operations
- Performance metrics (latency, vector count)
"""

import time
from contextlib import contextmanager
from typing import Any, List, Optional, cast

import structlog
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, PointStruct, ScoredPoint, SearchParams

from .opentelemetry_config import OPENTELEMETRY_AVAILABLE, get_tracer

logger = structlog.get_logger(__name__)


class TracedQdrantClient:
    """
    Wrapper around QdrantClient that adds OpenTelemetry tracing.

    Usage:
        client = TracedQdrantClient(url="http://localhost:6333")
        results = await client.search(
            collection_name="memories",
            query_vector=[0.1, 0.2, ...],
            limit=10
        )
    """

    def __init__(self, *args, **kwargs):
        """Initialize traced Qdrant client."""
        self.client = QdrantClient(*args, **kwargs)
        self.tracer = get_tracer("rae.qdrant") if OPENTELEMETRY_AVAILABLE else None

    @contextmanager
    def _trace_operation(
        self,
        operation: str,
        collection: Optional[str] = None,
        **attributes,
    ):
        """
        Create a span for a Qdrant operation.

        Args:
            operation: Operation name (e.g., "search", "upsert")
            collection: Collection name
            **attributes: Additional span attributes
        """
        if not self.tracer:
            yield None
            return

        start_time = time.time()

        with self.tracer.start_as_current_span(f"qdrant.{operation}") as span:
            # Set base attributes
            span.set_attribute("qdrant.operation", operation)
            if collection:
                span.set_attribute("qdrant.collection", collection)

            # Set additional attributes
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(f"qdrant.{key}", value)

            try:
                yield span
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)
                raise
            finally:
                # Record latency
                latency_ms = (time.time() - start_time) * 1000
                span.set_attribute("qdrant.latency_ms", round(latency_ms, 2))

    # ============================================================================
    # Collection Operations
    # ============================================================================

    def create_collection(self, collection_name: str, *args, **kwargs):
        """Create a collection with tracing."""
        with self._trace_operation("create_collection", collection=collection_name):
            return self.client.create_collection(collection_name, *args, **kwargs)

    def delete_collection(self, collection_name: str, **kwargs):
        """Delete a collection with tracing."""
        with self._trace_operation("delete_collection", collection=collection_name):
            return self.client.delete_collection(collection_name, **kwargs)

    def get_collection(self, collection_name: str):
        """Get collection info with tracing."""
        with self._trace_operation("get_collection", collection=collection_name):
            return self.client.get_collection(collection_name)

    def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists with tracing."""
        with self._trace_operation("collection_exists", collection=collection_name):
            return self.client.collection_exists(collection_name)

    def get_collections(self):
        """List all collections with tracing."""
        with self._trace_operation("get_collections"):
            return self.client.get_collections()

    # ============================================================================
    # Point Operations
    # ============================================================================

    def upsert(
        self,
        collection_name: str,
        points: List[PointStruct],
        wait: bool = True,
        **kwargs,
    ):
        """Upsert points with tracing."""
        with self._trace_operation(
            "upsert",
            collection=collection_name,
            vector_count=len(points),
            wait=wait,
        ):
            return self.client.upsert(
                collection_name=collection_name,
                points=points,
                wait=wait,
                **kwargs,
            )

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        query_filter: Optional[Filter] = None,
        search_params: Optional[SearchParams] = None,
        **kwargs,
    ) -> List[ScoredPoint]:
        """Search for similar vectors with tracing."""
        with self._trace_operation(
            "search",
            collection=collection_name,
            limit=limit,
            has_filter=query_filter is not None,
        ) as span:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=query_filter,
                search_params=search_params,
                **kwargs,
            )

            # Add result count to span
            if span:
                span.set_attribute("qdrant.results_count", len(results))

            return results

    def retrieve(
        self,
        collection_name: str,
        ids: List[str],
        with_vectors: bool = False,
        **kwargs,
    ):
        """Retrieve points by IDs with tracing."""
        with self._trace_operation(
            "retrieve",
            collection=collection_name,
            ids_count=len(ids),
            with_vectors=with_vectors,
        ):
            return self.client.retrieve(
                collection_name=collection_name,
                ids=ids,
                with_vectors=with_vectors,
                **kwargs,
            )

    def delete(
        self,
        collection_name: str,
        points_selector: Any,
        wait: bool = True,
        **kwargs,
    ):
        """Delete points with tracing."""
        with self._trace_operation(
            "delete",
            collection=collection_name,
            wait=wait,
        ):
            return self.client.delete(
                collection_name=collection_name,
                points_selector=points_selector,
                wait=wait,
                **kwargs,
            )

    def scroll(
        self,
        collection_name: str,
        scroll_filter: Optional[Filter] = None,
        limit: int = 10,
        with_vectors: bool = False,
        **kwargs,
    ):
        """Scroll through points with tracing."""
        with self._trace_operation(
            "scroll",
            collection=collection_name,
            limit=limit,
            has_filter=scroll_filter is not None,
            with_vectors=with_vectors,
        ) as span:
            results, next_page = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=limit,
                with_vectors=with_vectors,
                **kwargs,
            )

            # Add result count to span
            if span:
                span.set_attribute("qdrant.results_count", len(results))
                span.set_attribute("qdrant.has_next_page", next_page is not None)

            return results, next_page

    def count(
        self,
        collection_name: str,
        count_filter: Optional[Filter] = None,
        exact: bool = True,
        **kwargs,
    ) -> int:
        """Count points with tracing."""
        with self._trace_operation(
            "count",
            collection=collection_name,
            has_filter=count_filter is not None,
            exact=exact,
        ) as span:
            result = self.client.count(
                collection_name=collection_name,
                count_filter=count_filter,
                exact=exact,
                **kwargs,
            )

            count = result.count if hasattr(result, "count") else result

            # Add count to span
            if span:
                span.set_attribute("qdrant.count", count)

            return cast(int, count)

    # ============================================================================
    # Batch Operations
    # ============================================================================

    def batch_upsert(
        self,
        collection_name: str,
        points: List[PointStruct],
        batch_size: int = 100,
        wait: bool = True,
        **kwargs,
    ):
        """Batch upsert with tracing."""
        with self._trace_operation(
            "batch_upsert",
            collection=collection_name,
            vector_count=len(points),
            batch_size=batch_size,
            wait=wait,
        ):
            # Split into batches
            batches = [
                points[i : i + batch_size] for i in range(0, len(points), batch_size)
            ]

            results = []
            for batch in batches:
                result = self.client.upsert(
                    collection_name=collection_name,
                    points=batch,
                    wait=wait,
                    **kwargs,
                )
                results.append(result)

            return results

    # ============================================================================
    # Direct Client Access
    # ============================================================================

    def __getattr__(self, name):
        """
        Proxy all other methods to the underlying client.

        This allows access to any Qdrant client methods not explicitly wrapped.
        """
        return getattr(self.client, name)


# ============================================================================
# Convenience Functions
# ============================================================================


def create_traced_client(*args, **kwargs) -> TracedQdrantClient:
    """
    Create a traced Qdrant client.

    Args:
        *args, **kwargs: Arguments passed to QdrantClient

    Returns:
        TracedQdrantClient instance

    Example:
        client = create_traced_client(url="http://localhost:6333")
    """
    return TracedQdrantClient(*args, **kwargs)
