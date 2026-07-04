"""Main RAE Engine - Orchestrates all RAE-core components."""

from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import UUID

from rae_core.config import RAESettings
from rae_core.interfaces.cache import ICacheProvider
from rae_core.interfaces.embedding import IEmbeddingProvider
from rae_core.interfaces.llm import ILLMProvider
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.interfaces.sync import ISyncProvider
from rae_core.interfaces.vector import IVectorStore
from rae_core.llm.orchestrator import LLMOrchestrator
from rae_core.reflection.engine import ReflectionEngine
from rae_core.search.engine import HybridSearchEngine
from rae_core.sync.protocol import SyncProtocol


class RAEEngine:
    """Main RAE Engine coordinating all components.

    Provides a unified interface for:
    - Memory storage and retrieval
    - Hybrid search (dense + sparse)
    - LLM orchestration
    - Reflection and meta-cognition
    - Memory synchronization
    """

    def __init__(
        self,
        memory_storage: IMemoryStorage,
        vector_store: IVectorStore,
        embedding_provider: IEmbeddingProvider,
        settings: RAESettings | None = None,
        llm_provider: ILLMProvider | None = None,
        cache_provider: ICacheProvider | None = None,
        sync_provider: ISyncProvider | None = None,
    ) -> None:
        """Initialize RAE Engine."""
        self.memory_storage = memory_storage
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.settings = settings or RAESettings()
        self.llm_provider = llm_provider
        self.cache_provider = cache_provider
        self.sync_provider = sync_provider

        # Initialize sub-engines
        from rae_core.search.strategies import SearchStrategy
        from rae_core.search.strategies.fulltext import FullTextStrategy
        from rae_core.search.strategies.vector import VectorSearchStrategy

        strategies: dict[str, SearchStrategy] = {}
        strategies["fulltext"] = FullTextStrategy(memory_storage=memory_storage)

        if vector_store and embedding_provider:
            strategies["vector"] = VectorSearchStrategy(
                vector_store=vector_store,
                embedding_provider=embedding_provider,
            )

        search_cache = None
        if cache_provider:
            from rae_core.search.cache import SearchCache
            search_cache = SearchCache(cache_provider=cache_provider)

        self.search_engine = HybridSearchEngine(
            strategies=strategies,
            cache=search_cache,
        )

        self.reflection_engine = ReflectionEngine(
            memory_storage=memory_storage,
            llm_provider=llm_provider,
        )

        self.llm_orchestrator: LLMOrchestrator | None = None
        if llm_provider:
            from rae_core.llm.config import LLMConfig
            llm_config = LLMConfig(
                default_provider="default",
                providers={},
                enable_cache=self.settings.cache_enabled,
                cache_ttl=self.settings.cache_ttl,
            )
            self.llm_orchestrator = LLMOrchestrator(
                config=llm_config,
                providers={"default": llm_provider},
                cache=cache_provider,
            )

        self.sync_protocol: SyncProtocol | None = None
        if sync_provider and self.settings.sync_enabled:
            self.sync_protocol = SyncProtocol(
                sync_provider=sync_provider,
                encryption_enabled=self.settings.sync_encryption_enabled,
            )

    async def store_memory(
        self,
        tenant_id: str,
        agent_id: str,
        content: str,
        layer: str = "sensory",
        importance: float = 0.5,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        memory_type: str = "text",
        project: str | None = None,
        session_id: str | None = None,
        ttl: int | None = None,
        source: str | None = None,
        strength: float = 1.0,
        info_class: str = "internal",
        governance: dict[str, Any] | None = None,
    ) -> UUID:
        """Store a new memory."""
        tags = tags or []
        metadata = metadata or {}
        governance = governance or {}

        expires_at = None
        if ttl:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

        default_embedding = None
        embeddings_map = {}

        if hasattr(self.embedding_provider, "generate_all_embeddings"):
            embeddings_map = await self.embedding_provider.generate_all_embeddings([content])
            if "default" in embeddings_map and embeddings_map["default"]:
                default_embedding = embeddings_map["default"][0]
            elif embeddings_map:
                default_embedding = list(embeddings_map.values())[0][0]
        else:
            embs = await self.embedding_provider.embed_batch([content])
            if embs:
                default_embedding = embs[0]
                embeddings_map = {"default": [embs[0]]}

        memory_id = await self.memory_storage.store_memory(
            tenant_id=tenant_id,
            agent_id=agent_id,
            content=content,
            layer=layer,
            importance=importance,
            tags=tags,
            metadata=metadata,
            embedding=default_embedding,
            memory_type=memory_type,
            project=project,
            session_id=session_id,
            expires_at=expires_at,
            source=source,
            strength=strength,
            info_class=info_class,
            governance=governance,
        )

        for model_name, model_embs in embeddings_map.items():
            if model_embs:
                await self.memory_storage.save_embedding(
                    memory_id=memory_id,
                    model_name=model_name,
                    embedding=model_embs[0],
                    tenant_id=tenant_id,
                    metadata={"source_length": len(content)},
                )

        if self.vector_store and embeddings_map:
            vector_payload = {}
            for model_name, model_embs in embeddings_map.items():
                if model_embs and model_embs[0]:
                    emb = model_embs[0]
                    dim = len(emb)
                    if dim == 1536: vector_payload["openai"] = emb
                    elif dim == 768: vector_payload["ollama"] = emb
                    elif dim == 384: vector_payload["dense"] = emb
                    elif dim == 1024: vector_payload["cohere"] = emb
                    elif len(embeddings_map) == 1: vector_payload["dense"] = emb

            vector_metadata = {"agent_id": agent_id, "layer": layer, "content": content, **metadata}
            store_data = vector_payload if vector_payload else default_embedding

            if store_data is not None:
                await self.vector_store.store_vector(
                    memory_id=memory_id,
                    embedding=store_data,
                    tenant_id=tenant_id,
                    metadata=vector_metadata,
                )

        return memory_id

    async def retrieve_memory(self, memory_id: UUID, tenant_id: str) -> dict[str, Any] | None:
        """Retrieve a memory by ID."""
        return await self.memory_storage.get_memory(memory_id=memory_id, tenant_id=tenant_id)

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        agent_id: str | None = None,
        layer: str | None = None,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        use_reranker: bool = False,
        custom_weights: Any = None,
    ) -> list[dict[str, Any]]:
        """Search memories using hybrid search with Semantic Resonance."""
        search_config = self.settings.get_search_config()
        top_k = top_k or search_config["top_k"]
        similarity_threshold = similarity_threshold or search_config["similarity_threshold"]

        filters: dict[str, Any] = {}
        if agent_id: filters["agent_id"] = agent_id
        if layer: filters["layer"] = layer
        filters["score_threshold"] = similarity_threshold

        results = await self.search_engine.search(query=query, tenant_id=tenant_id, filters=filters, limit=top_k)

        if use_reranker and len(results) > 0:
            rerank_top_k = search_config["rerank_top_k"]
            results = await self.search_engine.rerank(query=query, results=results[:rerank_top_k])

        # 4. Fetch actual memories and apply Math Layer scoring + Resonance
        from rae_core.math.controller import MathLayerController
        from rae_core.math.resonance import SemanticResonanceEngine

        math_controller = MathLayerController()
        resonance_engine = SemanticResonanceEngine()

        memories: list[dict[str, Any]] = []
        memory_ids = [str(mid) for mid, _ in results]
        
        graph_edges = []
        if hasattr(self.memory_storage, "get_edges_between"):
            graph_edges = await self.memory_storage.get_edges_between(memory_ids, tenant_id)

        for memory_id, score in results:
            memory = await self.memory_storage.get_memory(memory_id, tenant_id)
            if memory:
                if custom_weights:
                    math_score = math_controller.score_memory(memory=memory, query_similarity=score, weights=custom_weights)
                else:
                    math_score = math_controller.score_memory(memory=memory, query_similarity=score)
                
                memory["search_score"] = score
                memory["math_score"] = math_score
                memories.append(memory)

        if len(memories) > 1 and graph_edges:
            memories = resonance_engine.compute_resonance(memories, graph_edges)
        else:
            memories.sort(key=lambda x: x["math_score"], reverse=True)

        return memories

    async def run_reflection_cycle(self, tenant_id: str, agent_id: str, trigger_type: str = "scheduled") -> dict[str, Any]:
        """Run a reflection cycle."""
        return cast(dict[str, Any], await self.reflection_engine.run_reflection_cycle(tenant_id=tenant_id, agent_id=agent_id, trigger_type=trigger_type))

    async def generate_reflection(self, memory_ids: list[UUID], tenant_id: str, agent_id: str, reflection_type: str = "consolidation") -> dict[str, Any]:
        """Generate a reflection from specific memories."""
        return await self.reflection_engine.generate_reflection(memory_ids=memory_ids, tenant_id=tenant_id, agent_id=agent_id, reflection_type=reflection_type)

    async def sync_memories(self, tenant_id: str, agent_id: str) -> dict[str, Any] | None:
        """Synchronize memories with remote."""
        if not self.sync_protocol: return None
        response = await self.sync_protocol.sync(tenant_id=tenant_id, agent_id=agent_id)
        return {"success": response.success, "synced_count": len(response.synced_memory_ids), "conflicts": len(response.conflicts), "error": response.error_message}

    async def generate_text(self, prompt: str, provider_name: str | None = None, **kwargs: Any) -> str | None:
        """Generate text using LLM."""
        if not self.llm_orchestrator: return None
        llm_config = self.settings.get_llm_config()
        kwargs.setdefault("temperature", llm_config["temperature"])
        kwargs.setdefault("max_tokens", llm_config["max_tokens"])
        response, _ = await self.llm_orchestrator.generate(prompt=prompt, provider_name=provider_name, **kwargs)
        return response

    def get_status(self) -> dict[str, Any]:
        """Get engine status."""
        return {
            "settings": {"sensory_max_size": self.settings.sensory_max_size, "working_max_size": self.settings.working_max_size, "episodic_max_size": self.settings.episodic_max_size, "semantic_max_size": self.settings.semantic_max_size, "decay_rate": self.settings.decay_rate, "vector_backend": self.settings.vector_backend},
            "features": {"llm_enabled": self.llm_orchestrator is not None, "cache_enabled": self.settings.cache_enabled, "sync_enabled": self.sync_protocol is not None, "otel_enabled": self.settings.otel_enabled},
            "version": "0.4.0"
        }