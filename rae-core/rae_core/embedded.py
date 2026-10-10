"""Embedded RAE - Zero-Docker, Single-File In-Process Memory Engine.

Allows CLI agents (Antigravity, Hermes) and local scripts to run full RAE
cognitive memory (working, episodic, semantic, reflective) with zero Docker
dependencies, powered by SQLite and NumPy vector indexing.
"""

from pathlib import Path
from typing import Any
from uuid import UUID

import structlog

from rae_core.adapters.memory import InMemoryCache
from rae_core.adapters.sqlite.storage import SQLiteStorage
from rae_core.adapters.sqlite.vector import SQLiteVectorStore
from rae_core.config import RAESettings
from rae_core.embedding.manager import EmbeddingManager
from rae_core.engine import RAEEngine
from rae_core.models.envelope import ContextEnvelope
from rae_core.models.evidence_package import EvidencePackage
from rae_core.reflection.deterministic import DeterministicReflectionEngine
from rae_core.runtime import RAERuntime
from rae_core.search.adaptive_engine import AdaptiveSearchEngine
from rae_core.search.strategies.anchor import AnchorStrategy
from rae_core.search.strategies.fulltext import FullTextStrategy
from rae_core.search.strategies.vector import VectorSearchStrategy

logger = structlog.get_logger(__name__)


class EmbeddedEmbeddingProvider:
    """Lightweight hash-based or fallback embedding provider for zero-dependency mode."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    async def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        """Generate deterministic pseudo-embedding via murmur-like feature hashing."""
        import hashlib
        import math

        vec = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            return vec

        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if ((h >> 8) & 1) else -1.0
            vec[idx] += sign

        # L2 Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec

    async def embed_batch(
        self, texts: list[str], **kwargs: Any
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts."""
        return [await self.embed_text(t, **kwargs) for t in texts]

    def get_dimension(self) -> int:
        return self.dimension


class EmbeddedRAE:
    """Embedded, zero-dependency RAE memory engine for CLI agents and single-file runtimes."""

    def __init__(
        self,
        db_path: str,
        storage: SQLiteStorage,
        vector_store: SQLiteVectorStore,
        engine: RAEEngine,
        runtime: RAERuntime,
        reflection_engine: DeterministicReflectionEngine,
        tenant_id: str = "default",
        project: str = "default",
        is_temp: bool = False,
    ):
        self.db_path = db_path
        self.storage = storage
        self.vector_store = vector_store
        self.engine = engine
        self.runtime = runtime
        self.reflection_engine = reflection_engine
        self.tenant_id = tenant_id
        self.project = project
        self._is_temp = is_temp

    @classmethod
    async def open(
        cls,
        db_path: str = ":memory:",
        embedding_dim: int = 384,
        embedding_provider: Any = None,
        llm_provider: Any = None,
        tenant_id: str = "default",
        project: str = "default",
    ) -> "EmbeddedRAE":
        """Open or create an Embedded RAE storage engine.

        Args:
            db_path: Path to sqlite database file or ':memory:' for transient.
            embedding_dim: Dimension of embeddings (default: 384).
            embedding_provider: Optional custom embedding provider.
            llm_provider: Optional LLM provider.
            tenant_id: Default tenant identifier.
            project: Default project identifier.

        Returns:
            Configured and initialized EmbeddedRAE instance.
        """
        import tempfile

        if db_path != ":memory:":
            path = Path(db_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            db_str = str(path)
            is_temp = False
        else:
            tf = tempfile.NamedTemporaryFile(suffix=".rae.db", delete=False)
            db_str = tf.name
            tf.close()
            is_temp = True

        storage = SQLiteStorage(db_str)
        await storage.initialize()

        vector_store = SQLiteVectorStore(db_path=db_str)
        await vector_store.initialize()

        embed_prov = embedding_provider or EmbeddedEmbeddingProvider(dimension=embedding_dim)
        embed_mgr = EmbeddingManager(default_provider=embed_prov)
        cache_prov = InMemoryCache()

        search_strategies = {
            "vector": VectorSearchStrategy(
                vector_store=vector_store,
                embedding_provider=embed_mgr,
            ),
            "fulltext": FullTextStrategy(storage),
            "anchor": AnchorStrategy(storage),
        }

        search_engine = AdaptiveSearchEngine(
            strategies=search_strategies,
            embedding_provider=embed_mgr,
            memory_storage=storage,
        )

        settings = RAESettings()
        engine = RAEEngine(
            memory_storage=storage,
            vector_store=vector_store,
            embedding_provider=embed_mgr,
            llm_provider=llm_provider,
            settings=settings,
            cache_provider=cache_prov,
            search_engine=search_engine,
        )

        runtime = RAERuntime(engine, None)
        reflection_engine = DeterministicReflectionEngine()

        logger.info("embedded_rae_opened", db_path=db_str, tenant_id=tenant_id, project=project)

        return cls(
            db_path=db_str,
            storage=storage,
            vector_store=vector_store,
            engine=engine,
            runtime=runtime,
            reflection_engine=reflection_engine,
            tenant_id=tenant_id,
            project=project,
            is_temp=is_temp,
        )

    async def store(
        self,
        content: str,
        layer: str = "episodic",
        importance: float = 0.5,
        tags: list[str] | None = None,
        source: str = "embedded_agent",
        agent_id: str = "default",
        envelope: ContextEnvelope | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> UUID:
        """Store a memory item directly into the embedded manifold."""
        mem_id = await self.engine.store_memory(
            tenant_id=self.tenant_id,
            agent_id=agent_id,
            project=self.project,
            content=content,
            layer=layer,
            importance=importance,
            tags=tags or [],
            source=source,
            envelope=envelope,
            metadata=metadata or {},
            **kwargs,
        )
        return UUID(str(mem_id))

    async def query(
        self,
        query: str,
        top_k: int = 10,
        layer: str | None = None,
        filters: dict[str, Any] | None = None,
        enable_reranking: bool = False,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Query memories using the full multi-strategy search manifold."""
        return await self.engine.search_memories(
            query=query,
            tenant_id=self.tenant_id,
            project=self.project,
            layer=layer,
            top_k=top_k,
            filters=filters,
            enable_reranking=enable_reranking,
            **kwargs,
        )

    async def search_evidence(
        self,
        query: str,
        limit: int = 10,
        strategies: list[str] | None = None,
        auto_route: bool = True,
        **kwargs: Any,
    ) -> EvidencePackage:
        """Execute full evidence retrieval with confidence scores and provenance."""
        return await self.engine.search_evidence(
            query=query,
            tenant_id=self.tenant_id,
            project=self.project,
            top_k=limit,
            strategies=strategies,
            auto_route=auto_route,
            **kwargs,
        )

    async def consolidate(self) -> dict[str, Any]:
        """Perform instant Tier 1 deterministic memory consolidation."""
        memories = await self.storage.list_memories(
            tenant_id=self.tenant_id,
            project=self.project,
            limit=100,
        )
        if not memories or len(memories) < 2:
            return {"consolidated_count": 0, "clusters": 0}

        clusters = self.reflection_engine.cluster_memories(memories)
        consolidated = []
        for cluster in clusters:
            if len(cluster) >= 2:
                insight = self.reflection_engine.consolidate_cluster(cluster)
                if insight:
                    await self.store(
                        content=insight["content"],
                        layer="reflective",
                        importance=insight["importance"],
                        tags=insight["tags"] + ["consolidated"],
                        metadata={
                            "cluster_size": insight["cluster_size"],
                            "witness_count": insight["witness_count"],
                            "source_ids": insight["source_ids"],
                        },
                    )
                    consolidated.append(insight)

        return {
            "consolidated_count": len(consolidated),
            "clusters": len(clusters),
            "details": consolidated,
        }

    async def close(self) -> None:
        """Close storage connections."""
        if hasattr(self.storage, "close"):
            await self.storage.close()
        if hasattr(self.vector_store, "close"):
            await self.vector_store.close()
        if getattr(self, "_is_temp", False):
            try:
                Path(self.db_path).unlink(missing_ok=True)
            except Exception:
                pass
        logger.info("embedded_rae_closed", db_path=self.db_path)
