"""
ML Service Client - HTTP client for communicating with the ML microservice.

This client provides a clean interface for the main API to call
ML operations without tight coupling.

Features:
- Automatic retry logic with exponential backoff
- Circuit breaker pattern for fault tolerance
- Structured logging for debugging
- Timeout handling
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import httpx
import structlog
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from apps.memory_api.config import settings

logger = structlog.get_logger(__name__)


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    States:
    - CLOSED: Normal operation
    - OPEN: Blocking requests (after threshold failures)
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 30):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        """Record successful call - reset failure count."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record failed call - increment failure count."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )

    def can_attempt(self) -> bool:
        """Check if we can attempt a call."""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed > self.timeout_seconds:
                    self.state = "HALF_OPEN"
                    logger.info("circuit_breaker_half_open", elapsed_seconds=elapsed)
                    return True
            return False

        # HALF_OPEN: allow one attempt
        return True

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
        }


class MLServiceClient:
    """
    Enterprise-grade client for communicating with the ML microservice.

    Features:
    - Automatic retry with exponential backoff (3 attempts: 200ms, 400ms, 800ms)
    - Circuit breaker pattern (opens after 5 failures, resets after 30s)
    - Structured logging for all operations
    - Timeout handling (30s default)

    Handles entity resolution, NLP processing, embeddings, and other ML operations
    that have been offloaded to a separate service.
    """

    def __init__(
        self, base_url: Optional[str] = None, enable_circuit_breaker: bool = True
    ):
        """
        Initialize ML service client with resilience features.

        Args:
            base_url: Base URL of the ML service (default: from settings)
            enable_circuit_breaker: Enable circuit breaker pattern (default: True)
        """
        self.base_url: str = str(
            base_url or getattr(settings, "ML_SERVICE_URL", "http://ml-service:8001")
        )
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)
        self.circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None
        logger.info(
            "ml_service_client_initialized",
            base_url=self.base_url,
            circuit_breaker_enabled=enable_circuit_breaker,
        )

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _call_with_resilience(
        self, method: str, endpoint: str, **kwargs
    ) -> httpx.Response:
        """
        Internal method to make HTTP calls with circuit breaker and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            **kwargs: Additional arguments for httpx

        Returns:
            httpx.Response

        Raises:
            RuntimeError: If circuit breaker is open
            httpx.HTTPError: If request fails after retries
        """
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_attempt():
            raise RuntimeError(
                f"Circuit breaker is OPEN for ML Service. "
                f"State: {self.circuit_breaker.get_state()}"
            )

        # Define retry decorator
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.2, min=0.2, max=0.8),
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
            before_sleep=before_sleep_log(logger, log_level=logging.WARNING),
        )
        async def _make_request():
            if method.upper() == "GET":
                return await self.client.get(endpoint, **kwargs)
            elif method.upper() == "POST":
                return await self.client.post(endpoint, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

        try:
            response = await _make_request()
            response.raise_for_status()

            # Record success
            if self.circuit_breaker:
                self.circuit_breaker.record_success()

            return cast(httpx.Response, response)

        except Exception as e:
            # Record failure
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()

            logger.exception(
                "ml_service_call_failed",
                endpoint=endpoint,
                method=method,
                error=str(e),
                circuit_breaker_state=(
                    self.circuit_breaker.get_state() if self.circuit_breaker else None
                ),
            )
            raise

    async def resolve_entities(
        self, nodes: List[Dict[str, Any]], similarity_threshold: float = 0.85
    ) -> Dict[str, Any]:
        """
        Call ML service to resolve duplicate entities.

        Args:
            nodes: List of node dictionaries to resolve
            similarity_threshold: Threshold for considering nodes similar

        Returns:
            Dict containing merge_groups and statistics

        Raises:
            httpx.HTTPError: If ML service call fails
        """
        logger.info(
            "calling_ml_service_resolve_entities",
            node_count=len(nodes),
            threshold=similarity_threshold,
        )

        try:
            response = await self._call_with_resilience(
                method="POST",
                endpoint="/resolve-entities",
                json={"nodes": nodes, "similarity_threshold": similarity_threshold},
            )

            result = response.json()

            logger.info(
                "ml_service_resolve_entities_completed",
                groups_found=len(result.get("merge_groups", [])),
            )

            return cast(Dict[str, Any], result)

        except Exception as e:
            logger.error(
                "ml_service_resolve_entities_failed",
                error=str(e),
                node_count=len(nodes),
            )
            raise

    async def extract_triples(
        self, text: str, language: str = "en"
    ) -> List[Dict[str, str]]:
        """
        Call ML service to extract knowledge triples from text.

        Args:
            text: Text to extract triples from
            language: Language code (default: "en")

        Returns:
            List of triple dictionaries

        Raises:
            httpx.HTTPError: If ML service call fails
        """
        logger.info(
            "calling_ml_service_extract_triples",
            text_length=len(text),
            language=language,
        )

        try:
            response = await self._call_with_resilience(
                method="POST",
                endpoint="/extract-triples",
                json={"text": text, "language": language},
            )

            result = response.json()
            triples = result.get("triples", [])

            logger.info(
                "ml_service_extract_triples_completed", triples_found=len(triples)
            )

            return cast(List[Dict[str, str]], triples)

        except Exception as e:
            logger.error(
                "ml_service_extract_triples_failed", error=str(e), text_length=len(text)
            )
            raise

    async def generate_embeddings(
        self, texts: List[str], model: str = "all-MiniLM-L6-v2"
    ) -> Dict[str, Any]:
        """
        Call ML service to generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Name of the embedding model to use

        Returns:
            Dict containing embeddings, model name, and dimension

        Raises:
            httpx.HTTPError: If ML service call fails
        """
        logger.info(
            "calling_ml_service_generate_embeddings", text_count=len(texts), model=model
        )

        try:
            response = await self._call_with_resilience(
                method="POST",
                endpoint="/embeddings",
                json={"texts": texts, "model": model},
            )

            result = response.json()

            logger.info(
                "ml_service_embeddings_completed",
                embedding_count=len(result.get("embeddings", [])),
                dimension=result.get("dimension", 0),
            )

            return cast(Dict[str, Any], result)

        except Exception as e:
            logger.error(
                "ml_service_embeddings_failed", error=str(e), text_count=len(texts)
            )
            raise

    async def get_embedding(
        self, text: str, model: str = "all-MiniLM-L6-v2"
    ) -> List[float]:
        """
        Convenience wrapper to get a single embedding for a single text.

        Args:
            text: Text to embed
            model: Name of the embedding model to use

        Returns:
            List of floats representing the embedding

        Raises:
            httpx.HTTPError: If ML service call fails
            ValueError: If no embeddings were returned
        """
        result = await self.generate_embeddings([text], model=model)
        embeddings = result.get("embeddings", [])

        if not embeddings:
            raise ValueError(
                f"No embeddings returned from ML service for text: {text[:50]}..."
            )

        return cast(List[float], embeddings[0])

    async def extract_keywords(
        self, text: str, max_keywords: int = 10, language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Call ML service to extract keywords from text.

        Args:
            text: Text to extract keywords from
            max_keywords: Maximum number of keywords to return
            language: Language code (default: "en")

        Returns:
            List of keyword dictionaries with text, type, label, and score

        Raises:
            httpx.HTTPError: If ML service call fails
        """
        logger.info(
            "calling_ml_service_extract_keywords",
            text_length=len(text),
            max_keywords=max_keywords,
            language=language,
        )

        try:
            response = await self._call_with_resilience(
                method="POST",
                endpoint="/extract-keywords",
                json={"text": text, "max_keywords": max_keywords, "language": language},
            )

            result = response.json()
            keywords = result.get("keywords", [])

            logger.info(
                "ml_service_extract_keywords_completed", keywords_found=len(keywords)
            )

            return cast(List[Dict[str, Any]], keywords)

        except Exception as e:
            logger.error(
                "ml_service_extract_keywords_failed",
                error=str(e),
                text_length=len(text),
            )
            raise

    async def health_check(self) -> bool:
        """
        Check if ML service is healthy.

        Note: Health check bypasses circuit breaker to allow recovery detection.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            # Bypass circuit breaker for health checks
            response = await self.client.get("/health")
            is_healthy = response.status_code == 200

            if is_healthy and self.circuit_breaker:
                # Reset circuit breaker on successful health check
                self.circuit_breaker.record_success()

            return is_healthy

        except Exception as e:
            logger.warning("ml_service_health_check_failed", error=str(e))
            return False

    def get_circuit_breaker_state(self) -> Optional[Dict[str, Any]]:
        """
        Get current circuit breaker state for monitoring.

        Returns:
            Dict with state, failure_count, and last_failure, or None if disabled
        """
        if self.circuit_breaker:
            return self.circuit_breaker.get_state()
        return None
