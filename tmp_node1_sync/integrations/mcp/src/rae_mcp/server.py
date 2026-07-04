"""
Enterprise-grade MCP Server for RAE Memory Engine

This server implements the Model Context Protocol (MCP) to provide:
- Tools for memory operations (save, search, get context)
- Resources for project reflections
- Prompts for continuous context injection

The server communicates via STDIO using JSON-RPC protocol.
"""

import asyncio
import logging
import os
import re
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import mcp.server.stdio
import mcp.types as types
import structlog
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from prometheus_client import Counter, Histogram
from structlog.dev import ConsoleRenderer
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    format_exc_info,
)
from structlog.stdlib import BoundLogger, LoggerFactory, add_log_level, add_logger_name


def _configure_logging():
    """
    Configures structlog to output to stderr when stdin is not a TTY
    (i.e., when piped), and to stdout otherwise. This prevents logs
    from mixing with JSON-RPC responses when the script is used as a CLI tool.
    """
    shared_processors: List[Any] = [
        add_logger_name,
        add_log_level,
        TimeStamper(fmt="iso"),
        format_exc_info,  # Includes exception info in logs
        StackInfoRenderer(),  # Includes stack info
    ]

    if not sys.stdin.isatty():
        # Running in a non-interactive pipe, output structured logs to stderr
        structlog.configure(  # type: ignore[arg-type]
            processors=shared_processors
            + [
                JSONRenderer(),
            ],
            logger_factory=LoggerFactory(),
            wrapper_class=BoundLogger,
            cache_logger_on_first_use=True,
        )
        handler = logging.StreamHandler(sys.stderr)
    else:
        # Running interactively, output readable logs to stdout
        structlog.configure(  # type: ignore[arg-type]
            processors=shared_processors
            + [
                ConsoleRenderer(),
            ],
            logger_factory=LoggerFactory(),
            wrapper_class=BoundLogger,
            cache_logger_on_first_use=True,
        )
        handler = logging.StreamHandler(sys.stdout)

    logging.basicConfig(handlers=[handler], level=logging.INFO)


# Initialise logging before logger = structlog.get_logger()
_configure_logging()

logger = structlog.get_logger(__name__)

# =============================================================================
# OPENTELEMETRY CONFIGURATION
# =============================================================================

# Initialize a TracerProvider early to ensure `trace` is always available.

tp = TracerProvider()
trace.set_tracer_provider(tp)

# Initialize OpenTelemetry (optional, disabled by default)
OTEL_ENABLED = os.getenv("OTEL_ENABLED", "false").lower() == "true"
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "rae-mcp-server")
OTEL_EXPORTER = os.getenv("OTEL_EXPORTER", "console")  # console, jaeger, otlp

if OTEL_ENABLED:
    # The tracer provider is already set above. Now configure exporters if enabled.
    if OTEL_EXPORTER == "console":
        span_processor = BatchSpanProcessor(ConsoleSpanExporter())
        tp.add_span_processor(span_processor)
    # Add support for other exporters (Jaeger, OTLP) in future

    # Instrument httpx for automatic HTTP tracing
    HTTPXClientInstrumentor().instrument()

    logger.info(
        "opentelemetry_initialized",
        enabled=True,
        service_name=OTEL_SERVICE_NAME,
        exporter=OTEL_EXPORTER,
    )
else:
    logger.info("opentelemetry_disabled")
    # No additional action needed here, as a default TracerProvider is already set
    # and acts as a no-op if no exporters are added.

# Get tracer instance (will always work now)
tracer = trace.get_tracer(__name__)

# Prometheus Metrics
TOOLS_CALLED = Counter(
    "mcp_tools_called_total", "Total MCP tool invocations", ["tool_name"]
)
TOOL_ERRORS = Counter(
    "mcp_tool_errors_total", "Total MCP tool errors", ["tool_name", "error_type"]
)
TOOL_DURATION = Histogram(
    "mcp_tool_duration_seconds", "MCP tool execution duration", ["tool_name"]
)

RESOURCES_READ = Counter(
    "mcp_resources_read_total", "Total MCP resource reads", ["resource_uri"]
)
RESOURCE_ERRORS = Counter(
    "mcp_resource_errors_total", "Total MCP resource errors", ["resource_uri"]
)
RESOURCE_DURATION = Histogram(
    "mcp_resource_duration_seconds", "MCP resource read duration", ["resource_uri"]
)

PROMPTS_REQUESTED = Counter(
    "mcp_prompts_requested_total", "Total MCP prompt requests", ["prompt_name"]
)
PROMPT_ERRORS = Counter(
    "mcp_prompt_errors_total", "Total MCP prompt errors", ["prompt_name"]
)
PROMPT_DURATION = Histogram(
    "mcp_prompt_duration_seconds", "MCP prompt request duration", ["prompt_name"]
)


# PII Scrubber for Logging
class PIIScrubber:
    """
    Scrubs Personally Identifiable Information (PII) from log arguments.

    Detects and masks:
    - API keys, tokens, secrets
    - Passwords
    - Email addresses
    - Credit card numbers
    - IP addresses
    - Phone numbers
    - SSNs
    """

    # Patterns for PII detection
    PATTERNS = {
        "api_key": re.compile(
            r'(?i)(api[_-]?key|token|secret|password|passwd|pwd)[\s:=]+["\"]?([a-zA-Z0-9_\-\.]){16,}["\"]?'
        ),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        "credit_card": re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
        "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    }

    # Sensitive field names that should always be masked
    SENSITIVE_FIELDS = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "api_key",
        "apikey",
        "token",
        "access_token",
        "refresh_token",
        "auth_token",
        "session_token",
        "private_key",
        "secret_key",
        "client_secret",
        "api_secret",
    }

    @classmethod
    def scrub(cls, data: Any, max_content_length: int = 100) -> Any:
        """Scrub PII from data structure."""
        if isinstance(data, dict):
            return {
                key: cls._scrub_value(key, value, max_content_length)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [cls.scrub(item, max_content_length) for item in data]
        elif isinstance(data, str):
            return cls._scrub_string(data, max_content_length)
        else:
            return data

    @classmethod
    def _scrub_value(cls, key: str, value: Any, max_length: int) -> Any:
        """Scrub a value based on its key name and content."""
        # Check if field name is sensitive
        if isinstance(key, str) and key.lower() in cls.SENSITIVE_FIELDS:
            return "***REDACTED***"

        # Recursively scrub nested structures
        if isinstance(value, dict):
            return cls.scrub(value, max_length)
        elif isinstance(value, list):
            return [cls.scrub(item, max_length) for item in value]
        elif isinstance(value, str):
            # For content fields, truncate long strings
            if key == "content" and len(value) > max_length:
                scrubbed = cls._scrub_string(value[:max_length], max_length)
                return f"{scrubbed}... [truncated {len(value)} chars]"
            return cls._scrub_string(value, max_length)
        else:
            return value

    @classmethod
    def _scrub_string(cls, text: str, max_length: int = 100) -> str:
        """Scrub PII patterns from a string."""
        if not isinstance(text, str):
            return text

        scrubbed = text

        # Apply regex patterns
        for pattern_name, pattern in cls.PATTERNS.items():
            if pattern_name == "api_key":
                # Special handling for API keys (mask the value, keep the field name)
                scrubbed = pattern.sub(r"\1=***REDACTED***", scrubbed)
            elif pattern_name == "email":
                # Mask email but keep domain
                def mask_email(match):
                    email = match.group(0)
                    parts = email.split("@")
                    if len(parts) == 2:
                        return f"{parts[0][:2]}***@{parts[1]}"
                    return "***@***"

                scrubbed = pattern.sub(mask_email, scrubbed)
            elif pattern_name == "credit_card":
                scrubbed = pattern.sub(
                    lambda m: f"****-****-****-{m.group(0)[-4:]}", scrubbed
                )
            elif pattern_name == "ip_address":
                scrubbed = pattern.sub(
                    lambda m: f"{'.'.join(m.group(0).split('.')[:2])}.***.**", scrubbed
                )
            else:
                scrubbed = pattern.sub("***REDACTED***", scrubbed)

        return scrubbed


# Configuration from environment
RAE_API_URL = os.getenv("RAE_API_URL", "http://localhost:8001")
RAE_API_KEY = os.getenv("RAE_API_KEY", "dev-key")
RAE_PROJECT_ID = os.getenv("RAE_PROJECT_ID", "default-project")
RAE_TENANT_ID = os.getenv("RAE_TENANT_ID", "default-tenant")

# Memory layer mapping: MCP human-friendly names -> RAE API codes
LAYER_MAPPING = {
    "episodic": "em",  # Episodic Memory
    "working": "stm",  # Short-Term Memory (working context)
    "semantic": "ltm",  # Long-Term Memory (semantic knowledge)
    "ltm": "ltm",  # Long-Term Memory (direct)
    "reflective": "rm",  # Reflective Memory
    # Also support direct API codes
    "em": "em",
    "stm": "stm",
    "rm": "rm",
}

# Initialize MCP Server
server = Server("rae-memory")


class RAEMemoryClient:
    """
    Enterprise-grade client for RAE Memory API.

    Provides async methods for memory operations with comprehensive
    error handling and structured logging.
    """

    def __init__(
        self,
        api_url: str = RAE_API_URL,
        api_key: str = RAE_API_KEY,
        tenant_id: str = RAE_TENANT_ID,
    ):
        self.api_url = api_url
        self.headers = {
            "X-API-Key": api_key,
            "X-Tenant-Id": tenant_id,
            "Content-Type": "application/json",
        }
        self.base_url = f"{api_url}/v1"

    async def store_memory(
        self,
        content: str,
        source: str,
        layer: str = "em",
        tags: Optional[List[str]] = None,
        project: str = RAE_PROJECT_ID,
        importance: float = 0.5,
    ) -> Dict[str, Any]:
        """Store a memory in RAE."""
        with tracer.start_as_current_span("rae.mcp.store_memory") as span:
            # Add span attributes for observability
            span.set_attribute("memory.layer", layer)
            span.set_attribute("memory.source", source)
            span.set_attribute("memory.tags_count", len(tags or []))
            span.set_attribute("memory.project", project)
            span.set_attribute("memory.importance", importance)

            payload = {
                "content": content,
                "source": source,
                "layer": layer,
                "tags": tags or [],
                "project": project,
                "importance": importance,
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/memory/store",
                        json=payload,
                        headers=self.headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    result = response.json()

                    memory_id = result.get("id")
                    span.set_attribute("memory.id", memory_id)

                    logger.info(
                        "memory_stored",
                        memory_id=memory_id,
                        source=source,
                        layer=layer,
                    )

                    return result  # type: ignore[no-any-return]

            except httpx.HTTPStatusError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", "http_error")
                span.set_attribute("http.status_code", e.response.status_code)
                logger.error(
                    "memory_store_http_error",
                    status_code=e.response.status_code,
                    error=str(e),
                    response_text=e.response.text,
                )
                raise
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                logger.error("memory_store_error", error=str(e))
                raise

    async def search_memory(
        self,
        query: str,
        top_k: int = 5,
        project: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search RAE memory for relevant information."""
        with tracer.start_as_current_span("rae.mcp.search_memory") as span:
            # Add span attributes
            span.set_attribute("search.query", query)
            span.set_attribute("search.top_k", top_k)
            span.set_attribute("search.project", project or RAE_PROJECT_ID)

            payload = {
                "query_text": query,
                "k": top_k,
                "project": project or RAE_PROJECT_ID,
                "filters": filters or {},
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/memory/query",
                        json=payload,
                        headers=self.headers,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    result = response.json()

                    results = result.get("results", [])
                    span.set_attribute("search.result_count", len(results))

                    logger.info(
                        "memory_searched", query=query, result_count=len(results)
                    )

                    return results  # type: ignore[no-any-return]

            except httpx.HTTPStatusError as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", "http_error")
                span.set_attribute("http.status_code", e.response.status_code)
                logger.error(
                    "memory_search_http_error",
                    status_code=e.response.status_code,
                    error=str(e),
                    response_text=e.response.text,
                )
                raise
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                logger.error("memory_search_error", error=str(e))
                raise

    async def get_file_context(
        self,
        file_path: str,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get historical context about a file or module."""
        # Search by file path in source field
        query = f"file:{file_path}"

        return await self.search_memory(
            query=query, top_k=top_k, filters={"source": file_path}
        )

    async def get_latest_reflection(self, project: str = RAE_PROJECT_ID) -> str:
        """Get the latest project reflection."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/graph/reflection/hierarchical",
                    params={"project": project, "bucket_size": 10},
                    headers=self.headers,
                    timeout=60.0,
                )
                response.raise_for_status()
                result = response.json()

                summary = result.get("summary", "No reflection available.")

                logger.info(
                    "reflection_retrieved", project=project, summary_length=len(summary)
                )

                return summary  # type: ignore[no-any-return]

        except httpx.HTTPStatusError as e:
            logger.error(
                "reflection_http_error",
                status_code=e.response.status_code,
                error=str(e),
            )
            return "Error retrieving reflection."
        except Exception as e:
            logger.error("reflection_error", error=str(e))
            return "Error retrieving reflection."

    async def get_project_guidelines(
        self,
        project: str = RAE_PROJECT_ID,
    ) -> List[Dict[str, Any]]:
        """Get project guidelines from semantic memory."""
        return await self.search_memory(
            query="coding guidelines project conventions best practices",
            top_k=10,
            project=project,
            filters={"layer": "semantic"},
        )

    # ISO/IEC 42001 Compliance Methods

    async def request_approval(
        self,
        operation_type: str,
        operation_description: str,
        risk_level: str,
        resource_type: str,
        resource_id: str,
        requested_by: str,
    ) -> Dict[str, Any]:
        """Request approval for a high-risk operation."""
        payload = {
            "tenant_id": RAE_TENANT_ID,
            "project_id": RAE_PROJECT_ID,
            "operation_type": operation_type,
            "operation_description": operation_description,
            "risk_level": risk_level,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "requested_by": requested_by,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/v1/compliance/approvals",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("approval_request_error", error=str(e))
            raise

    async def check_approval_status(self, request_id: str) -> Dict[str, Any]:
        """Check approval request status."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/v1/compliance/approvals/{request_id}",
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("approval_status_error", error=str(e))
            raise

    async def get_circuit_breakers(self) -> List[Dict[str, Any]]:
        """Get all circuit breaker states."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/v1/compliance/circuit-breakers",
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("circuit_breakers_error", error=str(e))
            raise

    async def list_policies(self, policy_type: Optional[str] = None) -> Dict[str, Any]:
        """List governance policies."""
        params = {"tenant_id": RAE_TENANT_ID}
        if policy_type:
            params["policy_type"] = policy_type

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/v1/compliance/policies",
                    params=params,
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()  # type: ignore[no-any-return]

        except Exception as e:
            logger.error("policies_list_error", error=str(e))
            raise


# =============================================================================
# RATE LIMITING
# =============================================================================


class RateLimiter:
    """
    Simple in-memory rate limiter for MCP server.

    Tracks request counts per tenant within a sliding time window.
    Prevents abuse by limiting the number of tool calls per minute.

    Note: This is a simple implementation suitable for single-process servers.
    For distributed deployments, use Redis-based rate limiting.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """Initialize rate limiter."""
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}  # tenant_id -> timestamps

    def check_rate_limit(self, tenant_id: str) -> bool:
        """Check if request is within rate limit."""
        now = time.time()
        cutoff = now - self.window_seconds

        # Initialize tenant if not exists
        if tenant_id not in self._requests:
            self._requests[tenant_id] = []

        # Remove old timestamps outside window
        self._requests[tenant_id] = [
            ts for ts in self._requests[tenant_id] if ts > cutoff
        ]

        # Check if within limit
        if len(self._requests[tenant_id]) >= self.max_requests:
            logger.warning(
                "rate_limit_exceeded",
                tenant_id=tenant_id,
                request_count=len(self._requests[tenant_id]),
                limit=self.max_requests,
            )
            return False

        # Record this request
        self._requests[tenant_id].append(now)
        return True

    def get_remaining(self, tenant_id: str) -> int:
        """Get remaining requests for tenant."""
        now = time.time()
        cutoff = now - self.window_seconds

        if tenant_id not in self._requests:
            return self.max_requests

        # Count requests in current window
        recent = [ts for ts in self._requests[tenant_id] if ts > cutoff]
        return max(0, self.max_requests - len(recent))


# Initialize rate limiter
# Configuration via environment variables
RATE_LIMIT_ENABLED = os.getenv("MCP_RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("MCP_RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("MCP_RATE_LIMIT_WINDOW", "60"))

rate_limiter = RateLimiter(
    max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW
)

logger.info(
    "rate_limiter_initialized",
    enabled=RATE_LIMIT_ENABLED,
    max_requests=RATE_LIMIT_REQUESTS,
    window_seconds=RATE_LIMIT_WINDOW,
)

# Initialize RAE client
rae_client = RAEMemoryClient()


# =============================================================================
# MCP TOOLS IMPLEMENTATION
# =============================================================================


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List all available MCP tools."""
    return [
        types.Tool(
            name="save_memory",
            description=(
                "Store a memory in RAE for later retrieval. "
                "Use this to remember important information, decisions, "
                "code patterns, or any context that should be preserved."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content to remember",
                    },
                    "source": {
                        "type": "string",
                        "description": "Source identifier (e.g., file path, URL, 'user-input')",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization (e.g., ['bug', 'authentication'])",
                    },
                    "layer": {
                        "type": "string",
                        "enum": [
                            "episodic",
                            "working",
                            "semantic",
                            "ltm",
                            "reflective",
                        ],
                        "default": "episodic",
                        "description": (
                            "Memory layer: "
                            "episodic (recent events), "
                            "working (current task context), "
                            "semantic (concepts/guidelines), "
                            "ltm (long-term facts), "
                            "reflective (insights and learnings)"
                        ),
                    },
                    "importance": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.5,
                        "description": "Importance score (0.0=low, 0.5=medium, 1.0=critical)",
                    },
                },
                "required": ["content", "source"],
            },
        ),
        types.Tool(
            name="search_memory",
            description=(
                "Search RAE memory for relevant information. "
                "Use this to retrieve context, find similar patterns, "
                "or recall past decisions and solutions."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query describing what you're looking for",
                    },
                    "top_k": {
                        "type": "integer",
                        "default": 5,
                        "description": "Number of results to return (1-20)",
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_related_context",
            description=(
                "Get historical context about a specific file or module. "
                "Use this to understand what changes have been made, "
                "why certain decisions were made, or what issues have occurred."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (relative or absolute)",
                    },
                    "include_count": {
                        "type": "integer",
                        "default": 10,
                        "description": "Number of context items to include",
                    },
                },
                "required": ["file_path"],
            },
        ),
        # ISO/IEC 42001 Compliance Tools
        types.Tool(
            name="request_approval",
            description=(
                "Request human approval for high-risk operations. "
                "Use this for operations that require oversight, such as "
                "deleting data, modifying critical settings, or exporting sensitive information."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "operation_type": {
                        "type": "string",
                        "description": "Type of operation (e.g., 'delete', 'export', 'modify')",
                    },
                    "operation_description": {
                        "type": "string",
                        "description": "Human-readable description of what will be done",
                    },
                    "risk_level": {
                        "type": "string",
                        "enum": ["none", "low", "medium", "high", "critical"],
                        "description": "Risk level of the operation",
                    },
                    "resource_type": {
                        "type": "string",
                        "description": "Type of resource (e.g., 'memory', 'user_data', 'config')",
                    },
                    "resource_id": {
                        "type": "string",
                        "description": "Identifier of the resource",
                    },
                    "requested_by": {
                        "type": "string",
                        "description": "User ID requesting the operation",
                    },
                },
                "required": [
                    "operation_type",
                    "operation_description",
                    "risk_level",
                    "resource_type",
                    "resource_id",
                    "requested_by",
                ],
            },
        ),
        types.Tool(
            name="check_approval_status",
            description=(
                "Check the status of an approval request. "
                "Returns current status, approvers, and expiration time."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "UUID of the approval request",
                    },
                },
                "required": ["request_id"],
            },
        ),
        types.Tool(
            name="get_circuit_breakers",
            description=(
                "Get status of all circuit breakers in the system. "
                "Circuit breakers protect against cascading failures by "
                "failing fast when services are unhealthy."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        types.Tool(
            name="list_policies",
            description=(
                "List governance policies configured for the tenant. "
                "Includes data retention, access control, and approval workflows."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_type": {
                        "type": "string",
                        "enum": [
                            "data_retention",
                            "access_control",
                            "approval_workflow",
                            "trust_scoring",
                            "risk_assessment",
                            "human_oversight",
                        ],
                        "description": "Optional filter by policy type",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle MCP tool invocations."""
    # Track metrics
    start_time = time.time()
    TOOLS_CALLED.labels(tool_name=name).inc()

    # Create OpenTelemetry span for tool invocation
    with tracer.start_as_current_span(f"rae.mcp.tool.{name}") as span:
        span.set_attribute("tool.name", name)
        span.set_attribute("tool.tenant_id", RAE_TENANT_ID)

    # Check rate limit (if enabled)
    if RATE_LIMIT_ENABLED:
        if not rate_limiter.check_rate_limit(RAE_TENANT_ID):
            remaining = rate_limiter.get_remaining(RAE_TENANT_ID)
            error_msg = (
                f"⚠️ Rate limit exceeded\n\n"
                f"Tenant: {RAE_TENANT_ID}\n"
                f"Limit: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW}s\n"
                f"Remaining: {remaining}\n\n"
                f"Please wait a moment before trying again."
            )
            TOOL_ERRORS.labels(tool_name=name, error_type="rate_limit").inc()
            return [types.TextContent(type="text", text=error_msg)]

    # Scrub PII from arguments before logging
    scrubbed_arguments = PIIScrubber.scrub(arguments, max_content_length=200)
    logger.info("tool_called", tool=name, arguments=scrubbed_arguments)

    try:
        if name == "save_memory":
            # Extract arguments
            content = arguments.get("content")
            source = arguments.get("source")
            tags = arguments.get("tags", [])
            layer_input = arguments.get("layer", "episodic")
            importance = arguments.get("importance", 0.5)  # default medium importance

            # Map human-friendly layer name to API code
            layer = LAYER_MAPPING.get(layer_input, "em")  # default to episodic (em)

            # Validate
            if not content:
                return [
                    types.TextContent(type="text", text="Error: 'content' is required")
                ]
            if not source:
                return [
                    types.TextContent(type="text", text="Error: 'source' is required")
                ]

            # Store memory
            result = await rae_client.store_memory(
                content=content,
                source=source,
                layer=layer,
                tags=tags,
                importance=importance,
            )

            memory_id = result.get("id", "unknown")

            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"✓ Memory stored successfully\n"
                        f"ID: {memory_id}\n"
                        f"Layer: {layer_input}\n"
                        f"Tags: {', '.join(tags) if tags else 'none'}"
                    ),
                )
            ]

        elif name == "search_memory":
            # Extract arguments
            query = arguments.get("query")
            top_k = arguments.get("top_k", 5)

            # Validate
            if not query:
                return [
                    types.TextContent(type="text", text="Error: 'query' is required")
                ]

            # Search memory
            results = await rae_client.search_memory(query=query, top_k=top_k)

            if not results:
                return [
                    types.TextContent(
                        type="text", text=f"No memories found for query: '{query}'"
                    )
                ]

            # Format results
            formatted = f"Found {len(results)} relevant memories:\n\n"

            for i, mem in enumerate(results, 1):
                score = mem.get("score", 0)
                content = mem.get("content", "")
                source = mem.get("source", "unknown")
                tags = mem.get("tags", [])

                formatted += f"{i}. [Score: {score:.3f}]\n"
                formatted += f"   Source: {source}\n"
                if tags:
                    formatted += f"   Tags: {', '.join(tags)}\n"
                formatted += f"   Content: {content[:200]}{'...' if len(content) > 200 else ''}\n\n"

            return [types.TextContent(type="text", text=formatted)]

        elif name == "get_related_context":
            # Extract arguments
            file_path = arguments.get("file_path")
            include_count = arguments.get("include_count", 10)

            # Validate
            if not file_path:
                return [
                    types.TextContent(
                        type="text", text="Error: 'file_path' is required"
                    )
                ]

            # Get context
            results = await rae_client.get_file_context(
                file_path=file_path, top_k=include_count
            )

            if not results:
                return [
                    types.TextContent(
                        type="text", text=f"No context found for file: {file_path}"
                    )
                ]

            # Format context
            formatted = f"Historical context for: {file_path}\n"
            formatted += f"Found {len(results)} related items:\n\n"

            for i, mem in enumerate(results, 1):
                timestamp = mem.get("timestamp", "unknown")
                content = mem.get("content", "")

                formatted += f"{i}. [{timestamp}]\n"
                formatted += (
                    f"   {content[:300]}{'...' if len(content) > 300 else ''}\n\n"
                )

            return [types.TextContent(type="text", text=formatted)]

        elif name == "request_approval":
            # Extract arguments
            operation_type = arguments.get("operation_type")
            operation_description = arguments.get("operation_description")
            risk_level = arguments.get("risk_level")
            resource_type = arguments.get("resource_type")
            resource_id = arguments.get("resource_id")
            requested_by = arguments.get("requested_by")

            # Validate
            if not all(
                [
                    operation_type,
                    operation_description,
                    risk_level,
                    resource_type,
                    resource_id,
                    requested_by,
                ]
            ):
                return [
                    types.TextContent(
                        type="text",
                        text="Error: All fields are required for approval request",
                    )
                ]

            # Request approval
            result = await rae_client.request_approval(
                operation_type=str(operation_type),
                operation_description=str(operation_description),
                risk_level=str(risk_level),
                resource_type=str(resource_type),
                resource_id=str(resource_id),
                requested_by=str(requested_by),
            )

            request_id = result.get("request_id", "unknown")
            status = result.get("status", "unknown")
            min_approvals = result.get("min_approvals", 0)

            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"✓ Approval request submitted\n\n"
                        f"Request ID: {request_id}\n"
                        f"Status: {status}\n"
                        f"Risk Level: {risk_level}\n"
                        f"Operation: {operation_type}\n"
                        f"Required Approvals: {min_approvals}\n\n"
                        f"Use 'check_approval_status' tool with request_id to check status."
                    ),
                )
            ]

        elif name == "check_approval_status":
            # Extract arguments
            request_id = arguments.get("request_id")

            # Validate
            if not request_id:
                return [
                    types.TextContent(
                        type="text", text="Error: 'request_id' is required"
                    )
                ]

            # Check status
            result = await rae_client.check_approval_status(request_id=request_id)

            status = result.get("status", "unknown")
            risk_level = result.get("risk_level", "unknown")
            approvers = result.get("approvers", [])
            min_approvals = result.get("min_approvals", 0)
            current_approvals = result.get("current_approvals", 0)
            expires_at = result.get("expires_at", "N/A")

            formatted = (
                f"Approval Request Status\n"
                f"{ '=' * 40}\n\n"
                f"Request ID: {request_id}\n"
                f"Status: {status}\n"
                f"Risk Level: {risk_level}\n"
                f"Approvals: {current_approvals}/{min_approvals}\n"
                f"Expires: {expires_at}\n"
            )

            if approvers:
                formatted += "\nApprovers:\n"
                for approver in approvers:
                    formatted += f"  - {approver}\n"

            return [types.TextContent(type="text", text=formatted)]

        elif name == "get_circuit_breakers":
            # Get circuit breakers
            breakers = await rae_client.get_circuit_breakers()

            if not breakers:
                return [
                    types.TextContent(
                        type="text",
                        text="No circuit breakers found or error retrieving data.",
                    )
                ]

            formatted = f"Circuit Breaker Status\n{'=' * 40}\n\n"

            for breaker in breakers:
                name_field = breaker.get("name", "unknown")
                state = breaker.get("state", "unknown")
                failure_count = breaker.get("failure_count", 0)
                success_rate = breaker.get("success_rate", 0)

                status_emoji = (
                    "✓" if state == "closed" else "⚠" if state == "half_open" else "✗"
                )

                formatted += (
                    f"{status_emoji} {name_field}\n"
                    f"   State: {state}\n"
                    f"   Failures: {failure_count}\n"
                    f"   Success Rate: {success_rate:.1%}\n\n"
                )

            return [types.TextContent(type="text", text=formatted)]

        elif name == "list_policies":
            # Extract arguments
            policy_type = arguments.get("policy_type")

            # List policies
            result = await rae_client.list_policies(policy_type=policy_type)

            policies = result.get("policies", [])

            if not policies:
                return [
                    types.TextContent(
                        type="text",
                        text=f"No policies found{f' for type: {policy_type}' if policy_type else ''}.",
                    )
                ]

            formatted = f"Governance Policies\n{'=' * 40}\n\n"

            for policy in policies:
                policy_id = policy.get("policy_id", "unknown")
                policy_type_field = policy.get("policy_type", "unknown")
                status = policy.get("status", "unknown")
                version = policy.get("version", 1)

                formatted += (
                    f"• {policy_id} (v{version})\n"
                    f"  Type: {policy_type_field}\n"
                    f"  Status: {status}\n\n"
                )

            return [types.TextContent(type="text", text=formatted)]

        else:
            TOOL_ERRORS.labels(tool_name=name, error_type="unknown_tool").inc()
            return [
                types.TextContent(type="text", text=f"Error: Unknown tool '{name}'")
            ]

    except Exception as e:
        TOOL_ERRORS.labels(tool_name=name, error_type=type(e).__name__).inc()
        logger.exception("tool_execution_error", tool=name, error=str(e))
        return [
            types.TextContent(
                type="text", text=f"Error executing tool '{name}': {str(e)}"
            )
        ]
    finally:
        # Record execution duration
        duration = time.time() - start_time
        TOOL_DURATION.labels(tool_name=name).observe(duration)


# =============================================================================
# MCP RESOURCES IMPLEMENTATION
# =============================================================================


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available MCP resources."""
    return [
        types.Resource(
            uri="rae://project/reflection",
            name="Project Reflection",
            description=(
                "Current reflective insights about the project. "
                "Provides a synthesized summary of recent activities, "
                "patterns, and key decisions."
            ),
            mimeType="text/plain",
        ),
        types.Resource(
            uri="rae://project/guidelines",
            name="Project Guidelines",
            description=(
                "Coding guidelines and project conventions. "
                "Includes best practices, patterns, and standards "
                "specific to this project."
            ),
            mimeType="text/plain",
        ),
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read MCP resource content."""
    start_time = time.time()
    RESOURCES_READ.labels(resource_uri=uri).inc()

    logger.info("resource_read", uri=uri)

    try:
        if uri == "rae://project/reflection":
            # Fetch latest reflection
            reflection = await rae_client.get_latest_reflection()
            return reflection

        elif uri == "rae://project/guidelines":
            # Fetch project guidelines
            guidelines = await rae_client.get_project_guidelines()

            if not guidelines:
                return "No project guidelines found."

            # Format guidelines
            formatted = "PROJECT GUIDELINES\n"
            formatted += "=" * 60 + "\n\n"

            for i, guideline in enumerate(guidelines, 1):
                content = guideline.get("content", "")
                formatted += f"{i}. {content}\n\n"

            formatted += "=" * 60 + "\n"
            formatted += f"Last updated: {datetime.now().isoformat()}\n"

            return formatted

        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    except Exception as e:
        RESOURCE_ERRORS.labels(resource_uri=uri).inc()
        logger.exception("resource_read_error", uri=uri, error=str(e))
        return f"Error reading resource '{uri}': {str(e)}"
    finally:
        duration = time.time() - start_time
        RESOURCE_DURATION.labels(resource_uri=uri).observe(duration)


# =============================================================================
# MCP PROMPTS IMPLEMENTATION
# =============================================================================


@server.list_prompts()
async def handle_list_prompts() -> list[types.Prompt]:
    """List available MCP prompts."""
    return [
        types.Prompt(
            name="project-guidelines",
            description=(
                "Key project guidelines from RAE memory. "
                "Automatically inject coding standards and conventions "
                "into the conversation context."
            ),
            arguments=[],
        ),
        types.Prompt(
            name="recent-context",
            description=(
                "Recent project context and activities. "
                "Provides awareness of what has been happening recently."
            ),
            arguments=[],
        ),
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict) -> types.GetPromptResult:
    """Get MCP prompt content."""
    start_time = time.time()
    PROMPTS_REQUESTED.labels(prompt_name=name).inc()

    logger.info("prompt_requested", prompt=name)

    try:
        if name == "project-guidelines":
            # Fetch project guidelines
            guidelines = await rae_client.get_project_guidelines()

            if not guidelines:
                content = "No project guidelines found in memory."
            else:
                content = "PROJECT GUIDELINES:\n\n"
                for g in guidelines:
                    content += f"• {g.get('content', '')}\n"

            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=content),
                    )
                ]
            )

        elif name == "recent-context":
            # Fetch recent episodic memories
            recent = await rae_client.search_memory(
                query="recent activities changes updates", top_k=10
            )

            if not recent:
                content = "No recent context available."
            else:
                content = "RECENT PROJECT CONTEXT:\n\n"
                for mem in recent:
                    timestamp = mem.get("timestamp", "unknown")
                    text = mem.get("content", "")
                    content += f"[{timestamp}] {text}\n\n"

            return types.GetPromptResult(
                messages=[
                    types.PromptMessage(
                        role="user",
                        content=types.TextContent(type="text", text=content),
                    )
                ]
            )

        else:
            raise ValueError(f"Unknown prompt: {name}")

    except Exception as e:
        PROMPT_ERRORS.labels(prompt_name=name).inc()
        logger.exception("prompt_error", prompt=name, error=str(e))

        return types.GetPromptResult(
            messages=[
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text", text=f"Error retrieving prompt '{name}': {str(e)}"
                    ),
                )
            ]
        )
    finally:
        duration = time.time() - start_time
        PROMPT_DURATION.labels(prompt_name=name).observe(duration)


# =============================================================================
# SERVER MAIN ENTRY POINT
# =============================================================================


async def main():
    """
    Main entry point for the RAE MCP Server.

    Initializes the server and starts listening on STDIO.
    """
    logger.info(
        "rae_mcp_server_starting",
        version="1.0.0",
        api_url=RAE_API_URL,
        project_id=RAE_PROJECT_ID,
        tenant_id=RAE_TENANT_ID,
    )

    try:
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="rae-memory",
                    server_version="1.0.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )
    except asyncio.CancelledError:
        logger.info("rae_mcp_server_shutdown", reason="stdin pipe closed gracefully")
    except Exception as e:  # Catch specific exception for logging
        logger.exception("rae_mcp_server_fatal_error", error=str(e))
        sys.exit(1)  # Exit with a non-zero code for unhandled errors
    sys.exit(0)  # Exit cleanly on successful completion or graceful shutdown


if __name__ == "__main__":
    asyncio.run(main())
