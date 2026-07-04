"""Main orchestrator controller - coordinates all agents and enforces quality."""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict

import yaml

from orchestrator.adapters import (
    ClaudeAdapter,
    GeminiAdapter,
    ModelType,
    TaskComplexity,
    TaskRisk,
)
from orchestrator.agents import (
    AgentTask,
    CodeReviewerAgent,
    ImplementerAgent,
    PlannerAgent,
    PlanReviewerAgent,
)
from orchestrator.core.model_router import ModelRouter
from orchestrator.core.quality_gate import QualityGate
from orchestrator.core.telemetry import init_telemetry

logger = logging.getLogger(__name__)


class TaskStatus:
    """Task status constants."""

    NEW = "new"
    PLANNING = "planning"
    PLAN_REVIEW = "plan_review"
    PLAN_APPROVED = "plan_approved"
    IMPLEMENTING = "implementing"
    AWAITING_HUMAN = "awaiting_human_review"
    DONE = "done"
    FAILED = "failed"


class Orchestrator:
    """Main orchestrator coordinating multi-agent system."""

    def __init__(self, working_dir: str):
        """Initialize orchestrator.

        Args:
            working_dir: Working directory for operations
        """
        self.working_dir = Path(working_dir)

        # Load provider configuration
        providers_config_path = self.working_dir / ".orchestrator" / "providers.yaml"
        gemini_enabled = True  # Default to enabled
        if providers_config_path.exists():
            with open(providers_config_path, "r") as f:
                config = yaml.safe_load(f)
                gemini_enabled = (
                    config.get("providers", {}).get("gemini", {}).get("enabled", True)
                )

        self.router = ModelRouter(gemini_enabled=gemini_enabled)
        self.quality_gate = QualityGate(str(self.working_dir))
        self.telemetry = init_telemetry()

        # Initialize agents
        self.planner = PlannerAgent()
        self.plan_reviewer = PlanReviewerAgent()
        self.implementer = ImplementerAgent()
        self.code_reviewer = CodeReviewerAgent()

        # Model adapters cache
        self._adapters: Dict[ModelType, Any] = {}

        logger.info(f"Orchestrator initialized in {self.working_dir}")

    def _get_adapter(self, model_type: ModelType):
        """Get or create model adapter.

        Args:
            model_type: Type of model

        Returns:
            Model adapter instance
        """
        if model_type in self._adapters:
            return self._adapters[model_type]

        # Create adapter
        if model_type == ModelType.CLAUDE_SONNET:
            adapter = ClaudeAdapter(model_type, str(self.working_dir))
        elif model_type in [ModelType.GEMINI_PRO, ModelType.GEMINI_FLASH]:
            adapter = GeminiAdapter(model_type, str(self.working_dir))
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

        self._adapters[model_type] = adapter
        return adapter

    async def run_task(self, task_def: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single task through the orchestrator.

        Args:
            task_def: Task definition from tasks.yaml

        Returns:
            Task result dictionary
        """
        task_id = task_def["id"]
        task_area = task_def.get("area", "unknown")
        task_risk_str = task_def.get("risk", "medium")
        TaskRisk[task_risk_str.upper()]

        logger.info(f"Starting task {task_id}: {task_def['goal']}")

        start_time = time.time()
        status = TaskStatus.NEW

        # Start telemetry span for task
        with self.telemetry.trace_task(task_id, task_area, task_risk_str):
            try:
                # Phase 1: Planning
                status = TaskStatus.PLANNING
                plan = await self._create_plan(task_def)

                if "error" in plan:
                    raise RuntimeError(f"Planning failed: {plan['error']}")

                # Phase 2: Plan Review
                status = TaskStatus.PLAN_REVIEW
                review = await self._review_plan(task_def, plan)

                if "error" in review:
                    raise RuntimeError(f"Plan review failed: {review['error']}")

                # Check review status
                review_status = review.get("status", "rejected")
                if review_status == "rejected":
                    logger.error(
                        f"Plan rejected: {review.get('reasoning', 'No reason provided')}"
                    )
                    status = TaskStatus.AWAITING_HUMAN
                    self.telemetry.record_task_complete(
                        "human_required",
                        time.time() - start_time,
                        task_area,
                        task_risk_str,
                    )
                    return {
                        "task_id": task_id,
                        "status": status,
                        "plan": plan,
                        "review": review,
                        "message": "Plan rejected by reviewer - human review required",
                    }

                # Phase 3: Implementation (for each step)
                status = TaskStatus.IMPLEMENTING
                steps = plan.get("steps", [])

                for step in steps:
                    step_result = await self._execute_step(task_def, step)

                    if not step_result["success"]:
                        logger.error(
                            f"Step {step['id']} failed: {step_result.get('error')}"
                        )
                        status = TaskStatus.FAILED
                        break

                # Phase 4: Final Quality Gate
                if status == TaskStatus.IMPLEMENTING:
                    gate_result = await self.quality_gate.validate(
                        changed_files=[],  # TODO: track changed files
                        change_size="MEDIUM",
                    )

                    if not gate_result.can_merge:
                        logger.error(f"Quality gate failed: {gate_result.summary}")
                        status = TaskStatus.FAILED
                        self.telemetry.record_quality_gate("failed")
                    else:
                        logger.info(f"Quality gate passed: {gate_result.summary}")
                        status = TaskStatus.DONE
                        self.telemetry.record_quality_gate("passed")

                # Record completion
                duration = time.time() - start_time
                self.telemetry.record_task_complete(
                    status if status == TaskStatus.DONE else "fail",
                    duration,
                    task_area,
                    task_risk_str,
                )

                logger.info(
                    f"Task {task_id} completed with status {status} in {duration:.2f}s"
                )

                return {
                    "task_id": task_id,
                    "status": status,
                    "plan": plan,
                    "duration": duration,
                }

            except Exception as e:
                logger.exception(f"Task {task_id} failed with exception")
                self.telemetry.record_task_complete(
                    "fail", time.time() - start_time, task_area, task_risk_str
                )
                return {
                    "task_id": task_id,
                    "status": TaskStatus.FAILED,
                    "error": str(e),
                }

    async def _create_plan(self, task_def: Dict[str, Any]) -> Dict[str, Any]:
        """Create implementation plan for task.

        Args:
            task_def: Task definition

        Returns:
            Plan dictionary
        """
        task_id = task_def["id"]
        task_area = task_def.get("area", "unknown")
        task_risk_str = task_def.get("risk", "medium")
        task_risk = TaskRisk[task_risk_str.upper()]
        task_complexity = TaskComplexity.MEDIUM  # TODO: determine from task

        # Choose planner model
        routing_decision = self.router.choose_planner(
            task_risk, task_area, task_complexity
        )

        logger.info(
            f"Planning with {routing_decision.model.value}: {routing_decision.rationale}"
        )

        # Record routing decision
        self.telemetry.record_model_routing(
            task_risk_str,
            task_area,
            routing_decision.model.value,
            routing_decision.rationale,
        )

        # Set adapter for planner
        adapter = self._get_adapter(routing_decision.model)
        self.planner.set_adapter(adapter)

        # Create agent task
        agent_task = AgentTask(
            task_id=task_id,
            description=task_def["goal"],
            context={
                "constraints": task_def.get("constraints", []),
                "context_files": task_def.get("context_files", []),
            },
            complexity=task_complexity,
            risk=task_risk,
            working_directory=str(self.working_dir),
            files_to_read=task_def.get("context_files", []),
        )

        # Execute planner with telemetry
        with self.telemetry.trace_llm_call(
            provider=adapter.__class__.__name__.replace("Adapter", "").lower(),
            model=routing_decision.model.value,
            role="planner",
        ):
            response = await self.planner.execute(agent_task)
            self.telemetry.record_llm_call(
                provider=adapter.__class__.__name__.replace("Adapter", "").lower(),
                model=routing_decision.model.value,
                role="planner",
                cost_usd=routing_decision.estimated_cost,
            )

        if not response.success:
            return {"error": response.error}

        return response.result

    async def _review_plan(
        self, task_def: Dict[str, Any], plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Review implementation plan.

        Args:
            task_def: Task definition
            plan: Plan to review

        Returns:
            Review dictionary
        """
        task_id = task_def["id"]
        task_area = task_def.get("area", "unknown")
        task_risk_str = task_def.get("risk", "medium")
        task_risk = TaskRisk[task_risk_str.upper()]

        # Get planner model from plan metadata (or infer from task)
        planner_decision = self.router.choose_planner(
            task_risk, task_area, TaskComplexity.MEDIUM
        )

        # Choose reviewer model (must be different)
        routing_decision = self.router.choose_plan_reviewer(
            planner_decision.model, task_risk
        )

        logger.info(
            f"Plan review with {routing_decision.model.value}: {routing_decision.rationale}"
        )

        # Set adapter for reviewer
        adapter = self._get_adapter(routing_decision.model)
        self.plan_reviewer.set_adapter(adapter)

        # Create agent task
        agent_task = AgentTask(
            task_id=task_id,
            description=f"Review plan for: {task_def['goal']}",
            context={"plan": plan},
            complexity=TaskComplexity.MEDIUM,
            risk=task_risk,
            working_directory=str(self.working_dir),
        )

        # Execute reviewer with telemetry
        with self.telemetry.trace_llm_call(
            provider=adapter.__class__.__name__.replace("Adapter", "").lower(),
            model=routing_decision.model.value,
            role="plan_reviewer",
        ):
            response = await self.plan_reviewer.execute(agent_task)
            self.telemetry.record_llm_call(
                provider=adapter.__class__.__name__.replace("Adapter", "").lower(),
                model=routing_decision.model.value,
                role="plan_reviewer",
                cost_usd=routing_decision.estimated_cost,
            )

        if not response.success:
            return {"error": response.error}

        return response.result

    async def _execute_step(
        self, task_def: Dict[str, Any], step: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single implementation step.

        Args:
            task_def: Task definition
            step: Step to execute

        Returns:
            Step result dictionary
        """
        step_id = step["id"]
        step_type = step.get("type", "implementation")
        step_risk_str = step.get("risk", "medium")
        step_risk = TaskRisk[step_risk_str.upper()]
        step_complexity_str = step.get("estimated_complexity", "medium")
        step_complexity = TaskComplexity[step_complexity_str.upper()]
        task_area = task_def.get("area", "unknown")

        logger.info(f"Executing step {step_id}: {step.get('description')}")

        with self.telemetry.trace_step(step_id, step_type, step_risk_str):
            # Choose implementer model
            impl_decision = self.router.choose_implementer(
                step_risk, step_complexity, step_type, task_area
            )

            # Choose code reviewer model (must be different)
            review_decision = self.router.choose_code_reviewer(
                impl_decision.model, step_risk
            )

            # Implementation
            impl_adapter = self._get_adapter(impl_decision.model)
            self.implementer.set_adapter(impl_adapter)

            agent_task = AgentTask(
                task_id=task_def["id"],
                description=step.get("description", ""),
                context={"step": step},
                complexity=step_complexity,
                risk=step_risk,
                working_directory=str(self.working_dir),
            )

            with self.telemetry.trace_llm_call(
                provider=impl_adapter.__class__.__name__.replace("Adapter", "").lower(),
                model=impl_decision.model.value,
                role="implementer",
            ):
                impl_response = await self.implementer.execute(agent_task)
                self.telemetry.record_llm_call(
                    provider=impl_adapter.__class__.__name__.replace(
                        "Adapter", ""
                    ).lower(),
                    model=impl_decision.model.value,
                    role="implementer",
                    cost_usd=impl_decision.estimated_cost,
                )

            if not impl_response.success:
                return {"success": False, "error": impl_response.error}

            # Code Review
            review_adapter = self._get_adapter(review_decision.model)
            self.code_reviewer.set_adapter(review_adapter)

            review_task = AgentTask(
                task_id=task_def["id"],
                description=f"Review code for step: {step.get('description')}",
                context={
                    "step": step,
                    "implementation": impl_response.result,
                },
                complexity=step_complexity,
                risk=step_risk,
                working_directory=str(self.working_dir),
            )

            with self.telemetry.trace_llm_call(
                provider=review_adapter.__class__.__name__.replace(
                    "Adapter", ""
                ).lower(),
                model=review_decision.model.value,
                role="code_reviewer",
            ):
                review_response = await self.code_reviewer.execute(review_task)
                self.telemetry.record_llm_call(
                    provider=review_adapter.__class__.__name__.replace(
                        "Adapter", ""
                    ).lower(),
                    model=review_decision.model.value,
                    role="code_reviewer",
                    cost_usd=review_decision.estimated_cost,
                )

            if not review_response.success:
                return {"success": False, "error": review_response.error}

            # Check review status
            review_result = review_response.result
            review_status = review_result.get("status", "rejected")

            if review_status == "rejected":
                self.telemetry.log_cross_review_rejection(
                    review_decision.model.value,
                    impl_decision.model.value,
                    review_result.get("reasoning", "Unknown reason"),
                )
                return {
                    "success": False,
                    "error": f"Code review rejected: {review_result.get('reasoning')}",
                }

            self.telemetry.record_step_complete(step_type, "success")
            return {"success": True, "implementation": impl_response.result}


async def main():
    """Main entry point."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Orchestrator for multi-agent development"
    )
    parser.add_argument(
        "--tasks", default=".orchestrator/tasks.yaml", help="Path to tasks.yaml file"
    )
    parser.add_argument(
        "--working-dir", default=".", help="Working directory for operations"
    )
    parser.add_argument("--task-id", help="Run specific task by ID")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Load tasks
    tasks_file = Path(args.tasks)
    if not tasks_file.exists():
        logger.error(f"Tasks file not found: {tasks_file}")
        sys.exit(1)

    with open(tasks_file) as f:
        config = yaml.safe_load(f)
        tasks = config.get("tasks", [])

    if not tasks:
        logger.error("No tasks found in tasks.yaml")
        sys.exit(1)

    # Filter tasks if specific ID requested
    if args.task_id:
        tasks = [t for t in tasks if t["id"] == args.task_id]
        if not tasks:
            logger.error(f"Task {args.task_id} not found")
            sys.exit(1)

    # Initialize orchestrator
    orchestrator = Orchestrator(args.working_dir)

    # Run tasks
    for task_def in tasks:
        result = await orchestrator.run_task(task_def)
        logger.info(f"Task {task_def['id']} result: {result['status']}")


if __name__ == "__main__":
    asyncio.run(main())
