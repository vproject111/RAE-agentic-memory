"""
Context Builder - Working Memory Construction with Reflections

This service builds the Working Memory (Layer 2) by combining:
- Recent conversation messages
- Relevant Long-Term Memories (LTM)
- Lessons Learned from Reflective Memory
- User/system profiles

Implements the context injection pattern from RAE v1 Implementation Plan.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import UUID

import structlog

from apps.memory_api.config import settings
from apps.memory_api.observability.rae_tracing import get_tracer
from apps.memory_api.services.memory_scoring_v2 import (
    ScoringWeights,
    compute_batch_scores,
    rank_memories_by_score,
)
from apps.memory_api.services.memory_scoring_v3 import (
    ScoringWeightsV3,
    compute_batch_scores_v3,
)
from apps.memory_api.services.reflection_engine_v2 import ReflectionEngineV2
from apps.memory_api.services.smart_reranker import SmartReranker

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)
tracer = get_tracer(__name__)


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class ContextConfig:
    """Configuration for context building"""

    # Token budgets
    max_total_tokens: int = 8000
    max_messages_tokens: int = 4000
    max_ltm_tokens: int = 2000
    max_reflections_tokens: int = 1024
    max_profile_tokens: int = 512

    # Retrieval limits
    max_ltm_items: int = 10
    max_reflection_items: int = 5
    min_reflection_importance: float = 0.5

    # Scoring
    enable_enhanced_scoring: bool = True
    enable_scoring_v3: bool = False
    scoring_weights: Optional[ScoringWeights] = None


# ============================================================================
# Context Components
# ============================================================================


@dataclass
class ContextComponent:
    """A single component of the context"""

    type: str  # "message", "ltm", "reflection", "profile"
    content: str
    metadata: Dict[str, Any]
    tokens: int = 0


@dataclass
class WorkingMemoryContext:
    """
    Complete Working Memory context ready for LLM.

    Contains all components needed for agent execution.
    """

    # Core components
    messages: List[ContextComponent]
    ltm_items: List[ContextComponent]
    reflections: List[ContextComponent]
    profile_items: List[ContextComponent]

    # Formatted output
    system_prompt: str
    context_text: str

    # Metadata
    total_tokens: int
    retrieval_stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "messages": [
                {"type": c.type, "content": c.content, "metadata": c.metadata}
                for c in self.messages
            ],
            "ltm_items": [
                {"type": c.type, "content": c.content, "metadata": c.metadata}
                for c in self.ltm_items
            ],
            "reflections": [
                {"type": c.type, "content": c.content, "metadata": c.metadata}
                for c in self.reflections
            ],
            "profile_items": [
                {"type": c.type, "content": c.content, "metadata": c.metadata}
                for c in self.profile_items
            ],
            "system_prompt": self.system_prompt,
            "context_text": self.context_text,
            "total_tokens": self.total_tokens,
            "retrieval_stats": self.retrieval_stats,
        }


# ============================================================================
# ContextBuilder Service
# ============================================================================


class ContextBuilder:
    """
    Service for building Working Memory context with reflections.

    This implements Layer 2 (Working Memory) of the 4-layer memory architecture,
    combining inputs from Layer 1 (Sensory), Layer 3 (LTM), and Layer 4 (Reflective).
    """

    def __init__(
        self,
        rae_service: "RAECoreService",
        reflection_engine: Optional[ReflectionEngineV2] = None,
        config: Optional[ContextConfig] = None,
    ):
        """
        Initialize ContextBuilder

        Args:
            rae_service: RAECoreService for retrieval
            reflection_engine: Reflection engine for querying reflections
            config: Context configuration
        """
        self.rae_service = rae_service
        self.reflection_engine = reflection_engine or ReflectionEngineV2(
            rae_service=rae_service
        )
        self.reranker = SmartReranker()
        self.config = config or ContextConfig()

    async def build_context(
        self,
        tenant_id: UUID,
        project_id: str,
        query: str,
        recent_messages: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> WorkingMemoryContext:
        """
        Build complete Working Memory context.

        Args:
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Current user query/task
            recent_messages: Recent conversation messages
            user_id: Optional user identifier
            session_id: Optional session identifier

        Returns:
            WorkingMemoryContext with all components
        """
        with tracer.start_as_current_span("rae.context_builder.build") as span:
            span.set_attribute("rae.tenant_id", tenant_id)
            span.set_attribute("rae.project_id", project_id)
            span.set_attribute("rae.context.query_length", len(query))
            span.set_attribute("rae.context.max_tokens", self.config.max_total_tokens)

            logger.info(
                "context_building_started",
                tenant_id=tenant_id,
                project_id=project_id,
                query_length=len(query),
            )

            retrieval_stats = {
                "ltm_retrieved": 0,
                "reflections_retrieved": 0,
                "scoring_method": (
                    "enhanced" if self.config.enable_enhanced_scoring else "basic"
                ),
            }

            # 1. Format recent messages
            message_components = self._format_messages(recent_messages or [])
            span.set_attribute("rae.context.messages_count", len(message_components))

            # 2. Retrieve relevant LTM
            ltm_components = await self._retrieve_ltm(
                tenant_id=tenant_id,
                project_id=project_id,
                query=query,
            )
            retrieval_stats["ltm_retrieved"] = len(ltm_components)
            span.set_attribute("rae.context.ltm_retrieved", len(ltm_components))

            # 3. Retrieve relevant reflections (Lessons Learned)
            reflection_components = await self._retrieve_reflections(
                tenant_id=tenant_id,
                project_id=project_id,
                query=query,
            )
            retrieval_stats["reflections_retrieved"] = len(reflection_components)
            span.set_attribute(
                "rae.context.reflections_retrieved", len(reflection_components)
            )

            # 4. Retrieve user/system profile
            profile_components = await self._retrieve_profile(
                tenant_id=tenant_id, project_id=project_id, user_id=user_id
            )
            span.set_attribute("rae.context.profile_items", len(profile_components))

            # 5. Build formatted context
            system_prompt, context_text = self._build_formatted_context(
                messages=message_components,
                ltm_items=ltm_components,
                reflections=reflection_components,
                profile_items=profile_components,
            )

            # 6. Calculate total tokens (rough estimate)
            total_tokens = (
                sum(c.tokens for c in message_components)
                + sum(c.tokens for c in ltm_components)
                + sum(c.tokens for c in reflection_components)
                + sum(c.tokens for c in profile_components)
            )

            span.set_attribute("rae.context.total_tokens", total_tokens)
            span.set_attribute(
                "rae.context.scoring_method", retrieval_stats["scoring_method"]
            )
            span.set_attribute("rae.outcome.label", "success")

            logger.info(
                "context_building_completed",
                tenant_id=tenant_id,
                total_tokens=total_tokens,
                stats=retrieval_stats,
            )

            return WorkingMemoryContext(
                messages=message_components,
                ltm_items=ltm_components,
                reflections=reflection_components,
                profile_items=profile_components,
                system_prompt=system_prompt,
                context_text=context_text,
                total_tokens=total_tokens,
                retrieval_stats=retrieval_stats,
            )

    def _format_messages(
        self, messages: List[Dict[str, Any]]
    ) -> List[ContextComponent]:
        """Format recent conversation messages"""
        components = []
        for msg in messages[-10:]:  # Last 10 messages
            content = msg.get("content", "")
            role = msg.get("role", "user")
            tokens = len(content.split()) * 1.3  # Rough estimate

            components.append(
                ContextComponent(
                    type="message",
                    content=content,
                    metadata={"role": role},
                    tokens=int(tokens),
                )
            )

        return components

    async def _retrieve_ltm(
        self, tenant_id: UUID, project_id: str, query: str
    ) -> List[ContextComponent]:
        """
        Retrieve relevant Long-Term Memories.

        Uses enhanced scoring if enabled.
        """
        # Get query embedding (will be used for vector search in production)
        # query_embedding = await get_embedding(query)

        # Retrieve episodic and semantic memories
        episodic = await self.rae_service.list_memories(
            tenant_id=str(tenant_id), project=project_id, layer="episodic", limit=50
        )
        semantic = await self.rae_service.list_memories(
            tenant_id=str(tenant_id), project=project_id, layer="semantic"
        )

        all_memories = episodic + semantic

        if not all_memories:
            return []

        # TODO: In production, use vector search to get similarity scores
        # For now, use placeholder similarity
        similarity_scores = [0.8] * len(all_memories)

        # Phase 3: Selection and Ranking
        top_memories: List[Dict[str, Any]] = []

        if self.config.enable_scoring_v3:
            # Use Iteration 3 Scoring (Formal RAE Objective)
            score_results_v3 = compute_batch_scores_v3(
                memories=all_memories,
                similarity_scores=similarity_scores,
                weights=ScoringWeightsV3(
                    w1_relevance=settings.MATH_V3_W1_RELEVANCE,
                    w2_importance=settings.MATH_V3_W2_IMPORTANCE,
                    w3_recency=settings.MATH_V3_W3_RECENCY,
                    w4_centrality=settings.MATH_V3_W4_CENTRALITY,
                    w5_diversity=settings.MATH_V3_W5_DIVERSITY,
                    w6_density=settings.MATH_V3_W6_DENSITY,
                ),
            )
            # Use Any cast to avoid V3 vs V2 type mismatch
            ranked_v3 = rank_memories_by_score(
                all_memories, cast(Any, score_results_v3)
            )

            # --- Iteration 2: Smart Re-Ranker ---
            if settings.ENABLE_SMART_RERANKER:
                # Take a larger pool for re-ranking (e.g. top 50)
                candidates = ranked_v3[: settings.RERANKER_TOP_K_CANDIDATES]
                # Apply re-ranking
                ranked_v3 = await self.reranker.rerank(
                    candidates, query, limit=settings.RERANKER_FINAL_K
                )
                # Use this new list as top_memories (it's already limited)
                top_memories = ranked_v3
            else:
                top_memories = ranked_v3[: self.config.max_ltm_items]

        elif self.config.enable_enhanced_scoring:
            # Use enhanced scoring
            score_results_v2 = compute_batch_scores(
                memories=all_memories,
                similarity_scores=similarity_scores,
                weights=self.config.scoring_weights,
            )
            ranked_v2 = rank_memories_by_score(
                all_memories, cast(Any, score_results_v2)
            )
            top_memories = ranked_v2[: self.config.max_ltm_items]
        else:
            # Basic ranking by similarity
            ranked_basic = sorted(
                zip(all_memories, similarity_scores),
                key=lambda x: x[1],
                reverse=True,
            )
            top_memories = [m[0] for m in ranked_basic[: self.config.max_ltm_items]]

        # Convert to components
        components = []
        for mem in top_memories:
            content = mem.get("content", "")
            tokens = len(content.split()) * 1.3

            components.append(
                ContextComponent(
                    type="ltm",
                    content=content,
                    metadata={
                        "id": str(mem.get("id")),
                        "layer": mem.get("layer"),
                        "importance": mem.get("importance", 0.5),
                        "created_at": str(mem.get("created_at", "")),
                    },
                    tokens=int(tokens),
                )
            )

        return components

    async def _retrieve_reflections(
        self, tenant_id: UUID, project_id: str, query: str
    ) -> List[ContextComponent]:
        """
        Retrieve relevant reflections (Lessons Learned).

        This is the key integration point for Reflective Memory (Layer 4).
        """
        # Check if reflective memory is enabled
        if not settings.REFLECTIVE_MEMORY_ENABLED:
            logger.info(
                "reflections_retrieval_skipped",
                tenant_id=tenant_id,
                reason="reflective_memory_disabled",
            )
            return []

        # Apply mode-specific limits
        max_items = settings.REFLECTIVE_MAX_ITEMS_PER_QUERY
        min_importance = settings.REFLECTION_MIN_IMPORTANCE_THRESHOLD

        logger.info(
            "reflections_retrieval_started",
            tenant_id=tenant_id,
            mode=settings.REFLECTIVE_MEMORY_MODE,
            max_items=max_items,
            min_importance=min_importance,
        )

        # Query reflections using reflection engine
        reflections = await self.reflection_engine.query_reflections(
            tenant_id=str(tenant_id),
            project_id=project_id,
            query_text=query,
            k=max_items,
            min_importance=min_importance,
        )

        # Convert to components
        components = []
        for refl in reflections:
            content = refl.get("content", "")
            tokens = len(content.split()) * 1.3

            components.append(
                ContextComponent(
                    type="reflection",
                    content=content,
                    metadata={
                        "id": str(refl.get("id")),
                        "importance": refl.get("importance", 0.5),
                        "tags": refl.get("tags", []),
                        "created_at": str(refl.get("created_at", "")),
                    },
                    tokens=int(tokens),
                )
            )

        logger.info(
            "reflections_retrieval_completed",
            tenant_id=tenant_id,
            retrieved_count=len(components),
        )

        return components

    async def _retrieve_profile(
        self,
        tenant_id: UUID,
        project_id: str,
        user_id: Optional[str] = None,
    ) -> List[ContextComponent]:
        """Retrieve user/system profile information"""
        # TODO: Implement profile retrieval
        # For now, return empty
        return []

    def _build_formatted_context(
        self,
        messages: List[ContextComponent],
        ltm_items: List[ContextComponent],
        reflections: List[ContextComponent],
        profile_items: List[ContextComponent],
    ) -> tuple[str, str]:
        """
        Build formatted context for LLM.

        Returns:
            Tuple of (system_prompt, context_text)
        """
        sections = []

        # 1. System prompt (always included)
        system_prompt = (
            "You are a helpful AI assistant with access to memory and reflections."
        )

        # 2. Profile section (if any)
        if profile_items:
            profile_text = "\n".join([p.content for p in profile_items])
            sections.append(f"# User Profile\n{profile_text}")

        # 3. Lessons Learned section (CRITICAL for reflective memory)
        if reflections:
            lessons = []
            for refl in reflections:
                tags = refl.metadata.get("tags", [])
                tag_text = f" [{', '.join(tags)}]" if tags else ""
                lessons.append(f"- {refl.content}{tag_text}")

            lessons_text = "\n".join(lessons)
            sections.append(
                f"# Lessons Learned (internal reflective memory)\n{lessons_text}"
            )
        elif not settings.REFLECTIVE_MEMORY_ENABLED:
            # Explicitly indicate when reflective memory is disabled
            sections.append(
                "# Lessons Learned\n[Reflective memory is currently disabled]"
            )

        # 4. Relevant Context section (LTM)
        if ltm_items:
            context_items = []
            for ltm in ltm_items:
                layer = ltm.metadata.get("layer", "")
                context_items.append(f"- [{layer}] {ltm.content}")

            context_text = "\n".join(context_items)
            sections.append(f"# Relevant Context\n{context_text}")

        # 5. Recent messages handled separately (in conversation history)

        # Combine sections
        full_context = "\n\n".join(sections)

        return system_prompt, full_context

    async def inject_reflections_into_prompt(
        self,
        base_prompt: str,
        tenant_id: UUID,
        project_id: str,
        query: str,
    ) -> str:
        """
        Helper method to inject reflections into an existing prompt.

        Args:
            base_prompt: Original system prompt
            tenant_id: Tenant identifier
            project_id: Project identifier
            query: Current query for relevance

        Returns:
            Enhanced prompt with reflections injected
        """
        reflections = await self._retrieve_reflections(
            tenant_id=tenant_id, project_id=project_id, query=query
        )

        if not reflections:
            return base_prompt

        # Format reflections
        lessons = []
        for refl in reflections:
            tags = refl.metadata.get("tags", [])
            tag_text = f" [{', '.join(tags)}]" if tags else ""
            lessons.append(f"- {refl.content}{tag_text}")

        lessons_text = "\n".join(lessons)

        # Inject into prompt
        enhanced_prompt = f"""{base_prompt}

# Lessons Learned (internal memory)
{lessons_text}

Consider these lessons when formulating your response."""

        return enhanced_prompt
