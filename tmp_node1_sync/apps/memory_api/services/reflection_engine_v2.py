"""
ReflectionEngineV2 - Actor-Evaluator-Reflector Pattern Implementation

This service implements the RAE v1 Reflective Memory system following
the Actor → Evaluator → Reflector pattern described in the implementation plan.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast
from uuid import UUID

import structlog

from apps.memory_api.config import settings
from apps.memory_api.models.reflection_v2_models import (
    Event,
    LLMReflectionResponse,
    OutcomeType,
    ReflectionContext,
    ReflectionResult,
)
from apps.memory_api.services.llm import get_llm_provider

if TYPE_CHECKING:
    from apps.memory_api.services.rae_core_service import RAECoreService

logger = structlog.get_logger(__name__)


# ============================================================================
# LLM Prompts
# ============================================================================

REFLECTION_FAILURE_PROMPT = """You are a reflective reasoning engine that learns from failures.

Analyze the following task execution that resulted in an error or failure:

Task Goal: {task_goal}
Task Description: {task_description}

Execution Events:
{events}

Error Information:
- Category: {error_category}
- Message: {error_message}
- Context: {error_context}

Your task:
1. Identify the root cause of the failure
2. Explain what went wrong and why
3. Generate a concise "lesson learned" that can prevent similar issues
4. If possible, suggest a specific strategy or rule for handling this scenario

Provide your analysis as a structured JSON with:
- reflection: A clear explanation of what went wrong (2-3 sentences)
- strategy: A specific actionable strategy or rule (1-2 sentences, optional)
- importance: How important is this lesson? (0.0-1.0, where 1.0 is critical)
- confidence: How confident are you in this analysis? (0.0-1.0)
- tags: List of relevant tags (e.g., ["sql", "timeout", "performance"])
"""

REFLECTION_SUCCESS_PROMPT = """You are a reflective reasoning engine that learns from successes.

Analyze the following task execution that resulted in success:

Task Goal: {task_goal}
Task Description: {task_description}

Execution Events:
{events}

Outcome: SUCCESS

Your task:
1. Identify what strategies or approaches led to success
2. Determine if this is a reusable pattern worth remembering
3. Generate a concise insight about effective approaches

Provide your analysis as a structured JSON with:
- reflection: A clear explanation of what worked well (2-3 sentences)
- strategy: A specific actionable strategy if reusable (1-2 sentences, optional)
- importance: How valuable is this insight? (0.0-1.0, where 1.0 is highly valuable)
- confidence: How confident are you in this analysis? (0.0-1.0)
- tags: List of relevant tags (e.g., ["optimization", "best-practice", "pattern"])
"""


# ============================================================================
# ReflectionEngineV2
# ============================================================================


class ReflectionEngineV2:
    """
    Enhanced Reflection Engine implementing Actor-Evaluator-Reflector pattern.

    This engine generates reflections from:
    - Failures (errors, timeouts, validation failures)
    - Successes (valuable strategies, patterns)
    - Partial outcomes (incomplete but informative)

    Features:
    - Structured reflection generation using LLM
    - Importance and confidence scoring
    - Automatic categorization and tagging
    - Storage to memory_items with proper typing
    - Graph linking in Qdrant (optional)
    """

    def __init__(
        self,
        rae_service: "RAECoreService",
    ):
        """
        Initialize ReflectionEngineV2

        Args:
            rae_service: RAECoreService for memory operations
        """
        self.rae_service = rae_service
        self.llm_provider = get_llm_provider()

    async def generate_reflection(
        self,
        context: ReflectionContext,
    ) -> ReflectionResult:
        """
        Generate a reflection from execution context.

        This is the main entry point following the Reflector pattern:
        1. Analyze the context (events, outcome, error)
        2. Generate structured reflection using LLM
        3. Score importance and confidence
        4. Return ReflectionResult

        Args:
            context: ReflectionContext with events, outcome, error info

        Returns:
            ReflectionResult with reflection text, strategy, scoring
        """
        logger.info(
            "reflection_generation_started",
            tenant_id=context.tenant_id,
            project_id=context.project_id,
            outcome=context.outcome.value,
            event_count=len(context.events),
        )

        try:
            # Choose prompt based on outcome
            if context.outcome in [
                OutcomeType.FAILURE,
                OutcomeType.ERROR,
                OutcomeType.TIMEOUT,
            ]:
                llm_response = await self._generate_failure_reflection(context)
            elif context.outcome == OutcomeType.SUCCESS:
                llm_response = await self._generate_success_reflection(context)
            else:  # PARTIAL
                llm_response = await self._generate_failure_reflection(context)

            # Build ReflectionResult
            result = ReflectionResult(
                reflection_text=llm_response.reflection,
                strategy_text=llm_response.strategy,
                importance=llm_response.importance,
                confidence=llm_response.confidence,
                tags=llm_response.tags,
                error_category=context.error.error_category if context.error else None,
                source_event_ids=[event.event_id for event in context.events],
                related_memory_ids=context.related_memory_ids or [],
                metadata={
                    "outcome": context.outcome.value,
                    "task_description": context.task_description,
                    "event_count": len(context.events),
                    "session_id": (
                        str(context.session_id) if context.session_id else None
                    ),
                },
                generated_at=datetime.now(timezone.utc),
            )

            logger.info(
                "reflection_generated",
                tenant_id=context.tenant_id,
                importance=result.importance,
                confidence=result.confidence,
                has_strategy=result.strategy_text is not None,
            )

            return result

        except Exception as e:
            logger.error(
                "reflection_generation_failed",
                tenant_id=context.tenant_id,
                error=str(e),
                exc_info=True,
            )
            raise

    async def _generate_failure_reflection(
        self, context: ReflectionContext
    ) -> LLMReflectionResponse:
        """
        Generate reflection for failure cases using LLM.

        Args:
            context: ReflectionContext with error information

        Returns:
            LLMReflectionResponse with structured reflection
        """
        # Format events for prompt
        events_text = self._format_events(context.events)

        # Format error info
        error_category = (
            context.error.error_category.value if context.error else "unknown"
        )
        error_message = (
            context.error.error_message if context.error else "No error details"
        )
        error_context = context.error.context if context.error else {}

        # Format prompt
        prompt = REFLECTION_FAILURE_PROMPT.format(
            task_goal=context.task_goal or "Not specified",
            task_description=context.task_description or "Not specified",
            events=events_text,
            error_category=error_category,
            error_message=error_message,
            error_context=error_context,
        )

        # Generate structured response
        result = await self.llm_provider.generate_structured(
            system="You are a helpful reflection engine that learns from execution traces.",
            prompt=prompt,
            model=settings.RAE_LLM_MODEL_DEFAULT,
            response_model=LLMReflectionResponse,
        )
        result = cast(LLMReflectionResponse, result)

        return result

    async def _generate_success_reflection(
        self, context: ReflectionContext
    ) -> LLMReflectionResponse:
        """
        Generate reflection for success cases using LLM.

        Args:
            context: ReflectionContext with successful execution

        Returns:
            LLMReflectionResponse with structured reflection
        """
        # Format events for prompt
        events_text = self._format_events(context.events)

        # Format prompt
        prompt = REFLECTION_SUCCESS_PROMPT.format(
            task_goal=context.task_goal or "Not specified",
            task_description=context.task_description or "Not specified",
            events=events_text,
        )

        # Generate structured response
        result = await self.llm_provider.generate_structured(
            system="You are a helpful reflection engine that identifies successful patterns.",
            prompt=prompt,
            model=settings.RAE_LLM_MODEL_DEFAULT,
            response_model=LLMReflectionResponse,
        )
        result = cast(LLMReflectionResponse, result)

        return result

    def _format_events(self, events: List[Event]) -> str:
        """
        Format events for LLM prompt.

        Args:
            events: List of Event objects

        Returns:
            Formatted string representation
        """
        lines = []
        for i, event in enumerate(events, 1):
            timestamp = event.timestamp.strftime("%H:%M:%S")
            lines.append(
                f"{i}. [{timestamp}] {event.event_type.value}: {event.content}"
            )
            if event.tool_name:
                lines.append(f"   Tool: {event.tool_name}")
            if event.error:
                lines.append(f"   Error: {event.error}")

        return "\n".join(lines)

    async def store_reflection(
        self,
        result: ReflectionResult,
        tenant_id: str,
        project_id: str,
        session_id: Optional[UUID] = None,
    ) -> Dict[str, str]:
        """
        Store reflection result to database.

        Stores both reflection and strategy (if present) as separate memory items
        with proper memory_type classification.

        Args:
            result: ReflectionResult to store
            tenant_id: Tenant identifier
            project_id: Project identifier
            session_id: Optional session identifier

        Returns:
            Dict with reflection_id and optional strategy_id
        """
        stored_ids = {}

        # Store reflection
        reflection_id = await self.rae_service.store_memory(
            tenant_id=tenant_id,
            project=project_id,
            content=result.reflection_text,
            source="reflection_engine_v2",
            importance=result.importance,
            layer="reflective",  # Reflective Memory layer
            tags=result.tags,
        )

        stored_ids["reflection_id"] = reflection_id

        logger.info(
            "reflection_stored",
            tenant_id=tenant_id,
            project_id=project_id,
            reflection_id=reflection_id,
            importance=result.importance,
        )

        # Store strategy if present
        if result.strategy_text:
            strategy_id = await self.rae_service.store_memory(
                tenant_id=tenant_id,
                project=project_id,
                content=result.strategy_text,
                source="reflection_engine_v2",
                importance=result.importance
                * 1.1,  # Strategies slightly more important
                layer="reflective",
                tags=(result.tags or []) + ["strategy"],
            )

            stored_ids["strategy_id"] = strategy_id

            logger.info(
                "strategy_stored",
                tenant_id=tenant_id,
                project_id=project_id,
                strategy_id=strategy_id,
            )

        return stored_ids

    async def query_reflections(
        self,
        tenant_id: str,
        project_id: str,
        query_text: Optional[str] = None,
        k: int = 5,
        min_importance: float = 0.5,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query reflections using Hybrid Search (Vector + Full-Text).

        This ensures that even specific technical codes or exact matches
        are found and used during the reflection process.
        """
        if not query_text:
            # Fallback to listing if no query provided
            reflections = await self.rae_service.list_memories(
                tenant_id=tenant_id, layer="reflective", project=project_id, limit=100
            )
        else:
            # HYBRID SEARCH: The core of RAE's multi-strategy retrieval
            reflections = await self.rae_service.engine.search_memories(
                query=query_text,
                tenant_id=tenant_id,
                agent_id=project_id,
                layer="reflective",  # Focus on Layer 4
                top_k=k * 2,  # Fetch more for filtering
            )

        # Filtering and post-processing
        filtered = [r for r in reflections if r.get("importance", 0) >= min_importance]

        if tags:
            filtered = [
                r for r in filtered if any(tag in r.get("tags", []) for tag in tags)
            ]

        return filtered[:k]
