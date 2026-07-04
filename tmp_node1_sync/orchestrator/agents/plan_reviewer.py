"""Plan-Reviewer-Agent: Cross-checks implementation plans."""

import json
from typing import Any, Dict

from .base import AgentResponse, AgentTask, BaseAgent


class PlanReviewerAgent(BaseAgent):
    """Agent responsible for reviewing implementation plans.

    CRITICAL: Must use a different model than Planner to avoid blind spots.
    """

    def __init__(self):
        """Initialize Plan-Reviewer-Agent."""
        super().__init__(name="Plan-Reviewer-Agent", role="plan_reviewer")

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Review an implementation plan.

        Args:
            task: Task containing plan to review

        Returns:
            Agent response with review result
        """
        try:
            # Extract plan from context
            plan = task.context.get("plan")
            if not plan:
                return AgentResponse(
                    success=False,
                    result=None,
                    error="No plan provided for review",
                )

            # Build review prompt
            prompt = self._build_review_prompt(task, plan)

            # Call model
            result = await self._call_model(
                prompt=prompt,
                task_type="plan_review",
                complexity=task.complexity,
                risk=task.risk,
                working_dir=task.working_directory,
            )

            if not result.success:
                return AgentResponse(
                    success=False,
                    result=None,
                    error=result.error,
                )

            # Parse review from output
            review = self._parse_review(result.output)

            return AgentResponse(
                success=True,
                result=review,
                metadata={
                    "model": result.metadata.get("model") if result.metadata else None,
                    "raw_output": result.output,
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                result=None,
                error=f"Plan review failed: {str(e)}",
            )

    def _build_review_prompt(self, task: AgentTask, plan: Dict[str, Any]) -> str:
        """Build prompt for plan review.

        Args:
            task: Agent task
            plan: Plan to review

        Returns:
            Formatted review prompt
        """
        base_prompt = self._build_base_prompt(task)

        review_instructions = f"""

Your task is to review the implementation plan below for completeness and quality.

PLAN TO REVIEW:
{json.dumps(plan, indent=2)}

REVIEW CRITERIA:
1. Completeness - Are all necessary steps included?
2. Feasibility - Can these steps realistically be implemented?
3. Risk Assessment - Are risks properly identified?
4. Missing Steps - What critical steps are missing?
5. Order - Is the sequence logical and dependency-aware?
6. Testing - Are testing and validation steps included?
7. Quality - Will this plan maintain ZERO-WARNINGS policy?
8. Rollback - Is there a clear rollback strategy?

OUTPUT FORMAT (JSON):
{{
  "plan_id": "{plan.get("task_id", "unknown")}-v{plan.get("plan_version", 1)}",
  "status": "approved|rejected|needs_revision",
  "review": {{
    "completeness": 1-10,
    "feasibility": 1-10,
    "risk_assessment": 1-10,
    "missing_steps": ["step description 1", "step description 2"],
    "concerns": ["concern 1", "concern 2"],
    "suggestions": ["suggestion 1", "suggestion 2"]
  }},
  "required_changes": ["change 1", "change 2"],
  "optional_improvements": ["improvement 1", "improvement 2"]
}}

IMPORTANT:
- Be critical but constructive
- Different perspective than Planner (you're the second pair of eyes)
- Focus on catching omissions and unrealistic assumptions
- Ensure ZERO-WARNINGS compliance is addressed
- Check for proper error handling and validation steps

Now review the plan:
"""

        return base_prompt + review_instructions

    def _parse_review(self, output: str) -> Dict[str, Any]:
        """Parse review from model output.

        Args:
            output: Raw model output

        Returns:
            Parsed review dictionary
        """
        import re

        # Look for JSON code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", output, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON object
            json_match = re.search(r"\{.*\}", output, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # No JSON found, return structured error
                return {
                    "error": "Failed to parse review",
                    "raw_output": output,
                }

        try:
            review = json.loads(json_str)
            return review
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in review: {e}",
                "raw_output": output,
            }
