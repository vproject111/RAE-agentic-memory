# apps/memory-api/logging_config.py
"""
Enterprise-grade logging configuration for RAE Memory API.

This module implements sophisticated logging with:
- Structured logging via structlog
- Configurable log levels for different components
- Separation between application logs and library logs
- JSON output for production parsing
- Clean, readable output for development

Operational Excellence:
- Library logs (uvicorn, asyncpg, httpx) can be set to WARNING to reduce noise
- Application logs maintain INFO level for visibility
- All levels are configurable via environment variables
"""

import logging
import re
import sys

import structlog
from structlog.types import Processor

# Conditionally import OpenTelemetry
try:
    from opentelemetry.trace import get_current_span

    opentelemetry_installed = True
except ImportError:
    opentelemetry_installed = False

# Pre-compile regex for performance
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
KEY_REGEX = re.compile(
    r'(api[_-]?key|secret|token)=([\'"]?)([a-zA-Z0-9\-_]{8,})\2', re.IGNORECASE
)


def pii_masking_processor(logger, method_name, event_dict):
    """
    [ISO 27001] Masks PII (Emails, Keys) in log messages and dictionary values.
    """
    # 1. Mask message if it's a string
    if isinstance(event_dict.get("event"), str):
        event_dict["event"] = EMAIL_REGEX.sub("[EMAIL]", event_dict["event"])
        event_dict["event"] = KEY_REGEX.sub(r"\1=[REDACTED]", event_dict["event"])

    # 2. Iterate over keys to mask values
    for key, value in event_dict.items():
        if isinstance(value, str):
            # Mask common sensitive keys
            if (
                "key" in key.lower()
                or "secret" in key.lower()
                or "password" in key.lower()
            ):
                if len(value) > 4:  # Don't mask short non-sensitive values
                    event_dict[key] = "***"
            else:
                # General regex masking
                value = EMAIL_REGEX.sub("[EMAIL]", value)
                event_dict[key] = value

    return event_dict


def add_trace_id_to_log(logger, method_name, event_dict):
    """
    Processor to add the current OpenTelemetry trace_id and span_id to log events.
    """
    if not opentelemetry_installed:
        return event_dict

    span = get_current_span()
    span_context = span.get_span_context()
    if span_context.is_valid:  # is_valid is a property, not a method
        event_dict["trace_id"] = f"{span_context.trace_id:x}"
        event_dict["span_id"] = f"{span_context.span_id:x}"
    return event_dict


def setup_logging():
    """
    Set up enterprise-grade structured logging for the application.

    Configures different log levels for:
    - External libraries (uvicorn, asyncpg, httpx, celery) - controlled by LOG_LEVEL
    - RAE application code - controlled by RAE_APP_LOG_LEVEL

    This separation ensures production logs are clean while maintaining
    visibility into application behavior.
    """
    # Import settings here to avoid circular imports
    from apps.memory_api.config import settings

    # Parse log levels from configuration
    external_log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.WARNING)
    app_log_level = getattr(logging, settings.RAE_APP_LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        pii_masking_processor,  # [ISO 27001]
        structlog.processors.StackInfoRenderer(),
    ]

    # Conditionally add the OpenTelemetry processor
    if opentelemetry_installed and settings.OTEL_TRACES_ENABLED:
        shared_processors.insert(4, add_trace_id_to_log)

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # These run after all processors from structlog.configure()
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Configure root logger with external library level
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(external_log_level)

    # Configure application loggers with app-specific level
    app_logger = logging.getLogger("apps.memory_api")
    app_logger.setLevel(app_log_level)

    # Configure external library loggers explicitly
    # These libraries can be noisy on INFO level in production
    external_loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "asyncpg",
        "httpx",
        "httpcore",
        "celery",
        "celery.worker",
        "kombu",
        "amqp",
    ]

    for logger_name in external_loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(external_log_level)

    # Disable uvicorn's access log completely (we have our own middleware)
    logging.getLogger("uvicorn.access").disabled = True

    # Log the configuration for visibility
    structlog.get_logger(__name__).info(
        "logging_configured",
        external_log_level=settings.LOG_LEVEL,
        app_log_level=settings.RAE_APP_LOG_LEVEL,
    )
