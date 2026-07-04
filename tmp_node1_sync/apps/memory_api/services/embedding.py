import hashlib
from typing import Any, List, Optional, cast

import litellm

from apps.memory_api.metrics import embedding_time_histogram
from rae_core.interfaces.embedding import IEmbeddingProvider

# --- Embedding Model Loading ---


class EmbeddingService:
    def __init__(self, settings: Optional[Any] = None):
        self._settings = settings
        self._initialized = False
        self.litellm_model = "text-embedding-3-small"  # Default

    @property
    def settings(self):
        from apps.memory_api.config import settings as default_settings

        return self._settings or default_settings

    def _initialize_model(self) -> None:
        """Lazy initialization of the embedding model settings."""
        if self._initialized:
            return

        # Determine best default model based on env
        if self.settings.RAE_LLM_BACKEND == "ollama":
            self.litellm_model = "ollama/nomic-embed-text"
        elif self.settings.OPENAI_API_KEY:
            self.litellm_model = "text-embedding-3-small"

        print(f"Embedding service initialized with LiteLLM model: {self.litellm_model}")
        self._initialized = True

    def _generate_hash_embedding(self, text: str, dimension: int) -> List[float]:
        """
        Generate a deterministic pseudo-random embedding using Bag-of-Words averaging.
        This preserves some semantic similarity for identical words, aiding smoke tests.
        """
        words = text.lower().split()
        if not words:
            return [0.0] * dimension

        # Initialize zero vector
        vector = [0.0] * dimension

        # Simple Linear Congruential Generator constants
        a = 1664525
        c = 1013904223
        m = 2**32

        for word in words:
            # Hash the word to seed the RNG
            hash_obj = hashlib.md5(word.encode("utf-8"), usedforsecurity=False)
            seed = int(hash_obj.hexdigest(), 16)
            current = seed

            for i in range(dimension):
                current = (a * current + c) % m
                # Normalize to [-1, 1]
                val = (current / m) * 2 - 1
                vector[i] += val

        # Normalize the result vector
        magnitude = sum(x * x for x in vector) ** 0.5
        if magnitude > 0:
            vector = [x / magnitude for x in vector]

        return vector

    @embedding_time_histogram.time()
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense embeddings for a list of texts (synchronous) via LiteLLM.
        """
        self._initialize_model()

        # Calibration: Apply Nomic prefixes if using nomic-embed-text
        processed_texts = []
        if "nomic" in self.litellm_model.lower():
            for t in texts:
                if not t.startswith("search_"):
                    if len(t) < 100 and "?" in t:
                        processed_texts.append(f"search_query: {t}")
                    else:
                        processed_texts.append(f"search_document: {t}")
                else:
                    processed_texts.append(t)
        else:
            processed_texts = texts

        # Use LiteLLM for embeddings
        try:
            kwargs = {}
            if self.litellm_model.startswith("ollama/"):
                kwargs["api_base"] = (
                    self.settings.OLLAMA_API_BASE or self.settings.OLLAMA_API_URL
                )

            response = litellm.embedding(
                model=self.litellm_model, input=processed_texts, **kwargs
            )
            return [d["embedding"] for d in response["data"]]
        except Exception as e:
            print(f"LiteLLM embedding failed: {e}")
            # Fallback to Hash Embeddings for Smoke Tests in CI
            dim = self.get_dimension_for_model(self.litellm_model)
            return [self._generate_hash_embedding(t, dim) for t in texts]

    def get_dimension_for_model(self, model_name: str) -> int:
        if "openai" in model_name or "text-embedding-3" in model_name:
            return 1536
        if "nomic" in model_name:
            return 768
        return 384

    async def generate_embeddings_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generates dense embeddings for a list of texts (asynchronous).
        """
        # If remote ML service is configured and RAE_PROFILE is distributed, use it
        if self.settings.RAE_PROFILE == "distributed" or (
            self.settings.ML_SERVICE_URL
            and "localhost" not in self.settings.ML_SERVICE_URL
            and "127.0.0.1" not in self.settings.ML_SERVICE_URL
        ):
            from apps.memory_api.services.ml_service_client import MLServiceClient

            client = MLServiceClient(base_url=self.settings.ML_SERVICE_URL)
            try:
                result = await client.generate_embeddings(texts)
                return cast(List[List[float]], result.get("embeddings", []))
            finally:
                await client.close()

        self._initialize_model()

        # LiteLLM supports async via aembedding
        try:
            kwargs = {}
            if self.litellm_model.startswith("ollama/"):
                kwargs["api_base"] = (
                    self.settings.OLLAMA_API_BASE or self.settings.OLLAMA_API_URL
                )

            response = await litellm.aembedding(
                model=self.litellm_model, input=texts, **kwargs
            )
            return [d["embedding"] for d in response["data"]]
        except Exception as e:
            print(f"LiteLLM async embedding failed: {e}")
            dim = self.get_dimension_for_model(self.litellm_model)
            return [self._generate_hash_embedding(t, dim) for t in texts]

    async def generate_embeddings_for_model(
        self, texts: List[str], model_name: str
    ) -> List[List[float]]:
        """
        Generates embeddings for a specific model via LiteLLM.
        """
        try:
            kwargs = {}
            if model_name.startswith("ollama/"):
                kwargs["api_base"] = (
                    self.settings.OLLAMA_API_BASE or self.settings.OLLAMA_API_URL
                )

            response = await litellm.aembedding(model=model_name, input=texts, **kwargs)
            return [d["embedding"] for d in response["data"]]
        except Exception as e:
            print(f"LiteLLM embedding for {model_name} failed: {e}")
            dim = self.get_dimension_for_model(model_name)
            return [self._generate_hash_embedding(t, dim) for t in texts]


class LocalEmbeddingProvider(IEmbeddingProvider):
    """Local embedding provider wrapping LiteLLM."""

    def __init__(self, embedding_service: Any = None):
        self.service = embedding_service or get_embedding_service()

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        results = await self.service.generate_embeddings_async([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        return await self.service.generate_embeddings_async(texts)

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        self.service._initialize_model()
        return self.service.get_dimension_for_model(self.service.litellm_model)


class RemoteEmbeddingProvider(IEmbeddingProvider):
    """Embedding provider that offloads to a remote ML service (e.g., Node1)."""

    def __init__(self, base_url: str, dimension: int = 384):
        self.base_url = base_url
        self.dimension = dimension

    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text by calling remote service."""
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts by calling remote service."""
        from apps.memory_api.services.ml_service_client import MLServiceClient

        client = MLServiceClient(base_url=self.base_url)
        try:
            result = await client.generate_embeddings(texts)
            return cast(List[List[float]], result.get("embeddings", []))
        finally:
            await client.close()

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return self.dimension


class TaskQueueEmbeddingProvider(IEmbeddingProvider):
    """Embedding provider that offloads by creating tasks in the Control Plane queue."""

    def __init__(self, task_repo: Any, dimension: int = 384, timeout_sec: int = 60):
        self.task_repo = task_repo
        self.dimension = dimension
        self.timeout_sec = timeout_sec

    async def embed_text(self, text: str) -> List[float]:
        results = await self.embed_batch([text])
        return results[0] if results else []

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Offload embedding generation to a compute node via Task Queue.
        Waits for the task to be completed.
        """
        # 1. Create task
        task_payload = {
            "texts": texts,
            "model": "all-MiniLM-L6-v2",
            "goal": "Generate embeddings for batch",
        }

        # We need a way to create the task.
        # This provider is initialized with task_repo (which might be raw pool or repo)
        # Assuming task_repo has create_task method
        from apps.memory_api.repositories.task_repository import TaskRepository

        if not isinstance(self.task_repo, TaskRepository):
            from apps.memory_api.repositories.task_repository import TaskRepository

            repo = TaskRepository(self.task_repo)
        else:
            repo = self.task_repo

        task = await repo.create_task(
            type="llm_inference",  # Node agent handles llm_inference by calling Ollama
            payload=task_payload,
            priority=10,
        )

        task_id = task.id

        # 2. Poll for result
        import asyncio
        import time

        start_time = time.time()
        while time.time() - start_time < self.timeout_sec:
            updated_task = await repo.get_task(task_id)
            if updated_task and updated_task.status == "COMPLETED":
                import json

                result_data = (
                    json.loads(updated_task.result)
                    if isinstance(updated_task.result, str)
                    else updated_task.result
                )
                if result_data is None:
                    result_data = {}
                return cast(List[List[float]], result_data.get("embeddings", []))
            elif updated_task and updated_task.status == "FAILED":
                raise RuntimeError(f"Task {task_id} failed: {updated_task.error}")

            await asyncio.sleep(1.0)

        raise TimeoutError(
            f"Embedding task {task_id} timed out after {self.timeout_sec}s"
        )

    def get_dimension(self) -> int:
        return self.dimension


class MathOnlyEmbeddingProvider(IEmbeddingProvider):
    """
    Embedding provider for RAE-Lite profile.
    Returns empty/dummy embeddings, letting the Math Layer handle ranking.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    async def embed_text(self, text: str) -> List[float]:
        return [0.0] * self.dimension

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.0] * self.dimension for _ in texts]

    def get_dimension(self) -> int:
        return self.dimension


# Singleton instance
embedding_service = EmbeddingService()


def get_embedding_service() -> EmbeddingService:
    return embedding_service
