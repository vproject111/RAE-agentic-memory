"""
RAE-Core integration service.

Wraps RAEEngine and adapters for use in FastAPI application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

import asyncpg
import redis.asyncio as redis
import structlog
from fastapi import Request
from qdrant_client import AsyncQdrantClient

from apps.memory_api.services.dashboard_websocket import DashboardWebSocketService
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
from rae_core.exceptions.base import SecurityPolicyViolationError
from rae_core.interfaces.cache import ICacheProvider
from rae_core.interfaces.database import IDatabaseProvider
from rae_core.interfaces.reranking import IReranker
from rae_core.interfaces.storage import IMemoryStorage
from rae_core.interfaces.vector import IVectorStore
from rae_core.models.interaction import AgentAction, RAEInput
from rae_core.models.search import SearchResponse
from rae_core.runtime import RAERuntime
from rae_core.types.enums import InformationClass, MemoryLayer

logger = structlog.get_logger(__name__)


class RAECoreService:
    """
    Integration service for RAE-Core.

    Manages RAEEngine and RAERuntime lifecycles.
    """

    def __init__(
        self,
        postgres_pool: Optional[asyncpg.Pool] = None,
        qdrant_client: Optional[AsyncQdrantClient] = None,
        redis_client: Optional[redis.Redis] = None,
    ):
        """
        Initialize service with infrastructure clients.
        """
        self.postgres_pool = postgres_pool
        self.qdrant_client = qdrant_client
        self.redis_client = redis_client

        self.postgres_adapter: IMemoryStorage
        self.qdrant_adapter: IVectorStore
        self.redis_adapter: ICacheProvider
        self.mcp_client: Optional[Any] = None
        self.savings_service: Optional[TokenSavingsService] = None
        self.websocket_service: Optional[DashboardWebSocketService] = None
        self.tuning_service: Any = None  # Phase 4

        if postgres_pool:
            self.savings_service = TokenSavingsService(postgres_pool)
            self.websocket_service = DashboardWebSocketService(postgres_pool)

            # Phase 4: Self-improvement service
            from apps.memory_api.services.tuning_service import TuningService

            self.tuning_service = TuningService(self)

        from apps.memory_api.config import settings

        # 1. Initialize embedding providers (Multi-Vector Support)
        self._init_embedding_providers(settings)

        # 2. Initialize adapters
        self._init_adapters(settings, postgres_pool, qdrant_client, redis_client)

        # 3. Initialize Engine & Runtime
        self._init_engine(settings, postgres_pool)

        # New: Reflection Engine
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

        # New: RAERuntime for RAE-First flow (Use Engine for implicit capture policy enforcement)
        self.runtime = RAERuntime(
            cast(Any, self.engine), None
        )  # Agent set per execution

        self.szubar_mode = False  # Tryb Szubartowskiego (Pressure/Emergent Learning)

        logger.info("rae_core_service_initialized", profile=settings.RAE_PROFILE)

    def enable_szubar_mode(self, enabled: bool = True) -> None:
        """Enable or disable RAE-SZUBAR Mode (Evolutionary Pressure)."""
        self.szubar_mode = enabled
        logger.info("szubar_mode_changed", enabled=enabled)

    def _init_embedding_providers(self, settings: Any) -> None:
        """Initialize embedding providers (Multi-Vector Support)."""

        self.embedding_provider = EmbeddingManager(
            default_provider=LocalEmbeddingProvider()
        )

        # Register ONNX
        import os

        if settings.RAE_EMBEDDING_BACKEND == "onnx" or os.getenv("ONNX_EMBEDDER_PATH"):
            self._register_onnx_provider(settings)

        # Register API
        if settings.RAE_EMBEDDING_BACKEND == "api":
            api_provider = LocalEmbeddingProvider()
            self.embedding_provider.register_provider("api", api_provider)
            self.embedding_provider._default_provider = api_provider
            # Important: set default_model_name to the actual model for proper vector space targeting
            self.embedding_provider.default_model_name = (
                settings.RAE_EMBEDDING_MODEL or "api"
            )
            logger.info(
                "registered_api_embedding_provider",
                model=self.embedding_provider.default_model_name,
            )

        # Register MCP
        if settings.RAE_EMBEDDING_BACKEND == "mcp":
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
                settings.ONNX_EMBEDDER_PATH or "models/nomic-embed-text-v1.5/model.onnx"
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
                    use_gpu=settings.RAE_USE_GPU,
                )
                self.embedding_provider.register_provider(model_name, onnx_provider)
                if settings.RAE_EMBEDDING_BACKEND == "onnx":
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
                command=settings.RAE_MCP_SERVER_COMMAND,
                args=settings.RAE_MCP_SERVER_ARGS,
            )
            self.mcp_client = mcp_client
            mcp_provider = MCPEmbeddingProvider(
                tool_name=settings.RAE_MCP_EMBEDDING_TOOL, client=mcp_client
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

            # Calibration: Use 'nomic' vector space for nomic models, 'dense' for others
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
        from rae_core.search.engine import HybridSearchEngine
        from rae_core.search.strategies.fulltext import FullTextStrategy
        from rae_core.search.strategies.vector import VectorSearchStrategy

        search_strategies = {
            "vector": VectorSearchStrategy(
                vector_store=self.qdrant_adapter,
                embedding_provider=self.embedding_provider,
            ),
            "fulltext": FullTextStrategy(memory_storage=self.postgres_adapter),
        }

        # SYSTEM 40.15: Optional Graph Store for Lite Mode
        graph_repo = None
        if postgres_pool:
            try:
                graph_repo = self.enhanced_graph_repo
            except Exception as e:
                logger.warning("graph_repo_init_skipped", reason=str(e))

        search_engine = HybridSearchEngine(
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

        if settings.RAE_RERANKER_BACKEND == "emerald":
            return EmeraldReranker(self.embedding_provider, self.postgres_adapter)
        if settings.RAE_RERANKER_BACKEND == "api" and settings.RAE_RERANKER_API_URL:
            return ApiReranker(
                api_url=settings.RAE_RERANKER_API_URL,
                api_key=settings.RAE_RERANKER_API_KEY,
            )
        if settings.RAE_RERANKER_BACKEND == "mcp":
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
        """
        Execute an agent action through RAERuntime (RAE-First).
        """
        from uuid import uuid4

        from rae_core.interfaces.agent import BaseAgent

        # Create a transient agent wrapper for the LLM
        class TransientAgent(BaseAgent):
            def __init__(self, service: "RAECoreService"):
                self.service = service

            async def run(self, rae_input: RAEInput) -> AgentAction:
                # 1. Build context using core ContextBuilder (Agnostic)
                from rae_core.context.builder import ContextBuilder

                builder = ContextBuilder(max_tokens=4000)

                agent_id = rae_input.context.get("agent_id", "default")
                project = rae_input.context.get("project", "default")

                # Search for relevant memories in RAE across ALL layers
                search_results = await self.service.engine.search_memories(
                    query=rae_input.content,
                    tenant_id=rae_input.tenant_id,
                    agent_id=agent_id,
                    project=project,
                    layer=None,
                    top_k=10,
                )

                # Use core builder to assemble LLM-ready context
                context_text, _ = builder.build_context(
                    memories=search_results, query=rae_input.content
                )

                # RAE-SZUBAR PRESSURE: Inject failures
                pressure_constraints = ""
                if self.service.szubar_mode:
                    # 1. Search for failures in the current context
                    failures = await self.service.engine.search_memories(
                        query=rae_input.content,
                        tenant_id=rae_input.tenant_id,
                        agent_id="default",  # Failures are usually project-wide
                        project=project,
                        layer=None,
                        top_k=5,
                        filters={"governance.is_failure": "true"},
                    )

                    # 2. If nothing found, try project-wide wildcard search for failures
                    if not failures:
                        failures = await self.service.engine.search_memories(
                            query="*",
                            tenant_id=rae_input.tenant_id,
                            agent_id="default",
                            project=project,
                            layer=None,
                            top_k=5,
                            filters={"governance.is_failure": "true"},
                        )

                    if failures:
                        pressure_constraints = (
                            "\nCRITICAL: DO NOT REPEAT THESE FAILURES:\n"
                        )
                        for f in failures:
                            # Handle both dict and potentially other types from adapters
                            if isinstance(f, dict):
                                gov = f.get("governance") or {}
                                # Handle case where governance might be stringified JSON
                                if isinstance(gov, str):
                                    try:
                                        import json

                                        gov = json.loads(gov)
                                    except Exception:
                                        gov = {}
                                trace = gov.get("failure_trace", "Unknown failure")
                                content = f.get("content", "Unknown error")
                                pressure_constraints += (
                                    f"- {content} (Reason: {trace})\n"
                                )

                system_prompt = (
                    "YOU ARE A RAE HIVE AGENT. YOU OPERATE WITHIN AN AGNOSTIC, DETERMINISTIC ENGINE.\n"
                    "CORE MANDATES:\n"
                    "1. MODEL AGNOSTIC: Do not assume specific LLM or embedding library (e.g. use standard Python, avoid sklearn/torch unless specified).\n"
                    "2. ARCHITECTURAL PURITY: Follow RABO ontology and System 93 specs.\n"
                    "3. NO BLOAT: Favor algorithmic elegance (O(log n)) over heavy libraries.\n\n"
                    f"RELEVANT PROJECT CONTEXT:\n{context_text}\n{pressure_constraints}\n\n"
                    f"Task: {rae_input.content}"
                )

                # 2. Generate response using LLM or DESIGNED MATH (Fallback)
                try:
                    import asyncio

                    # Check if LLM is actually available
                    if not self.service.engine.llm_provider:
                        raise RuntimeError("LLM Provider not available (RAE-Lite Mode)")

                    # RELAXED TIMEOUT for weak machines (120s)
                    llm_result = await asyncio.wait_for(
                        self.service.engine.generate_text(
                            prompt=rae_input.content, system_prompt=system_prompt
                        ),
                        timeout=120.0,
                    )
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning("llm_call_failed", error=str(e))
                    # Fallback to direct context or raw answer
                    if search_results:
                        llm_result = (
                            "" + str(search_results[0].get("content", ""))[:500]
                        )
                    else:
                        llm_result = f"I encountered an issue connecting to the model: {str(e)}. Please check system logs."
                if not llm_result:
                    llm_result = "I couldn't generate a response."

                # Extract signals for importance
                signals = []
                if "stability" in llm_result.lower():
                    signals.append("fallback")
                if "decision" in llm_result.lower() or "rule" in llm_result.lower():
                    signals.append("decision")

                from rae_core.models.interaction import AgentActionType

                return AgentAction(
                    type=AgentActionType.FINAL_ANSWER,
                    content=llm_result,
                    confidence=0.5 if "FALLBACK" in llm_result else 0.9,
                    reasoning=(
                        "LLM with Math Fallback"
                        if "FALLBACK" in llm_result
                        else "LLM generation"
                    ),
                    signals=signals,
                )

        # Initialize Runtime with the transient agent
        self.runtime.agent = TransientAgent(self)

        # 4. Context Resolution (ISO 27000 Isolation)
        project_canonical = self._resolve_project_context(project)
        agent_canonical = agent_id or "default"

        # Execute through RAERuntime (Enforces Hard Frames & Implicit Capture)
        return await self.runtime.process(
            RAEInput(
                content=prompt,
                tenant_id=str(tenant_id),
                request_id=uuid4(),
                context={
                    "agent_id": agent_canonical,
                    "project": project_canonical,
                    "session_id": session_id or "default-session",
                    "metadata": metadata or {},
                },
            )
        )

    async def ainit(self):
        """Perform asynchronous initialization of adapters."""
        if hasattr(self.qdrant_adapter, "ainit"):
            await cast(Any, self.qdrant_adapter).ainit()

        # Add other async inits here if needed
        logger.info("rae_core_service_async_initialized")

    @property
    def db(self) -> IDatabaseProvider:
        """Get agnostic database provider."""
        if self.postgres_pool:
            from rae_adapters.postgres_db import PostgresDatabaseProvider

            return PostgresDatabaseProvider(self.postgres_pool)

        # Fallback for Lite mode
        raise RuntimeError("Database provider not available (RAE-Lite mode with no DB)")

    @property
    def enhanced_graph_repo(self) -> Any:
        """Get enhanced graph repository."""
        from apps.memory_api.repositories.graph_repository_enhanced import (
            EnhancedGraphRepository,
        )

        return EnhancedGraphRepository(self.db)

    def _enforce_security_policy(
        self, info_class: str, target_layer: str | MemoryLayer
    ) -> None:
        """Enforce ISO 27000 security policies."""
        layer_value = (
            target_layer.value
            if isinstance(target_layer, MemoryLayer)
            else target_layer
        )
        info_class = info_class.lower()

        # 1. RESTRICTED: Only allowed in Working layer
        if info_class == InformationClass.RESTRICTED:
            if layer_value != MemoryLayer.WORKING:
                logger.error(
                    "security_policy_violation",
                    reason="RESTRICTED data blocked outside Working layer",
                    layer=layer_value,
                    info_class=info_class,
                )
                raise SecurityPolicyViolationError(
                    f"Security Policy Violation: RESTRICTED data cannot be stored in {layer_value} layer. "
                    "Only 'working' layer is allowed for restricted information."
                )

        # 2. CONFIDENTIAL: Blocked from Semantic layer
        elif info_class == InformationClass.CONFIDENTIAL:
            if layer_value == MemoryLayer.SEMANTIC:
                logger.error(
                    "security_policy_violation",
                    reason="CONFIDENTIAL data blocked from Semantic layer",
                    layer=layer_value,
                    info_class=info_class,
                )
                raise SecurityPolicyViolationError(
                    f"Security Policy Violation: CONFIDENTIAL data cannot be promoted to {layer_value} layer."
                )

        # 3. INTERNAL: Promotion to Semantic requires HITL/Sanitization (Policy placeholder)
        elif info_class == InformationClass.INTERNAL:
            if layer_value == MemoryLayer.SEMANTIC:
                # In future this could trigger a mandatory HITL/Sanitization flag check
                pass

    def _detect_agentic_patterns(self, governance: dict, tags: list[str]) -> list[str]:
        """Detect agentic patterns and return updated tags."""
        pattern_type = governance.get("pattern_type")
        fields = governance.get("fields", {})

        if pattern_type == "prompt_chaining":
            chain_length = fields.get("chain_length", 0)
            if chain_length > 5:
                if "high_risk_sequence" not in tags:
                    tags.append("high_risk_sequence")
                    logger.warning(
                        "high_risk_sequence_detected", chain_length=chain_length
                    )

        elif pattern_type == "routing_decision":
            confidence = fields.get("decision_basis_confidence") or fields.get(
                "confidence", 1.0
            )
            if confidence < 0.5:
                if "hitl_review_required" not in tags:
                    tags.append("hitl_review_required")
                    logger.warning(
                        "low_confidence_routing_detected", confidence=confidence
                    )

        elif pattern_type == "tool_invocation":
            cost_metrics = fields.get("cost_metrics", {})
            token_count = cost_metrics.get("token_count", 0)
            if token_count > 10000:
                if "heavy_tool_use" not in tags:
                    tags.append("heavy_tool_use")
                    logger.info("heavy_tool_use_detected", token_count=token_count)

        elif pattern_type == "reflection":
            conf_before = fields.get("confidence_before", 1.0)
            conf_after = fields.get("confidence_after", 1.0)
            if conf_after < conf_before:
                if "deeper_reflection_needed" not in tags:
                    tags.append("deeper_reflection_needed")
                    logger.warning(
                        "confidence_delta_negative",
                        before=conf_before,
                        after=conf_after,
                    )

        elif pattern_type == "multi_agent_interaction":
            conflicts = fields.get("conflict_points", [])
            if conflicts:
                if "coordination_failure" not in tags:
                    tags.append("coordination_failure")
                    logger.warning(
                        "agent_coordination_conflict_detected", conflicts=conflicts
                    )

        return tags

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
        import json
        import uuid

        from rae_core.exceptions.base import ContractViolationError

        name = human_label or agent_id or source or "Unknown Agent"
        mid = (metadata or {}).get("target_id") or str(uuid.uuid4())

        payload = {}
        if content.strip().startswith("{") and content.strip().endswith("}"):
            try:
                payload = json.loads(content)
            except Exception:
                payload = {"analysis": content}
        else:
            payload = {"analysis": content}

        # SYSTEM 93.3: Hallucination Prevention Context
        # Inject actual source content for L1 Grounding verification
        source_memories = await self.engine.search_memories(
            query=content, tenant_id=tenant_id, top_k=5
        )
        payload["retrieved_sources_content"] = [m["content"] for m in source_memories]

        payload.update(
            {
                "retrieved_sources": [str(m["id"]) for m in source_memories],
                "decision": (metadata or {}).get("decision", "proceed"),
                "confidence": (metadata or {}).get("confidence", 0.5),
                "metadata": {
                    **(metadata or {}),
                    "trace_id": str(session_id or "audit-000"),
                },
            }
        )

        # SYSTEM 93.4: Full Decision Provenance
        # We link the decision to the specific memories that influenced it
        validation_results = await self.reflection_coordinator.run_reflections(payload)

        # PERMANENT AUDIT TRAIL
        audit_content = (
            f"DECISION AUDIT: {name}\n"
            f"Decision: {payload['decision']}\n"
            f"Confidence: {payload['confidence']}\n"
            f"Reasoning: {payload['analysis'][:500]}\n"
            f"Evidence IDs: {payload['retrieved_sources']}\n"
            f"Validation: {validation_results['final_decision']}"
        )

        await self.engine.store_memory(
            tenant_id=tenant_id,
            agent_id="oracle_auditor",
            content=audit_content,
            layer="reflective",
            tags=["decision_provenance", "audit_log"],
            metadata={
                "target_id": mid,
                "evidence_ids": payload["retrieved_sources"],
                "validation_full": validation_results,
            },
        )

        if validation_results.get("final_decision") == "blocked":
            raise ContractViolationError(
                f"Decision Blocked by Oracle: {validation_results['block_reasons']}"
            )

        updated_metadata = (metadata or {}).copy()
        updated_metadata["audit_verified"] = True
        updated_metadata["provenance_link"] = payload["retrieved_sources"]
        return updated_metadata

    def _resolve_project_context(self, project: Optional[str]) -> str:
        """
        Intelligently resolve project name from context.
        Hierarchy: explicit > env(RAE_PROJECT) > env(PROJECT_NAME) > default.
        """
        import os

        if project and project != "default":
            return project

        env_project = os.getenv("RAE_PROJECT") or os.getenv("PROJECT_NAME")
        if env_project:
            return env_project

        return "default"

    async def store_memory(
        self,
        tenant_id: str,
        project: Optional[str],
        content: str,
        source: str,
        importance: Optional[float] = None,
        tags: Optional[list] = None,
        layer: Optional[str] = None,
        # New fields
        session_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        ttl: Optional[int] = None,
        info_class: str = "internal",
        governance: Optional[dict] = None,
        metadata: Optional[dict] = None,
        agent_id: Optional[str] = None,
        human_label: Optional[str] = None,
    ) -> str:
        """
        Store memory using RAEEngine.
        """
        # 1. Enforcement Logic (ISO 27000)
        target_layer = layer or MemoryLayer.EPISODIC
        self._enforce_security_policy(info_class, target_layer)

        # 2. Agentic Pattern Detection (Governance logic)
        tags = tags or []
        if governance:
            tags = self._detect_agentic_patterns(governance, tags)

        # SYSTEM 93.1: Hard Frames 2.0 Contract Enforcement
        if "agent_decision" in tags or "operation_result" in tags or layer == "working":
            try:
                metadata = await self._handle_hard_frames(
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
            except SecurityPolicyViolationError:
                raise
            except Exception as e:
                logger.warning("audit_failed", error=str(e))

        # 3. Context Resolution (Best Practice: Avoid 'default' pollution)
        project_canonical = self._resolve_project_context(project)
        agent_canonical = agent_id or "default"
        metadata = metadata or {}

        # Store in RAEEngine
        if layer == "sensory" and ttl is None:
            ttl = 86400  # 24 hours default for sensory layer

        memory_id = await self.engine.store_memory(
            tenant_id=tenant_id,
            agent_id=agent_canonical,
            content=content,
            layer=target_layer,
            importance=importance or 0.5,
            tags=tags,
            metadata=metadata,
            human_label=human_label,
            project=project_canonical,
            session_id=session_id,
            memory_type=memory_type or "text",
            ttl=ttl,
            source=source,
            info_class=info_class,
            governance=governance,
        )

        logger.info(
            "memory_stored_in_engine",
            memory_id=str(memory_id),
            tenant_id=tenant_id,
            project=project_canonical,
            agent_id=agent_canonical,
            layer=target_layer,
            type=memory_type or "text",
        )

        # Broadcast update if WebSocket service is available
        if self.websocket_service:
            try:
                # We use asyncio.create_task to not block the main flow
                import asyncio

                asyncio.create_task(
                    self.websocket_service.broadcast_memory_created(
                        tenant_id=tenant_id,
                        project=project_canonical,
                        memory_id=memory_id,
                        content=content,
                        importance=importance or 0.5,
                    )
                )
            except Exception as e:
                logger.warning("websocket_broadcast_failed", error=str(e))

        return str(memory_id)

    async def get_memory(
        self, memory_id: str, tenant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a memory by ID."""
        try:
            mem_uuid = UUID(memory_id)
        except ValueError:
            return None

        return await self.postgres_adapter.get_memory(mem_uuid, tenant_id)

    async def delete_memory(self, memory_id: str, tenant_id: str) -> bool:
        """Delete a memory by ID."""
        try:
            mem_uuid = UUID(memory_id)
        except ValueError:
            return False

        return await self.postgres_adapter.delete_memory(mem_uuid, tenant_id)

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
        return await self.postgres_adapter.list_memories(
            tenant_id=tenant_id,
            agent_id=agent_id,
            project=project,
            layer=layer,
            tags=tags,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    async def count_memories(
        self,
        tenant_id: str,
        layer: str,
        project: str,
        agent_id: str | None = None,
    ) -> int:
        """Count memories for a layer and project."""
        from typing import cast

        return cast(
            int,
            await self.postgres_adapter.count_memories(
                tenant_id=tenant_id, agent_id=agent_id, layer=layer
            ),
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
        return await self.postgres_adapter.get_metric_aggregate(
            tenant_id=tenant_id,
            metric=metric,
            func=func,
            filters={"agent_id": project, "layer": layer},
        )

    async def update_memory_access_batch(
        self,
        memory_ids: List[str],
        tenant_id: str,
    ) -> int:
        """Update access stats for multiple memories."""
        if not memory_ids:
            return 0

        try:
            # Filter valid UUIDs
            valid_ids = []
            for mid in memory_ids:
                try:
                    valid_ids.append(UUID(mid))
                except ValueError:
                    continue

            if not valid_ids:
                return 0

            await self.postgres_adapter.update_memory_access_batch(
                memory_ids=valid_ids, tenant_id=tenant_id
            )
            return len(valid_ids)
        except Exception as e:
            logger.error("update_memory_access_batch_failed", error=str(e))
            return 0

    async def adjust_importance(
        self,
        memory_id: str | UUID,
        delta: float,
        tenant_id: str,
    ) -> Optional[float]:
        """Adjust memory importance."""
        try:
            if isinstance(memory_id, UUID):
                mem_uuid = memory_id
            else:
                mem_uuid = UUID(str(memory_id))

            return await self.postgres_adapter.adjust_importance(
                memory_id=mem_uuid, delta=delta, tenant_id=tenant_id
            )
        except (ValueError, Exception) as e:
            logger.error(
                "adjust_importance_failed", memory_id=str(memory_id), error=str(e)
            )
            return None

    async def decay_importance(
        self,
        tenant_id: str,
        decay_rate: float,
        consider_access_stats: bool = False,
    ) -> int:
        """Apply importance decay to all memories for a tenant."""
        from typing import cast

        return cast(
            int,
            await self.engine.memory_storage.decay_importance(
                tenant_id, decay_rate, consider_access_stats
            ),
        )

    async def _get_tenant_weights(self, tenant_id: str) -> Optional[Any]:
        """Retrieve custom scoring weights for tenant from config."""
        try:
            sql = "SELECT config FROM tenants WHERE id = $1"
            config_raw = await self.db.fetchval(sql, tenant_id)
            if not config_raw:
                return None

            import json

            config = (
                json.loads(config_raw) if isinstance(config_raw, str) else config_raw
            )

            if config and "math_weights" in config:
                from rae_core.math.structure import ScoringWeights

                w = config["math_weights"]
                return ScoringWeights(
                    alpha=float(w.get("alpha", 0.5)),
                    beta=float(w.get("beta", 0.3)),
                    gamma=float(w.get("gamma", 0.2)),
                )

        except Exception as e:
            logger.warning(
                "failed_to_load_tenant_weights", tenant_id=tenant_id, error=str(e)
            )
        return None

    async def query_memories(
        self,
        tenant_id: str,
        project: str,
        query: str,
        k: int = 10,
        layers: Optional[list] = None,
        filters: Optional[dict] = None,  # <--- NEW
    ) -> SearchResponse:
        """
        Query memories across layers with dynamic weights.
        """
        import time

        start_time = time.time()

        # 1. Get dynamic weights from tuning service
        weights = None
        if self.tuning_service:
            try:
                weights = await self.tuning_service.get_current_weights(str(tenant_id))
            except Exception as e:
                logger.warning("failed_to_get_tuning_weights", error=str(e))

        # Override weights for Szubar Mode
        if self.szubar_mode:
            from rae_core.math.structure import ScoringWeights

            weights = ScoringWeights.szubar_profile()
            logger.debug("using_szubar_weights_for_query")

        # 2. Execute Engine search
        target_layer = (layers[0] if layers else None) or (filters or {}).get("layer")
        raw_results = await self.engine.search_memories(
            query=query,
            tenant_id=str(tenant_id),
            agent_id="default",  # Explicitly use default agent
            project=project,  # Strict context
            layer=target_layer,
            top_k=k,
            filters=filters,
            custom_weights=weights,
        )

        # 3. Map to SearchResponse model
        from rae_core.models.search import SearchResponse, SearchResult, SearchStrategy

        results_list = []
        for res in raw_results:
            metadata_val = res.get("metadata", {})
            # Fix for Pydantic validation error if DB/Qdrant returns stringified JSON
            if isinstance(metadata_val, str):
                try:
                    import json

                    metadata_val = json.loads(metadata_val)
                except Exception:
                    metadata_val = {}

            # SYSTEM 40.16: Non-negative Score Enforcement
            raw_score = (
                res.get("math_score")
                if res.get("math_score") is not None
                else res.get("search_score", 0.0)
            )
            # Ensure score is at least 0.0 for Pydantic validation
            safe_score = max(0.0, float(raw_score))

            results_list.append(
                SearchResult(
                    memory_id=str(res.get("id")),
                    content=res.get("content", ""),
                    human_label=res.get("human_label"),
                    score=safe_score,
                    strategy_used=SearchStrategy.HYBRID,
                    metadata=metadata_val,
                )
            )

        response = SearchResponse(
            results=results_list,
            query=query,
            strategy=SearchStrategy.HYBRID,
            total_found=len(results_list),
            execution_time_ms=(time.time() - start_time) * 1000,
        )

        # 4. AUDIT: Record this search in the Working Layer (DISABLED FOR PERFORMANCE/NOISE)
        # try:
        #     audit_content = f"Search Query: {query} | Results: {len(results_list)} | Weights: {weights}"
        #     await self.engine.store_memory(...)
        # except Exception as e:
        #     logger.warning("search_audit_failed", error=str(e))

        return response

    async def search_memories(
        self,
        query: str,
        tenant_id: str,
        project: Optional[str] = None,
        layer: Optional[str] = None,
        limit: int = 10,
        enable_reranking: bool = False,
        filters: Optional[dict] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search memories across layers using RAE Core Engine.
        """
        weights = None
        if self.tuning_service:
            try:
                weights = await self.tuning_service.get_current_weights(str(tenant_id))
            except Exception as e:
                logger.warning("failed_to_get_tuning_weights", error=str(e))

        if self.szubar_mode:
            from rae_core.math.structure import ScoringWeights

            weights = ScoringWeights.szubar_profile()

        return await self.engine.search_memories(
            query=query,
            tenant_id=str(tenant_id),
            agent_id="default",
            project=project,
            layer=layer,
            top_k=limit,
            filters=filters,
            custom_weights=weights,
            enable_reranking=enable_reranking,
        )

    async def consolidate_memories(
        self,
        tenant_id: str,
        project: str,
    ) -> dict:
        """
        Trigger memory consolidation.
        """
        results = await self.engine.run_reflection_cycle(
            tenant_id=tenant_id,
            agent_id="default",
            trigger_type="manual",
        )

        logger.info(
            "memories_consolidated",
            tenant_id=tenant_id,
            project=project,
            results=results,
        )

        if self.savings_service and results:
            try:
                tokens_saved = results.get("tokens_saved", 0)
                if tokens_saved > 0:
                    await self.savings_service.track_savings(
                        tenant_id=tenant_id,
                        project=project,
                        model="gpt-4o",
                        predicted_tokens=tokens_saved,
                        real_tokens=0,
                        savings_type="compression",
                    )
            except Exception as e:
                logger.warning("failed_to_track_consolidation_savings", error=str(e))

        return results

    async def generate_reflections(
        self,
        tenant_id: str,
        project: str,
    ) -> list:
        """
        Generate reflections from patterns.
        """
        return []

    async def get_statistics(
        self,
        tenant_id: str,
        project: str,
    ) -> dict:
        """
        Get memory statistics across all layers.
        """
        return self.engine.get_status()

    async def clear_memories(
        self,
        tenant_id: str,
    ) -> dict:
        """
        Clear all memories for tenant.
        """
        return {"deleted": 0}

    async def get_session_context(
        self,
        session_id: str,
        tenant_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all memories associated with a specific session.
        """
        sql = """
            SELECT *
            FROM memories
            WHERE tenant_id = $1
                AND session_id = $2
            ORDER BY timestamp ASC
            LIMIT $3
        """
        records = await self.db.fetch(sql, tenant_id, session_id, limit)
        return [dict(r) for r in records]

    async def list_unique_tenants(self) -> List[str]:
        """List all unique tenant IDs in the system."""
        if hasattr(self.postgres_adapter, "list_unique_tenants"):
            return cast(
                List[str], await cast(Any, self.postgres_adapter).list_unique_tenants()
            )

        records = await self.db.fetch(
            "SELECT DISTINCT tenant_id FROM memories WHERE tenant_id IS NOT NULL"
        )
        return [str(r["tenant_id"]) for r in records]

    async def list_tenants_with_details(self) -> List[Dict[str, str]]:
        """List all tenants with their names."""
        try:
            records = await self.db.fetch("SELECT id, name FROM tenants ORDER BY name")
            return [
                {"id": str(r["id"]), "name": r["name"] or "Unnamed"} for r in records
            ]
        except Exception as e:
            logger.warning("failed_to_list_tenant_details", error=str(e))
            # Fallback to IDs only
            ids = await self.list_unique_tenants()
            return [{"id": i, "name": f"Tenant {i[:8]}..."} for i in ids]

    async def update_tenant_name(self, tenant_id: str, name: str) -> bool:
        """Update tenant name."""
        try:
            # Check if tenant exists in tenants table
            exists = await self.db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM tenants WHERE id = $1)", tenant_id
            )

            if exists:
                await self.db.execute(
                    "UPDATE tenants SET name = $1 WHERE id = $2", name, tenant_id
                )
            else:
                # If not in tenants table but in memories (legacy), insert it
                # Assuming 'enterprise' tier and empty config for now
                await self.db.execute(
                    """
                    INSERT INTO tenants (id, name, tier, config)
                    VALUES ($1, $2, 'enterprise', '{}')
                    ON CONFLICT (id) DO UPDATE SET name = $2
                    """,
                    tenant_id,
                    name,
                )
            return True
        except Exception as e:
            logger.error("update_tenant_name_failed", tenant_id=tenant_id, error=str(e))
            return False

    async def rename_project(
        self, tenant_id: str, old_project_id: str, new_project_id: str
    ) -> bool:
        """
        Rename a project (agent_id) by updating all references in the database.
        This is a heavy operation affecting memories, metrics, etc.
        """
        try:
            if not self.postgres_pool:
                return False
            async with self.postgres_pool.acquire() as conn:
                async with conn.transaction():
                    # Update memories
                    await conn.execute(
                        """
                        UPDATE memories
                        SET project = $1, agent_id = $1
                        WHERE tenant_id = $2 AND (project = $3 OR agent_id = $3)
                        """,
                        new_project_id,
                        tenant_id,
                        old_project_id,
                    )

                    # Update metrics (if we had a project column, but metrics are timeseries so maybe skip or update)
                    # For now, we only update memories as that's the source of truth for RAE

                    logger.info(
                        "project_renamed",
                        tenant_id=tenant_id,
                        old=old_project_id,
                        new=new_project_id,
                    )
                    return True
        except Exception as e:
            logger.error("rename_project_failed", error=str(e))
            return False

    async def list_unique_projects(self, tenant_id: str) -> List[str]:
        """List all unique project IDs for a tenant."""
        records = await self.db.fetch(
            "SELECT DISTINCT agent_id as project FROM memories WHERE tenant_id = $1 AND agent_id IS NOT NULL",
            tenant_id,
        )
        return [str(r["project"]) for r in records]

    async def list_active_project_tenants(
        self, since: datetime
    ) -> List[Dict[str, str]]:
        """List unique (project, tenant_id) pairs with recent activity."""
        records = await self.db.fetch(
            """
            SELECT DISTINCT agent_id as project, tenant_id
            FROM memories
            WHERE created_at >= $1 AND agent_id IS NOT NULL
            """,
            since.replace(tzinfo=None),
        )
        return [{"project": r["project"], "tenant_id": r["tenant_id"]} for r in records]

    async def list_long_sessions(
        self, tenant_id: str, project: str, threshold: int
    ) -> List[Dict[str, Any]]:
        """List sessions with event count above threshold."""
        sql = """
            SELECT
                session_id,
                COUNT(*) as event_count
            FROM memories
            WHERE tenant_id = $1
                AND agent_id = $2
                AND layer = 'episodic'
                AND session_id IS NOT NULL
            GROUP BY session_id
            HAVING COUNT(*) >= $3
            ORDER BY COUNT(*) DESC
        """
        records = await self.db.fetch(sql, tenant_id, project, threshold)
        return [dict(r) for r in records]

    async def apply_global_memory_decay(self, decay_rate: float) -> None:
        """Apply decay to all memories strength."""
        await self.db.execute(
            "UPDATE memories SET strength = strength * $1", decay_rate
        )

    async def delete_expired_memories(self) -> int:
        """Delete all expired memories in the system."""
        result = await self.db.execute(
            "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < NOW()"
        )
        if result and isinstance(result, str) and result.startswith("DELETE"):
            return int(result.split()[-1])
        return 0

    async def delete_old_episodic_memories(self, days: int) -> int:
        """Delete old episodic memories to manage data lifecycle."""
        interval = f"{days} days"
        result = await self.db.execute(
            "DELETE FROM memories WHERE layer = 'episodic' AND created_at < NOW() - $1::interval",
            interval,
        )
        if result and isinstance(result, str) and result.startswith("DELETE"):
            return int(result.split()[-1])
        return 0

    async def list_memories_for_graph_extraction(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List memories that are pending graph extraction."""
        records = await self.db.fetch(
            """
            SELECT DISTINCT tenant_id, ARRAY_AGG(id) as memory_ids
            FROM memories m
            WHERE layer = 'episodic'
                AND NOT EXISTS (
                    SELECT 1 FROM knowledge_graph_edges ke
                    WHERE ke.tenant_id = m.tenant_id
                    AND (ke.source_node_id IN (SELECT id FROM knowledge_graph_nodes WHERE node_id = m.id::text)
                            OR ke.target_node_id IN (SELECT id FROM knowledge_graph_nodes WHERE node_id = m.id::text))
                )
            GROUP BY tenant_id
            LIMIT $1
            """,
            limit,
        )
        return [dict(r) for r in records]


async def get_rae_core_service(request: Request) -> RAECoreService:
    """Dependency for getting RAECoreService from app state."""
    return request.app.state.rae_core_service
