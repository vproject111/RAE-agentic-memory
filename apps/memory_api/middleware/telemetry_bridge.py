"""Telemetry Bridge Middleware for closed-loop retrieval optimization (Stage 4, L7)."""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from rae_core.search.optimizer import MaturityMode, RetrievalOptimizer

logger = structlog.get_logger(__name__)


class RetrievalTelemetryBridge:
    """
    Bridge connecting RAE retrieval requests to RetrievalOptimizer.
    Tracks latency, confidence score, token cost, and success status,
    feeding multi-objective reward into RetrievalOptimizer.step(...).
    """

    def __init__(
        self,
        optimizer: Optional[RetrievalOptimizer] = None,
        mode: Optional[MaturityMode] = None,
    ):
        if optimizer is not None:
            self.optimizer = optimizer
        else:
            env_mode = os.getenv("RAE_OPTIMIZER_MODE", "advisory").lower()
            try:
                maturity = mode or MaturityMode(env_mode)
            except ValueError:
                maturity = MaturityMode.ADVISORY
            self.optimizer = RetrievalOptimizer(mode=maturity)

    async def record_search_evidence(
        self,
        package: Any,
        latency_ms: float,
        token_cost: float = 0.0,
        strategy: str = "hybrid",
    ) -> float:
        """
        Record an evidence retrieval result, compute reward, and step the optimizer.
        Attaches calculated telemetry directly to package.metadata["telemetry"].
        """
        confidence = float(getattr(package, "confidence_score", 0.0))
        items = getattr(package, "items", [])
        is_failed = len(items) == 0

        reward = self.optimizer.compute_reward(
            quality=confidence,
            latency_ms=latency_ms,
            token_cost=token_cost,
            is_failed=is_failed,
        )

        rec = self.optimizer.step(
            strategy_name=strategy,
            quality=confidence,
            latency_ms=latency_ms,
            token_cost=token_cost,
            is_failed=is_failed,
        )

        telemetry_data = {
            "latency_ms": round(latency_ms, 2),
            "quality": round(confidence, 4),
            "reward": round(reward, 4),
            "token_cost": token_cost,
            "is_failed": is_failed,
            "mode": rec.mode.value,
            "strategy": strategy,
            "current_weights": dict(self.optimizer.current_weights),
        }

        if hasattr(package, "metadata") and isinstance(package.metadata, dict):
            package.metadata["telemetry"] = telemetry_data

        logger.info(
            "retrieval_telemetry_recorded",
            reward=round(reward, 4),
            latency_ms=round(latency_ms, 2),
            quality=round(confidence, 4),
            mode=rec.mode.value,
        )

        return reward


# Global singleton bridge instance
_GLOBAL_BRIDGE: Optional[RetrievalTelemetryBridge] = None


def get_telemetry_bridge() -> RetrievalTelemetryBridge:
    """Get or initialize global telemetry bridge singleton."""
    global _GLOBAL_BRIDGE
    if _GLOBAL_BRIDGE is None:
        _GLOBAL_BRIDGE = RetrievalTelemetryBridge()
    return _GLOBAL_BRIDGE


def reset_telemetry_bridge(
    bridge: Optional[RetrievalTelemetryBridge] = None,
) -> RetrievalTelemetryBridge:
    """Reset or override global telemetry bridge singleton (primarily for testing)."""
    global _GLOBAL_BRIDGE
    _GLOBAL_BRIDGE = bridge or RetrievalTelemetryBridge()
    return _GLOBAL_BRIDGE


class TelemetryBridgeMiddleware(BaseHTTPMiddleware):
    """
    Middleware monitoring /v2/search/evidence and recording request timing.
    """

    def __init__(self, app: Any, bridge: Optional[RetrievalTelemetryBridge] = None):
        super().__init__(app)
        self.bridge = bridge or get_telemetry_bridge()

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if request.url.path.endswith("/search/evidence") or request.url.path.endswith(
            "/evidence"
        ):
            response.headers["X-Retrieval-Latency-Ms"] = f"{duration_ms:.2f}"

        return response
