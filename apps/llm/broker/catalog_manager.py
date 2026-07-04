import os
import json
import logging
import asyncio
import httpx
from typing import Dict, List, Any, Optional
import redis
from rae_core.llm import ModelDescriptor, CapabilityMatrix

logger = logging.getLogger(__name__)

STATIC_MODEL_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "context_window": 128000, "max_tokens": 4096, "capabilities": {"chat": True, "json_schema": True, "tools": True, "vision": True}},
        {"id": "gpt-4o-mini", "name": "GPT-4o mini", "provider": "openai", "context_window": 128000, "max_tokens": 16384, "capabilities": {"chat": True, "json_schema": True, "tools": True, "vision": True}},
        {"id": "gpt-5.5", "name": "GPT-5.5", "provider": "openai", "context_window": 272000, "max_tokens": 128000, "capabilities": {"chat": True, "json_schema": True, "tools": True, "vision": True, "reasoning": True}}
    ],
    "anthropic": [
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "context_window": 200000, "max_tokens": 8192, "capabilities": {"chat": True, "tools": True, "vision": True}},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "provider": "anthropic", "context_window": 200000, "max_tokens": 8192, "capabilities": {"chat": True, "tools": True}}
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "context_window": 1048576, "max_tokens": 8192, "capabilities": {"chat": True, "tools": True, "vision": True}},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "gemini", "context_window": 2097152, "max_tokens": 8192, "capabilities": {"chat": True, "tools": True, "vision": True}}
    ],
    "deepseek": [
        {"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek", "context_window": 64000, "max_tokens": 8192, "capabilities": {"chat": True, "tools": True}}
    ],
    "qwen": [
        {"id": "qwen-turbo", "name": "Qwen Turbo", "provider": "qwen", "context_window": 32000, "max_tokens": 8192, "capabilities": {"chat": True, "tools": True}}
    ]
}

class ModelCatalogManager:
    def __init__(self, cache_file_path: Optional[str] = None):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.cache_file_path = cache_file_path or "/tmp/rae_model_catalog_cache.json"
        self._local_lock = asyncio.Lock()
        
    def _get_redis(self) -> Optional[redis.Redis]:
        try:
            return redis.from_url(self.redis_url, decode_responses=True, socket_connect_timeout=2)
        except Exception:
            return None

    async def get_models(self, provider: str) -> List[ModelDescriptor]:
        provider = provider.lower()
        
        # 1. Try Redis cache
        r_client = self._get_redis()
        if r_client:
            try:
                cached_data = r_client.get(f"rae:model_catalog:{provider}")
                if cached_data:
                    return self._parse_descriptors(json.loads(cached_data))
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # 2. Try Local file cache
        if os.path.exists(self.cache_file_path):
            try:
                with open(self.cache_file_path, "r") as f:
                    data = json.load(f)
                    if provider in data:
                        return self._parse_descriptors(data[provider])
            except Exception as e:
                logger.warning(f"Local cache file read error: {e}")

        # 3. Cache miss or offline - trigger refresh in background & return static defaults
        asyncio.create_task(self.refresh_catalog_async())
        
        return self._parse_descriptors(STATIC_MODEL_CATALOG.get(provider, []))

    async def refresh_catalog_async(self) -> None:
        async with self._local_lock:
            updated_catalog = {}
            tasks = []
            
            providers_to_refresh = []
            if os.getenv("OPENAI_API_KEY"):
                providers_to_refresh.append("openai")
            if os.getenv("ANTHROPIC_API_KEY"):
                providers_to_refresh.append("anthropic")
            if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
                providers_to_refresh.append("gemini")
            if os.getenv("DEEPSEEK_API_KEY"):
                providers_to_refresh.append("deepseek")
            if os.getenv("QWEN_API_KEY"):
                providers_to_refresh.append("qwen")
                
            for prov in providers_to_refresh:
                tasks.append(self._fetch_provider_models(prov))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for prov, res in zip(providers_to_refresh, results):
                if isinstance(res, list) and res:
                    updated_catalog[prov] = res
                    r_client = self._get_redis()
                    if r_client:
                        try:
                            r_client.setex(f"rae:model_catalog:{prov}", 43200, json.dumps(res))
                        except Exception as e:
                            logger.error(f"Failed to write to Redis for {prov}: {e}")
                            
            if updated_catalog:
                existing = {}
                if os.path.exists(self.cache_file_path):
                    try:
                        with open(self.cache_file_path, "r") as f:
                            existing = json.load(f)
                    except Exception:
                        pass
                existing.update(updated_catalog)
                try:
                    with open(self.cache_file_path, "w") as f:
                        json.dump(existing, f)
                except Exception as e:
                    logger.error(f"Failed to write to local cache file: {e}")

    async def _fetch_provider_models(self, provider: str) -> List[Dict[str, Any]]:
        try:
            if provider == "openai":
                return await self._fetch_openai_compatible(
                    "https://api.openai.com/v1/models",
                    os.getenv("OPENAI_API_KEY", ""),
                    "openai"
                )
            elif provider == "deepseek":
                return await self._fetch_openai_compatible(
                    "https://api.deepseek.com/v1/models",
                    os.getenv("DEEPSEEK_API_KEY", ""),
                    "deepseek"
                )
            elif provider == "qwen":
                return await self._fetch_openai_compatible(
                    "https://dashscope.aliyuncs.com/compatible-mode/v1/models",
                    os.getenv("QWEN_API_KEY", ""),
                    "qwen"
                )
            elif provider == "anthropic":
                return STATIC_MODEL_CATALOG["anthropic"]
            elif provider == "gemini":
                key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    data = resp.json()
                    models = []
                    for m in data.get("models", []):
                        name = m.get("name", "")
                        model_id = name.split("/")[-1] if "/" in name else name
                        if not model_id.startswith("gemini-"):
                            continue
                        models.append({
                            "id": model_id,
                            "name": m.get("displayName", model_id),
                            "provider": "gemini",
                            "context_window": m.get("inputTokenLimit", 1048576),
                            "max_tokens": m.get("outputTokenLimit", 8192),
                            "capabilities": {
                                "chat": "generateContent" in m.get("supportedGenerationMethods", []),
                                "tools": True,
                                "vision": True
                            }
                        })
                    return models
        except Exception as e:
            logger.error(f"Error fetching models for {provider}: {e}")
            return []

    async def _fetch_openai_compatible(self, url: str, key: str, provider: str) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {key}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            models = []
            for m in data.get("data", []):
                model_id = m.get("id", "")
                models.append({
                    "id": model_id,
                    "name": model_id,
                    "provider": provider,
                    "context_window": 128000,
                    "max_tokens": 4096,
                    "capabilities": {
                        "chat": True,
                        "json_schema": True,
                        "tools": True
                    }
                })
            return models

    def _parse_descriptors(self, raw_list: List[Dict[str, Any]]) -> List[ModelDescriptor]:
        descriptors = []
        for item in raw_list:
            caps = item.get("capabilities", {})
            matrix = CapabilityMatrix(
                chat=caps.get("chat", True),
                json_schema=caps.get("json_schema", False),
                tools=caps.get("tools", False),
                vision=caps.get("vision", False),
                embeddings=caps.get("embeddings", False),
                streaming=caps.get("streaming", True),
                reasoning=caps.get("reasoning", False)
            )
            descriptors.append(
                ModelDescriptor(
                    id=item["id"],
                    name=item.get("name", item["id"]),
                    provider=item.get("provider", "unknown"),
                    context_window=item.get("context_window", 128000),
                    max_tokens=item.get("max_tokens", 4096),
                    capabilities=matrix,
                    cost=item.get("cost", {"input": 1.0, "output": 5.0, "cacheRead": 0.1, "cacheWrite": 0.0})
                )
            )
        return descriptors
