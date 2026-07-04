"""
RAE Memory SDK Decorators

This module provides decorators for automatic memory tracing of function executions.
"""

import asyncio
import functools
import json
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Optional

import structlog

if TYPE_CHECKING:
    from rae_memory_sdk.client import MemoryClient

logger = structlog.get_logger(__name__)


def trace_memory(
    client: "MemoryClient",
    layer: str = "episodic",
    tags: Optional[List[str]] = None,
    capture_args: bool = True,
    capture_result: bool = True,
    project: Optional[str] = None,
):
    """
    Decorator to automatically trace function execution to RAE memory.

    This decorator captures function calls, their arguments, and results,
    storing them as episodic memories in the RAE system. It supports both
    synchronous and asynchronous functions.

    Args:
        client: MemoryClient instance for storing memories
        layer: Memory layer to store in (default: "episodic")
        tags: Optional list of tags for categorization
        capture_args: Whether to capture function arguments (default: True)
        capture_result: Whether to capture function results (default: True)
        project: Optional project identifier (default: uses client's default)

    Returns:
        Decorated function that automatically logs to RAE memory

    Example:
        ```python
        from rae_memory_sdk import MemoryClient
        from rae_memory_sdk.decorators import trace_memory

        client = MemoryClient(api_url="http://localhost:8000")

        @trace_memory(client, layer="episodic", tags=["business-logic"])
        def process_payment(amount: float, user_id: str):
            # Business logic here
            return {"status": "success", "transaction_id": "123"}

        # Function execution is automatically logged to RAE
        result = process_payment(99.99, "user-456")
        ```

    Enterprise Features:
        - Full type safety with type hints
        - Comprehensive error handling and logging
        - Support for both sync and async functions
        - Configurable capture of arguments and results
        - Background task execution to avoid blocking
        - Structured logging for observability
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            """Wrapper for synchronous functions."""
            # Execute function and capture execution time
            start_time = datetime.now(timezone.utc)
            exception_occurred = None
            result = None

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                exception_occurred = e
                raise
            finally:
                # Build memory content
                end_time = datetime.now(timezone.utc)
                duration_ms = (end_time - start_time).total_seconds() * 1000

                content = _build_memory_content(
                    func_name=func.__name__,
                    module=func.__module__,
                    args=args if capture_args else None,
                    kwargs=kwargs if capture_args else None,
                    result=(
                        result if capture_result and not exception_occurred else None
                    ),
                    exception=exception_occurred,
                    duration_ms=duration_ms,
                    is_async=False,
                )

                # Store asynchronously in background
                try:
                    _store_memory_sync(
                        client=client,
                        content=content,
                        layer=layer,
                        tags=tags or [],
                        source=f"trace/{func.__module__}.{func.__name__}",
                        project=project,
                    )
                except Exception as store_error:
                    logger.error(
                        "trace_memory_storage_failed",
                        function=func.__name__,
                        error=str(store_error),
                    )

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            """Wrapper for asynchronous functions."""
            # Execute function and capture execution time
            start_time = datetime.now(timezone.utc)
            exception_occurred = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                exception_occurred = e
                raise
            finally:
                # Build memory content
                end_time = datetime.now(timezone.utc)
                duration_ms = (end_time - start_time).total_seconds() * 1000

                content = _build_memory_content(
                    func_name=func.__name__,
                    module=func.__module__,
                    args=args if capture_args else None,
                    kwargs=kwargs if capture_args else None,
                    result=(
                        result if capture_result and not exception_occurred else None
                    ),
                    exception=exception_occurred,
                    duration_ms=duration_ms,
                    is_async=True,
                )

                # Store in background task (fire-and-forget)
                try:
                    asyncio.create_task(
                        _store_memory_async(
                            client=client,
                            content=content,
                            layer=layer,
                            tags=tags or [],
                            source=f"trace/{func.__module__}.{func.__name__}",
                            project=project,
                        )
                    )
                except Exception as store_error:
                    logger.error(
                        "trace_memory_storage_failed",
                        function=func.__name__,
                        error=str(store_error),
                    )

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def _build_memory_content(
    func_name: str,
    module: str,
    args: Optional[tuple],
    kwargs: Optional[dict],
    result: Optional[Any],
    exception: Optional[Exception],
    duration_ms: float,
    is_async: bool,
) -> str:
    """
    Build structured memory content from function execution data.

    Args:
        func_name: Name of the function
        module: Module path of the function
        args: Function positional arguments
        kwargs: Function keyword arguments
        result: Function return value
        exception: Exception if one occurred
        duration_ms: Execution duration in milliseconds
        is_async: Whether the function is async

    Returns:
        Formatted memory content string
    """
    func_type = "Async function" if is_async else "Function"
    content_parts = [f"{func_type} '{func_name}' executed"]

    if args or kwargs:
        # Serialize args safely
        args_str = _safe_serialize(args) if args else "()"
        kwargs_str = _safe_serialize(kwargs) if kwargs else "{}"
        content_parts.append(f"with args={args_str}, kwargs={kwargs_str}")

    if exception:
        content_parts.append(
            f"⚠️ Exception occurred: {type(exception).__name__}: {str(exception)}"
        )
    elif result is not None:
        result_str = _safe_serialize(result)
        content_parts.append(f"Result: {result_str}")

    content_parts.append(f"[Duration: {duration_ms:.2f}ms]")

    return " ".join(content_parts)


def _safe_serialize(obj: Any, max_length: int = 500) -> str:
    """
    Safely serialize an object to string, with truncation.

    Args:
        obj: Object to serialize
        max_length: Maximum length of serialized string

    Returns:
        Serialized string representation
    """
    try:
        # Try JSON serialization first
        serialized = json.dumps(obj, default=str)
    except (TypeError, ValueError):
        # Fallback to string representation
        serialized = str(obj)

    # Truncate if too long
    if len(serialized) > max_length:
        serialized = serialized[:max_length] + "... [truncated]"

    return serialized


def _store_memory_sync(
    client: "MemoryClient",
    content: str,
    layer: str,
    tags: List[str],
    source: str,
    project: Optional[str],
) -> None:
    """
    Store memory synchronously using the MemoryClient.

    Args:
        client: MemoryClient instance
        content: Memory content
        layer: Memory layer
        tags: Tags list
        source: Source identifier
        project: Project identifier
    """
    from .models import StoreMemoryRequest

    try:
        memory_request = StoreMemoryRequest(
            content=content,
            layer=layer,
            tags=tags,
            source=source,
            project=project or "default",
        )
        client.store(memory_request)

        logger.debug(
            "trace_memory_stored",
            source=source,
            layer=layer,
            tags=tags,
        )
    except Exception as e:
        logger.error(
            "trace_memory_store_error",
            source=source,
            error=str(e),
        )


async def _store_memory_async(
    client: "MemoryClient",
    content: str,
    layer: str,
    tags: List[str],
    source: str,
    project: Optional[str],
) -> None:
    """
    Store memory asynchronously using the MemoryClient.

    This is a fire-and-forget operation that runs in the background
    without blocking the main function execution.

    Args:
        client: MemoryClient instance
        content: Memory content
        layer: Memory layer
        tags: Tags list
        source: Source identifier
        project: Project identifier
    """
    from .models import StoreMemoryRequest

    try:
        # Check if client has async methods
        if hasattr(client, "store_async"):
            memory_request = StoreMemoryRequest(
                content=content,
                layer=layer,
                tags=tags,
                source=source,
                project=project or "default",
            )
            await client.store_async(memory_request)
        else:
            # Fallback to sync method in executor
            await asyncio.get_event_loop().run_in_executor(
                None,
                _store_memory_sync,
                client,
                content,
                layer,
                tags,
                source,
                project,
            )

        logger.debug(
            "trace_memory_stored_async",
            source=source,
            layer=layer,
            tags=tags,
        )
    except Exception as e:
        logger.error(
            "trace_memory_store_error_async",
            source=source,
            error=str(e),
        )
