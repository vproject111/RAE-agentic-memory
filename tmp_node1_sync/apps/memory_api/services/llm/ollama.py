import json
from typing import Optional, Type

import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from ...config import settings
from .base import LLMProvider, LLMResult, LLMResultUsage

logger = structlog.get_logger(__name__)


class OllamaProvider(LLMProvider):
    """
    An LLM provider that uses a local or remote Ollama server.
    """

    def __init__(self, api_url: Optional[str] = None):
        # Multi-node support: Use the list from config
        self.hosts = settings.OLLAMA_HOSTS
        if api_url and api_url not in self.hosts:
            self.hosts.insert(0, api_url)

        # Current active client (will be updated by _get_client)
        self.active_url = self.hosts[0]
        self.client = httpx.AsyncClient(base_url=self.active_url, timeout=300.0)
        logger.info("ollama_provider_initialized", available_hosts=self.hosts)

    async def _get_client(self):
        """Returns the first responsive client from the hosts list."""
        for url in self.hosts:
            try:
                # Fast ping to see if host is alive
                async with httpx.AsyncClient(base_url=url, timeout=2.0) as check_client:
                    response = await check_client.get("/api/tags")
                    if response.status_code == 200:
                        if url != self.active_url:
                            logger.info(
                                "switching_ollama_host", old=self.active_url, new=url
                            )
                            self.active_url = url
                            self.client = httpx.AsyncClient(base_url=url, timeout=300.0)
                        return self.client
            except Exception:
                continue

        # If none respond, return the last known client as fallback
        return self.client

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=5), stop=stop_after_attempt(3)
    )
    async def generate(self, *, system: str, prompt: str, model: str) -> LLMResult:
        """
        Generates content using the Ollama /api/generate endpoint.
        """
        # Strip 'ollama/' prefix if present
        clean_model = model.replace("ollama/", "")
        client = await self._get_client()
        try:
            payload = {
                "model": clean_model,
                "system": system,
                "prompt": prompt,
                "stream": False,
            }
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()

            result_data = response.json()

            usage = LLMResultUsage(
                prompt_tokens=result_data.get("prompt_eval_count", 0),
                candidates_tokens=result_data.get("eval_count", 0),
                total_tokens=result_data.get("prompt_eval_count", 0)
                + result_data.get("eval_count", 0),
            )

            return LLMResult(
                text=result_data.get("response", "").strip(),
                usage=usage,
                model_name=model,
                finish_reason=result_data.get("done_reason", "stop"),
            )
        except httpx.ConnectError:
            print(
                f"Could not connect to Ollama server at {self.active_url}. Is it running?"
            )
            raise
        except Exception as e:
            print(f"Ollama API call failed: {e}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=2, max=5), stop=stop_after_attempt(3)
    )
    async def generate_structured(
        self, *, system: str, prompt: str, model: str, response_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Generates structured content using the Ollama /api/generate endpoint.
        """
        try:
            payload = {
                "model": model,
                "system": system,
                "prompt": prompt,
                "stream": False,  # We want a single response
                "format": "json",
            }
            response = await self.client.post("/api/generate", json=payload)
            response.raise_for_status()

            result_data = response.json()
            response_json = json.loads(result_data.get("response", "{}"))
            return response_model.model_validate(response_json)

        except httpx.ConnectError:
            print(
                f"Could not connect to Ollama server at {self.active_url}. Is it running?"
            )
            raise
        except Exception as e:
            print(f"Ollama API call failed: {e}")
            raise
