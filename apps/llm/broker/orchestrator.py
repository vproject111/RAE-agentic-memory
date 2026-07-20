import asyncio
import logging
from typing import Any, Dict, cast

import yaml

from ..models import LLMRequest, LLMResponse
from .llm_router import LLMRouter

logger = logging.getLogger(__name__)


class LLMOrchestrator:
    def __init__(self, router=None, config_path=None, task_repo=None):
        self.router = router or LLMRouter(task_repo=task_repo)
        self.config = self._load_config(config_path)
        self.models_config = {m["id"]: m for m in self.config.get("models", [])}
        self.strategies_config = self.config.get("strategies", {})
        self.default_strategy = self.config.get("default_strategy", "default")

    def _load_config(self, config_path):
        if config_path is None:
            import pathlib

            config_path = str(
                pathlib.Path(__file__).parent.parent / "config" / "llm_config.yaml"
            )
        try:
            with open(config_path, "r") as f:
                return cast(Dict[str, Any], yaml.safe_load(f))
        except:
            return {}

    async def generate(self, request: LLMRequest) -> LLMResponse:
        strategy_name = request.strategy or self.default_strategy
        strategy_config = self.strategies_config.get(
            strategy_name, self.strategies_config.get("default", {})
        )

        mode = strategy_config.get("mode", "single")
        if mode == "consensus":
            return await self._execute_consensus(request, strategy_config)
        elif mode == "fallback":
            return await self._execute_fallback(request, strategy_config)
        return await self._execute_single(request, strategy_config)

    async def _execute_single(self, request, strategy_config):
        return await self._call_model(request, strategy_config.get("primary"))

    async def _execute_fallback(self, request, strategy_config):
        try:
            return await self._call_model(request, strategy_config.get("primary"))
        except Exception as e:
            logger.warning(f"Fallback triggered: {e}")
            return await self._call_model(request, strategy_config.get("fallback"))

    async def _execute_consensus(self, request, strategy_config):
        model_ids = strategy_config.get("models", [])
        logger.info(f"⚖️ CONSENSUS MODE: Invoking models {model_ids}")

        # Wywołujemy wszystkie modele równolegle (Lean Parallelism)
        tasks = [self._call_model(request, m_id) for m_id in model_ids]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        valid_responses = [r for r in responses if not isinstance(r, Exception)]
        if not valid_responses:
            raise Exception("All models in consensus failed.")

        # Prosta logika konsensusu: zwracamy odpowiedź najdłuższą/najbardziej szczegółową
        # (w przyszłości: głosowanie nad kluczami JSON)
        best_response = max(valid_responses, key=lambda x: len(x.content))
        best_response.content = (
            f"[CONSENSUS RESULT from {len(valid_responses)} models]\n"
            + best_response.content
        )
        return best_response

    async def _call_model(self, request, model_id):
        m_conf = self.models_config.get(model_id)
        if not m_conf:
            return await self.router.complete(request)

        import copy

        req_copy = copy.copy(request)
        req_copy.model = m_conf["model_name"]
        return await self.router.complete(req_copy)
