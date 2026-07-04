"""
OpenTelemetry Configuration - Enterprise Distributed Tracing

This module configures OpenTelemetry for comprehensive distributed tracing across:
- FastAPI HTTP requests
- Database queries (PostgreSQL via asyncpg/psycopg2)
- Redis operations
- External HTTP requests
- LLM API calls

Traces are exported to OTLP-compatible backends:
- Jaeger (local development)
- Tempo (Grafana Cloud)
- Elastic APM
- AWS X-Ray
- Google Cloud Trace

Environment Variables:
- OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (default: http://localhost:4317)
- OTEL_SERVICE_NAME: Service name (default: rae-memory-api)
- OTEL_TRACES_ENABLED: Enable tracing (default: true)
- OTEL_EXPORTER_TYPE: otlp, jaeger, console (default: otlp)
"""

import os
from typing import TYPE_CHECKING, Any

import structlog

# Optional OpenTelemetry imports
try:  # pragma: no cover
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    OPENTELEMETRY_AVAILABLE = True
except ImportError:  # pragma: no cover
    trace = None  # type: ignore[assignment]
    OTLPSpanExporter = None  # type: ignore[assignment,misc]
    AsyncPGInstrumentor = None  # type: ignore[assignment,misc]
    CeleryInstrumentor = None  # type: ignore[assignment,misc]
    FastAPIInstrumentor = None  # type: ignore[assignment,misc]
    LoggingInstrumentor = None  # type: ignore[assignment,misc]
    Psycopg2Instrumentor = None  # type: ignore[assignment,misc]
    RedisInstrumentor = None  # type: ignore[assignment,misc]
    RequestsInstrumentor = None  # type: ignore[assignment,misc]
    HTTPXClientInstrumentor = None  # type: ignore[assignment,misc]
    SERVICE_NAME = None  # type: ignore[assignment]
    SERVICE_VERSION = None  # type: ignore[assignment]
    Resource = None  # type: ignore[assignment,misc]
    TracerProvider = None  # type: ignore[assignment,misc]
    BatchSpanProcessor = None  # type: ignore[assignment,misc]
    ConsoleSpanExporter = None  # type: ignore[assignment,misc]
    OPENTELEMETRY_AVAILABLE = False

if TYPE_CHECKING:
    from opentelemetry import trace  # noqa: F401
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: F401
        OTLPSpanExporter,
    )
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor  # noqa: F401
    from opentelemetry.instrumentation.celery import CeleryInstrumentor  # noqa: F401
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # noqa: F401
    from opentelemetry.instrumentation.httpx import (  # noqa: F401
        HTTPXClientInstrumentor,
    )
    from opentelemetry.instrumentation.logging import LoggingInstrumentor  # noqa: F401
    from opentelemetry.instrumentation.psycopg2 import (  # noqa: F401
        Psycopg2Instrumentor,
    )
    from opentelemetry.instrumentation.redis import RedisInstrumentor  # noqa: F401
    from opentelemetry.instrumentation.requests import (  # noqa: F401
        RequestsInstrumentor,
    )
    from opentelemetry.sdk.resources import (  # noqa: F401
        SERVICE_NAME,
        SERVICE_VERSION,
        Resource,
    )
    from opentelemetry.sdk.trace import TracerProvider  # noqa: F401
    from opentelemetry.sdk.trace.export import (  # noqa: F401
        BatchSpanProcessor,
        ConsoleSpanExporter,
    )

logger = structlog.get_logger(__name__)


# ============================================================================
# Configuration
# ============================================================================

OTEL_ENABLED = os.getenv("OTEL_TRACES_ENABLED", "true").lower() == "true"
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "rae-memory-api")
OTEL_SERVICE_VERSION = os.getenv("OTEL_SERVICE_VERSION", "2.0.0-enterprise")
OTEL_EXPORTER_ENDPOINT = os.getenv(
    "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
)
OTEL_EXPORTER_TYPE = os.getenv("OTEL_EXPORTER_TYPE", "otlp")  # otlp, console, none


# ============================================================================
# Tracer Provider Setup
# ============================================================================


def setup_opentelemetry():
    """
    Initialize OpenTelemetry tracing with configured exporter.

    This function should be called once during application startup,
    before any instrumented code runs.

    Returns:
        TracerProvider instance if successful, None otherwise
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.info(
            "opentelemetry_disabled",
            reason="OpenTelemetry packages not installed. "
            "Install with: pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-otlp-proto-grpc "
            "opentelemetry-instrumentation-fastapi "
            "opentelemetry-instrumentation-logging "
            "opentelemetry-instrumentation-psycopg2 "
            "opentelemetry-instrumentation-redis "
            "opentelemetry-instrumentation-requests",
        )
        return None

    if not OTEL_ENABLED:
        logger.info("opentelemetry_disabled", reason="OTEL_TRACES_ENABLED=false")
        return None

    # Check if we are in a container and trying to export to localhost
    if os.path.exists("/.dockerenv") and "localhost" in OTEL_EXPORTER_ENDPOINT:
        logger.info(
            "opentelemetry_disabled",
            reason="Inside container but endpoint points to localhost. Set correct OTEL_EXPORTER_OTLP_ENDPOINT if tracing is needed.",
        )
        return None

    try:
        # Create resource with service metadata
        resource = Resource.create(  # type: ignore[misc]
            {
                SERVICE_NAME: OTEL_SERVICE_NAME,  # type: ignore[dict-item]
                SERVICE_VERSION: OTEL_SERVICE_VERSION,  # type: ignore[dict-item]
                "deployment.environment": os.getenv("ENVIRONMENT", "development"),
                "service.namespace": "rae",
                "service.instance.id": os.getenv("HOSTNAME", "localhost"),
            }
        )

        # Create tracer provider
        tracer_provider = TracerProvider(resource=resource)  # type: ignore[misc]

        # Configure exporter based on type
        if OTEL_EXPORTER_TYPE == "console":
            # Console exporter for debugging
            span_exporter: Any = ConsoleSpanExporter()  # type: ignore[misc]
            logger.info("opentelemetry_console_exporter", service=OTEL_SERVICE_NAME)
        elif OTEL_EXPORTER_TYPE == "otlp":
            # OTLP exporter (default) for Jaeger, Tempo, etc.
            span_exporter = OTLPSpanExporter(  # type: ignore[misc]
                endpoint=OTEL_EXPORTER_ENDPOINT,
                insecure=True,  # Use TLS in production
            )
            logger.info(
                "opentelemetry_otlp_exporter",
                service=OTEL_SERVICE_NAME,
                endpoint=OTEL_EXPORTER_ENDPOINT,
            )
        else:
            logger.warning("opentelemetry_no_exporter", type=OTEL_EXPORTER_TYPE)
            return None

        # Add batch span processor (buffers spans for efficiency)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))  # type: ignore[arg-type]

        # Set global tracer provider
        trace.set_tracer_provider(tracer_provider)  # type: ignore[union-attr]

        logger.info(
            "opentelemetry_initialized",
            service=OTEL_SERVICE_NAME,
            version=OTEL_SERVICE_VERSION,
            exporter=OTEL_EXPORTER_TYPE,
        )

        return tracer_provider

    except Exception as e:
        logger.error("opentelemetry_setup_failed", error=str(e))
        return None


# ============================================================================
# Auto-Instrumentation
# ============================================================================


def instrument_fastapi(app):
    """
    Instrument FastAPI application with OpenTelemetry.

    This adds automatic tracing for all HTTP requests, including:
    - Request/response timing
    - HTTP method, path, status code
    - Request headers (filtered)
    - Exceptions and errors

    Args:
        app: FastAPI application instance
    """
    if not OPENTELEMETRY_AVAILABLE or not OTEL_ENABLED:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)  # type: ignore[union-attr]
        logger.info("opentelemetry_fastapi_instrumented")
    except Exception as e:
        logger.error("opentelemetry_fastapi_failed", error=str(e))


def instrument_libraries():
    """
    Instrument common libraries for automatic tracing.

    This adds tracing for:
    - HTTP requests (requests library)
    - PostgreSQL queries (psycopg2 and asyncpg)
    - Redis operations (redis-py)
    - Python logging (adds trace context to logs)
    - Celery tasks (background job processing)
    """
    if not OPENTELEMETRY_AVAILABLE or not OTEL_ENABLED:
        return

    try:
        # Instrument requests library (for external HTTP calls)
        RequestsInstrumentor().instrument()  # type: ignore[misc]
        logger.info("opentelemetry_requests_instrumented")

        # Instrument HTTPX (for async external HTTP calls)
        if HTTPXClientInstrumentor is not None:
            HTTPXClientInstrumentor().instrument()  # type: ignore[misc]
            logger.info("opentelemetry_httpx_instrumented")

        # Instrument PostgreSQL (psycopg2)
        Psycopg2Instrumentor().instrument()  # type: ignore[misc]
        logger.info("opentelemetry_psycopg2_instrumented")

        # Instrument PostgreSQL (asyncpg)
        AsyncPGInstrumentor().instrument()  # type: ignore[misc]
        logger.info("opentelemetry_asyncpg_instrumented")

        # Instrument Redis
        RedisInstrumentor().instrument()  # type: ignore[misc]
        logger.info("opentelemetry_redis_instrumented")

        # Instrument Celery
        CeleryInstrumentor().instrument()  # type: ignore[misc]
        logger.info("opentelemetry_celery_instrumented")

        # Instrument logging (adds trace_id to logs)
        LoggingInstrumentor().instrument(set_logging_format=False)  # type: ignore[misc]
        logger.info("opentelemetry_logging_instrumented")

    except Exception as e:
        logger.error("opentelemetry_library_instrumentation_failed", error=str(e))


# ============================================================================
# Custom Span Helpers
# ============================================================================


class NoOpSpan:
    """No-op implementation of OTel Span."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_attribute(self, key, value):
        pass

    def record_exception(self, exception):
        pass

    def set_status(self, status):
        pass

    def is_recording(self):
        return False

    def end(self):
        pass


class NoOpTracer:
    """No-op implementation of OTel Tracer."""

    def start_as_current_span(self, name, **kwargs):
        return NoOpSpan()

    def start_span(self, name, **kwargs):
        return NoOpSpan()


def get_tracer(name: str = OTEL_SERVICE_NAME):
    """
    Get a tracer instance for creating custom spans.

    Usage:
        tracer = get_tracer("my-component")
        with tracer.start_as_current_span("my-operation") as span:
            span.set_attribute("custom.key", "value")
            # ... do work ...

    Returns:
        Tracer instance (OpenTelemetry or NoOp)
    """
    if not OPENTELEMETRY_AVAILABLE:
        return NoOpTracer()

    return trace.get_tracer(name, OTEL_SERVICE_VERSION)  # type: ignore[union-attr]


def add_span_attributes(**attributes):
    """
    Add attributes to the current active span.

    Usage:
        add_span_attributes(
            user_id="user123",
            tenant_id="tenant456",
            operation="memory_create"
        )
    """
    if not OPENTELEMETRY_AVAILABLE:
        return

    span = trace.get_current_span()  # type: ignore[union-attr]
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def record_exception(exception: Exception):
    """
    Record an exception in the current span.

    Usage:
        try:
            # ... code that might fail ...
        except Exception as e:
            record_exception(e)
            raise
    """
    if not OPENTELEMETRY_AVAILABLE:
        return

    span = trace.get_current_span()  # type: ignore[union-attr]
    if span.is_recording():
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR))  # type: ignore[union-attr]


# ============================================================================
# Custom Instrumentation for LLM Calls
# ============================================================================


class LLMTracer:
    """
    Custom tracer for LLM API calls.

    Adds detailed tracing for expensive LLM operations, including:
    - Model name and provider
    - Token counts (input/output)
    - Cost information
    - Cache hits
    - Latency

    Usage:
        async with LLMTracer.trace(model="gpt-4o-mini", operation="embedding"):
            result = await llm_client.generate(...)
            LLMTracer.record_tokens(input=1000, output=500)
            LLMTracer.record_cost(0.0025)
    """

    @staticmethod
    def trace(model: str, operation: str, provider: str = "unknown"):
        """
        Create a span for an LLM operation.

        Returns:
            Span instance if OpenTelemetry is available, None otherwise
        """
        if not OPENTELEMETRY_AVAILABLE:
            return None

        tracer = get_tracer("rae.llm")
        if tracer is None:
            return None

        span = tracer.start_span(f"llm.{operation}")
        span.set_attribute("llm.model", model)
        span.set_attribute("llm.provider", provider)
        span.set_attribute("llm.operation", operation)
        return span

    @staticmethod
    def record_tokens(input_tokens: int, output_tokens: int):
        """Record token usage in current span."""
        if not OPENTELEMETRY_AVAILABLE:
            return

        add_span_attributes(
            llm_input_tokens=input_tokens,
            llm_output_tokens=output_tokens,
            llm_total_tokens=input_tokens + output_tokens,
        )

    @staticmethod
    def record_cost(cost_usd: float):
        """Record cost in current span."""
        if not OPENTELEMETRY_AVAILABLE:
            return

        add_span_attributes(llm_cost_usd=cost_usd)

    @staticmethod
    def record_cache_hit(is_hit: bool):
        """Record cache hit/miss."""
        if not OPENTELEMETRY_AVAILABLE:
            return

        add_span_attributes(llm_cache_hit=is_hit)


# ============================================================================
# Deployment Examples
# ============================================================================

"""
=== Local Development with Jaeger ===

1. Start Jaeger (all-in-one):
   docker run -d --name jaeger \
     -p 4317:4317 \
     -p 16686:16686 \
     jaegertracing/all-in-one:latest

2. Configure environment:
   export OTEL_TRACES_ENABLED=true
   export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
   export OTEL_SERVICE_NAME=rae-memory-api

3. View traces:
   http://localhost:16686


=== Grafana Cloud Tempo ===

1. Get OTLP endpoint and API key from Grafana Cloud

2. Configure environment:
   export OTEL_TRACES_ENABLED=true
   export OTEL_EXPORTER_OTLP_ENDPOINT=https://tempo-prod-xx-xxx.grafana.net:443
   export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-api-key>"


=== Elastic APM ===

1. Get APM Server URL and secret token

2. Configure environment:
   export OTEL_TRACES_ENABLED=true
   export OTEL_EXPORTER_OTLP_ENDPOINT=https://apm-server:8200
   export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <secret-token>"


=== AWS X-Ray (via ADOT Collector) ===

1. Deploy AWS Distro for OpenTelemetry Collector

2. Configure environment:
   export OTEL_TRACES_ENABLED=true
   export OTEL_EXPORTER_OTLP_ENDPOINT=http://adot-collector:4317


=== Kubernetes with Tempo ===

apiVersion: v1
kind: ConfigMap
metadata:
  name: rae-otel-config
data:
  OTEL_TRACES_ENABLED: "true"
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://tempo:4317"
  OTEL_SERVICE_NAME: "rae-memory-api"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rae-api
spec:
  template:
    spec:
      containers:
      - name: api
        envFrom:
        - configMapRef:
            name: rae-otel-config
"""


# ============================================================================
# Trace Context Propagation
# ============================================================================

"""
For distributed tracing across services, trace context is automatically
propagated via W3C TraceContext headers:

- traceparent: 00-<trace-id>-<span-id>-<flags>
- tracestate: <vendor-specific-state>

When calling external services or Celery tasks, ensure these headers
are forwarded to maintain the trace chain.

Example with httpx:
    from opentelemetry.propagate import inject

    headers = {}
    inject(headers)  # Adds traceparent/tracestate
    response = await httpx.get(url, headers=headers)

Example with Celery:
    from opentelemetry.propagate import inject

    headers = {}
    inject(headers)
    task.apply_async(args=(...), headers=headers)
"""
