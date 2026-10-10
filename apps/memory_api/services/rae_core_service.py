"""RAE-Core integration service (Facade Pattern).

Wraps RAEEngine and delegates domain responsibilities to specialized delegates.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

import asyncpg
import redis.asyncio as redis
import structlog
from fastapi import Request
from qdrant_client import AsyncQdrantClient

from apps.memory_api.services.delegates import (
    GovernanceDelegate,
    MemoryIngestionDelegate,
    MemoryLifecycleDelegate,
    MemoryRetrievalDelegate,
)
from apps.memory_api.services.embedding import (
    LocalEmbeddingProvider,
)
from apps.memory_api.services.llm import get_llm_provider
from apps.memory_api.services.token_savings_service import TokenSavingsService
from rae_adapters.postgres import PostgreSQLStorage
from rae_adapters.qdrant import QdrantVectorStore
from rae_adapters.redis_cache import RedisCache
from rae_core.config import RAESettings
from rae_core.embedding.manager import EmbeddingManager
from rae_core.engine import RAEEngine
from rae_core.interfaces.cache import ICacheProvider
from rae_core.interfaces.database import IDatabaseProvider
from rae_core.interfaces.reranking import IReranker
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.interfaces.vector import IVectorStore
from rae_core.models.envelope import ContextEnvelope
from rae_core.models.evidence_package import EvidencePackage
from rae_core.models.interaction import AgentAction
from rae_core.models.search import SearchResponse
from rae_core.runtime import RAERuntime
from rae_core.types.enums import MemoryLayer

logger = structlog.get_logger(__name__)


class RAECoreService:
    """Integration service for RAE-Core (Facade).

    Coordinates RAEEngine, RAERuntime, adapters, and domain delegates.
    """

    def __init__(
        self,
        postgres_pool: Optional[asyncpg.Pool] = None,
        qdrant_client: Optional[AsyncQdrantClient] = None,
        redis_client: Optional[redis.Redis] = None,
    ):
        """Initialize service with infrastructure clients."""
        self.postgres_pool = postgres_pool
        self.qdrant_client = qdrant_client
        self.redis_client = redis_client

        self.postgres_adapter: IMemoryStorage
        self.qdrant_adapter: IVectorStore
        self.redis_adapter: ICacheProvider
        self.mcp_client: Optional[Any] = None
        self.savings_service: Optional[TokenSavingsService] = None
        self.websocket_service: Optional[Any] = None
        self.tuning_service: Any = None
        from apps.memory_api.services.alert_service import AlertService

        self.alert_service = AlertService()

        if postgres_pool:
            from apps.memory_api.services import dashboard_websocket as ws_mod

            self.savings_service = TokenSavingsService(postgres_pool)
            self.websocket_service = ws_mod.DashboardWebSocketService(postgres_pool)

            from apps.memory_api.services.tuning_service import TuningService

            self.tuning_service = TuningService(self)

        from apps.memory_api.config import settings

        # 1. Initialize embedding providers (Multi-Vector Support)
        self._init_embedding_providers(settings)

        # 2. Initialize adapters
        self._init_adapters(settings, postgres_pool, qdrant_client, redis_client)

        # 3. Initialize Engine & Runtime
        self._init_engine(settings, postgres_pool)

        # 4. Reflection Engine
        from apps.memory_api.services.reflection_engine_v2 import ReflectionEngineV2
        from rae_core.reflection.layers.coordinator import ReflectionCoordinator

        self.reflection_engine = ReflectionEngineV2(self)
        self.reflection_coordinator = ReflectionCoordinator(
            mode=(
                settings.RAE_PROFILE
                if settings.RAE_PROFILE in ["standard", "advanced"]
                else "standard"
            ),
            enforce_hard_frames=True,
            storage=self.postgres_adapter,
        )

        # 5. RAERuntime for RAE-First flow
        self.runtime = RAERuntime(cast(Any, self.engine), None)

        self.szubar_mode = False

        # 6. Initialize Domain Delegates (Facade Pattern)
        self.ingestion_delegate = MemoryIngestionDelegate(self)
        self.retrieval_delegate = MemoryRetrievalDelegate(self)
        self.lifecycle_delegate = MemoryLifecycleDelegate(self)
        self.governance_delegate = GovernanceDelegate(self)

        logger.info("rae_core_service_initialized", profile=settings.RAE_PROFILE)

    def enable_szubar_mode(self, enabled: bool = True) -> None:
        """Enable or disable RAE-SZUBAR Mode (Evolutionary Pressure)."""
        self.szubar_mode = enabled
        logger.info("szubar_mode_changed", enabled=enabled)

    def _init_embedding_providers(self, settings: Any) -> None:
        """Initialize embedding providers (Multi-Vector Support)."""
        import os

        self.embedding_provider = EmbeddingManager(
            default_provider=LocalEmbeddingProvider()
        )

        # Register ONNX
        if getattr(settings, "RAE_EMBEDDING_BACKEND", None) == "onnx" or os.getenv("ONNX_EMBEDDER_PATH"):
            self._register_onnx_provider(settings)

        # Register API
        if getattr(settings, "RAE_EMBEDDING_BACKEND", None) == "api":
            api_provider = LocalEmbeddingProvider()
            self.embedding_provider.register_provider("api", api_provider)
            self.embedding_provider._default_provider = api_provider
            self.embedding_provider.default_model_name = (
                getattr(settings, "RAE_EMBEDDING_MODEL", None) or "api"
            )
            logger.info(
                "registered_api_embedding_provider",
                model=self.embedding_provider.default_model_name,
            )

        # Register MCP
        if getattr(settings, "RAE_EMBEDDING_BACKEND", None) == "mcp":
            self._register_mcp_provider(settings)

        # Default fallback
        if self.embedding_provider.default_model_name != "litellm":
            self.embedding_provider.register_provider(
                "litellm", LocalEmbeddingProvider()
            )

    def _register_onnx_provider(self, settings: Any) -> None:
        """Helper to register ONNX provider."""
        import os

        try:
            from rae_core.embedding.native import NativeEmbeddingProvider

            model_path = (
                getattr(settings, "ONNX_EMBEDDER_PATH", None) or "models/nomic-embed-text-v1.5/model.onnx"
            )
            if not os.path.exists(model_path):
                model_path = "models/all-MiniLM-L6-v2/model.onnx"

            if os.path.exists(model_path):
                tokenizer_path = os.path.join(
                    os.path.dirname(model_path), "tokenizer.json"
                )
                model_name = "nomic" if "nomic" in model_path.lower() else "mini-lm"
                onnx_provider = NativeEmbeddingProvider(
                    model_path=model_path,
                    tokenizer_path=tokenizer_path,
                    model_name=model_name,
                    use_gpu=getattr(settings, "RAE_USE_GPU", False),
                )
                self.embedding_provider.register_provider(model_name, onnx_provider)
                if getattr(settings, "RAE_EMBEDDING_BACKEND", None) == "onnx":
                    self.embedding_provider._default_provider = onnx_provider
                    self.embedding_provider.default_model_name = model_name
                logger.info("registered_onnx_provider", name=model_name)
        except Exception as e:
            logger.error("onnx_initialization_failed", error=str(e))

    def _register_mcp_provider(self, settings: Any) -> None:
        """Helper to register MCP provider."""
        try:
            from apps.memory_api.services.embedding import MCPEmbeddingProvider
            from rae_core.utils.mcp_client import RAEMCPClient

            mcp_client = RAEMCPClient(
                command=getattr(settings, "RAE_MCP_SERVER_COMMAND", "python"),
                args=getattr(settings, "RAE_MCP_SERVER_ARGS", []),
            )
            self.mcp_client = mcp_client
            mcp_provider = MCPEmbeddingProvider(
                tool_name=getattr(settings, "RAE_MCP_EMBEDDING_TOOL", "get_embeddings"), client=mcp_client
            )
            self.embedding_provider.register_provider("mcp", mcp_provider)
            self.embedding_provider._default_provider = mcp_provider
            self.embedding_provider.default_model_name = "mcp"
            logger.info("registered_mcp_embedding_provider")
        except Exception as e:
            logger.error("mcp_initialization_failed", error=str(e))

    def _init_adapters(
        self,
        settings: Any,
        postgres_pool: Optional[asyncpg.Pool],
        qdrant_client: Optional[AsyncQdrantClient],
        redis_client: Optional[redis.Redis],
    ) -> None:
        """Initialize infrastructure adapters."""
        import os

        db_mode = os.getenv("RAE_DB_MODE") or settings.RAE_DB_MODE
        ignore_db = (
            postgres_pool is None
            or (db_mode == "ignore" and postgres_pool is None)
            or (settings.RAE_PROFILE == "lite" and os.getenv("RAE_FORCE_DB") != "1")
        )
        if postgres_pool is not None:
            ignore_db = False

        # Storage
        if postgres_pool and not ignore_db:
            self.postgres_adapter = cast(
                IMemoryStorage, PostgreSQLStorage(pool=postgres_pool)
            )
        else:
            from rae_adapters.memory import InMemoryStorage

            self.postgres_adapter = cast(IMemoryStorage, InMemoryStorage())

        # Vector
        if qdrant_client and not ignore_db:
            dim = self.embedding_provider.get_dimension()

            v_name = (
                "nomic"
                if "nomic" in (self.embedding_provider.default_model_name or "").lower()
                else "dense"
            )

            self.qdrant_adapter = QdrantVectorStore(
                client=cast(Any, qdrant_client),
                embedding_dim=dim,
                distance=getattr(settings, "RAE_VECTOR_DISTANCE", "Cosine"),
                vector_name=v_name,
            )
        else:
            from rae_adapters.memory import InMemoryVectorStore

            self.qdrant_adapter = InMemoryVectorStore()

        # Cache
        if redis_client and not ignore_db:
            self.redis_adapter = RedisCache(redis_client=redis_client)
        else:
            from rae_adapters.memory import InMemoryCache

            self.redis_adapter = InMemoryCache()

    def _init_engine(
        self, settings: Any, postgres_pool: Optional[asyncpg.Pool]
    ) -> None:
        """Initialize Search Engine and RAE Core Engine."""
        self.llm_provider = get_llm_provider(task_repo=postgres_pool)
        self.settings = RAESettings(sensory_max_size=100, working_max_size=100)

        # Reranker
        reranker = self._create_reranker(settings)

        # Search Engine
        from rae_core.search.strategies.anchor import AnchorStrategy
        from rae_core.search.strategies.fulltext import FullTextStrategy
        from rae_core.search.strategies.sparse import SparseVectorStrategy
        from rae_core.search.strategies.vector import VectorSearchStrategy

        search_strategies = {
            "vector": VectorSearchStrategy(
                vector_store=self.qdrant_adapter,
                embedding_provider=self.embedding_provider,
            ),
            "fulltext": FullTextStrategy(self.postgres_adapter),
            "sparse": SparseVectorStrategy(self.postgres_adapter),
            "anchor": AnchorStrategy(self.postgres_adapter),
        }

        # Optional Graph Store for Lite Mode
        graph_repo = None
        if postgres_pool:
            try:
                graph_repo = self.enhanced_graph_repo
            except Exception as e:
                logger.warning("graph_repo_init_skipped", reason=str(e))

        if graph_repo:
            from rae_core.search.strategies.graph import GraphTraversalStrategy
            from rae_core.search.strategies.graph_lite import GraphLiteStrategy

            search_strategies["graph"] = GraphTraversalStrategy(
                graph_repo, self.postgres_adapter
            )
            primary_seed = search_strategies.get("vector") or search_strategies.get(
                "fulltext"
            )
            search_strategies["graph_lite"] = GraphLiteStrategy(
                graph_store=graph_repo,
                memory_storage=self.postgres_adapter,
                seed_strategy=primary_seed,
            )

        from rae_core.search.strategies.visual import VisualSearchStrategy

        search_strategies["visual"] = VisualSearchStrategy()

        from rae_core.search.adaptive_engine import AdaptiveSearchEngine

        search_engine = AdaptiveSearchEngine(
            strategies=search_strategies,
            embedding_provider=self.embedding_provider,
            memory_storage=self.postgres_adapter,
            reranker=reranker,
            graph_store=graph_repo,
        )

        self.engine = RAEEngine(
            memory_storage=self.postgres_adapter,
            vector_store=self.qdrant_adapter,
            embedding_provider=self.embedding_provider,
            llm_provider=cast(Any, self.llm_provider),
            settings=self.settings,
            cache_provider=self.redis_adapter,
            search_engine=search_engine,
            graph_store=graph_repo,
        )

        logger.info(
            "rae_core_engine_components_ready",
            storage=type(self.postgres_adapter).__name__,
            vector_store=type(self.qdrant_adapter).__name__,
            embedding=type(self.embedding_provider).__name__,
        )

    def _create_reranker(self, settings: Any) -> Optional[IReranker]:
        """Create configured reranker instance."""
        from rae_core.search.engine import EmeraldReranker
        from rae_core.search.rerankers.api import ApiReranker
        from rae_core.search.rerankers.mcp import McpReranker

        if getattr(settings, "RAE_RERANKER_BACKEND", None) == "emerald":
            return EmeraldReranker(self.embedding_provider, self.postgres_adapter)
        if getattr(settings, "RAE_RERANKER_BACKEND", None) == "api" and getattr(settings, "RAE_RERANKER_API_URL", None):
            return ApiReranker(
                api_url=settings.RAE_RERANKER_API_URL,
                api_key=getattr(settings, "RAE_RERANKER_API_KEY", None),
            )
        if getattr(settings, "RAE_RERANKER_BACKEND", None) == "mcp":
            return McpReranker()
        return None

    async def execute_action(
        self,
        tenant_id: str | UUID,
        agent_id: str,
        prompt: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        project: Optional[str] = None,
    ) -> AgentAction:
        """Execute an agent action through RAERuntime (RAE-First)."""
        return await self.governance_delegate.execute_action(
            tenant_id=tenant_id,
            agent_id=agent_id,
            prompt=prompt,
            session_id=session_id,
            metadata=metadata,
            project=project,
        )

    async def ainit(self) -> None:
        """Perform asynchronous initialization of adapters."""
        if hasattr(self.qdrant_adapter, "ainit"):
            await cast(Any, self.qdrant_adapter).ainit()
        logger.info("rae_core_service_async_initialized")

    @property
    def db(self) -> IDatabaseProvider:
        """Get agnostic database provider."""
        if self.postgres_pool:
            from rae_adapters.postgres_db import PostgresDatabaseProvider

            return PostgresDatabaseProvider(self.postgres_pool)
        raise RuntimeError("Database provider not available (RAE-Lite mode with no DB)")

    @property
    def enhanced_graph_repo(self) -> Any:
        """Get enhanced graph repository."""
        from apps.memory_api.repositories.graph_repository_enhanced import (
            EnhancedGraphRepository,
        )

        return EnhancedGraphRepository(self.db)

    # -------------------------------------------------------------------------
    # Delegated Methods (Preserving 100% Backwards Compatibility)
    # -------------------------------------------------------------------------

    def _enforce_security_policy(
        self,
        info_class: str,
        target_layer: str | MemoryLayer,
        tenant_id: str = "unknown",
    ) -> None:
        """Enforce ISO 27000 security policies."""
        self.ingestion_delegate.enforce_security_policy(
            info_class=info_class, target_layer=target_layer, tenant_id=tenant_id
        )

    def _detect_agentic_patterns(self, governance: dict, tags: list[str]) -> list[str]:
        """Detect agentic patterns and return updated tags."""
        return self.ingestion_delegate.detect_agentic_patterns(governance, tags)

    async def _handle_hard_frames(
        self,
        tenant_id: str,
        content: str,
        tags: list[str],
        layer: Optional[str],
        session_id: Optional[str],
        human_label: Optional[str],
        agent_id: Optional[str],
        source: str,
        metadata: Optional[dict],
    ) -> Optional[dict]:
        """SYSTEM 93.1: Hard Frames 2.0 Contract Enforcement helper."""
        return await self.ingestion_delegate.handle_hard_frames(
            tenant_id=tenant_id,
            content=content,
            tags=tags,
            layer=layer,
            session_id=session_id,
            human_label=human_label,
            agent_id=agent_id,
            source=source,
            metadata=metadata,
        )

    def _resolve_project_context(self, project: Optional[str]) -> str:
        """Intelligently resolve project name from context."""
        return self.ingestion_delegate.resolve_project_context(project)

    @staticmethod
    def _contains_code(text: str) -> bool:
        """Heuristic check for code presence in memory content."""
        return MemoryIngestionDelegate.contains_code(text)

    async def store_memory(
        self,
        tenant_id: str,
        project: Optional[str],
        content: str,
        source: str,
        importance: Optional[float] = None,
        tags: Optional[list] = None,
        layer: Optional[str] = None,
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        ttl: Optional[int] = None,
        info_class: str = "internal",
        governance: Optional[dict] = None,
        metadata: Optional[dict] = None,
        agent_id: Optional[str] = None,
        human_label: Optional[str] = None,
        envelope: Optional[ContextEnvelope] = None,
    ) -> str:
        """Store memory using RAEEngine."""
        return await self.ingestion_delegate.store_memory(
            tenant_id=tenant_id,
            project=project,
            content=content,
            source=source,
            importance=importance,
            tags=tags,
            layer=layer,
            session_id=session_id,
            memory_type=memory_type,
            ttl=ttl,
            info_class=info_class,
            governance=governance,
            metadata=metadata,
            agent_id=agent_id,
            human_label=human_label,
            envelope=envelope,
        )

    async def get_memory(
        self, memory_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
        return await self.retrieval_delegate.get_memory(memory_id, tenant_id)

    async def delete_memory(self, memory_id: str, tenant_id: str) -> bool:
        """Delete a memory by ID."""
        return await self.lifecycle_delegate.delete_memory(memory_id, tenant_id)

    async def list_memories(
        self,
        tenant_id: str,
        layer: Optional[str] = None,
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List memories for a specific layer and project (agent)."""
        return await self.retrieval_delegate.list_memories(
            tenant_id=tenant_id,
            layer=layer,
            project=project,
            tags=tags,
            filters=filters,
            limit=limit,
            offset=offset,
            agent_id=agent_id,
        )

    async def count_memories(
        self,
        tenant_id: str,
        layer: str,
        project: str,
        agent_id: str | None = None,
    ) -> int:
        """Count memories for a layer and project."""
        return await self.retrieval_delegate.count_memories(
            tenant_id=tenant_id, layer=layer, project=project, agent_id=agent_id
        )

    async def get_metric_aggregate(
        self,
        tenant_id: str,
        layer: str,
        project: str,
        metric: str,
        func: str,
    ) -> float:
        """Get aggregate metric (e.g., avg importance)."""
        return await self.lifecycle_delegate.get_metric_aggregate(
            tenant_id=tenant_id, layer=layer, project=project, metric=metric, func=func
        )

    async def update_memory_access_batch(
        self,
        memory_ids: List[str],
        tenant_id: str,
    ) -> int:
        """Update access stats for multiple memories."""
        return await self.lifecycle_delegate.update_memory_access_batch(
            memory_ids=memory_ids, tenant_id=tenant_id
        )

    async def adjust_importance(
        self,
        memory_id: str | UUID,
        delta: float,
        tenant_id: str,
    ) -> Optional[float]:
        """Adjust memory importance."""
        return await self.lifecycle_delegate.adjust_importance(
            memory_id=memory_id, delta=delta, tenant_id=tenant_id
        )

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = False,
    ) -> int:
        """Apply importance decay to all memories for a tenant."""
        return await self.lifecycle_delegate.decay_importance(
            tenant_id=tenant_id,
            decay_rate=decay_rate,
            consider_access_stats=consider_access_stats,
        )

    async def _get_tenant_weights(self, tenant_id: str) -> Optional[Any]:
        """Retrieve custom scoring weights for tenant from config."""
        return await self.lifecycle_delegate.get_tenant_weights(tenant_id)

    async def query_memories(
        self,
        tenant_id: str,
        project: str,
        query: str,
        k: int = 10,
        layers: Optional[list] = None,
        filters: Optional[dict] = None,
    ) -> SearchResponse:
        """Query memories across layers with dynamic weights."""
        return await self.retrieval_delegate.query_memories(
            tenant_id=tenant_id,
            project=project,
            query=query,
            k=k,
            layers=layers,
            filters=filters,
        )

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        project: Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 10,
        enable_reranking: bool = False,
        filters: Optional[dict] = None,
        auto_route: bool = False,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Search memories across layers using RAE Core Engine."""
        return await self.retrieval_delegate.search_memories(
            query=query,
            tenant_id=tenant_id,
            project=project,
            layer=layer,
            limit=limit,
            enable_reranking=enable_reranking,
            filters=filters,
            auto_route=auto_route,
            **kwargs,
        )

    async def search_evidence(
        self,
        query: str,
        tenant_id: str = "default",
        project: Optional[str] = None,
        agent_id: Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 10,
        strategies: Optional[List[str]] = None,
        custom_weights: Optional[Dict[str, float]] = None,
        auto_route: bool = False,
        enable_reranking: bool = False,
        force_2pass: bool = False,
        filters: Optional[dict] = None,
        **kwargs: Any,
    ) -> EvidencePackage:
        """Search memories across layers returning an auditable EvidencePackage."""
        return await self.retrieval_delegate.search_evidence(
            query=query,
            tenant_id=tenant_id,
            project=project,
            agent_id=agent_id,
            layer=layer,
            limit=limit,
            strategies=strategies,
            custom_weights=custom_weights,
            auto_route=auto_route,
            enable_reranking=enable_reranking,
            force_2pass=force_2pass,
            filters=filters,
            **kwargs,
        )

    async def consolidate_memories(
        self,
        tenant_id: str,
        project: str,
    ) -> dict:
        """Trigger memory consolidation."""
        return await self.lifecycle_delegate.consolidate_memories(
            tenant_id=tenant_id, project=project
        )

    async def generate_reflections(
        self,
        tenant_id: str,
        project: str,
    ) -> list:
        """Generate reflections from patterns."""
        return await self.lifecycle_delegate.generate_reflections(
            tenant_id=tenant_id, project=project
        )

    async def get_statistics(
        self,
        tenant_id: str,
        project: str,
    ) -> dict:
        """Get memory statistics across all layers."""
        return await self.lifecycle_delegate.get_statistics(
            tenant_id=tenant_id, project=project
        )

    async def clear_memories(
        self,
        tenant_id: str,
    ) -> dict:
        """Clear all memories for tenant."""
        return await self.lifecycle_delegate.clear_memories(tenant_id=tenant_id)

    async def get_session_context(
        self,
        session_id: str,
        tenant_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Retrieve all memories associated with a specific session."""
        return await self.retrieval_delegate.get_session_context(
            session_id=session_id, tenant_id=tenant_id, limit=limit
        )

    async def list_unique_tenants(self) -> List[str]:
        """List all unique tenant IDs in the system."""
        return await self.lifecycle_delegate.list_unique_tenants()

    async def list_tenants_with_details(self) -> List[Dict[str, str]]:
        """List all tenants with their names."""
        return await self.lifecycle_delegate.list_tenants_with_details()

    async def update_tenant_name(self, tenant_id: str, name: str) -> bool:
        """Update tenant name."""
        return await self.lifecycle_delegate.update_tenant_name(
            tenant_id=tenant_id, name=name
        )

    async def rename_project(
        self, tenant_id: str, old_project_id: str, new_project_id: str
    ) -> bool:
        """Rename a project by updating all references in the database."""
        return await self.lifecycle_delegate.rename_project(
            tenant_id=tenant_id,
            old_project_id=old_project_id,
            new_project_id=new_project_id,
        )

    async def list_unique_projects(self, tenant_id: str) -> List[str]:
        """List all unique project IDs for a tenant."""
        return await self.lifecycle_delegate.list_unique_projects(tenant_id)

    async def list_active_project_tenants(
        self, since: datetime
    ) -> List[Dict[str, str]]:
        """List unique (project, tenant_id) pairs with recent activity."""
        return await self.lifecycle_delegate.list_active_project_tenants(since)

    async def list_long_sessions(
        self, tenant_id: str, project: str, threshold: int
    ) -> List[Dict[str, Any]]:
        """List sessions with event count above threshold."""
        return await self.lifecycle_delegate.list_long_sessions(
            tenant_id=tenant_id, project=project, threshold=threshold
        )

    async def apply_global_memory_decay(self, decay_rate: float) -> None:
        """Apply decay to all memories strength."""
        await self.lifecycle_delegate.apply_global_memory_decay(decay_rate)

    async def delete_expired_memories(self) -> int:
        """Delete all expired memories in the system."""
        return await self.lifecycle_delegate.delete_expired_memories()

    async def delete_old_episodic_memories(self, days: int) -> int:
        """Delete old episodic memories to manage data lifecycle."""
        return await self.lifecycle_delegate.delete_old_episodic_memories(days)

    async def list_memories_for_graph_extraction(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List memories that are pending graph extraction."""
        return await self.retrieval_delegate.list_memories_for_graph_extraction(limit)


async def get_rae_core_service(request: Request) -> RAECoreService:
    """Dependency for getting RAECoreService from app state."""
    return request.app.state.rae_core_service
