import os
from collections.abc import AsyncIterator
from typing import Optional

import httpx
import structlog

from ..models import (
    EmbeddingRequest,
    EmbeddingResponse,
    LLMChunk,
    LLMProviderError,
    LLMRequest,
    LLMResponse,
    TokenUsage,
)

logger = structlog.get_logger(__name__)


class OllamaProvider:
    def __init__(self, api_url: Optional[str] = None):
        self.name = "ollama"
        self.max_context_tokens = 8192
        self.supports_streaming = False  # Set explicitly
        self.supports_tools = False
        self.api_url = api_url or os.getenv("OLLAMA_API_URL", "http://ollama-dev:11434")
        # Persistent client for performance
        self.client = httpx.AsyncClient(base_url=self.api_url, timeout=600.0)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system_msg = next(
            (m.content for m in request.messages if m.role == "system"), ""
        )
        user_msg = next((m.content for m in request.messages if m.role == "user"), "")

        payload = {
            "model": request.model,
            "prompt": user_msg,
            "system": system_msg,
            "stream": False,
            "options": {
                "temperature": request.temperature or 0.1,
                "num_ctx": self.max_context_tokens,
            },
        }

        try:
            # PURE ASYNC CALL - Best for Python 3.14
            response = await self.client.post("/api/generate", json=payload)

            if response.status_code != 200:
                raise LLMProviderError(
                    f"Ollama Error {response.status_code}: {response.text[:100]}"
                )

            data = response.json()
            return LLMResponse(
                text=data.get("response", ""),
                model_name=request.model,
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                finish_reason="stop",
                raw=data,
            )
        except Exception as e:
            logger.error("ollama_connection_failed", error=str(e))
            raise LLMProviderError(f"Ollama Connection Failed: {str(e)}")

    async def stream(self, request: LLMRequest) -> AsyncIterator[LLMChunk]:
        yield LLMChunk(text="Streaming disabled for stability")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate a single embedding."""
        response = await self.embed_batch(request)
        return response

    async def embed_batch(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate batch embeddings via Ollama /api/embed."""
        payload = {
            "model": request.model,
            "input": request.input,
        }

        try:
            # SYSTEM 96.1: Direct Ollama Embed API
            response = await self.client.post("/api/embed", json=payload)

            if response.status_code != 200:
                # Fallback to legacy /api/embeddings if /api/embed fails
                logger.warning(
                    "ollama_embed_failed_trying_legacy", status=response.status_code
                )
                return await self._embed_batch_legacy(request)

            data = response.json()
            return EmbeddingResponse(
                embeddings=data.get("embeddings", []), model=request.model, raw=data
            )
        except Exception as e:
            logger.error("ollama_embedding_failed", error=str(e))
            raise LLMProviderError(f"Ollama Embedding Failed: {str(e)}")

    async def _embed_batch_legacy(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Legacy fallback for older Ollama versions."""
        embeddings = []
        for text in request.input:
            payload = {"model": request.model, "prompt": text}
            response = await self.client.post("/api/embeddings", json=payload)
            if response.status_code == 200:
                embeddings.append(response.json().get("embedding", []))
            else:
                logger.error("ollama_legacy_embed_failed", text=text[:50])

        return EmbeddingResponse(embeddings=embeddings, model=request.model)
