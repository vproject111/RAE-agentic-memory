"""
Evaluator - Assessment Interface for Actor-Evaluator-Reflector Pattern

This module defines the Evaluator interface, responsible for assessing
the outcome of actor executions before triggering reflections.

Pattern: Actor → **Evaluator** → Reflector
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, cast

from pydantic import BaseModel

from apps.memory_api.config import settings
from apps.memory_api.models.reflection_v2_models import ErrorInfo, OutcomeType
from apps.memory_api.services.llm import get_llm_provider

# ============================================================================
# LLM Response Models
# ============================================================================


class LLMEvaluationResponse(BaseModel):
    """Response model for LLM evaluation."""

    is_success: bool
    quality_score: float
    outcome_type: str
    reasons: list[str]
    should_reflect: bool
    importance: float


# ============================================================================
# Execution Context
# ============================================================================


@dataclass
class ExecutionContext:
    """
    Context of an execution to be evaluated.

    Contains all information needed by the Evaluator to assess
    success/failure and trigger appropriate reflections.
    """

    # Execution trace
    events: List[Dict[str, Any]]  # Execution events (tool calls, responses, errors)
    response: str  # Final response/output
    execution_time_ms: int  # Execution duration

    # Task context
    task_description: Optional[str] = None
    task_goal: Optional[str] = None
    expected_outcome: Optional[str] = None

    # Error information (if any)
    error: Optional[ErrorInfo] = None
    error_traceback: Optional[str] = None

    # Metadata
    tenant_id: str = ""
    project_id: str = ""
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# Evaluation Result
# ============================================================================


@dataclass
class EvaluationResult:
    """
    Result of execution evaluation.

    Used by Reflector to decide whether to generate reflections
    and what importance to assign.
    """

    # Core assessment
    outcome: OutcomeType  # success / failure / partial / timeout / error
    is_ok: bool  # Quick boolean for success check

    # Error details (if failure)
    error_info: Optional[ErrorInfo] = None

    # Quality assessment
    quality_score: float = 0.5  # 0.0-1.0 quality rating
    reasons: Optional[List[str]] = None  # Explanation of assessment
    notes: Optional[str] = None  # Additional context

    # Reflection hints
    importance_hint: Optional[float] = None  # Suggested importance for reflection
    should_reflect: bool = True  # Whether to trigger reflection

    # Metadata
    evaluation_method: str = "default"  # e.g., "llm", "deterministic", "hybrid"
    confidence: float = 1.0  # Confidence in evaluation

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []


# ============================================================================
# Evaluator Protocol
# ============================================================================


class Evaluator(Protocol):
    """
    Protocol for evaluating actor execution outcomes.

    Implementations can use:
    - Deterministic rules (test results, status codes)
    - LLM-based assessment (quality, helpfulness, safety)
    - Hybrid approaches (rules + LLM)
    """

    async def evaluate(self, context: ExecutionContext) -> EvaluationResult:
        """
        Evaluate execution outcome.

        Args:
            context: ExecutionContext with trace and results

        Returns:
            EvaluationResult with outcome assessment
        """
        ...


# ============================================================================
# Built-in Evaluators
# ============================================================================


class DeterministicEvaluator:
    """
    Simple deterministic evaluator based on explicit error presence.

    Use for:
    - Test execution (pass/fail)
    - Tool status codes (200/4xx/5xx)
    - Explicit error flags
    """

    async def evaluate(self, context: ExecutionContext) -> EvaluationResult:
        """
        Evaluate based on error presence and explicit signals.

        Args:
            context: ExecutionContext

        Returns:
            EvaluationResult
        """
        # Check for explicit error
        if context.error:
            return EvaluationResult(
                outcome=OutcomeType.ERROR,
                is_ok=False,
                error_info=context.error,
                quality_score=0.0,
                reasons=["Explicit error detected", context.error.error_message],
                importance_hint=0.7,  # Errors are usually important
                should_reflect=True,
                evaluation_method="deterministic",
                confidence=1.0,
            )

        # Check execution time (timeout heuristic)
        if context.execution_time_ms > 60000:  # 60 seconds
            return EvaluationResult(
                outcome=OutcomeType.TIMEOUT,
                is_ok=False,
                quality_score=0.2,
                reasons=["Execution time exceeded reasonable threshold"],
                importance_hint=0.6,
                should_reflect=True,
                evaluation_method="deterministic",
                confidence=0.8,
            )

        # Default: assume success if no errors
        return EvaluationResult(
            outcome=OutcomeType.SUCCESS,
            is_ok=True,
            quality_score=1.0,
            reasons=["No errors detected"],
            importance_hint=0.3,  # Success less important than failures
            should_reflect=False,  # Don't reflect on simple successes
            evaluation_method="deterministic",
            confidence=1.0,
        )


class ThresholdEvaluator:
    """
    Evaluator based on configurable quality thresholds.

    Use for:
    - Partial successes (some tests pass, some fail)
    - Quality scores from external tools
    - Performance metrics
    """

    def __init__(
        self,
        success_threshold: float = 0.8,
        failure_threshold: float = 0.3,
    ):
        """
        Initialize with thresholds.

        Args:
            success_threshold: Min score for success (>= this = success)
            failure_threshold: Max score for failure (<= this = failure)
        """
        self.success_threshold = success_threshold
        self.failure_threshold = failure_threshold

    async def evaluate(self, context: ExecutionContext) -> EvaluationResult:
        """
        Evaluate based on quality score thresholds.

        Expects context.metadata['quality_score'] to be set.

        Args:
            context: ExecutionContext

        Returns:
            EvaluationResult
        """
        # Extract quality score from metadata
        quality_score = 0.5
        if context.metadata and "quality_score" in context.metadata:
            quality_score = float(context.metadata["quality_score"])

        # Classify outcome
        if quality_score >= self.success_threshold:
            outcome = OutcomeType.SUCCESS
            is_ok = True
            reasons = [f"Quality score {quality_score:.2f} meets success threshold"]
            should_reflect = False
        elif quality_score <= self.failure_threshold:
            outcome = OutcomeType.FAILURE
            is_ok = False
            reasons = [f"Quality score {quality_score:.2f} below failure threshold"]
            should_reflect = True
        else:
            outcome = OutcomeType.PARTIAL
            is_ok = False
            reasons = [f"Quality score {quality_score:.2f} in partial success range"]
            should_reflect = True

        return EvaluationResult(
            outcome=outcome,
            is_ok=is_ok,
            quality_score=quality_score,
            reasons=reasons,
            importance_hint=1.0 - quality_score,  # Lower quality = higher importance
            should_reflect=should_reflect,
            evaluation_method="threshold",
            confidence=0.9,
        )


class LLMEvaluator:
    """
    Evaluator that uses an LLM to assess execution outcomes.
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        self.llm_provider = llm_provider or get_llm_provider()

    async def evaluate(self, context: ExecutionContext) -> EvaluationResult:
        """
        Evaluate execution outcome using LLM.

        Args:
            context: ExecutionContext with trace and results

        Returns:
            EvaluationResult
        """
        # Prepare prompt
        prompt = self._build_prompt(context)

        # Call LLM
        try:
            response = cast(
                LLMEvaluationResponse,
                await self.llm_provider.generate_structured(
                    system="You are an expert evaluator of AI agent execution. Assess the quality and success of the following task execution.",
                    prompt=prompt,
                    model=settings.RAE_LLM_MODEL_DEFAULT,
                    response_model=LLMEvaluationResponse,
                ),
            )

            # Map outcome string to enum
            outcome_map = {
                "success": OutcomeType.SUCCESS,
                "failure": OutcomeType.FAILURE,
                "partial": OutcomeType.PARTIAL,
                "error": OutcomeType.ERROR,
                "timeout": OutcomeType.TIMEOUT,
            }
            outcome = outcome_map.get(
                response.outcome_type.lower(), OutcomeType.PARTIAL
            )

            return EvaluationResult(
                outcome=outcome,
                is_ok=response.is_success,
                quality_score=response.quality_score,
                reasons=response.reasons,
                importance_hint=response.importance,
                should_reflect=response.should_reflect,
                evaluation_method="llm",
                confidence=0.9,  # High confidence in LLM assessment
            )

        except Exception:
            # Fallback to deterministic evaluation on error
            return await DeterministicEvaluator().evaluate(context)

    def _build_prompt(self, context: ExecutionContext) -> str:
        """Build prompt for LLM evaluation"""

        events_str = "\n".join([f"- {e}" for e in context.events])

        return f"""
        Task Goal: {context.task_goal or "Not specified"}
        Task Description: {context.task_description or "Not specified"}
        Expected Outcome: {context.expected_outcome or "Not specified"}

        Execution Events:
        {events_str}

        Final Response:
        {context.response}

        Error Info:
        {context.error if context.error else "None"}

        Evaluate whether the task was successful, assign a quality score (0.0-1.0), and determine if this execution is worth reflecting on (e.g. for learning from mistakes or saving successful strategies).
        """


# ============================================================================
# Evaluator Factory
# ============================================================================


def get_evaluator(evaluator_type: str = "deterministic") -> Evaluator:
    """
    Factory function for getting evaluator instances.

    Args:
        evaluator_type: Type of evaluator ("deterministic", "threshold", "llm")

    Returns:
        Evaluator instance
    """
    if evaluator_type == "deterministic":
        return DeterministicEvaluator()
    elif evaluator_type == "threshold":
        return ThresholdEvaluator()
    elif evaluator_type == "llm":
        return LLMEvaluator()
    else:
        raise ValueError(f"Unknown evaluator type: {evaluator_type}")


# ============================================================================
# Helper Functions
# ============================================================================


def should_trigger_reflection(result: EvaluationResult) -> bool:
    """
    Determine if reflection should be triggered based on evaluation.

    Args:
        result: EvaluationResult

    Returns:
        True if reflection should be generated
    """
    # Always reflect on errors and failures
    if result.outcome in [OutcomeType.ERROR, OutcomeType.FAILURE, OutcomeType.TIMEOUT]:
        return True

    # Reflect on partial successes if explicitly flagged
    if result.outcome == OutcomeType.PARTIAL and result.should_reflect:
        return True

    # Check explicit flag
    return result.should_reflect


def get_reflection_importance(result: EvaluationResult) -> float:
    """
    Calculate importance score for reflection based on evaluation.

    Args:
        result: EvaluationResult

    Returns:
        Importance score (0.0-1.0)
    """
    # Use hint if provided
    if result.importance_hint is not None:
        return max(0.0, min(1.0, result.importance_hint))

    # Default heuristics
    if result.outcome == OutcomeType.ERROR:
        return 0.8  # Errors are important
    elif result.outcome == OutcomeType.FAILURE:
        return 0.7  # Failures are important
    elif result.outcome == OutcomeType.TIMEOUT:
        return 0.6  # Timeouts are moderately important
    elif result.outcome == OutcomeType.PARTIAL:
        return 0.5  # Partial successes moderately important
    else:  # SUCCESS
        return 0.3  # Successes less important
