"""Model routing logic for intelligent task assignment."""

from dataclasses import dataclass
from typing import Any, Dict

from orchestrator.adapters.base import ModelType, TaskComplexity, TaskRisk


@dataclass
class RoutingDecision:
    """Result of model routing decision."""

    model: ModelType
    rationale: str
    estimated_cost: float
    confidence: float  # 0.0-1.0


class ModelRouter:
    """Routes tasks to appropriate models based on complexity, risk, and area."""

    def __init__(self, gemini_enabled: bool = True):
        """Initialize model router with routing rules.

        Args:
            gemini_enabled: Whether Gemini models are available
        """
        # Cost per 1K tokens (from plan)
        self.costs = {
            ModelType.GEMINI_FLASH: 0.00001875,
            ModelType.GEMINI_PRO: 0.00025,
            ModelType.CLAUDE_SONNET: 0.003,
        }
        self.gemini_enabled = gemini_enabled

    def choose_planner(
        self, task_risk: TaskRisk, task_area: str, task_complexity: TaskComplexity
    ) -> RoutingDecision:
        """Choose model for Planner-Agent role.

        Args:
            task_risk: Risk level of the task
            task_area: Area of work (core, math, api, docs, tests)
            task_complexity: Complexity level

        Returns:
            Routing decision with model and rationale
        """
        # High-risk core/math tasks → Claude Sonnet
        if task_risk == TaskRisk.HIGH and task_area in ["core", "math"]:
            return RoutingDecision(
                model=ModelType.CLAUDE_SONNET,
                rationale="High-risk core/math requires best reasoning (Sonnet)",
                estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,  # ~3K tokens
                confidence=0.95,
            )

        # High-risk API/services → Gemini Pro
        if task_risk == TaskRisk.HIGH and task_area in ["api", "services"]:
            return RoutingDecision(
                model=ModelType.GEMINI_PRO,
                rationale="High-risk API/services, Gemini Pro has good architecture sense",
                estimated_cost=self.costs[ModelType.GEMINI_PRO] * 3,
                confidence=0.85,
            )

        # Medium-risk → Gemini Pro
        if task_risk == TaskRisk.MEDIUM:
            return RoutingDecision(
                model=ModelType.GEMINI_PRO,
                rationale="Medium risk, Gemini Pro is cost-effective for standard planning",
                estimated_cost=self.costs[ModelType.GEMINI_PRO] * 3,
                confidence=0.90,
            )

        # Low-risk docs/comments → Gemini Flash (if available) or Claude
        if task_risk == TaskRisk.LOW and task_area in ["docs", "comments"]:
            if self.gemini_enabled:
                return RoutingDecision(
                    model=ModelType.GEMINI_FLASH,
                    rationale="Low-risk docs, Gemini Flash is cheap and sufficient",
                    estimated_cost=self.costs[ModelType.GEMINI_FLASH] * 3,
                    confidence=0.95,
                )
            else:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Low-risk docs (Gemini disabled, using Claude Sonnet)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,
                    confidence=0.95,
                )

        # Default: Gemini Pro (if available) or Claude
        if self.gemini_enabled:
            return RoutingDecision(
                model=ModelType.GEMINI_PRO,
                rationale="Default choice for general planning tasks",
                estimated_cost=self.costs[ModelType.GEMINI_PRO] * 3,
                confidence=0.75,
            )
        else:
            return RoutingDecision(
                model=ModelType.CLAUDE_SONNET,
                rationale="Default choice (Gemini disabled, using Claude Sonnet)",
                estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,
                confidence=0.90,
            )

    def choose_plan_reviewer(
        self, planner_model: ModelType, task_risk: TaskRisk
    ) -> RoutingDecision:
        """Choose model for Plan-Reviewer-Agent role.

        CRITICAL: Must be different than Planner to avoid blind spots.

        Args:
            planner_model: Model used by Planner
            task_risk: Risk level of the task

        Returns:
            Routing decision with model and rationale
        """
        # RULE: Different than Planner
        if planner_model == ModelType.CLAUDE_SONNET:
            # If Gemini disabled, use Claude again (same model for now)
            if self.gemini_enabled:
                return RoutingDecision(
                    model=ModelType.GEMINI_PRO,
                    rationale="Cross-review: Gemini Pro reviews Claude Sonnet's plan",
                    estimated_cost=self.costs[ModelType.GEMINI_PRO] * 2,  # ~2K tokens
                    confidence=0.90,
                )
            else:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Cross-review: Claude Sonnet (Gemini disabled, using same model)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 2,
                    confidence=0.85,
                )
        elif planner_model == ModelType.GEMINI_PRO:
            # For high-risk, use Claude; otherwise Flash
            if task_risk == TaskRisk.HIGH:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Cross-review: Claude Sonnet reviews Gemini Pro's plan (high-risk)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 2,
                    confidence=0.95,
                )
            else:
                if self.gemini_enabled:
                    return RoutingDecision(
                        model=ModelType.GEMINI_FLASH,
                        rationale="Cross-review: Gemini Flash reviews Gemini Pro's plan (low-risk)",
                        estimated_cost=self.costs[ModelType.GEMINI_FLASH] * 2,
                        confidence=0.85,
                    )
                else:
                    return RoutingDecision(
                        model=ModelType.CLAUDE_SONNET,
                        rationale="Cross-review: Claude Sonnet (Gemini disabled)",
                        estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 2,
                        confidence=0.85,
                    )
        else:  # Planner is Flash
            return RoutingDecision(
                model=ModelType.CLAUDE_SONNET,
                rationale="Cross-review: Claude Sonnet reviews Gemini Flash's plan",
                estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 2,
                confidence=0.90,
            )

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
        # High-risk or large complexity → Claude Sonnet
        if step_risk == TaskRisk.HIGH or step_complexity == TaskComplexity.LARGE:
            return RoutingDecision(
                model=ModelType.CLAUDE_SONNET,
                rationale="High-risk/complex implementation requires best reasoning (Sonnet)",
                estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 5,  # ~5K tokens
                confidence=0.95,
            )

        # Simple docs/comments/refactor → Gemini Flash or Claude
        if step_type in ["docs", "comments", "simple_refactor"]:
            if self.gemini_enabled:
                return RoutingDecision(
                    model=ModelType.GEMINI_FLASH,
                    rationale="Simple docs/comments, Gemini Flash is fast and cheap",
                    estimated_cost=self.costs[ModelType.GEMINI_FLASH] * 5,
                    confidence=0.95,
                )
            else:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Simple docs/comments (Gemini disabled, using Claude Sonnet)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 5,
                    confidence=0.95,
                )

        # Low-risk tests → Gemini Flash or Claude
        if step_area == "tests" and step_risk == TaskRisk.LOW:
            if self.gemini_enabled:
                return RoutingDecision(
                    model=ModelType.GEMINI_FLASH,
                    rationale="Low-risk tests, Gemini Flash is good at writing tests",
                    estimated_cost=self.costs[ModelType.GEMINI_FLASH] * 5,
                    confidence=0.90,
                )
            else:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Low-risk tests (Gemini disabled, using Claude Sonnet)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 5,
                    confidence=0.90,
                )

        # Default: Gemini Pro or Claude
        if self.gemini_enabled:
            return RoutingDecision(
                model=ModelType.GEMINI_PRO,
                rationale="Default choice for medium-complexity implementation",
                estimated_cost=self.costs[ModelType.GEMINI_PRO] * 5,
                confidence=0.80,
            )
        else:
            return RoutingDecision(
                model=ModelType.CLAUDE_SONNET,
                rationale="Default implementation (Gemini disabled, using Claude Sonnet)",
                estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 5,
                confidence=0.90,
            )

    def choose_code_reviewer(
        self, implementer_model: ModelType, step_risk: TaskRisk
    ) -> RoutingDecision:
        """Choose model for Code-Reviewer-Agent role.

        CRITICAL: Must be different than Implementer to catch issues.

        Args:
            implementer_model: Model used by Implementer
            step_risk: Risk level of the step

        Returns:
            Routing decision with model and rationale
        """
        # RULE: Different than Implementer
        if implementer_model == ModelType.CLAUDE_SONNET:
            if self.gemini_enabled:
                return RoutingDecision(
                    model=ModelType.GEMINI_PRO,
                    rationale="Cross-review: Gemini Pro reviews Claude Sonnet's code",
                    estimated_cost=self.costs[ModelType.GEMINI_PRO] * 3,  # ~3K tokens
                    confidence=0.90,
                )
            else:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Cross-review: Claude Sonnet (Gemini disabled, using same model)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,
                    confidence=0.85,
                )
        elif implementer_model == ModelType.GEMINI_FLASH:
            # Flash code needs high-quality review
            return RoutingDecision(
                model=ModelType.CLAUDE_SONNET,
                rationale="Cross-review: Claude Sonnet reviews Gemini Flash's code",
                estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,
                confidence=0.95,
            )
        else:  # Implementer is Pro
            # For high-risk, use Claude; otherwise Flash
            if step_risk == TaskRisk.HIGH:
                return RoutingDecision(
                    model=ModelType.CLAUDE_SONNET,
                    rationale="Cross-review: Claude Sonnet reviews Gemini Pro's code (high-risk)",
                    estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,
                    confidence=0.95,
                )
            else:
                if self.gemini_enabled:
                    return RoutingDecision(
                        model=ModelType.GEMINI_FLASH,
                        rationale="Cross-review: Gemini Flash reviews Gemini Pro's code (low-risk)",
                        estimated_cost=self.costs[ModelType.GEMINI_FLASH] * 3,
                        confidence=0.85,
                    )
                else:
                    return RoutingDecision(
                        model=ModelType.CLAUDE_SONNET,
                        rationale="Cross-review: Claude Sonnet (Gemini disabled)",
                        estimated_cost=self.costs[ModelType.CLAUDE_SONNET] * 3,
                        confidence=0.85,
                    )

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
        reviewer_decision = self.choose_plan_reviewer(planner_decision.model, task_risk)

        planning_cost = (
            planner_decision.estimated_cost + reviewer_decision.estimated_cost
        )

        # Implementation phase (average across steps)
        impl_cost = 0.0
        for _ in range(num_steps):
            impl_decision = self.choose_implementer(
                task_risk, task_complexity, "implementation", task_area
            )
            review_decision = self.choose_code_reviewer(impl_decision.model, task_risk)
            impl_cost += impl_decision.estimated_cost + review_decision.estimated_cost

        total_cost = planning_cost + impl_cost

        return {
            "planning_cost": round(planning_cost, 6),
            "implementation_cost": round(impl_cost, 6),
            "total_cost": round(total_cost, 6),
            "num_steps": num_steps,
            "planner_model": planner_decision.model.value,
            "primary_implementer": self.choose_implementer(
                task_risk, task_complexity, "implementation", task_area
            ).model.value,
        }
