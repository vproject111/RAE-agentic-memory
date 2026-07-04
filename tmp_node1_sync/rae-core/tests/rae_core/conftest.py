import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from rae_core.interfaces.llm import ILLMProvider
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.interfaces.vector import IVectorStore


class MockMemoryStorage(IMemoryStorage):
    def __init__(self):
        self._memories: dict[UUID, dict[str, Any]] = {}
        self._lock = asyncio.Lock()  # To simulate async behavior

    async def store_memory(
        self,
        content: str,
        layer: str,
        tenant_id: str,
        agent_id: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        embedding: list[float] | None = None,
        importance: float | None = None,
        expires_at: datetime | None = None,
    ) -> UUID:
        async with self._lock:
            memory_id = uuid4()
            now = datetime.now(timezone.utc)
            memory = {
                "id": memory_id,
                "content": content,
                "layer": layer,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "tags": tags or [],
                "metadata": metadata or {},
                "embedding": embedding,
                "importance": importance or 0.5,
                "created_at": now,
                "last_accessed_at": now,
                "expires_at": expires_at,
                "usage_count": 0,
            }
            self._memories[memory_id] = memory
            return memory_id

    async def get_memory(
        self, memory_id: UUID, tenant_id: str
    ) -> dict[str, Any] | None:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                return memory.copy()
            return None

    async def update_memory(
        self, memory_id: UUID, tenant_id: str, updates: dict[str, Any]
    ) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory.update(updates)
                return True
            return False

    async def delete_memory(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                del self._memories[memory_id]
                return True
            return False

    async def list_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
        tags: list[str] | None = None,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> list[dict[str, Any]]:
        async with self._lock:
            results = []
            for memory in self._memories.values():
                if (
                    memory["tenant_id"] == tenant_id
                    and (agent_id is None or memory["agent_id"] == agent_id)
                    and (layer is None or memory["layer"] == layer)
                    and (tags is None or any(tag in memory["tags"] for tag in tags))
                ):
                    # Apply additional filters
                    match = True
                    if filters:
                        for key, value in filters.items():
                            if key.startswith("metadata."):
                                meta_key = key.split(".", 1)[1]
                                if memory.get("metadata", {}).get(meta_key) != value:
                                    match = False

                    if match:
                        results.append(memory.copy())

            # Sort results
            reverse = order_direction.lower() == "desc"
            results.sort(key=lambda m: m.get(order_by, ""), reverse=reverse)  # type: ignore[arg-type,return-value]

            return results[offset : offset + limit]

    async def delete_memories_with_metadata_filter(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        metadata_filter: dict[str, Any],
    ) -> int:
        async with self._lock:
            to_delete = []
            for mid, memory in self._memories.items():
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                ):
                    match = True
                    for key, value in metadata_filter.items():
                        if "__lt" in key:
                            field = key.replace("__lt", "")
                            val = memory.get("metadata", {}).get(field)
                            if val is None or not (val < value):
                                match = False
                        else:
                            if memory.get("metadata", {}).get(key) != value:
                                match = False

                    if match:
                        to_delete.append(mid)

            for mid in to_delete:
                del self._memories[mid]
            return len(to_delete)

    async def count_memories(
        self,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
    ) -> int:
        async with self._lock:
            count = 0
            for memory in self._memories.values():
                if (
                    memory["tenant_id"] == tenant_id
                    and (agent_id is None or memory["agent_id"] == agent_id)
                    and (layer is None or memory["layer"] == layer)
                ):
                    count += 1
            return count

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str,
        layer: str,
        limit: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            results = []
            for memory in self._memories.values():
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                ):
                    # Filter logic
                    match = True
                    if filters:
                        # Handle expiration filter
                        if filters.get("not_expired"):
                            if memory.get("expires_at") and memory[
                                "expires_at"
                            ] < datetime.now(timezone.utc):
                                match = False

                        # Handle metadata dot notation filters (e.g., "metadata.is_semantic")
                        for key, value in filters.items():
                            if key.startswith("metadata."):
                                meta_key = key.split(".", 1)[1]
                                if memory.get("metadata", {}).get(meta_key) != value:
                                    match = False

                    if match:
                        # Simple "score" based on content presence (mock)
                        score = (
                            1.0 if query.lower() in memory["content"].lower() else 0.5
                        )
                        results.append({"memory": memory.copy(), "score": score})

            results.sort(key=lambda x: x["score"], reverse=True)  # type: ignore[arg-type, return-value]
            return results[:limit]

    async def delete_expired_memories(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
    ) -> int:
        async with self._lock:
            to_delete = []
            now = datetime.now(timezone.utc)
            for mid, memory in self._memories.items():
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                    and memory.get("expires_at")
                    and memory["expires_at"] < now
                ):
                    to_delete.append(mid)

            for mid in to_delete:
                del self._memories[mid]
            return len(to_delete)

    async def delete_memories_below_importance(
        self,
        tenant_id: str,
        agent_id: str,
        layer: str,
        importance_threshold: float,
    ) -> int:
        async with self._lock:
            to_delete = []
            for mid, memory in self._memories.items():
                if (
                    memory["tenant_id"] == tenant_id
                    and memory["agent_id"] == agent_id
                    and memory["layer"] == layer
                    and memory.get("importance", 0) < importance_threshold
                ):
                    to_delete.append(mid)

            for mid in to_delete:
                del self._memories[mid]
            return len(to_delete)

    async def update_memory_access(
        self,
        memory_id: UUID,
        tenant_id: str,
    ) -> bool:
        return await self.increment_access_count(memory_id, tenant_id)

    async def update_memory_expiration(
        self,
        memory_id: UUID,
        tenant_id: str,
        expires_at: datetime,
    ) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory["expires_at"] = expires_at
                return True
            return False

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        metric: str,
        func: str,
        filters: dict[str, Any] | None = None,
    ) -> float:
        return 0.0

    async def update_memory_access_batch(
        self,
        memory_ids: list[UUID],
        tenant_id: str,
    ) -> bool:
        for mid in memory_ids:
            await self.update_memory_access(mid, tenant_id)
        return True

    async def adjust_importance(
        self,
        memory_id: UUID,
        delta: float,
        tenant_id: str,
    ) -> float:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                new_imp = float(memory.get("importance", 0.5)) + delta
                new_imp = max(0.0, min(1.0, new_imp))
                memory["importance"] = new_imp
                return new_imp
            return 0.0

    async def increment_access_count(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self._lock:
            memory = self._memories.get(memory_id)
            if memory and memory["tenant_id"] == tenant_id:
                memory["usage_count"] += 1
                memory["last_accessed_at"] = datetime.now(timezone.utc)
                return True
            return False

    async def save_embedding(
        self,
        memory_id: UUID,
        model_name: str,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        async with self._lock:
            # For mock, we can just return True or store it somewhere if needed
            return True


class MockVectorStore(IVectorStore):
    def __init__(self):
        self._vectors: dict[tuple[UUID, str], dict[str, Any]] = (
            {}
        )  # (memory_id, tenant_id) -> {embedding, metadata}
        self._lock = asyncio.Lock()

    async def store_vector(
        self,
        memory_id: UUID,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        async with self._lock:
            self._vectors[(memory_id, tenant_id)] = {
                "embedding": embedding,
                "metadata": metadata or {},
            }
            return True

    async def search_similar(
        self,
        query_embedding: list[float],
        tenant_id: str,
        layer: str | None = None,
        limit: int = 10,
        score_threshold: float | None = None,
    ) -> list[tuple[UUID, float]]:
        async with self._lock:
            results: list[tuple[UUID, float]] = []
            # Simplified similarity search: just return some dummy results
            # In a real mock, you'd calculate cosine similarity
            for (mem_id, tid), vec_data in self._vectors.items():
                if tid == tenant_id:
                    # Dummy score for now
                    score = 0.85
                    results.append((mem_id, score))
            return sorted(results, key=lambda x: x[1], reverse=True)[:limit]

    async def delete_vector(self, memory_id: UUID, tenant_id: str) -> bool:
        async with self._lock:
            if (memory_id, tenant_id) in self._vectors:
                del self._vectors[(memory_id, tenant_id)]
                return True
            return False

    async def update_vector(
        self,
        memory_id: UUID,
        embedding: list[float],
        tenant_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        async with self._lock:
            if (memory_id, tenant_id) in self._vectors:
                self._vectors[(memory_id, tenant_id)].update(
                    {"embedding": embedding, "metadata": metadata or {}}
                )
                return True
            return False

    async def get_vector(self, memory_id: UUID, tenant_id: str) -> list[float] | None:
        async with self._lock:
            vec_data = self._vectors.get((memory_id, tenant_id))
            return vec_data["embedding"] if vec_data else None

    async def batch_store_vectors(
        self, vectors: list[tuple[UUID, list[float], dict[str, Any]]], tenant_id: str
    ) -> int:
        async with self._lock:
            count = 0
            for mem_id, embedding, metadata in vectors:
                self._vectors[(mem_id, tenant_id)] = {
                    "embedding": embedding,
                    "metadata": metadata or {},
                }
                count += 1
            return count


class MockLLMProvider(ILLMProvider):
    def __init__(self):
        self._responses: dict[str, str] = {}
        self._lock = asyncio.Lock()

    def set_response(self, prompt_prefix: str, response: str):
        self._responses[prompt_prefix] = response

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stop_sequences: list[str] | None = None,
    ) -> str:
        async with self._lock:
            for prefix, resp in self._responses.items():
                if prompt.startswith(prefix):
                    return resp
            return f"Mocked LLM response for: {prompt}"

    async def generate_with_context(
        self,
        messages: list[dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7,
    ) -> str:
        async with self._lock:
            last_message = messages[-1]["content"] if messages else ""
            return f"Mocked LLM context response for: {last_message}"

    async def count_tokens(self, text: str) -> int:
        return len(text.split())  # Very basic token count

    def supports_function_calling(self) -> bool:
        return True

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        return [{"text": "MockEntity", "type": "MockType", "confidence": 0.9}]

    async def summarize(self, text: str, max_length: int = 200) -> str:
        return f"Mocked summary of: {text[:max_length]}"


@pytest.fixture(scope="function")
async def mock_memory_storage() -> MockMemoryStorage:
    """Provides a mocked IMemoryStorage instance."""
    return MockMemoryStorage()


@pytest.fixture(scope="function")
async def mock_vector_store() -> MockVectorStore:
    """Provides a mocked IVectorStore instance."""
    return MockVectorStore()


@pytest.fixture(scope="function")
async def mock_llm_provider() -> MockLLMProvider:
    """Provides a mocked ILLMProvider instance."""
    return MockLLMProvider()


@pytest.fixture
def golden_snapshot(request: Any) -> Any:
    """Fixture to record and verify golden snapshots for Rust migration."""

    def _record(
        test_name: str,
        inputs: dict[str, Any],
        output: Any,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        snapshot = {
            "test_name": test_name,
            "inputs": inputs,
            "output": output,
            "metadata": metadata or {},
        }

        # Ensure directory exists
        golden_dir = Path("rae-core/tests/golden")
        golden_dir.mkdir(parents=True, exist_ok=True)

        file_path = golden_dir / f"{test_name}.json"
        with open(file_path, "w") as f:
            # Handle non-serializable objects (like UUIDs)
            def serializer(obj: Any) -> str:
                if isinstance(obj, UUID):
                    return str(obj)
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            json.dump(snapshot, f, indent=2, default=serializer)

    return _record
