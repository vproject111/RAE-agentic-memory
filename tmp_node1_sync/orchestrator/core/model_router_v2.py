"""Provider-agnostic model routing logic.

Updated version that uses ProviderRegistry instead of hardcoded ModelType enum.
Maintains the same intelligent routing rules while supporting any LLM provider.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from orchestrator.adapters.base import TaskComplexity, TaskRisk
from orchestrator.providers import ModelInfo, ModelTier, ProviderRegistry


@dataclass
class RoutingDecision:
    """Result of model routing decision."""

    model_id: str  # Full model identifier (e.g., 'claude-sonnet-4-5-20250929')
    provider: str  # Provider name (e.g., 'claude', 'gemini')
    model_info: ModelInfo  # Full model metadata
    rationale: str  # Why this model was chosen
    estimated_cost: float  # Estimated cost in USD
    confidence: float  # 0.0-1.0


class ModelRouterV2:
    """Provider-agnostic model router.

    Routes tasks to appropriate models based on complexity, risk, and area.
    Uses ProviderRegistry to discover available models dynamically.
    """

    def __init__(self, registry: ProviderRegistry):
        """Initialize model router with provider registry.

        Args:
            registry: Provider registry for model discovery
        """
        self.registry = registry

    def _find_model(
        self,
        capability: Optional[str] = None,
        tier: Optional[ModelTier] = None,
        max_cost: Optional[float] = None,
        prefer_local: bool = False,
    ) -> Optional[ModelInfo]:
        """Find best model matching criteria.

        Args:
            capability: Required capability (e.g., 'code', 'planning')
            tier: Required tier (FAST, STANDARD, ADVANCED)
            max_cost: Maximum cost per 1K input tokens
            prefer_local: Prefer local models (cost=0)

        Returns:
            Best matching model or None
        """
        return self.registry.find_best_model(
            capability=capability,
            prefer_local=prefer_local,
            max_cost=max_cost,
        )

    def choose_planner(
        self,
        task_risk: TaskRisk,
        task_area: str,
        task_complexity: TaskComplexity,
    ) -> RoutingDecision:
        """Choose model for Planner-Agent role.

        Args:
            task_risk: Risk level of the task
            task_area: Area of work (core, math, api, docs, tests)
            task_complexity: Complexity level

        Returns:
            Routing decision with model and rationale
        """
        # High-risk core/math tasks → Advanced reasoning
        if task_risk == TaskRisk.HIGH and task_area in ["core", "math"]:
            model = self._find_model(
                capability="complex_reasoning", tier=ModelTier.ADVANCED
            )
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="High-risk core/math requires best reasoning (Advanced tier)",
                    estimated_cost=model.cost_per_1k_input * 3,  # ~3K tokens
                    confidence=0.95,
                )

        # High-risk API/services → Standard planning
        if task_risk == TaskRisk.HIGH and task_area in ["api", "services"]:
            model = self._find_model(capability="planning", tier=ModelTier.STANDARD)
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="High-risk API/services, Standard tier has good architecture sense",
                    estimated_cost=model.cost_per_1k_input * 3,
                    confidence=0.85,
                )

        # Medium-risk → Standard planning
        if task_risk == TaskRisk.MEDIUM:
            model = self._find_model(capability="planning", tier=ModelTier.STANDARD)
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="Medium risk, Standard tier is cost-effective for planning",
                    estimated_cost=model.cost_per_1k_input * 3,
                    confidence=0.90,
                )

        # Low-risk docs/comments → Fast tier
        if task_risk == TaskRisk.LOW and task_area in ["docs", "comments"]:
            model = self._find_model(capability="docs", tier=ModelTier.FAST)
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="Low-risk docs, Fast tier is cheap and sufficient",
                    estimated_cost=model.cost_per_1k_input * 3,
                    confidence=0.95,
                )

        # Default: Find cheapest planning model
        model = self.registry.find_cheapest_model(capability="planning")
        if model:
            return RoutingDecision(
                model_id=model.model_id,
                provider=model.provider,
                model_info=model,
                rationale="Default choice for general planning tasks",
                estimated_cost=model.cost_per_1k_input * 3,
                confidence=0.75,
            )

        # Fallback: Any available model
        models = self.registry.list_models()
        if models:
            model = models[0]
            return RoutingDecision(
                model_id=model.model_id,
                provider=model.provider,
                model_info=model,
                rationale="Fallback: using first available model",
                estimated_cost=model.cost_per_1k_input * 3,
                confidence=0.50,
            )

        raise RuntimeError("No models available in provider registry")

    def choose_plan_reviewer(
        self, planner_model_id: str, task_risk: TaskRisk
    ) -> RoutingDecision:
        """Choose model for Plan-Reviewer-Agent role.

        CRITICAL: Must be different than Planner to avoid blind spots.

        Args:
            planner_model_id: Model ID used by Planner
            task_risk: Risk level of the task

        Returns:
            Routing decision with model and rationale
        """
        planner_info = self.registry.get_model_info(planner_model_id)
        if not planner_info:
            raise ValueError(f"Unknown planner model: {planner_model_id}")

        # Get all available review-capable models
        review_models = self.registry.list_models(capability="review")

        # Filter out the planner's provider (cross-review rule)
        review_models = [
            m for m in review_models if m.provider != planner_info.provider
        ]

        if not review_models:
            # If no cross-provider option, at least use different model from same provider
            review_models = self.registry.list_models(capability="review")
            review_models = [m for m in review_models if m.model_id != planner_model_id]

        # For high-risk, prefer Advanced tier reviewer
        if task_risk == TaskRisk.HIGH:
            advanced_reviewers = [
                m for m in review_models if m.tier == ModelTier.ADVANCED
            ]
            if advanced_reviewers:
                model = min(advanced_reviewers, key=lambda m: m.cost_per_1k_input)
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale=f"Cross-review: {model.provider} reviews {planner_info.provider}'s plan (high-risk)",
                    estimated_cost=model.cost_per_1k_input * 2,
                    confidence=0.95,
                )

        # Otherwise, use cheapest available reviewer
        if review_models:
            model = min(review_models, key=lambda m: m.cost_per_1k_input)
            return RoutingDecision(
                model_id=model.model_id,
                provider=model.provider,
                model_info=model,
                rationale=f"Cross-review: {model.provider} reviews {planner_info.provider}'s plan",
                estimated_cost=model.cost_per_1k_input * 2,
                confidence=0.90,
            )

        raise RuntimeError("No suitable review models available")

    def choose_implementer(
        self,
        step_risk: TaskRisk,
        step_complexity: TaskComplexity,
        step_type: str,
        step_area: str,
    ) -> RoutingDecision:
        """Choose model for Implementer-Agent role.

        Args:
            step_risk: Risk level of the step
            step_complexity: Complexity of the step
            step_type: Type of step (implementation, testing, docs, etc.)
            step_area: Area of work (core, math, api, docs, tests)

        Returns:
            Routing decision with model and rationale
        """
        # High-risk or large complexity → Advanced tier
        if step_risk == TaskRisk.HIGH or step_complexity == TaskComplexity.LARGE:
            model = self._find_model(capability="code", tier=ModelTier.ADVANCED)
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="High-risk/complex implementation requires best reasoning (Advanced)",
                    estimated_cost=model.cost_per_1k_input * 5,
                    confidence=0.95,
                )

        # Simple docs/comments/refactor → Fast tier
        if step_type in ["docs", "comments", "simple_refactor"]:
            model = self._find_model(capability="docs", tier=ModelTier.FAST)
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="Simple docs/comments, Fast tier is sufficient",
                    estimated_cost=model.cost_per_1k_input * 5,
                    confidence=0.95,
                )

        # Low-risk tests → Fast tier
        if step_area == "tests" and step_risk == TaskRisk.LOW:
            model = self._find_model(capability="code", tier=ModelTier.FAST)
            if model:
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale="Low-risk tests, Fast tier is good for test generation",
                    estimated_cost=model.cost_per_1k_input * 5,
                    confidence=0.90,
                )

        # Default: Standard tier code generation
        model = self._find_model(capability="code", tier=ModelTier.STANDARD)
        if model:
            return RoutingDecision(
                model_id=model.model_id,
                provider=model.provider,
                model_info=model,
                rationale="Default choice for medium-complexity implementation",
                estimated_cost=model.cost_per_1k_input * 5,
                confidence=0.80,
            )

        # Fallback: Cheapest code-capable model
        model = self.registry.find_cheapest_model(capability="code")
        if model:
            return RoutingDecision(
                model_id=model.model_id,
                provider=model.provider,
                model_info=model,
                rationale="Fallback: cheapest code-capable model",
                estimated_cost=model.cost_per_1k_input * 5,
                confidence=0.70,
            )

        raise RuntimeError("No code-capable models available")

    def choose_code_reviewer(
        self, implementer_model_id: str, step_risk: TaskRisk
    ) -> RoutingDecision:
        """Choose model for Code-Reviewer-Agent role.

        CRITICAL: Must be different than Implementer to catch issues.

        Args:
            implementer_model_id: Model ID used by Implementer
            step_risk: Risk level of the step

        Returns:
            Routing decision with model and rationale
        """
        implementer_info = self.registry.get_model_info(implementer_model_id)
        if not implementer_info:
            raise ValueError(f"Unknown implementer model: {implementer_model_id}")

        # Get all available review-capable models
        review_models = self.registry.list_models(capability="review")

        # Filter out the implementer's provider (cross-review rule)
        review_models = [
            m for m in review_models if m.provider != implementer_info.provider
        ]

        if not review_models:
            # If no cross-provider option, at least use different model from same provider
            review_models = self.registry.list_models(capability="review")
            review_models = [
                m for m in review_models if m.model_id != implementer_model_id
            ]

        # For high-risk, prefer Advanced tier reviewer
        if step_risk == TaskRisk.HIGH:
            advanced_reviewers = [
                m for m in review_models if m.tier == ModelTier.ADVANCED
            ]
            if advanced_reviewers:
                model = min(advanced_reviewers, key=lambda m: m.cost_per_1k_input)
                return RoutingDecision(
                    model_id=model.model_id,
                    provider=model.provider,
                    model_info=model,
                    rationale=f"Cross-review: {model.provider} reviews {implementer_info.provider}'s code (high-risk)",
                    estimated_cost=model.cost_per_1k_input * 3,
                    confidence=0.95,
                )

        # Otherwise, use cheapest available reviewer
        if review_models:
            model = min(review_models, key=lambda m: m.cost_per_1k_input)
            return RoutingDecision(
                model_id=model.model_id,
                provider=model.provider,
                model_info=model,
                rationale=f"Cross-review: {model.provider} reviews {implementer_info.provider}'s code",
                estimated_cost=model.cost_per_1k_input * 3,
                confidence=0.90,
            )

        raise RuntimeError("No suitable review models available")

    def estimate_task_cost(
        self,
        task_risk: TaskRisk,
        task_area: str,
        task_complexity: TaskComplexity,
        num_steps: int = 5,
    ) -> Dict[str, Any]:
        """Estimate total cost for a complete task.

        Args:
            task_risk: Risk level of the task
            task_area: Area of work
            task_complexity: Complexity level
            num_steps: Estimated number of implementation steps

        Returns:
            Cost breakdown dictionary
        """
        # Planning phase
        planner_decision = self.choose_planner(task_risk, task_area, task_complexity)
        reviewer_decision = self.choose_plan_reviewer(
            planner_decision.model_id, task_risk
        )

        planning_cost = (
            planner_decision.estimated_cost + reviewer_decision.estimated_cost
        )

        # Implementation phase (average across steps)
        impl_cost = 0.0
        for _ in range(num_steps):
            impl_decision = self.choose_implementer(
                task_risk, task_complexity, "implementation", task_area
            )
            review_decision = self.choose_code_reviewer(
                impl_decision.model_id, task_risk
            )
            impl_cost += impl_decision.estimated_cost + review_decision.estimated_cost

        total_cost = planning_cost + impl_cost

        return {
            "planning_cost": round(planning_cost, 6),
            "implementation_cost": round(impl_cost, 6),
            "total_cost": round(total_cost, 6),
            "num_steps": num_steps,
            "planner_model": planner_decision.model_id,
            "planner_provider": planner_decision.provider,
            "primary_implementer": self.choose_implementer(
                task_risk, task_complexity, "implementation", task_area
            ).model_id,
        }
