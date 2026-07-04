"""OpenTelemetry telemetry infrastructure for orchestrator.

Provides 3-layer observability:
1. Traces - execution flow tracking
2. Metrics - quantitative measurements
3. Logs - detailed textual information
"""

import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    metrics = None


logger = logging.getLogger(__name__)


@dataclass
class TelemetryConfig:
    """Configuration for telemetry."""

    enabled: bool = True
    service_name: str = "orchestrator"
    otlp_endpoint: Optional[str] = None  # e.g., "http://localhost:4318"
    environment: str = "development"

    @classmethod
    def from_env(cls) -> "TelemetryConfig":
        """Load config from environment variables."""
        return cls(
            enabled=os.getenv("OTEL_ENABLED", "true").lower() == "true",
            service_name=os.getenv("OTEL_SERVICE_NAME", "orchestrator"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"),
            environment=os.getenv("DEPLOYMENT_ENVIRONMENT", "development"),
        )


class OrchestratorTelemetry:
    """Telemetry manager for orchestrator.

    Provides traces, metrics, and structured logging.
    """

    def __init__(self, config: Optional[TelemetryConfig] = None):
        """Initialize telemetry.

        Args:
            config: Telemetry configuration (defaults to env-based config)
        """
        self.config = config or TelemetryConfig.from_env()

        if not self.config.enabled:
            logger.info("Telemetry disabled")
            self.tracer = None
            self.meter = None
            self._metrics = {}
            return

        if not OTEL_AVAILABLE:
            logger.warning(
                "OpenTelemetry not available. Install with: "
                "pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp"
            )
            self.tracer = None
            self.meter = None
            self._metrics = {}
            return

        # Initialize metrics dict
        self._metrics = {}

        # Initialize OpenTelemetry
        self._setup_tracing()
        self._setup_metrics()

        logger.info(
            f"Telemetry initialized: service={self.config.service_name}, "
            f"endpoint={self.config.otlp_endpoint}"
        )

    def _setup_tracing(self):
        """Setup distributed tracing."""
        resource = Resource(
            attributes={
                SERVICE_NAME: self.config.service_name,
                "deployment.environment": self.config.environment,
            }
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Add OTLP exporter if endpoint configured
        if self.config.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True,  # For local development
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(__name__)

    def _setup_metrics(self):
        """Setup metrics collection."""
        resource = Resource(
            attributes={
                SERVICE_NAME: self.config.service_name,
                "deployment.environment": self.config.environment,
            }
        )

        # Create metric reader
        if self.config.otlp_endpoint:
            otlp_exporter = OTLPMetricExporter(
                endpoint=self.config.otlp_endpoint,
                insecure=True,
            )
            reader = PeriodicExportingMetricReader(
                otlp_exporter, export_interval_millis=10000
            )
        else:
            reader = None

        # Create meter provider
        provider = MeterProvider(
            resource=resource, metric_readers=[reader] if reader else []
        )
        metrics.set_meter_provider(provider)
        self.meter = metrics.get_meter(__name__)

        # Initialize metrics
        self._init_metrics()

    def _init_metrics(self):
        """Initialize all orchestrator metrics."""
        if not self.meter:
            self._metrics = {}
            return

        # Task metrics
        self._metrics["tasks_total"] = self.meter.create_counter(
            name="orchestrator_tasks_total",
            description="Total number of tasks processed",
            unit="1",
        )

        self._metrics["task_duration"] = self.meter.create_histogram(
            name="orchestrator_task_duration_seconds",
            description="Task execution duration",
            unit="s",
        )

        # Step metrics
        self._metrics["steps_total"] = self.meter.create_counter(
            name="orchestrator_steps_total",
            description="Total number of steps processed",
            unit="1",
        )

        # LLM metrics
        self._metrics["llm_calls_total"] = self.meter.create_counter(
            name="orchestrator_llm_calls_total",
            description="Total LLM API calls",
            unit="1",
        )

        self._metrics["llm_tokens_total"] = self.meter.create_counter(
            name="orchestrator_llm_tokens_total",
            description="Total tokens consumed",
            unit="1",
        )

        self._metrics["llm_cost_usd"] = self.meter.create_counter(
            name="orchestrator_llm_cost_usd",
            description="Total LLM cost in USD",
            unit="USD",
        )

        # Quality gate metrics
        self._metrics["quality_gate_runs"] = self.meter.create_counter(
            name="orchestrator_quality_gate_runs_total",
            description="Total quality gate runs",
            unit="1",
        )

        self._metrics["quality_regressions"] = self.meter.create_counter(
            name="orchestrator_quality_regressions_total",
            description="Quality regressions detected",
            unit="1",
        )

        # Model routing
        self._metrics["model_routing"] = self.meter.create_counter(
            name="orchestrator_model_routing",
            description="Model routing decisions",
            unit="1",
        )

    @contextmanager
    def trace_task(self, task_id: str, task_area: str, task_risk: str):
        """Create span for task execution.

        Args:
            task_id: Task identifier
            task_area: Task area (core, math, api, docs, tests)
            task_risk: Risk level (low, medium, high)

        Yields:
            Span context manager
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            "task.run",
            attributes={
                "task.id": task_id,
                "task.area": task_area,
                "task.risk": task_risk,
            },
        ) as span:
            yield span

    @contextmanager
    def trace_step(self, step_id: str, step_type: str, step_risk: str):
        """Create span for step execution.

        Args:
            step_id: Step identifier
            step_type: Type of step
            step_risk: Risk level

        Yields:
            Span context manager
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            "step.run",
            attributes={
                "step.id": step_id,
                "step.type": step_type,
                "step.risk": step_risk,
            },
        ) as span:
            yield span

    @contextmanager
    def trace_llm_call(self, provider: str, model: str, role: str):
        """Create span for LLM call.

        Args:
            provider: LLM provider (gemini_cli, claude_api, local_ollama)
            model: Model name
            role: Agent role (planner, reviewer, implementer, etc.)

        Yields:
            Span context manager
        """
        if not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            "llm.call",
            attributes={
                "llm.provider": provider,
                "llm.model_name": model,
                "llm.role": role,
            },
        ) as span:
            yield span

    def record_task_complete(
        self, status: str, duration: float, task_area: str, task_risk: str
    ):
        """Record task completion metrics.

        Args:
            status: Task status (success, fail, human_required)
            duration: Task duration in seconds
            task_area: Task area
            task_risk: Risk level
        """
        if not self._metrics:
            return

        self._metrics["tasks_total"].add(
            1,
            attributes={
                "status": status,
                "task.area": task_area,
                "task.risk": task_risk,
            },
        )

        self._metrics["task_duration"].record(
            duration,
            attributes={
                "status": status,
                "task.area": task_area,
            },
        )

    def record_step_complete(self, step_type: str, status: str, attempt: int = 1):
        """Record step completion metrics.

        Args:
            step_type: Type of step
            status: Step status
            attempt: Attempt number
        """
        if not self._metrics:
            return

        self._metrics["steps_total"].add(
            1,
            attributes={
                "type": step_type,
                "status": status,
                "attempt": str(attempt),
            },
        )

    def record_llm_call(
        self,
        provider: str,
        model: str,
        role: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
    ):
        """Record LLM call metrics.

        Args:
            provider: LLM provider
            model: Model name
            role: Agent role
            input_tokens: Input token count
            output_tokens: Output token count
            cost_usd: Cost in USD
        """
        if not self._metrics:
            return

        attrs = {
            "provider": provider,
            "model": model,
            "role": role,
        }

        self._metrics["llm_calls_total"].add(1, attributes=attrs)

        if input_tokens or output_tokens:
            self._metrics["llm_tokens_total"].add(
                input_tokens + output_tokens, attributes={**attrs, "type": "total"}
            )

        if cost_usd > 0:
            self._metrics["llm_cost_usd"].add(cost_usd, attributes=attrs)

    def record_quality_gate(self, status: str, regression_type: Optional[str] = None):
        """Record quality gate execution.

        Args:
            status: Gate status (passed, failed)
            regression_type: Type of regression if failed
        """
        if not self._metrics:
            return

        self._metrics["quality_gate_runs"].add(1, attributes={"status": status})

        if regression_type:
            self._metrics["quality_regressions"].add(
                1, attributes={"type": regression_type}
            )

    def record_model_routing(
        self, task_risk: str, task_area: str, model_chosen: str, reason: str
    ):
        """Record model routing decision.

        Args:
            task_risk: Risk level
            task_area: Task area
            model_chosen: Selected model
            reason: Routing reason
        """
        if not self._metrics:
            return

        self._metrics["model_routing"].add(
            1,
            attributes={
                "task.risk": task_risk,
                "task.area": task_area,
                "model": model_chosen,
                "reason": reason,
            },
        )

    def log_routing_decision(
        self, task_id: str, step_id: str, role: str, model: str, reason: str
    ):
        """Log routing decision.

        Args:
            task_id: Task identifier
            step_id: Step identifier
            role: Agent role
            model: Selected model
            reason: Routing reason
        """
        logger.info(
            f"Routing: task={task_id} step={step_id} role={role} → "
            f"model={model} (reason: {reason})"
        )

    def log_quality_gate_failure(self, reason: str, details: str):
        """Log quality gate failure.

        Args:
            reason: Failure reason
            details: Detailed information
        """
        logger.error(f"Quality gate FAILED: {reason}")
        logger.error(f"Details: {details}")

    def log_cross_review_rejection(
        self, reviewer_model: str, implementer_model: str, reason: str
    ):
        """Log cross-review rejection.

        Args:
            reviewer_model: Reviewer model
            implementer_model: Implementer model
            reason: Rejection reason
        """
        logger.warning(
            f"Code-Reviewer ({reviewer_model}) REJECTED patch from "
            f"Implementer ({implementer_model}): {reason}"
        )


# Global telemetry instance
_telemetry: Optional[OrchestratorTelemetry] = None


def init_telemetry(config: Optional[TelemetryConfig] = None) -> OrchestratorTelemetry:
    """Initialize global telemetry instance.

    Args:
        config: Optional telemetry configuration

    Returns:
        Telemetry instance
    """
    global _telemetry
    _telemetry = OrchestratorTelemetry(config)
    return _telemetry


def get_telemetry() -> OrchestratorTelemetry:
    """Get global telemetry instance.

    Returns:
        Telemetry instance

    Raises:
        RuntimeError: If telemetry not initialized
    """
    if _telemetry is None:
        # Auto-initialize with defaults
        return init_telemetry()
    return _telemetry
