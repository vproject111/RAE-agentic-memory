"""Planner-Agent: Creates step-by-step implementation plans."""

import json
from typing import Any, Dict

from .base import AgentResponse, AgentTask, BaseAgent


class PlannerAgent(BaseAgent):
    """Agent responsible for creating implementation plans from tasks."""

    def __init__(self):
        """Initialize Planner-Agent."""
        super().__init__(name="Planner-Agent", role="planner")

    async def execute(self, task: AgentTask) -> AgentResponse:
        """Create a step-by-step plan for the task.

        Args:
            task: Task to create plan for

        Returns:
            Agent response with plan in JSON format
        """
        try:
            # Build planner prompt
            prompt = self._build_planner_prompt(task)

            # Call model
            result = await self._call_model(
                prompt=prompt,
                task_type="planning",
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

            # Parse plan from output
            plan = self._parse_plan(result.output)

            return AgentResponse(
                success=True,
                result=plan,
                metadata={
                    "model": result.metadata.get("model") if result.metadata else None,
                    "raw_output": result.output,
                },
            )

        except Exception as e:
            return AgentResponse(
                success=False,
                result=None,
                error=f"Planner execution failed: {str(e)}",
            )

    def _build_planner_prompt(self, task: AgentTask) -> str:
        """Build prompt for planning.

        Args:
            task: Agent task

        Returns:
            Formatted planning prompt
        """
        base_prompt = self._build_base_prompt(task)

        planning_instructions = """

Your task is to create a detailed, step-by-step implementation plan.

GUIDELINES:
1. Break down the task into concrete, actionable steps
2. Each step should be independent and testable
3. Include analysis, implementation, testing, and validation steps
4. Identify risks and dependencies for each step
5. Estimate complexity for each step
6. Specify files to create/modify

OUTPUT FORMAT (JSON):
{
  "task_id": "TASK-ID",
  "plan_version": 1,
  "steps": [
    {
      "id": "S1",
      "type": "analysis|implementation|testing|validation|docs",
      "description": "Clear description of what to do",
      "risk": "low|medium|high",
      "estimated_complexity": "trivial|small|medium|large",
      "files_to_read": ["path/to/file.py"],
      "files_to_create": ["path/to/new_file.py"],
      "files_to_modify": ["path/to/existing.py"],
      "tests_required": true|false,
      "commands": ["command to run"],
      "dependencies": ["S2", "S3"]
    }
  ],
  "estimated_duration": "estimate in hours",
  "dependencies": ["external dependency"],
  "rollback_strategy": "how to revert if needed"
}

IMPORTANT:
- Be thorough but practical
- Consider existing code patterns
- Ensure ZERO-WARNINGS policy compliance
- Include validation steps
- Plan for error handling

Now create the plan:
"""

        return base_prompt + planning_instructions

    def _parse_plan(self, output: str) -> Dict[str, Any]:
        """Parse plan from model output.

        Args:
            output: Raw model output

        Returns:
            Parsed plan dictionary
        """
        # Try to find JSON in output
        # Models often wrap JSON in markdown code blocks
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
                    "error": "Failed to parse plan",
                    "raw_output": output,
                }

        try:
            plan = json.loads(json_str)
            return plan
        except json.JSONDecodeError as e:
            return {
                "error": f"Invalid JSON in plan: {e}",
                "raw_output": output,
            }
